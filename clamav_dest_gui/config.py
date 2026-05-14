from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppPaths:
    default_quarantine: Path = field(default_factory=lambda: Path.home() / "Quarantaine_ClamAV")


@dataclass(slots=True)
class ScanState:
    scanned_files: int = 0
    infected_files: int = 0
    is_running: bool = False