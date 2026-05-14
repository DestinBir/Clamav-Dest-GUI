from __future__ import annotations

from dataclasses import dataclass
import json
import os
import subprocess
from pathlib import Path
from typing import Callable


LogCallback = Callable[[str, str | None], None]
CountCallback = Callable[[int, int], None]


@dataclass(slots=True)
class ScanCommand:
    command: list[str]
    quarantine: Path
    target: Path


@dataclass(frozen=True, slots=True)
class DiskTarget:
    name: str
    path: Path
    size: str = ""
    filesystem: str = ""
    removable: bool = False

    @property
    def label(self) -> str:
        details = [str(self.path)]
        if self.size:
            details.append(self.size)
        if self.filesystem:
            details.append(self.filesystem)
        if self.removable:
            details.append("removable")
        return f"{self.name}  -  {'  -  '.join(details)}"


class ClamAVService:
    def __init__(self, log: LogCallback, counts_changed: CountCallback):
        self._log = log
        self._counts_changed = counts_changed
        self._process: subprocess.Popen[str] | None = None
        self._stop_requested = False

    @property
    def process(self) -> subprocess.Popen[str] | None:
        return self._process

    def open_directory(self, path: str) -> None:
        if not os.path.isdir(path):
            self._log(f"Directory does not exist: {path}", "infected")
            return
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError:
            self._log("xdg-open is not available on this system.", "infected")

    def list_scan_targets(self) -> list[DiskTarget]:
        targets = self._targets_from_lsblk()
        if not targets:
            targets = self._targets_from_mounts()

        root = DiskTarget(name="System root", path=Path("/"))
        unique: dict[Path, DiskTarget] = {root.path: root}
        for target in targets:
            unique.setdefault(target.path, target)
        return sorted(unique.values(), key=lambda item: (str(item.path) != "/", str(item.path).lower()))

    def update_database(self, use_sudo: bool = True) -> None:
        prefix = ["sudo"] if use_sudo else []
        self._log("Preparing ClamAV signature update...", "info")
        self._run_optional(prefix + ["systemctl", "stop", "clamav-freshclam"])
        self._log("Running freshclam update...", "info")
        proc = subprocess.Popen(
            prefix + ["freshclam"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._stream_output(proc, tag="muted")
        return_code = proc.wait()
        self._run_optional(prefix + ["systemctl", "start", "clamav-freshclam"])
        if return_code == 0:
            self._log("Database update complete.", "ok")
        else:
            self._log(f"freshclam finished with exit code {return_code}. Check the output above.", "infected")

    def start_scan(self, command: ScanCommand) -> None:
        self._stop_requested = False
        self._process = subprocess.Popen(
            command.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        infected_files = 0
        scanned_files = 0
        in_summary = False

        assert self._process.stdout is not None
        for raw_line in self._process.stdout:
            line = raw_line.rstrip()
            if not line:
                continue

            if "SCAN SUMMARY" in line:
                in_summary = True
                self._log("─── SCAN SUMMARY ───", "info")
                continue

            if in_summary:
                self._log(line, "info")
                if "Scanned files:" in line:
                    scanned_files = self._parse_trailing_int(line, scanned_files)
                    self._counts_changed(scanned_files, infected_files)
                if "Infected files:" in line:
                    infected_files = self._parse_trailing_int(line, infected_files)
                    self._counts_changed(scanned_files, infected_files)
            else:
                self._log(line, "infected" if "FOUND" in line else "muted")

        return_code = self._process.wait()
        if self._stop_requested or return_code < 0:
            self._log("Scan stopped before completion.", "info")
        elif infected_files == 0 and return_code == 0:
            self._log("✔ No threats found. Disk is clean.", "ok")
        else:
            if infected_files > 0:
                self._log(f"⚠ {infected_files} infected file(s) moved to quarantine.", "infected")
            else:
                self._log(f"Scan finished with exit code {return_code}. Check the output above.", "infected")
        self._process = None

    def stop_scan(self) -> None:
        if self._process:
            self._stop_requested = True
            self._process.terminate()
            self._log("Scan stopped by user.", "info")

    def build_scan_command(self, target: str, quarantine: str, use_sudo: bool) -> ScanCommand:
        target_path = Path(target).expanduser().resolve()
        quarantine_path = Path(quarantine).expanduser().resolve()
        quarantine_path.mkdir(parents=True, exist_ok=True)

        command: list[str] = []
        if use_sudo:
            command.append("sudo")
        command += ["clamscan", "-r", "-i", f"--move={quarantine_path}", str(target_path)]
        return ScanCommand(command=command, quarantine=quarantine_path, target=target_path)

    def validate_target(self, target: str) -> Path:
        target_path = Path(target).expanduser()
        if not target_path.is_dir():
            raise FileNotFoundError(f"Path does not exist: {target}")
        return target_path.resolve()

    def _stream_output(self, proc: subprocess.Popen[str], tag: str) -> None:
        if proc.stdout is None:
            return
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if line:
                self._log(line, tag)

    @staticmethod
    def _parse_trailing_int(line: str, fallback: int) -> int:
        try:
            return int(line.split(":")[-1].strip())
        except ValueError:
            return fallback

    @staticmethod
    def _run_optional(command: list[str]) -> None:
        try:
            subprocess.run(command, capture_output=True, check=False)
        except FileNotFoundError:
            return

    @staticmethod
    def _targets_from_lsblk() -> list[DiskTarget]:
        try:
            proc = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,LABEL,MOUNTPOINTS,SIZE,TYPE,FSTYPE,RM"],
                capture_output=True,
                check=False,
                text=True,
            )
        except FileNotFoundError:
            return []

        if proc.returncode != 0 or not proc.stdout:
            return []

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return []

        targets: list[DiskTarget] = []

        def visit(device: dict, parent_name: str = "") -> None:
            name = device.get("label") or device.get("name") or parent_name or "Disk"
            mountpoints = device.get("mountpoints") or []
            if isinstance(mountpoints, str):
                mountpoints = [mountpoints]

            for mountpoint in mountpoints:
                if mountpoint:
                    targets.append(
                        DiskTarget(
                            name=str(name),
                            path=Path(mountpoint),
                            size=str(device.get("size") or ""),
                            filesystem=str(device.get("fstype") or ""),
                            removable=bool(device.get("rm")),
                        )
                    )

            for child in device.get("children") or []:
                visit(child, str(name))

        for block_device in data.get("blockdevices", []):
            visit(block_device)
        return targets

    @staticmethod
    def _targets_from_mounts() -> list[DiskTarget]:
        targets: list[DiskTarget] = []
        try:
            with Path("/proc/mounts").open(encoding="utf-8") as mounts:
                for line in mounts:
                    parts = line.split()
                    if len(parts) < 3:
                        continue
                    source, mountpoint, filesystem = parts[:3]
                    if source.startswith(("/dev/", "UUID=", "LABEL=")):
                        targets.append(DiskTarget(name=Path(source).name, path=Path(mountpoint), filesystem=filesystem))
        except OSError:
            return []
        return targets
