"""Tests for certificate CLI commands."""

import os
import stat

import pytest
from typer.testing import CliRunner

from nauyaca.__main__ import app

runner = CliRunner()


class TestCertGenerate:
    """Tests for the cert generate command."""

    def test_generate_creates_files(self, tmp_path):
        """Test that cert generate creates cert and key files."""
        result = runner.invoke(
            app, ["cert", "generate", "testcert", "--output-dir", str(tmp_path)]
        )

        assert result.exit_code == 0
        assert (tmp_path / "testcert.pem").exists()
        assert (tmp_path / "testcert.key").exists()
        assert "Certificate generated successfully" in result.output

    def test_generate_key_has_restricted_permissions(self, tmp_path):
        """Test that generated key file has restricted permissions."""
        runner.invoke(
            app, ["cert", "generate", "testcert", "--output-dir", str(tmp_path)]
        )

        key_file = tmp_path / "testcert.key"
        key_stat = os.stat(key_file)
        # Check that only owner can read/write (0o600)
        assert key_stat.st_mode & 0o777 == stat.S_IRUSR | stat.S_IWUSR

    def test_generate_shows_fingerprint(self, tmp_path):
        """Test that cert generate shows certificate fingerprint."""
        result = runner.invoke(
            app, ["cert", "generate", "testcert", "--output-dir", str(tmp_path)]
        )

        assert result.exit_code == 0
        assert "Fingerprint" in result.output
        assert "sha256:" in result.output

    def test_generate_shows_usage_hint(self, tmp_path):
        """Test that cert generate shows usage hint."""
        result = runner.invoke(
            app, ["cert", "generate", "testcert", "--output-dir", str(tmp_path)]
        )

        assert result.exit_code == 0
        assert "--client-cert" in result.output
        assert "--client-key" in result.output

    def test_generate_refuses_overwrite_without_force(self, tmp_path):
        """Test that cert generate refuses to overwrite without --force."""
        # Create existing files
        (tmp_path / "existing.pem").write_text("existing cert")

        result = runner.invoke(
            app, ["cert", "generate", "existing", "--output-dir", str(tmp_path)]
        )

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_generate_overwrites_with_force(self, tmp_path):
        """Test that cert generate overwrites with --force."""
        # Create existing files
        (tmp_path / "existing.pem").write_text("old cert")
        (tmp_path / "existing.key").write_text("old key")

        result = runner.invoke(
            app,
            ["cert", "generate", "existing", "--output-dir", str(tmp_path), "--force"],
        )

        assert result.exit_code == 0
        # Verify new content was written
        assert (tmp_path / "existing.pem").read_text() != "old cert"

    def test_generate_custom_validity(self, tmp_path):
        """Test that cert generate accepts custom validity period."""
        result = runner.invoke(
            app,
            [
                "cert",
                "generate",
                "testcert",
                "--output-dir",
                str(tmp_path),
                "--valid-days",
                "730",
            ],
        )

        assert result.exit_code == 0
        assert "Certificate generated successfully" in result.output

    def test_generate_creates_default_directory(self, tmp_path, monkeypatch):
        """Test that cert generate creates ~/.nauyaca/certs/ if needed."""
        # Use a custom home directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        result = runner.invoke(app, ["cert", "generate", "testcert"])

        assert result.exit_code == 0
        assert (fake_home / ".nauyaca" / "certs" / "testcert.pem").exists()


class TestCertInfo:
    """Tests for the cert info command."""

    def test_info_shows_certificate_details(self, tmp_path):
        """Test that cert info shows certificate details."""
        # First generate a cert
        gen_result = runner.invoke(
            app, ["cert", "generate", "testcert", "--output-dir", str(tmp_path)]
        )
        assert gen_result.exit_code == 0, f"Generate failed: {gen_result.output}"

        # Then get info
        result = runner.invoke(app, ["cert", "info", str(tmp_path / "testcert.pem")])

        assert result.exit_code == 0, f"Info failed: {result.output}"
        assert "Subject" in result.output
        assert "Fingerprint" in result.output
        assert "Not After" in result.output

    def test_info_nonexistent_file(self, tmp_path):
        """Test that cert info handles nonexistent file."""
        result = runner.invoke(app, ["cert", "info", str(tmp_path / "nonexistent.pem")])

        assert result.exit_code != 0
