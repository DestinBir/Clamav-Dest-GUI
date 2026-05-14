from __future__ import annotations

from clamav_dest_gui.ui.main_window import build_app


def main() -> int:
    app = build_app()
    app.mainloop()
    return 0