"""File watching implementations for hot-reload.

This module provides file watching abstractions with two implementations:
- WatchfilesWatcher: Fast, OS-native watching using the watchfiles library
- PollingWatcher: Fallback polling-based watching that works everywhere
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from ...utils.logging import get_logger

if TYPE_CHECKING:
    from .config import ReloadConfig

logger = get_logger(__name__)


class FileWatcher(ABC):
    """Abstract base class for file watchers.

    File watchers monitor directories and return changed files when detected.
    """

    def __init__(self, config: "ReloadConfig") -> None:
        """Initialize watcher.

        Args:
            config: Reload configuration.
        """
        self.config = config

    @abstractmethod
    def wait_for_changes(self) -> list[Path]:
        """Wait for file changes.

        Blocks until changes are detected, then returns the changed files.

        Returns:
            List of changed file paths.
        """
        ...

    @staticmethod
    def create(config: "ReloadConfig") -> "FileWatcher":
        """Factory method to create appropriate watcher.

        Attempts to use WatchfilesWatcher for best performance,
        falls back to PollingWatcher if watchfiles is not available.

        Args:
            config: Reload configuration.

        Returns:
            FileWatcher instance.
        """
        try:
            from watchfiles import watch  # noqa: F401

            logger.info("file_watcher_created", backend="watchfiles")
            return WatchfilesWatcher(config)
        except ImportError:
            logger.warning(
                "watchfiles_not_available",
                fallback="polling",
                hint="pip install watchfiles",
            )
            return PollingWatcher(config)


class WatchfilesWatcher(FileWatcher):
    """File watcher using the watchfiles library.

    This provides efficient, platform-native file watching using inotify (Linux),
    FSEvents (macOS), or ReadDirectoryChangesW (Windows).
    """

    def wait_for_changes(self) -> list[Path]:
        """Wait for file changes using watchfiles.

        Returns:
            List of changed file paths.
        """
        from watchfiles import watch

        watch_paths = [str(d) for d in self.config.watch_dirs]

        logger.debug(
            "watching_for_changes",
            watch_dirs=watch_paths,
            extensions=self.config.watch_extensions,
        )

        # watch() yields sets of (change_type, path) tuples
        # We only need the first set of changes
        for changes in watch(*watch_paths):
            changed_files: list[Path] = []
            filtered_count = 0

            for _change_type, path_str in changes:
                path = Path(path_str)

                # Filter by extension
                if self.config.should_watch_file(path):
                    changed_files.append(path)
                else:
                    filtered_count += 1

            if changed_files:
                logger.debug(
                    "changes_detected",
                    matched=len(changed_files),
                    filtered=filtered_count,
                    files=[str(f) for f in changed_files[:3]],
                )
                return changed_files
            elif filtered_count > 0:
                logger.debug(
                    "changes_filtered",
                    filtered=filtered_count,
                    extensions=self.config.watch_extensions,
                )

        return []  # Should not reach here


class PollingWatcher(FileWatcher):
    """Polling-based file watcher.

    Periodically scans directories for file modification time changes.
    Less efficient than WatchfilesWatcher but works everywhere without
    external dependencies.
    """

    def __init__(self, config: "ReloadConfig") -> None:
        """Initialize polling watcher.

        Args:
            config: Reload configuration.
        """
        super().__init__(config)
        self._file_mtimes: dict[Path, float] = self._scan_files()
        logger.debug(
            "polling_watcher_initialized",
            tracked_files=len(self._file_mtimes),
            extensions=self.config.watch_extensions,
        )

    def _scan_files(self) -> dict[Path, float]:
        """Scan all watched files and record modification times.

        Returns:
            Dictionary mapping file paths to modification times.
        """
        mtimes: dict[Path, float] = {}

        for watch_dir in self.config.watch_dirs:
            if not watch_dir.exists():
                continue

            for path in watch_dir.rglob("*"):
                if path.is_file() and self.config.should_watch_file(path):
                    try:
                        mtimes[path] = path.stat().st_mtime
                    except OSError:
                        # File might have been deleted between rglob and stat
                        pass

        return mtimes

    def wait_for_changes(self) -> list[Path]:
        """Wait for file changes using polling.

        Returns:
            List of changed file paths.
        """
        import time

        logger.debug(
            "polling_for_changes",
            watch_dirs=[str(d) for d in self.config.watch_dirs],
            interval=self.config.polling_interval,
        )

        while True:
            time.sleep(self.config.polling_interval)

            current_mtimes = self._scan_files()
            changed_files: list[Path] = []

            # Check for new or modified files
            for path, mtime in current_mtimes.items():
                old_mtime = self._file_mtimes.get(path)
                if old_mtime is None or old_mtime != mtime:
                    changed_files.append(path)

            # Check for deleted files (optional, but good for completeness)
            for path in self._file_mtimes:
                if path not in current_mtimes:
                    changed_files.append(path)

            # Update tracked state
            self._file_mtimes = current_mtimes

            if changed_files:
                logger.debug(
                    "changes_detected",
                    matched=len(changed_files),
                    files=[str(f) for f in changed_files[:3]],
                )
                return changed_files
