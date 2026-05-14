from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from clamav_dest_gui.config import AppPaths, ScanState
from clamav_dest_gui.services.clamav import ClamAVService, DiskTarget


BG = "#080d14"
PANEL = "#101722"
PANEL_2 = "#141d2b"
FIELD = "#0c121c"
BORDER = "#223044"
ACCENT = "#38bdf8"
ACCENT_2 = "#22c55e"
DANGER = "#fb7185"
WARNING = "#fbbf24"
TEXT = "#e5edf6"
MUTED = "#8b9aaf"
INK = "#050812"

FONT_MAIN = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_SECTION = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 10)


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ClamAV Dest GUI")
        self.geometry("1040x720")
        self.minsize(900, 620)
        self.configure(bg=BG)

        self.paths = AppPaths()
        self.state = ScanState()

        self.disk_path = tk.StringVar()
        self.disk_choice = tk.StringVar()
        self.quarantine_path = tk.StringVar(value=str(self.paths.default_quarantine))
        self.use_sudo = tk.BooleanVar(value=True)
        self.infected_count = tk.IntVar(value=0)
        self.scanned_count = tk.IntVar(value=0)
        self.quarantine_ready = tk.StringVar(value="Ready")
        self.status_text = tk.StringVar(value="Idle")

        self.disk_targets: list[DiskTarget] = []
        self.disk_labels: dict[str, DiskTarget] = {}

        self.service = ClamAVService(self._schedule_log, self._schedule_counts)
        self.logo_image = self._load_logo()

        self._configure_styles()
        self._build_ui()
        self._refresh_disks(log=False)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=FIELD, background=ACCENT_2, bordercolor=FIELD, thickness=5)
        style.configure(
            "Dark.TCombobox",
            fieldbackground=FIELD,
            background=PANEL_2,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(10, 6),
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", FIELD)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", FIELD)],
            selectforeground=[("readonly", TEXT)],
        )

    def _build_ui(self) -> None:
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True, padx=22, pady=20)

        self._build_header(shell)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True, pady=(16, 0))
        body.grid_columnconfigure(0, minsize=340, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._build_scan_panel(left)
        self._build_actions(left)
        self._build_log_panel(right)

        self.progress = ttk.Progressbar(shell, mode="indeterminate", style="TProgressbar")
        self.progress.pack(fill="x", pady=(14, 0))

    def _build_header(self, parent: tk.Widget) -> None:
        header = self._panel(parent, PANEL)
        header.pack(fill="x")
        header.grid_columnconfigure(1, weight=1)

        brand = tk.Frame(header, bg=PANEL)
        brand.grid(row=0, column=0, sticky="w", padx=18, pady=16)
        if self.logo_image is not None:
            tk.Label(brand, image=self.logo_image, bg=PANEL).pack(side="left", padx=(0, 14))
        else:
            tk.Label(brand, text="CGA", font=("Segoe UI", 18, "bold"), bg=ACCENT, fg=INK, padx=14, pady=10).pack(
                side="left", padx=(0, 14)
            )

        title = tk.Frame(brand, bg=PANEL)
        title.pack(side="left")
        tk.Label(title, text="ClamAV Dest GUI", font=FONT_TITLE, bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(
            title,
            text="Dark security console for disk scans, database updates, and quarantine control.",
            font=FONT_MAIN,
            bg=PANEL,
            fg=MUTED,
        ).pack(anchor="w", pady=(3, 0))

        status = tk.Frame(header, bg=PANEL)
        status.grid(row=0, column=1, sticky="e", padx=18, pady=16)
        tk.Label(status, text="STATUS", font=FONT_SMALL, bg=PANEL, fg=MUTED).pack(anchor="e")
        line = tk.Frame(status, bg=PANEL)
        line.pack(anchor="e", pady=(4, 0))
        self.status_dot = tk.Label(line, text="●", font=("Segoe UI", 14), bg=PANEL, fg=MUTED)
        self.status_dot.pack(side="left", padx=(0, 6))
        tk.Label(line, textvariable=self.status_text, font=FONT_SECTION, bg=PANEL, fg=TEXT).pack(side="left")

    def _build_scan_panel(self, parent: tk.Widget) -> None:
        panel = self._panel(parent, PANEL)
        panel.pack(fill="x")

        self._section_title(panel, "Scan Target")
        tk.Label(
            panel,
            text="Choose a mounted disk or partition. Refresh rescans the system mount list.",
            font=FONT_SMALL,
            bg=PANEL,
            fg=MUTED,
            wraplength=280,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 10))

        disk_row = tk.Frame(panel, bg=PANEL)
        disk_row.pack(fill="x", padx=16, pady=(0, 12))
        self.disk_combo = ttk.Combobox(
            disk_row,
            textvariable=self.disk_choice,
            values=[],
            state="readonly",
            style="Dark.TCombobox",
            font=FONT_MAIN,
        )
        self.disk_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.disk_combo.bind("<<ComboboxSelected>>", self._on_disk_selected)
        self.btn_refresh_disks = self._icon_btn(disk_row, "↻", self._refresh_disks, ACCENT)
        self.btn_refresh_disks.pack(side="right")

        self.selected_disk = tk.Label(panel, textvariable=self.disk_path, font=FONT_SMALL, bg=PANEL, fg=ACCENT)
        self.selected_disk.pack(anchor="w", padx=16, pady=(0, 16))

        self._section_title(panel, "Quarantine")
        self._path_row(panel, "Folder", self.quarantine_path, self._browse_quarantine)

        opts = tk.Frame(panel, bg=PANEL)
        opts.pack(fill="x", padx=16, pady=(8, 14))
        tk.Checkbutton(
            opts,
            text="Run privileged commands with sudo",
            variable=self.use_sudo,
            bg=PANEL,
            fg=TEXT,
            selectcolor=FIELD,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=FONT_MAIN,
            relief="flat",
        ).pack(anchor="w")

        metrics = tk.Frame(panel, bg=PANEL)
        metrics.pack(fill="x", padx=16, pady=(2, 16))
        for column in (0, 1):
            metrics.grid_columnconfigure(column, weight=1, uniform="metric")
        self._metric(metrics, "Scanned", self.scanned_count, ACCENT_2).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._metric(metrics, "Infected", self.infected_count, DANGER).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_actions(self, parent: tk.Widget) -> None:
        panel = self._panel(parent, PANEL)
        panel.pack(fill="x", pady=(14, 0))
        self._section_title(panel, "Actions")

        self.btn_scan = self._btn(panel, "Start Scan", self._start_scan, ACCENT_2)
        self.btn_scan.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_update = self._btn(panel, "Refresh Virus Database", self._run_freshclam, WARNING)
        self.btn_update.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_stop = self._btn(panel, "Stop Scan", self._stop_scan, DANGER)
        self.btn_stop.pack(fill="x", padx=16, pady=(0, 8))
        self.btn_stop.configure(state="disabled")

        self.btn_quarantine = self._btn(panel, "Open Quarantine", self._open_quarantine, BORDER, fg=TEXT)
        self.btn_quarantine.pack(fill="x", padx=16, pady=(0, 16))

    def _build_log_panel(self, parent: tk.Widget) -> None:
        toolbar = self._panel(parent, PANEL)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        tk.Label(toolbar, text="Scan Log", font=("Segoe UI", 14, "bold"), bg=PANEL, fg=TEXT).grid(
            row=0, column=0, sticky="w", padx=16, pady=13
        )
        self._btn(toolbar, "Clear", self._clear_log, BORDER, small=True, fg=TEXT).grid(
            row=0, column=1, sticky="e", padx=16, pady=12
        )

        log_panel = self._panel(parent, PANEL)
        log_panel.grid(row=1, column=0, sticky="nsew")
        self.log = scrolledtext.ScrolledText(
            log_panel,
            bg=FIELD,
            fg=TEXT,
            font=FONT_MONO,
            relief="flat",
            insertbackground=TEXT,
            selectbackground="#1f3b57",
            wrap="word",
            state="disabled",
            bd=0,
            padx=14,
            pady=12,
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=12)

        self.log.tag_config("infected", foreground=DANGER)
        self.log.tag_config("ok", foreground=ACCENT_2)
        self.log.tag_config("info", foreground=WARNING)
        self.log.tag_config("muted", foreground=MUTED)

    def _panel(self, parent: tk.Widget, bg: str) -> tk.Frame:
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)

    def _section_title(self, parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text.upper(), font=FONT_SECTION, bg=PANEL, fg=MUTED).pack(
            anchor="w", padx=16, pady=(14, 8)
        )

    def _metric(self, parent: tk.Widget, label: str, var: tk.Variable, color: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL_2, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(frame, text=label, font=FONT_SMALL, bg=PANEL_2, fg=MUTED).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(frame, textvariable=var, font=("Segoe UI", 20, "bold"), bg=PANEL_2, fg=color).pack(
            anchor="w", padx=12, pady=(0, 10)
        )
        return frame

    def _path_row(self, parent: tk.Widget, label: str, var: tk.StringVar, cmd) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(row, text=label, font=FONT_SMALL, bg=PANEL, fg=MUTED).pack(anchor="w")
        line = tk.Frame(row, bg=PANEL)
        line.pack(fill="x", pady=(5, 0))
        tk.Entry(
            line,
            textvariable=var,
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=FONT_MAIN,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        ).pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self._btn(line, "Browse", cmd, BORDER, small=True, fg=TEXT).pack(side="right")

    def _btn(self, parent: tk.Widget, text: str, cmd, color: str, small: bool = False, fg: str = INK) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=color,
            fg=fg,
            font=FONT_SMALL if small else FONT_SECTION,
            relief="flat",
            cursor="hand2",
            padx=10 if small else 16,
            pady=5 if small else 10,
            activebackground=color,
            activeforeground=fg,
            disabledforeground="#5b6675",
            bd=0,
        )

    def _icon_btn(self, parent: tk.Widget, text: str, cmd, color: str) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=color,
            fg=INK,
            font=("Segoe UI", 15, "bold"),
            relief="flat",
            cursor="hand2",
            width=3,
            pady=2,
            activebackground=color,
            activeforeground=INK,
            bd=0,
        )

    def _load_logo(self):
        candidates = [
            Path(__file__).resolve().parents[2] / "company_logo.png",
            Path(__file__).resolve().parents[2] / "logo.png",
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    image = tk.PhotoImage(file=str(candidate))
                    target_width = 72
                    if image.width() > target_width:
                        factor = max(1, image.width() // target_width)
                        image = image.subsample(factor, factor)
                    return image
                except tk.TclError:
                    continue
        return None

    def _refresh_disks(self, log: bool = True) -> None:
        self.disk_targets = self.service.list_scan_targets()
        self.disk_labels = {target.label: target for target in self.disk_targets}
        labels = list(self.disk_labels)
        self.disk_combo.configure(values=labels)

        current_path = self.disk_path.get()
        selected = next((label for label, target in self.disk_labels.items() if str(target.path) == current_path), "")
        if not selected and labels:
            selected = labels[0]

        if selected:
            self.disk_choice.set(selected)
            self._set_selected_disk(self.disk_labels[selected])
        else:
            self.disk_choice.set("")
            self.disk_path.set("")

        if log:
            self._log(f"Disk list refreshed: {len(labels)} target(s) available.", "info")

    def _set_selected_disk(self, target: DiskTarget) -> None:
        self.disk_path.set(str(target.path))

    def _on_disk_selected(self, _event=None) -> None:
        target = self.disk_labels.get(self.disk_choice.get())
        if target is not None:
            self._set_selected_disk(target)

    def _browse_quarantine(self):
        path = filedialog.askdirectory(title="Select quarantine folder")
        if path:
            self.quarantine_path.set(path)

    def _open_quarantine(self):
        self.service.open_directory(self.quarantine_path.get())

    def _schedule_log(self, message: str, tag: str | None = None) -> None:
        self.after(0, self._log, message, tag)

    def _schedule_counts(self, scanned: int, infected: int) -> None:
        self.after(0, self._update_counts, scanned, infected)

    def _log(self, msg, tag=None):
        self.log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n", tag or "")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _set_scanning(self, active):
        self.state.is_running = active
        state_on = "disabled" if active else "normal"
        state_off = "normal" if active else "disabled"
        self.btn_scan.configure(state=state_on)
        self.btn_update.configure(state=state_on)
        self.btn_refresh_disks.configure(state=state_on)
        self.btn_stop.configure(state=state_off)
        if active:
            self.progress.start(12)
            self.status_text.set("Working")
            self.status_dot.configure(fg=ACCENT_2)
        else:
            self.progress.stop()
            self.status_text.set("Idle")
            self.status_dot.configure(fg=MUTED)

    def _update_counts(self, scanned: int, infected: int) -> None:
        self.state.scanned_files = scanned
        self.state.infected_files = infected
        self.scanned_count.set(scanned)
        self.infected_count.set(infected)

    def _run_freshclam(self):
        def task():
            try:
                self.after(0, self._set_scanning, True)
                self.service.update_database(self.use_sudo.get())
            except FileNotFoundError:
                self._schedule_log("ERROR: freshclam or sudo not found. Install ClamAV first.", "infected")
            except Exception as error:
                self._schedule_log(f"ERROR: {error}", "infected")
            finally:
                self.after(0, self._set_scanning, False)

        threading.Thread(target=task, daemon=True).start()

    def _start_scan(self):
        disk = self.disk_path.get().strip()
        quarantine = self.quarantine_path.get().strip()

        if not disk:
            messagebox.showwarning("Missing disk", "Select a disk from the list first.")
            return

        try:
            target_path = self.service.validate_target(disk)
        except FileNotFoundError as error:
            messagebox.showerror("Invalid disk", str(error))
            self._refresh_disks()
            return

        command = self.service.build_scan_command(str(target_path), quarantine, self.use_sudo.get())

        self._update_counts(0, 0)
        self._set_scanning(True)
        self._log(f"Starting scan on: {command.target}", "info")
        self._log(f"Quarantine: {command.quarantine}", "info")

        def task():
            try:
                self.service.start_scan(command)
            except FileNotFoundError:
                self._schedule_log("ERROR: clamscan or sudo not found. Install ClamAV first.", "infected")
            except Exception as error:
                self._schedule_log(f"ERROR: {error}", "infected")
            finally:
                self.after(0, self._set_scanning, False)

        threading.Thread(target=task, daemon=True).start()

    def _stop_scan(self):
        self.service.stop_scan()
        self._set_scanning(False)


def build_app() -> MainWindow:
    return MainWindow()
