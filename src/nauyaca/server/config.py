"""Server configuration for Gemini server.

This module provides configuration data structures for the Gemini server.
"""

import sys
from dataclasses import dataclass

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..protocol.constants import DEFAULT_MAX_FILE_SIZE, DEFAULT_PORT

if TYPE_CHECKING:
    from .handler import FileUploadHandler
    from .router import Router

from .location import HandlerType, LocationConfig
from .middleware import (
    AccessControlConfig,
    CertificateAuthConfig,
    CertificateAuthPathRule,
    RateLimitConfig,
)


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
    enable_access_control: bool = True
    access_control_allow_list: list[str] | None = None
    access_control_deny_list: list[str] | None = None
    access_control_default_allow: bool = True

    # File serving limits
    max_file_size: int = DEFAULT_MAX_FILE_SIZE

    # Path-based certificate authentication
    # List of dicts with 'prefix', 'require_cert', and optional 'allowed_fingerprints'
    certificate_auth_paths: list[dict[str, Any]] | None = None

    # Client certificate requirement (triggers PyOpenSSL for self-signed certs)
    require_client_cert: bool = False

    # Logging/privacy
    hash_client_ips: bool = True

    # Titan upload configuration
    enable_titan: bool = False  # Disabled by default for security
    titan_upload_dir: Path | str | None = None
    titan_max_upload_size: int = 10 * 1024 * 1024  # 10 MiB default
    titan_allowed_mime_types: list[str] | None = None  # None = all allowed
    titan_auth_tokens: list[str] | None = None  # None = no auth required
    titan_enable_delete: bool = False  # Delete disabled by default for safety

    # Location-based routing configuration
    # If set, enables multi-handler routing (proxy, static, etc.)
    locations: list[LocationConfig] | None = None

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

        # Validate Titan configuration
        if isinstance(self.titan_upload_dir, str):
            self.titan_upload_dir = Path(self.titan_upload_dir)

        if self.enable_titan:
            if self.titan_upload_dir is None:
                raise ValueError("titan_upload_dir is required when Titan is enabled")
            # Create upload directory if it doesn't exist
            if not self.titan_upload_dir.exists():
                self.titan_upload_dir.mkdir(parents=True, exist_ok=True)

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
            AccessControlConfig instance if enabled and lists are configured,
            None otherwise.
        """
        if not self.enable_access_control:
            return None

        if not (self.access_control_allow_list or self.access_control_deny_list):
            return None

        return AccessControlConfig(
            allow_list=self.access_control_allow_list,
            deny_list=self.access_control_deny_list,
            default_allow=self.access_control_default_allow,
        )

    def get_certificate_auth_config(self) -> CertificateAuthConfig | None:
        """Get certificate authentication configuration.

        Returns:
            CertificateAuthConfig instance if path rules are configured, None otherwise.
        """
        if not self.certificate_auth_paths:
            return None

        path_rules = []
        for path_config in self.certificate_auth_paths:
            # Convert fingerprints list to set if present
            fingerprints_list = path_config.get("allowed_fingerprints")
            fingerprints = set(fingerprints_list) if fingerprints_list else None

            path_rules.append(
                CertificateAuthPathRule(
                    prefix=path_config["prefix"],
                    require_cert=path_config.get("require_cert", False),
                    allowed_fingerprints=fingerprints,
                )
            )

        return CertificateAuthConfig(path_rules=path_rules)

    def get_upload_handler(self) -> "FileUploadHandler | None":
        """Get the Titan upload handler if Titan is enabled.

        Returns:
            FileUploadHandler instance if Titan is enabled, None otherwise.
        """
        if not self.enable_titan or self.titan_upload_dir is None:
            return None

        from .handler import FileUploadHandler

        # Convert auth tokens list to set
        auth_tokens = set(self.titan_auth_tokens) if self.titan_auth_tokens else None

        return FileUploadHandler(
            upload_dir=self.titan_upload_dir,
            max_size=self.titan_max_upload_size,
            allowed_types=self.titan_allowed_mime_types,
            auth_tokens=auth_tokens,
            enable_delete=self.titan_enable_delete,
        )

    def get_location_router(
        self, enable_directory_listing: bool = False
    ) -> "Router | None":
        """Build a router from location configurations.

        Creates handlers for each location and registers them with a Router.
        If no locations are configured, returns None.

        Args:
            enable_directory_listing: Default directory listing setting for
                static handlers that don't specify it.

        Returns:
            Router instance configured with location handlers, or None if
            no locations are configured.

        Examples:
            >>> config = ServerConfig.from_toml(Path("config.toml"))
            >>> router = config.get_location_router()
            >>> if router:
            ...     response = router.route(request)
        """
        if not self.locations:
            return None

        from .handler import RequestHandler, StaticFileHandler
        from .proxy import ProxyHandler
        from .router import Router, RouteType

        def create_handler(loc: LocationConfig) -> RequestHandler:
            """Create handler instance from location config."""
            if loc.handler_type == HandlerType.STATIC:
                # document_root is validated in LocationConfig.__post_init__
                assert loc.document_root is not None
                return StaticFileHandler(
                    document_root=loc.document_root,
                    enable_directory_listing=loc.enable_directory_listing
                    or enable_directory_listing,
                    default_indices=loc.default_indices,
                    max_file_size=loc.max_file_size or self.max_file_size,
                )
            elif loc.handler_type == HandlerType.PROXY:
                # upstream is validated in LocationConfig.__post_init__
                assert loc.upstream is not None
                return ProxyHandler(
                    upstream=loc.upstream,
                    prefix=loc.prefix,
                    strip_prefix=loc.strip_prefix,
                    timeout=loc.timeout,
                )
            else:
                raise ValueError(f"Unknown handler type: {loc.handler_type}")

        router = Router()
        for location in self.locations:
            handler = create_handler(location)
            router.add_route(location.prefix, handler.handle, route_type=RouteType.PREFIX)

        return router

    @classmethod
    def from_env(cls) -> dict[str, Any]:
        """Extract configuration from environment variables.

        Reads NAUYACA_* environment variables and returns a dict suitable
        for overriding ServerConfig fields. Only returns values that are
        actually set in the environment.

        Supported variables:
            NAUYACA_HOST: Server host address
            NAUYACA_PORT: Server port (integer)
            NAUYACA_DOCUMENT_ROOT: Path to document root
            NAUYACA_CERTFILE: Path to TLS certificate
            NAUYACA_KEYFILE: Path to TLS private key

        Returns:
            Dict with keys matching ServerConfig fields.

        Raises:
            ValueError: If NAUYACA_PORT is not a valid integer.

        Examples:
            >>> import os
            >>> os.environ['NAUYACA_HOST'] = '0.0.0.0'
            >>> env_config = ServerConfig.from_env()
            >>> env_config.get('host')
            '0.0.0.0'
        """
        import os

        config: dict[str, Any] = {}

        # String fields
        if host := os.getenv("NAUYACA_HOST"):
            config["host"] = host

        # Integer fields
        port_str = os.getenv("NAUYACA_PORT")
        if port_str is not None:
            try:
                config["port"] = int(port_str)
            except ValueError as e:
                raise ValueError(
                    f"Invalid NAUYACA_PORT: {port_str!r} (must be an integer 1-65535)"
                ) from e

        # Path fields
        if document_root := os.getenv("NAUYACA_DOCUMENT_ROOT"):
            config["document_root"] = document_root

        if certfile := os.getenv("NAUYACA_CERTFILE"):
            config["certfile"] = certfile

        if keyfile := os.getenv("NAUYACA_KEYFILE"):
            config["keyfile"] = keyfile

        return config

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
        certificate_auth = data.get("certificate_auth", {})
        logging_config = data.get("logging", {})
        titan = data.get("titan", {})

        # Parse locations if present
        locations_data = data.get("locations", [])
        locations: list[LocationConfig] | None = None
        if locations_data:
            locations = [LocationConfig.from_dict(loc) for loc in locations_data]

        # Build config with proper type conversions
        return cls(
            # Server settings
            host=server.get("host", "localhost"),
            port=server.get("port", DEFAULT_PORT),
            document_root=server.get("document_root", "."),
            certfile=server.get("certfile"),
            keyfile=server.get("keyfile"),
            max_file_size=server.get("max_file_size", DEFAULT_MAX_FILE_SIZE),
            # Rate limiting
            enable_rate_limiting=rate_limit.get("enabled", True),
            rate_limit_capacity=rate_limit.get("capacity", 10),
            rate_limit_refill_rate=rate_limit.get("refill_rate", 1.0),
            rate_limit_retry_after=rate_limit.get("retry_after", 30),
            # Access control
            enable_access_control=access_control.get("enabled", True),
            access_control_allow_list=access_control.get("allow_list"),
            access_control_deny_list=access_control.get("deny_list"),
            access_control_default_allow=access_control.get("default_allow", True),
            # Path-based certificate authentication
            certificate_auth_paths=certificate_auth.get("paths"),
            require_client_cert=server.get("require_client_cert", False),
            # Logging/privacy
            hash_client_ips=logging_config.get("hash_ips", True),
            # Titan upload configuration
            enable_titan=titan.get("enabled", False),
            titan_upload_dir=titan.get("upload_dir"),
            titan_max_upload_size=titan.get("max_upload_size", 10 * 1024 * 1024),
            titan_allowed_mime_types=titan.get("allowed_mime_types"),
            titan_auth_tokens=titan.get("auth_tokens"),
            titan_enable_delete=titan.get("enable_delete", False),
            # Location-based routing
            locations=locations,
        )
