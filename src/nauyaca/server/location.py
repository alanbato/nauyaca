"""Location-based configuration for Gemini server.

This module provides location configuration for routing different URL paths
to different handlers (static, proxy, cgi, etc.).
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class HandlerType(Enum):
    """Types of request handlers for locations."""

    STATIC = auto()  # StaticFileHandler - serve static files
    PROXY = auto()  # ProxyHandler - forward to upstream
    # Future handler types:
    # CGI = auto()      # CGIHandler - execute scripts
    # FASTCGI = auto()  # FastCGIHandler - FastCGI protocol


@dataclass
class LocationConfig:
    """Configuration for a location block.

    Locations define how different URL paths are handled by the server.
    Each location has a prefix pattern and a handler configuration.

    Attributes:
        prefix: URL path prefix to match (e.g., "/api/", "/").
        handler_type: Type of handler for this location.
        document_root: For static handler - directory to serve files from.
        enable_directory_listing: For static handler - allow directory listings.
        upstream: For proxy handler - upstream server URL.
        strip_prefix: For proxy handler - remove prefix before forwarding.
        timeout: For proxy handler - request timeout in seconds.

    Examples:
        >>> # Static file location
        >>> static_loc = LocationConfig(
        ...     prefix="/",
        ...     handler_type=HandlerType.STATIC,
        ...     document_root=Path("./capsule"),
        ... )

        >>> # Proxy location
        >>> proxy_loc = LocationConfig(
        ...     prefix="/api/",
        ...     handler_type=HandlerType.PROXY,
        ...     upstream="gemini://backend:1965",
        ...     strip_prefix=True,
        ... )
    """

    # Matching
    prefix: str

    # Handler type
    handler_type: HandlerType

    # Static handler settings
    document_root: Path | None = None
    enable_directory_listing: bool = False
    default_indices: list[str] = field(
        default_factory=lambda: ["index.gmi", "index.gemini"]
    )
    max_file_size: int | None = None

    # Proxy handler settings
    upstream: str | None = None
    strip_prefix: bool = False
    timeout: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Ensure prefix starts with /
        if not self.prefix.startswith("/"):
            self.prefix = "/" + self.prefix

        # Validate handler-specific requirements
        if self.handler_type == HandlerType.STATIC:
            if self.document_root is None:
                raise ValueError(
                    f"Location '{self.prefix}': static handler requires document_root"
                )
            # Convert to Path if string
            if isinstance(self.document_root, str):
                self.document_root = Path(self.document_root)
            # Validate document_root exists and is a directory
            if not self.document_root.exists():
                raise ValueError(
                    f"Location '{self.prefix}': document_root does not exist: "
                    f"{self.document_root}"
                )
            if not self.document_root.is_dir():
                raise ValueError(
                    f"Location '{self.prefix}': document_root is not a directory: "
                    f"{self.document_root}"
                )

        elif self.handler_type == HandlerType.PROXY:
            if self.upstream is None:
                raise ValueError(
                    f"Location '{self.prefix}': proxy handler requires upstream"
                )
            if not self.upstream.startswith("gemini://"):
                raise ValueError(
                    f"Location '{self.prefix}': upstream must use gemini:// scheme"
                )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocationConfig":
        """Create LocationConfig from a dictionary (e.g., from TOML).

        Args:
            data: Dictionary with location configuration.

        Returns:
            LocationConfig instance.

        Raises:
            ValueError: If configuration is invalid.

        Examples:
            >>> config = LocationConfig.from_dict({
            ...     "prefix": "/api/",
            ...     "handler": "proxy",
            ...     "upstream": "gemini://backend:1965",
            ...     "strip_prefix": True,
            ... })
        """
        handler_str = data.get("handler", "static").lower()

        handler_map = {
            "static": HandlerType.STATIC,
            "proxy": HandlerType.PROXY,
        }

        handler_type = handler_map.get(handler_str)
        if handler_type is None:
            raise ValueError(f"Unknown handler type: {handler_str}")

        # Convert document_root to Path if present
        doc_root = data.get("document_root")
        if doc_root is not None:
            doc_root = Path(doc_root)

        return cls(
            prefix=data.get("prefix", "/"),
            handler_type=handler_type,
            # Static handler settings
            document_root=doc_root,
            enable_directory_listing=data.get("enable_directory_listing", False),
            default_indices=data.get("default_indices", ["index.gmi", "index.gemini"]),
            max_file_size=data.get("max_file_size"),
            # Proxy handler settings
            upstream=data.get("upstream"),
            strip_prefix=data.get("strip_prefix", False),
            timeout=data.get("timeout", 30.0),
        )
