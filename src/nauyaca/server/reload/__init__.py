"""Hot-reload functionality for Nauyaca server.

This package provides automatic server restart when source files change,
inspired by uvicorn's reload functionality.

Features:
- Process-based restart for clean state on each reload
- Uses watchfiles for efficient OS-native file watching (if available)
- Falls back to polling when watchfiles is not installed
- Configurable watch directories and file extensions

Usage:
    CLI:
        nauyaca serve ./capsule --reload
        nauyaca serve ./capsule --reload --reload-dir ./src

    Programmatic:
        from pathlib import Path
        from nauyaca.server.reload import ReloadConfig, run_with_reload

        config = ReloadConfig(
            watch_dirs=[Path("./src"), Path("./capsule")],
            watch_extensions=[".py", ".gmi"],
        )
        run_with_reload(config, ["serve", "./capsule"])
"""

from .config import ReloadConfig
from .supervisor import Supervisor, run_with_reload
from .watcher import FileWatcher, PollingWatcher, WatchfilesWatcher

__all__ = [
    "ReloadConfig",
    "Supervisor",
    "run_with_reload",
    "FileWatcher",
    "WatchfilesWatcher",
    "PollingWatcher",
]
