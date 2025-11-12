"""Server configuration for Gemini server.

This module provides configuration data structures for the Gemini server.
"""

from dataclasses import dataclass
from pathlib import Path

from ..protocol.constants import DEFAULT_PORT


@dataclass
class ServerConfig:
    """Configuration for Gemini server.

    Attributes:
        host: Server host address (default: "localhost").
        port: Server port (default: 1965).
        document_root: Path to directory containing files to serve.
        certfile: Path to TLS certificate file.
        keyfile: Path to TLS private key file.

    Examples:
        >>> config = ServerConfig(
        ...     host="localhost",
        ...     port=1965,
        ...     document_root=Path("/var/gemini/capsule"),
        ...     certfile=Path("/etc/gemini/cert.pem"),
        ...     keyfile=Path("/etc/gemini/key.pem")
        ... )
    """

    host: str = "localhost"
    port: int = DEFAULT_PORT
    document_root: Path | str = "."
    certfile: Path | str | None = None
    keyfile: Path | str | None = None

    def __post_init__(self):
        """Validate and normalize configuration after initialization."""
        # Convert string paths to Path objects
        if isinstance(self.document_root, str):
            self.document_root = Path(self.document_root)

        if isinstance(self.certfile, str):
            self.certfile = Path(self.certfile)

        if isinstance(self.keyfile, str):
            self.keyfile = Path(self.keyfile)

        # Validate document root
        if not self.document_root.exists():
            raise ValueError(f"Document root does not exist: {self.document_root}")

        if not self.document_root.is_dir():
            raise ValueError(f"Document root is not a directory: {self.document_root}")

        # Validate certificate files if provided
        if self.certfile and not self.certfile.exists():
            raise ValueError(f"Certificate file does not exist: {self.certfile}")

        if self.keyfile and not self.keyfile.exists():
            raise ValueError(f"Key file does not exist: {self.keyfile}")

        # Validate port range
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port number: {self.port} (must be 1-65535)")

    def validate(self) -> None:
        """Validate the server configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        # Additional runtime validation can be added here
        if (self.certfile is None) != (self.keyfile is None):
            raise ValueError(
                "Both certfile and keyfile must be provided together, "
                "or both must be None"
            )
