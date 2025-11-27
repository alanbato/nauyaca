"""Tests for server configuration."""

from pathlib import Path

import pytest

from nauyaca.server.config import ServerConfig


class TestServerConfigTOML:
    """Tests for TOML configuration loading."""

    def test_from_toml_full_config(self, tmp_path):
        """Test loading a complete TOML configuration."""
        # Create dummy cert/key files
        cert_file = tmp_path / "cert.pem"
        key_file = tmp_path / "key.pem"
        cert_file.write_text("dummy cert")
        key_file.write_text("dummy key")

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            f"""
[server]
host = "0.0.0.0"
port = 1965
document_root = "{tmp_path}"
certfile = "{cert_file}"
keyfile = "{key_file}"

[rate_limit]
enabled = true
capacity = 20
refill_rate = 2.0
retry_after = 60

[access_control]
allow_list = ["192.168.1.0/24", "10.0.0.1"]
deny_list = ["203.0.113.0/24"]
default_allow = false
"""
        )

        config = ServerConfig.from_toml(config_file)

        # Server settings
        assert config.host == "0.0.0.0"
        assert config.port == 1965
        assert config.document_root == tmp_path
        assert config.certfile == cert_file
        assert config.keyfile == key_file

        # Rate limiting
        assert config.enable_rate_limiting is True
        assert config.rate_limit_capacity == 20
        assert config.rate_limit_refill_rate == 2.0
        assert config.rate_limit_retry_after == 60

        # Access control
        assert config.access_control_allow_list == ["192.168.1.0/24", "10.0.0.1"]
        assert config.access_control_deny_list == ["203.0.113.0/24"]
        assert config.access_control_default_allow is False

    def test_from_toml_minimal_config(self, tmp_path):
        """Test loading a minimal TOML configuration with defaults."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
document_root = "."
"""
        )

        config = ServerConfig.from_toml(config_file)

        # Should use defaults
        assert config.host == "localhost"
        assert config.port == 1965
        assert config.document_root == Path(".")
        assert config.certfile is None
        assert config.keyfile is None

        # Rate limiting defaults
        assert config.enable_rate_limiting is True
        assert config.rate_limit_capacity == 10
        assert config.rate_limit_refill_rate == 1.0
        assert config.rate_limit_retry_after == 30

        # Access control defaults
        assert config.access_control_allow_list is None
        assert config.access_control_deny_list is None
        assert config.access_control_default_allow is True

    def test_from_toml_partial_sections(self, tmp_path):
        """Test loading config with some sections present, others missing."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
host = "127.0.0.1"
port = 8080
document_root = "."

[rate_limit]
capacity = 5
"""
        )

        config = ServerConfig.from_toml(config_file)

        # Specified values
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.rate_limit_capacity == 5

        # Defaults for missing values
        assert config.rate_limit_refill_rate == 1.0
        assert config.access_control_default_allow is True

    def test_from_toml_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing file."""
        config_file = tmp_path / "nonexistent.toml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            ServerConfig.from_toml(config_file)

    def test_from_toml_invalid_toml(self, tmp_path):
        """Test that ValueError is raised for invalid TOML."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text(
            """
[server
host = "broken
"""
        )

        with pytest.raises(ValueError, match="Failed to parse TOML"):
            ServerConfig.from_toml(config_file)

    def test_from_toml_path_conversion(self, tmp_path):
        """Test that string paths are converted to Path objects."""
        # Create actual files
        cert_file = tmp_path / "cert.pem"
        key_file = tmp_path / "key.pem"
        cert_file.write_text("dummy cert")
        key_file.write_text("dummy key")

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            f"""
[server]
document_root = "{tmp_path}"
certfile = "{cert_file}"
keyfile = "{key_file}"
"""
        )

        config = ServerConfig.from_toml(config_file)

        assert isinstance(config.document_root, Path)
        assert isinstance(config.certfile, Path)
        assert isinstance(config.keyfile, Path)

    def test_from_toml_type_conversions(self, tmp_path):
        """Test that TOML values are properly typed."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
host = "localhost"
port = 1965
document_root = "."

[rate_limit]
enabled = true
capacity = 10
refill_rate = 1.5
retry_after = 30

[access_control]
default_allow = false
"""
        )

        config = ServerConfig.from_toml(config_file)

        # Check types
        assert isinstance(config.host, str)
        assert isinstance(config.port, int)
        assert isinstance(config.enable_rate_limiting, bool)
        assert isinstance(config.rate_limit_capacity, int)
        assert isinstance(config.rate_limit_refill_rate, float)
        assert isinstance(config.rate_limit_retry_after, int)
        assert isinstance(config.access_control_default_allow, bool)

    def test_from_toml_empty_file(self, tmp_path):
        """Test loading from an empty TOML file uses all defaults."""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")

        config = ServerConfig.from_toml(config_file)

        # Should use all defaults
        assert config.host == "localhost"
        assert config.port == 1965
        assert config.document_root == Path(".")

    def test_from_toml_rate_limit_disabled(self, tmp_path):
        """Test that rate limiting can be disabled via TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
document_root = "."

[rate_limit]
enabled = false
"""
        )

        config = ServerConfig.from_toml(config_file)

        assert config.enable_rate_limiting is False

    def test_from_toml_access_control_lists(self, tmp_path):
        """Test that access control lists are properly loaded."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
document_root = "."

[access_control]
allow_list = ["192.168.1.0/24", "10.0.0.1", "172.16.0.0/12"]
deny_list = ["192.168.1.100"]
"""
        )

        config = ServerConfig.from_toml(config_file)

        assert isinstance(config.access_control_allow_list, list)
        assert len(config.access_control_allow_list) == 3
        assert "192.168.1.0/24" in config.access_control_allow_list

        assert isinstance(config.access_control_deny_list, list)
        assert len(config.access_control_deny_list) == 1
        assert "192.168.1.100" in config.access_control_deny_list


