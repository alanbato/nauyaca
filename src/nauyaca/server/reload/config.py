"""Configuration for hot-reload functionality.

This module provides configuration data structures for the hot-reload feature.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReloadConfig:
    """Configuration for server hot-reload.

    Attributes:
        watch_dirs: Directories to watch for changes.
        watch_extensions: File extensions to watch (e.g., ['.py', '.toml']).
        polling_interval: Interval in seconds for polling watcher (when watchfiles
            unavailable).

    Examples:
        >>> config = ReloadConfig(
        ...     watch_dirs=[Path("./src"), Path("./capsule")],
        ...     watch_extensions=[".py", ".gmi"],
        ... )
    """

    watch_dirs: list[Path] = field(default_factory=list)
    watch_extensions: list[str] = field(default_factory=lambda: [".py", ".gmi"])
    polling_interval: float = 1.0

    def __post_init__(self) -> None:
        """Validate and normalize configuration."""
        if not self.watch_dirs:
            raise ValueError("watch_dirs cannot be empty")

        # Normalize and resolve paths
        resolved_dirs: list[Path] = []
        for watch_dir in self.watch_dirs:
            resolved = Path(watch_dir).resolve()
            if not resolved.exists():
                raise ValueError(f"Watch directory does not exist: {watch_dir}")
            if not resolved.is_dir():
                raise ValueError(f"Watch path is not a directory: {watch_dir}")
            resolved_dirs.append(resolved)

        self.watch_dirs = resolved_dirs

        # Normalize extensions to lowercase with leading dot
        self.watch_extensions = [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in self.watch_extensions
        ]

    def should_watch_file(self, path: Path) -> bool:
        """Check if a file should trigger reload.

        Args:
            path: File path to check.

        Returns:
            True if file extension matches watch_extensions.
        """
        return path.suffix.lower() in self.watch_extensions
