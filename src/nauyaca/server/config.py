"""Server configuration for Gemini server.

This module provides configuration data structures for the Gemini server.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..protocol.constants import DEFAULT_PORT
from .middleware import AccessControlConfig, RateLimitConfig


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

    # Middleware configuration
    enable_rate_limiting: bool = True
    rate_limit_capacity: int = 10
    rate_limit_refill_rate: float = 1.0
    rate_limit_retry_after: int = 30

    # Access control
    access_control_allow_list: list[str] | None = None
    access_control_deny_list: list[str] | None = None
    access_control_default_allow: bool = True

    def __post_init__(self) -> None:
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

    def get_rate_limit_config(self) -> RateLimitConfig:
        """Get rate limit configuration.

        Returns:
            RateLimitConfig instance with current settings.
        """
        return RateLimitConfig(
            capacity=self.rate_limit_capacity,
            refill_rate=self.rate_limit_refill_rate,
            retry_after=self.rate_limit_retry_after,
        )

    def get_access_control_config(self) -> AccessControlConfig | None:
        """Get access control configuration.

        Returns:
            AccessControlConfig instance if any lists are configured, None otherwise.
        """
        if not (self.access_control_allow_list or self.access_control_deny_list):
            return None

        return AccessControlConfig(
            allow_list=self.access_control_allow_list,
            deny_list=self.access_control_deny_list,
            default_allow=self.access_control_default_allow,
        )

    @classmethod
    def from_toml(cls, path: Path) -> "ServerConfig":
        """Load configuration from TOML file.

        Args:
            path: Path to TOML configuration file.

        Returns:
            ServerConfig instance loaded from TOML.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid or cannot be parsed.

        Examples:
            >>> config = ServerConfig.from_toml(Path("config.toml"))
            >>> print(config.host, config.port)
            localhost 1965
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file: {e}") from e

        # Extract sections
        server = data.get("server", {})
        rate_limit = data.get("rate_limit", {})
        access_control = data.get("access_control", {})

        # Build config with proper type conversions
        return cls(
            # Server settings
            host=server.get("host", "localhost"),
            port=server.get("port", DEFAULT_PORT),
            document_root=server.get("document_root", "."),
            certfile=server.get("certfile"),
            keyfile=server.get("keyfile"),
            # Rate limiting
            enable_rate_limiting=rate_limit.get("enabled", True),
            rate_limit_capacity=rate_limit.get("capacity", 10),
            rate_limit_refill_rate=rate_limit.get("refill_rate", 1.0),
            rate_limit_retry_after=rate_limit.get("retry_after", 30),
            # Access control
            access_control_allow_list=access_control.get("allow_list"),
            access_control_deny_list=access_control.get("deny_list"),
            access_control_default_allow=access_control.get("default_allow", True),
        )
