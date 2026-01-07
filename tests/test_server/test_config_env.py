"""Tests for environment variable configuration."""

import os
from pathlib import Path

import pytest

from nauyaca.server.config import ServerConfig


class TestServerConfigFromEnv:
    """Tests for ServerConfig.from_env() method."""

    def test_from_env_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with no environment variables set."""
        # Clear any existing NAUYACA_ vars
        for key in list(os.environ.keys()):
            if key.startswith("NAUYACA_"):
                monkeypatch.delenv(key, raising=False)

        config = ServerConfig.from_env()
        assert config == {}

    def test_from_env_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NAUYACA_HOST environment variable."""
        monkeypatch.setenv("NAUYACA_HOST", "0.0.0.0")
        config = ServerConfig.from_env()
        assert config["host"] == "0.0.0.0"

    def test_from_env_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NAUYACA_PORT environment variable."""
        monkeypatch.setenv("NAUYACA_PORT", "8080")
        config = ServerConfig.from_env()
        assert config["port"] == 8080

    def test_from_env_port_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NAUYACA_PORT with invalid value raises ValueError."""
        monkeypatch.setenv("NAUYACA_PORT", "not-a-number")
        with pytest.raises(ValueError, match="Invalid NAUYACA_PORT"):
            ServerConfig.from_env()

    def test_from_env_document_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test NAUYACA_DOCUMENT_ROOT environment variable."""
        monkeypatch.setenv("NAUYACA_DOCUMENT_ROOT", str(tmp_path))
        config = ServerConfig.from_env()
        assert config["document_root"] == str(tmp_path)

    def test_from_env_certfile(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NAUYACA_CERTFILE environment variable."""
        monkeypatch.setenv("NAUYACA_CERTFILE", "/path/to/cert.pem")
        config = ServerConfig.from_env()
        assert config["certfile"] == "/path/to/cert.pem"

    def test_from_env_keyfile(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NAUYACA_KEYFILE environment variable."""
        monkeypatch.setenv("NAUYACA_KEYFILE", "/path/to/key.pem")
        config = ServerConfig.from_env()
        assert config["keyfile"] == "/path/to/key.pem"

    def test_from_env_all_vars(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test all supported environment variables together."""
        monkeypatch.setenv("NAUYACA_HOST", "127.0.0.1")
        monkeypatch.setenv("NAUYACA_PORT", "1965")
        monkeypatch.setenv("NAUYACA_DOCUMENT_ROOT", str(tmp_path))
        monkeypatch.setenv("NAUYACA_CERTFILE", "cert.pem")
        monkeypatch.setenv("NAUYACA_KEYFILE", "key.pem")

        config = ServerConfig.from_env()

        assert config["host"] == "127.0.0.1"
        assert config["port"] == 1965
        assert config["document_root"] == str(tmp_path)
        assert config["certfile"] == "cert.pem"
        assert config["keyfile"] == "key.pem"

    def test_from_env_partial(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with only some variables set."""
        # Clear all NAUYACA_ vars first
        for key in list(os.environ.keys()):
            if key.startswith("NAUYACA_"):
                monkeypatch.delenv(key, raising=False)

        # Set only host and port
        monkeypatch.setenv("NAUYACA_HOST", "192.168.1.1")
        monkeypatch.setenv("NAUYACA_PORT", "9999")

        config = ServerConfig.from_env()

        assert config == {"host": "192.168.1.1", "port": 9999}
        assert "document_root" not in config
        assert "certfile" not in config
        assert "keyfile" not in config

    def test_from_env_empty_values_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty environment variable values are ignored."""
        monkeypatch.setenv("NAUYACA_HOST", "")
        config = ServerConfig.from_env()
        assert "host" not in config


class TestServerConfigEnvIntegration:
    """Integration tests for environment variable configuration."""

    def test_env_overrides_defaults(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that environment variables override default values."""
        monkeypatch.setenv("NAUYACA_HOST", "10.0.0.1")
        monkeypatch.setenv("NAUYACA_PORT", "7777")

        # Create config with defaults
        config = ServerConfig(document_root=tmp_path)

        # Apply env overrides
        env_overrides = ServerConfig.from_env()
        for key, value in env_overrides.items():
            setattr(config, key, value)

        assert config.host == "10.0.0.1"
        assert config.port == 7777

    def test_env_overrides_toml(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that environment variables override TOML config values."""
        # Create TOML config file
        toml_content = f"""
[server]
host = "localhost"
port = 1965
document_root = "{tmp_path}"
"""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(toml_content)

        # Set env var to override
        monkeypatch.setenv("NAUYACA_HOST", "0.0.0.0")
        monkeypatch.setenv("NAUYACA_PORT", "8888")

        # Load from TOML
        config = ServerConfig.from_toml(toml_file)

        # Apply env overrides (as __main__.py does)
        env_overrides = ServerConfig.from_env()
        for key, value in env_overrides.items():
            setattr(config, key, value)

        # Environment should override TOML
        assert config.host == "0.0.0.0"
        assert config.port == 8888
