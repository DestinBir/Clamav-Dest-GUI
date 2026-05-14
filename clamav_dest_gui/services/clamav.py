from __future__ import annotations

from dataclasses import dataclass
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


class ClamAVService:
    def __init__(self, log: LogCallback, counts_changed: CountCallback):
        self._log = log
        self._counts_changed = counts_changed
        self._process: subprocess.Popen[str] | None = None

    @property
    def process(self) -> subprocess.Popen[str] | None:
        return self._process

    def open_directory(self, path: str) -> None:
        if os.path.isdir(path):
            subprocess.Popen(["xdg-open", path])

    def update_database(self) -> None:
        self._log("Stopping clamav-freshclam service...", "info")
        subprocess.run(["sudo", "systemctl", "stop", "clamav-freshclam"], capture_output=True)
        self._log("Running freshclam update...", "info")
        proc = subprocess.Popen(
            ["sudo", "freshclam"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._stream_output(proc, tag="muted")
        proc.wait()
        subprocess.run(["sudo", "systemctl", "start", "clamav-freshclam"], capture_output=True)
        self._log("Database update complete. Service restarted.", "ok")

    def start_scan(self, command: ScanCommand) -> None:
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

        self._process.wait()
        if infected_files == 0:
            self._log("✔ No threats found. Disk is clean.", "ok")
        else:
            self._log(f"⚠ {infected_files} infected file(s) moved to quarantine.", "infected")
        self._process = None

    def stop_scan(self) -> None:
        if self._process:
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