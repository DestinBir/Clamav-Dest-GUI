from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from clamav_dest_gui.config import AppPaths, ScanState
from clamav_dest_gui.services.clamav import ClamAVService


BG = "#1a1a2e"
SURFACE = "#16213e"
SURFACE_2 = "#10192f"
CARD = "#0f3460"
ACCENT = "#e94560"
GREEN = "#4ecca3"
YELLOW = "#f5a623"
BLUE = "#5aa9ff"
TEXT = "#eaeaea"
MUTED = "#8892a4"
HIGHLIGHT = "#ffd166"
FONT_MAIN = ("Courier New", 11)
FONT_TITLE = ("Courier New", 18, "bold")
FONT_SUBTITLE = ("Courier New", 10, "bold")
FONT_LABEL = ("Courier New", 10)


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ClamAV Scanner")
        self.geometry("820x680")
        self.resizable(True, True)
        self.configure(bg=BG)

        self.paths = AppPaths()
        self.state = ScanState()

        self.disk_path = tk.StringVar()
        self.quarantine_path = tk.StringVar(value=str(self.paths.default_quarantine))
        self.use_sudo = tk.BooleanVar(value=True)
        self.infected_count = tk.IntVar(value=0)
        self.scanned_count = tk.IntVar(value=0)
        self.quarantine_ready = tk.StringVar(value="Yes")
        self.status_text = tk.StringVar(value="Idle")

        self.service = ClamAVService(self._schedule_log, self._schedule_counts)
        self.logo_image = self._load_logo()

        self._build_ui()

    def _build_ui(self):
        hero = tk.Frame(self, bg=BG)
        hero.pack(fill="x", padx=24, pady=(20, 14))

        hero_card = tk.Frame(hero, bg=SURFACE_2, highlightthickness=1, highlightbackground="#20304f")
        hero_card.pack(fill="x")

        hero_top = tk.Frame(hero_card, bg=SURFACE_2)
        hero_top.pack(fill="x", padx=18, pady=(18, 8))

        logo_frame = tk.Frame(hero_top, bg=SURFACE_2)
        logo_frame.pack(side="left", padx=(0, 16))
        if self.logo_image is not None:
            tk.Label(logo_frame, image=self.logo_image, bg=SURFACE_2).pack()
        else:
            tk.Label(
                logo_frame,
                text="CGA",
                font=("Courier New", 24, "bold"),
                bg=CARD,
                fg=HIGHLIGHT,
                width=5,
                height=2,
            ).pack()

        title_block = tk.Frame(hero_top, bg=SURFACE_2)
        title_block.pack(side="left", fill="x", expand=True)
        tk.Label(title_block, text="Code, Growth Alive", font=FONT_TITLE, bg=SURFACE_2, fg=TEXT).pack(anchor="w")
        tk.Label(
            title_block,
            text="Security desk for ClamAV scans, database refreshes, and quarantine control.",
            font=FONT_LABEL,
            bg=SURFACE_2,
            fg=MUTED,
        ).pack(anchor="w", pady=(4, 6))

        badges = tk.Frame(title_block, bg=SURFACE_2)
        badges.pack(anchor="w", pady=(0, 6))
        self._pill(badges, "Bukavu, Sud-Kivu", BLUE).pack(side="left", padx=(0, 8))
        self._pill(badges, "Founded 2023", GREEN).pack(side="left", padx=(0, 8))
        self._pill(badges, "Software + Multimedia + IT", YELLOW).pack(side="left")

        status_box = tk.Frame(hero_top, bg=SURFACE_2)
        status_box.pack(side="right", padx=(16, 0))
        tk.Label(status_box, text="SERVICE STATUS", font=FONT_SUBTITLE, bg=SURFACE_2, fg=MUTED).pack(anchor="e")
        status_row = tk.Frame(status_box, bg=SURFACE_2)
        status_row.pack(anchor="e", pady=(4, 0))
        self.status_dot = tk.Label(status_row, text="●", font=("Courier New", 14), bg=SURFACE_2, fg=MUTED)
        self.status_dot.pack(side="left", padx=(0, 4))
        tk.Label(status_row, textvariable=self.status_text, font=FONT_LABEL, bg=SURFACE_2, fg=TEXT).pack(side="left")

        hero_bottom = tk.Frame(hero_card, bg=SURFACE_2)
        hero_bottom.pack(fill="x", padx=18, pady=(0, 16))
        self._metric(hero_bottom, "Files Scanned", self.scanned_count, GREEN).pack(side="left", padx=(0, 10))
        self._metric(hero_bottom, "Infected Found", self.infected_count, ACCENT).pack(side="left", padx=(0, 10))
        self._metric(hero_bottom, "Quarantine Ready", self.quarantine_ready, BLUE).pack(side="left")

        config_card = tk.Frame(self, bg=SURFACE, relief="flat")
        config_card.pack(fill="x", padx=24, pady=(0, 12))

        self._section_label(config_card, "SCAN CONFIGURATION")
        self._path_row(config_card, "Disk to scan:", self.disk_path, self._browse_disk)
        self._path_row(config_card, "Quarantine folder:", self.quarantine_path, self._browse_quarantine)

        opts = tk.Frame(config_card, bg=SURFACE)
        opts.pack(fill="x", padx=16, pady=(4, 12))

        tk.Checkbutton(
            opts,
            text="Run with sudo (recommended)",
            variable=self.use_sudo,
            bg=SURFACE,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=SURFACE,
            activeforeground=TEXT,
            font=FONT_LABEL,
        ).pack(side="left")

        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=24, pady=(0, 12))

        self.btn_update = self._btn(actions, "Refresh DB", self._run_freshclam, YELLOW)
        self.btn_update.pack(side="left", padx=(0, 8))

        self.btn_scan = self._btn(actions, "Start Scan", self._start_scan, GREEN)
        self.btn_scan.pack(side="left", padx=(0, 8))

        self.btn_stop = self._btn(actions, "Stop", self._stop_scan, ACCENT)
        self.btn_stop.pack(side="left")
        self.btn_stop.configure(state="disabled")

        self.btn_quarantine = self._btn(actions, "Open Quarantine", self._open_quarantine, MUTED)
        self.btn_quarantine.pack(side="right")

        stats_frame = tk.Frame(self, bg=BG)
        stats_frame.pack(fill="x", padx=24, pady=(0, 12))

        self._stat_card(stats_frame, "Files Scanned", self.scanned_count, GREEN).pack(side="left", padx=(0, 8))
        self._stat_card(stats_frame, "Infected Found", self.infected_count, ACCENT).pack(side="left")
        self._info_card(stats_frame).pack(side="right", fill="both", expand=True, padx=(12, 0))

        log_card = tk.Frame(self, bg=SURFACE)
        log_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        log_header = tk.Frame(log_card, bg=SURFACE)
        log_header.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(log_header, text="SCAN LOG", font=("Courier New", 9, "bold"), bg=SURFACE, fg=MUTED).pack(side="left")
        self._btn(log_header, "Clear", self._clear_log, MUTED, small=True).pack(side="right")

        self.log = scrolledtext.ScrolledText(
            log_card,
            bg="#0a0a1a",
            fg=TEXT,
            font=FONT_MAIN,
            relief="flat",
            insertbackground=TEXT,
            selectbackground=CARD,
            wrap="word",
            state="disabled",
            bd=0,
            padx=12,
            pady=8,
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.log.tag_config("infected", foreground=ACCENT)
        self.log.tag_config("ok", foreground=GREEN)
        self.log.tag_config("info", foreground=YELLOW)
        self.log.tag_config("muted", foreground=MUTED)

        self.progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=SURFACE, background=GREEN, thickness=4)
        self.progress.pack(fill="x", padx=24, pady=(0, 16))

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Courier New", 9, "bold"), bg=SURFACE, fg=MUTED).pack(
            anchor="w", padx=16, pady=(10, 4)
        )

    def _pill(self, parent, text, color):
        return tk.Label(
            parent,
            text=text,
            font=("Courier New", 9, "bold"),
            bg=color,
            fg="#08111f",
            padx=10,
            pady=4,
        )

    def _metric(self, parent, label, var, color):
        frame = tk.Frame(parent, bg=SURFACE_2, highlightthickness=1, highlightbackground="#20304f")
        tk.Label(frame, text=label, font=FONT_SUBTITLE, bg=SURFACE_2, fg=MUTED).pack(padx=14, pady=(10, 0))
        tk.Label(frame, textvariable=var, font=("Courier New", 20, "bold"), bg=SURFACE_2, fg=color).pack(
            padx=18, pady=(0, 10)
        )
        return frame

    def _path_row(self, parent, label, var, cmd):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", padx=16, pady=3)
        tk.Label(row, text=label, font=FONT_LABEL, bg=SURFACE, fg=MUTED, width=18, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=var, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", font=FONT_LABEL, bd=4).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        self._btn(row, "Browse", cmd, MUTED, small=True).pack(side="right")

    def _btn(self, parent, text, cmd, color, small=False):
        font = ("Courier New", 9) if small else ("Courier New", 10, "bold")
        pad = (6, 3) if small else (14, 7)
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=color,
            fg="#0a0a1a",
            font=font,
            relief="flat",
            cursor="hand2",
            padx=pad[0],
            pady=pad[1],
            activebackground=color,
            activeforeground="#0a0a1a",
        )

    def _stat_card(self, parent, label, var, color):
        frame = tk.Frame(parent, bg=SURFACE, relief="flat")
        tk.Label(frame, text=label, font=("Courier New", 9), bg=SURFACE, fg=MUTED).pack(pady=(8, 0))
        tk.Label(frame, textvariable=var, font=("Courier New", 22, "bold"), bg=SURFACE, fg=color).pack(
            padx=24, pady=(0, 8)
        )
        return frame

    def _info_card(self, parent):
        frame = tk.Frame(parent, bg=SURFACE, relief="flat", highlightthickness=1, highlightbackground="#20304f")
        tk.Label(frame, text="Code, Growth Alive", font=FONT_SUBTITLE, bg=SURFACE, fg=TEXT).pack(anchor="w", padx=14, pady=(10, 2))
        tk.Label(
            frame,
            text="Software development, web presence, multimedia, and support services for teams and individuals.",
            font=FONT_LABEL,
            wraplength=280,
            justify="left",
            bg=SURFACE,
            fg=MUTED,
        ).pack(anchor="w", padx=14, pady=(0, 10))
        return frame

    def _load_logo(self):
        candidates = [
            Path(__file__).resolve().parents[2] / "company_logo.png",
            Path(__file__).resolve().parents[2] / "logo.png",
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    image = tk.PhotoImage(file=str(candidate))
                    target_width = 168
                    if image.width() > target_width:
                        factor = max(1, image.width() // target_width)
                        image = image.subsample(factor, factor)
                    return image
                except tk.TclError:
                    continue
        return None

    def _browse_disk(self):
        path = filedialog.askdirectory(title="Select disk/folder to scan")
        if path:
            self.disk_path.set(path)

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
        self.btn_stop.configure(state=state_off)
        if active:
            self.progress.start(12)
            self.status_text.set("Scanning...")
            self.status_dot.configure(fg=GREEN)
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
                self.service.update_database()
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
            messagebox.showwarning("Missing path", "Please select a disk/folder to scan.")
            return

        try:
            target_path = self.service.validate_target(disk)
        except FileNotFoundError as error:
            messagebox.showerror("Invalid path", str(error))
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
                self._schedule_log("ERROR: clamscan not found. Install ClamAV first.", "infected")
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