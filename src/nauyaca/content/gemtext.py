"""Gemtext content generation utilities.

This module provides functions for generating gemtext content,
including directory listings and formatted text.
"""

from pathlib import Path


def generate_directory_listing(directory: Path, base_path: str = "/") -> str:
    """Generate a gemtext directory listing.

    Args:
        directory: Path to the directory to list.
        base_path: Base URL path for generating links (default: "/").

    Returns:
        A gemtext-formatted directory listing.

    Examples:
        >>> from pathlib import Path
        >>> listing = generate_directory_listing(Path("/tmp"))
        >>> "# Index of" in listing
        True
    """
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    # Normalize base_path to end with /
    if not base_path.endswith("/"):
        base_path += "/"

    lines = [
        f"# Index of {base_path}",
        "",
    ]

    # Add parent directory link if not at root
    if base_path != "/":
        parent_path = str(Path(base_path).parent)
        if not parent_path.endswith("/"):
            parent_path += "/"
        lines.append(f"=> {parent_path} ..")
        lines.append("")

    # Get all items in directory, sort with directories first
    items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))

    if not items:
        lines.append("(empty directory)")
        return "\n".join(lines)

    # Add entries
    for item in items:
        if item.is_dir():
            # Directory entry
            link_path = base_path + item.name + "/"
            lines.append(f"=> {link_path} {item.name}/")
        else:
            # File entry
            link_path = base_path + item.name
            # Add file size in human-readable format
            size = _format_file_size(item.stat().st_size)
            lines.append(f"=> {link_path} {item.name} ({size})")

    return "\n".join(lines)


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Formatted file size string (e.g., "1.5 KB", "2.3 MB").
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            if size_bytes < 10 and unit != "B":
                return f"{size_bytes:.1f} {unit}"
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