class TestServerConfigValidation:
    """Tests for ServerConfig validation."""

    def test_invalid_port_range(self):
        """Test that invalid port numbers are rejected."""
        with pytest.raises(ValueError, match="Invalid port number"):
            ServerConfig(document_root=".", port=70000)

        with pytest.raises(ValueError, match="Invalid port number"):
            ServerConfig(document_root=".", port=0)

    def test_mismatched_cert_key(self, tmp_path):
        """Test that cert and key must be provided together."""
        # Create a cert file but not a key file
        cert_file = tmp_path / "cert.pem"
        cert_file.write_text("dummy cert")

        config = ServerConfig(document_root=tmp_path, certfile=cert_file, keyfile=None)

        with pytest.raises(ValueError, match="Both certfile and keyfile"):
            config.validate()

    def test_helper_methods(self, tmp_path):
        """Test configuration helper methods."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
document_root = "."

[rate_limit]
capacity = 15
refill_rate = 2.5
retry_after = 45

[access_control]
allow_list = ["127.0.0.1"]
default_allow = false
"""
        )

        config = ServerConfig.from_toml(config_file)

        # Test rate limit config helper
        rate_config = config.get_rate_limit_config()
        assert rate_config.capacity == 15
        assert rate_config.refill_rate == 2.5
        assert rate_config.retry_after == 45

        # Test access control config helper
        ac_config = config.get_access_control_config()
        assert ac_config is not None
        assert ac_config.allow_list == ["127.0.0.1"]
        assert ac_config.default_allow is False

    def test_no_access_control_returns_none(self, tmp_path):
        """Test that get_access_control_config returns None when no ACLs configured."""
        config = ServerConfig(document_root=tmp_path)
        assert config.get_access_control_config() is None

    def test_certificate_auth_from_toml(self, tmp_path):
        """Test that certificate auth config is loaded from TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
document_root = "."

[certificate_auth]
require_cert = true
allowed_fingerprints = ["sha256:abc123", "sha256:def456"]
"""
        )

        config = ServerConfig.from_toml(config_file)

        assert config.require_client_cert is True
        assert config.allowed_cert_fingerprints == ["sha256:abc123", "sha256:def456"]

    def test_certificate_auth_helper_method(self, tmp_path):
        """Test get_certificate_auth_config helper method."""
        config = ServerConfig(
            document_root=tmp_path,
            require_client_cert=True,
            allowed_cert_fingerprints=["sha256:test1", "sha256:test2"],
        )

        cert_config = config.get_certificate_auth_config()

        assert cert_config is not None
        assert cert_config.require_cert is True
        assert cert_config.allowed_fingerprints == {"sha256:test1", "sha256:test2"}

    def test_no_certificate_auth_returns_none(self, tmp_path):
        """Test that get_certificate_auth_config returns None when not configured."""
        config = ServerConfig(document_root=tmp_path)
        assert config.get_certificate_auth_config() is None

    def test_logging_config_from_toml(self, tmp_path):
        """Test that logging config is loaded from TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[server]
document_root = "."

[logging]
hash_ips = false
"""
        )

        config = ServerConfig.from_toml(config_file)

        assert config.hash_client_ips is False

    def test_logging_config_defaults(self, tmp_path):
        """Test that logging config has correct defaults."""
        config = ServerConfig(document_root=tmp_path)

        # Default should be True (hash IPs for privacy)
        assert config.hash_client_ips is True
