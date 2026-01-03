"""Tests for TOFU database TOML export/import functionality."""

import sys
from pathlib import Path

import pytest
from cryptography import x509

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from nauyaca.security.tofu import TOFUDatabase


class TestTOFUExport:
    """Test TOFU database export to TOML."""

    def test_export_empty_database(self, tmp_path: Path):
        """Test exporting an empty database creates valid TOML."""
        db_path = tmp_path / "tofu.db"
        export_path = tmp_path / "export.toml"

        db = TOFUDatabase(db_path)
        count = db.export_toml(export_path)

        assert count == 0
        assert export_path.exists()

        # Verify TOML structure
        with open(export_path, "rb") as f:
            data = tomllib.load(f)

        assert "hosts" in data
        assert "_metadata" in data
        assert len(data["hosts"]) == 0

    def test_export_single_host(self, tmp_path: Path, test_cert: x509.Certificate):
        """Test exporting a single host."""
        db_path = tmp_path / "tofu.db"
        export_path = tmp_path / "export.toml"

        # Add a host
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        count = db.export_toml(export_path)

        assert count == 1
        assert export_path.exists()

        # Verify content
        with open(export_path, "rb") as f:
            data = tomllib.load(f)

        assert len(data["hosts"]) == 1
        key = "example.com:1965"
        assert key in data["hosts"]

        host = data["hosts"][key]
        assert host["hostname"] == "example.com"
        assert host["port"] == 1965
        assert "fingerprint" in host
        assert "first_seen" in host
        assert "last_seen" in host

    def test_export_multiple_hosts(
        self,
        tmp_path: Path,
        test_cert: x509.Certificate,
        test_cert_different: x509.Certificate,
    ):
        """Test exporting multiple hosts."""
        db_path = tmp_path / "tofu.db"
        export_path = tmp_path / "export.toml"

        # Add multiple hosts
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        db.trust("test.org", 1965, test_cert_different)
        db.trust("example.com", 300, test_cert)  # Same host, different port

        count = db.export_toml(export_path)

        assert count == 3

        # Verify all hosts present
        with open(export_path, "rb") as f:
            data = tomllib.load(f)

        assert len(data["hosts"]) == 3
        assert "example.com:1965" in data["hosts"]
        assert "test.org:1965" in data["hosts"]
        assert "example.com:300" in data["hosts"]


class TestTOFUImport:
    """Test TOFU database import from TOML."""

    def test_import_into_empty_database(self, tmp_path: Path, faker):
        """Test importing into an empty database."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Create test TOML with Faker-generated fingerprint
        import tomli_w

        data = {
            "hosts": {
                "example.com:1965": {
                    "hostname": "example.com",
                    "port": 1965,
                    "fingerprint": f"sha256:{faker.sha256(raw_output=False)}",
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import
        db = TOFUDatabase(db_path)
        added, updated, skipped = db.import_toml(import_path)

        assert added == 1
        assert updated == 0
        assert skipped == 0

        # Verify import
        db = TOFUDatabase(db_path)
        hosts = db.list_hosts()
        assert len(hosts) == 1
        assert hosts[0]["hostname"] == "example.com"

    def test_import_with_same_fingerprint_skips(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test that importing existing host with same fingerprint skips it."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Add host to database
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        info = db.get_host_info("example.com", 1965)

        # Create TOML with same fingerprint
        import tomli_w

        data = {
            "hosts": {
                "example.com:1965": {
                    "hostname": "example.com",
                    "port": 1965,
                    "fingerprint": info["fingerprint"],
                    "first_seen": info["first_seen"],
                    "last_seen": info["last_seen"],
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import
        db = TOFUDatabase(db_path)
        added, updated, skipped = db.import_toml(import_path)

        assert added == 0
        assert updated == 0
        assert skipped == 1

    def test_import_with_different_fingerprint_prompts(
        self, tmp_path: Path, test_cert: x509.Certificate, faker
    ):
        """Test that different fingerprint triggers conflict callback."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Add host to database
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)

        # Create TOML with different fingerprint using Faker
        import tomli_w

        data = {
            "hosts": {
                "example.com:1965": {
                    "hostname": "example.com",
                    "port": 1965,
                    "fingerprint": f"sha256:{faker.sha256(raw_output=False)}",
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import with callback that accepts
        def accept_all(hostname: str, port: int, old_fp: str, new_fp: str) -> bool:
            return True

        db = TOFUDatabase(db_path)
        added, updated, skipped = db.import_toml(import_path, on_conflict=accept_all)

        assert added == 0
        assert updated == 1
        assert skipped == 0

        # Verify fingerprint was updated to the Faker-generated one
        db = TOFUDatabase(db_path)
        info = db.get_host_info("example.com", 1965)
        # Verify fingerprint format (can't check exact value with Faker)
        assert info["fingerprint"].startswith("sha256:")
        assert len(info["fingerprint"]) == 71  # "sha256:" (7) + 64 hex chars

    def test_import_conflict_reject(
        self, tmp_path: Path, test_cert: x509.Certificate, faker
    ):
        """Test that rejecting conflict leaves original fingerprint."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Add host to database
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        original_fp = db.get_host_info("example.com", 1965)["fingerprint"]

        # Create TOML with different fingerprint using Faker
        import tomli_w

        data = {
            "hosts": {
                "example.com:1965": {
                    "hostname": "example.com",
                    "port": 1965,
                    "fingerprint": f"sha256:{faker.sha256(raw_output=False)}",
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import with callback that rejects
        def reject_all(hostname: str, port: int, old_fp: str, new_fp: str) -> bool:
            return False

        db = TOFUDatabase(db_path)
        added, updated, skipped = db.import_toml(import_path, on_conflict=reject_all)

        assert added == 0
        assert updated == 0
        assert skipped == 1

        # Verify fingerprint unchanged
        db = TOFUDatabase(db_path)
        info = db.get_host_info("example.com", 1965)
        assert info["fingerprint"] == original_fp

    def test_import_replace_mode(
        self, tmp_path: Path, test_cert: x509.Certificate, faker
    ):
        """Test import in replace mode clears existing entries."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Add existing hosts
        db = TOFUDatabase(db_path)
        db.trust("existing1.com", 1965, test_cert)
        db.trust("existing2.com", 1965, test_cert)

        # Create TOML with new hosts using Faker-generated fingerprint
        import tomli_w

        data = {
            "hosts": {
                "new1.com:1965": {
                    "hostname": "new1.com",
                    "port": 1965,
                    "fingerprint": f"sha256:{faker.sha256(raw_output=False)}",
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import in replace mode
        db = TOFUDatabase(db_path)
        added, updated, skipped = db.import_toml(import_path, merge=False)

        assert added == 1
        assert updated == 0
        assert skipped == 0

        # Verify only new host present
        db = TOFUDatabase(db_path)
        hosts = db.list_hosts()
        assert len(hosts) == 1
        assert hosts[0]["hostname"] == "new1.com"

    def test_import_invalid_toml_structure(self, tmp_path: Path):
        """Test that invalid TOML structure raises ValueError."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Create TOML without hosts section
        import tomli_w

        data = {"invalid": "structure"}

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import should fail
        db = TOFUDatabase(db_path)
        with pytest.raises(ValueError, match="missing 'hosts' section"):
            db.import_toml(import_path)

    def test_import_missing_required_field(self, tmp_path: Path):
        """Test that missing required field raises ValueError."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Create TOML missing fingerprint
        import tomli_w

        data = {
            "hosts": {
                "example.com:1965": {
                    "hostname": "example.com",
                    "port": 1965,
                    # Missing fingerprint
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import should fail
        db = TOFUDatabase(db_path)
        with pytest.raises(ValueError, match="missing required field"):
            db.import_toml(import_path)

    def test_import_invalid_fingerprint_format(self, tmp_path: Path):
        """Test that invalid fingerprint format raises ValueError."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Create TOML with invalid fingerprint
        import tomli_w

        data = {
            "hosts": {
                "example.com:1965": {
                    "hostname": "example.com",
                    "port": 1965,
                    "fingerprint": "invalid-format",  # Invalid
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import should fail
        db = TOFUDatabase(db_path)
        with pytest.raises(ValueError, match="invalid fingerprint format"):
            db.import_toml(import_path)

    def test_import_invalid_port(self, tmp_path: Path, faker):
        """Test that invalid port raises ValueError."""
        db_path = tmp_path / "tofu.db"
        import_path = tmp_path / "import.toml"

        # Create TOML with invalid port
        import tomli_w

        data = {
            "hosts": {
                "example.com:99999": {
                    "hostname": "example.com",
                    "port": 99999,  # Out of range
                    "fingerprint": f"sha256:{faker.sha256(raw_output=False)}",
                    "first_seen": "2025-01-15T10:30:00+00:00",
                    "last_seen": "2025-01-16T14:20:00+00:00",
                }
            }
        }

        with open(import_path, "wb") as f:
            tomli_w.dump(data, f)

        # Import should fail
        db = TOFUDatabase(db_path)
        with pytest.raises(ValueError, match="invalid port"):
            db.import_toml(import_path)


class TestTOFURoundTrip:
    """Test export/import round-trip."""

    def test_round_trip_preserves_data(
        self,
        tmp_path: Path,
        test_cert: x509.Certificate,
        test_cert_different: x509.Certificate,
    ):
        """Test that export -> import preserves all data correctly."""
        db1_path = tmp_path / "db1.db"
        db2_path = tmp_path / "db2.db"
        export_path = tmp_path / "export.toml"

        # Create database with multiple hosts
        db = TOFUDatabase(db1_path)
        db.trust("example.com", 1965, test_cert)
        db.trust("test.org", 1965, test_cert_different)
        db.trust("example.com", 300, test_cert)

        # Get original data
        original_hosts = db.list_hosts()

        # Export
        db.export_toml(export_path)

        # Import into new database
        db = TOFUDatabase(db2_path)
        db.import_toml(export_path)

        # Get imported data
        imported_hosts = db.list_hosts()

        # Verify all hosts present and fingerprints match
        assert len(imported_hosts) == len(original_hosts)

        original_by_key = {f"{h['hostname']}:{h['port']}": h for h in original_hosts}
        imported_by_key = {f"{h['hostname']}:{h['port']}": h for h in imported_hosts}

        for key in original_by_key:
            assert key in imported_by_key
            assert (
                original_by_key[key]["fingerprint"] == imported_by_key[key]["fingerprint"]
            )
            assert (
                original_by_key[key]["first_seen"] == imported_by_key[key]["first_seen"]
            )


class TestTOFURevokeByHostname:
    """Test TOFU database revoke by hostname functionality."""

    def test_count_by_hostname_empty_database(self, tmp_path: Path):
        """Test counting entries for a hostname in an empty database."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)

        count = db.count_by_hostname("example.com")
        assert count == 0

    def test_count_by_hostname_single_entry(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test counting when hostname has a single entry."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)

        count = db.count_by_hostname("example.com")
        assert count == 1

    def test_count_by_hostname_multiple_ports(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test counting when hostname has entries on multiple ports."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        db.trust("example.com", 1966, test_cert)
        db.trust("example.com", 300, test_cert)

        count = db.count_by_hostname("example.com")
        assert count == 3

    def test_count_by_hostname_ignores_other_hosts(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test counting only counts entries for the specified hostname."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        db.trust("example.com", 1966, test_cert)
        db.trust("other.com", 1965, test_cert)

        count = db.count_by_hostname("example.com")
        assert count == 2

    def test_revoke_by_hostname_empty_database(self, tmp_path: Path):
        """Test revoking by hostname in an empty database returns 0."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)

        deleted = db.revoke_by_hostname("example.com")
        assert deleted == 0

    def test_revoke_by_hostname_single_entry(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test revoking a single entry by hostname."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)

        deleted = db.revoke_by_hostname("example.com")
        assert deleted == 1

        # Verify entry is gone
        hosts = db.list_hosts()
        assert len(hosts) == 0

    def test_revoke_by_hostname_multiple_ports(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test revoking all entries for a hostname with multiple ports."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        db.trust("example.com", 1966, test_cert)
        db.trust("example.com", 300, test_cert)

        deleted = db.revoke_by_hostname("example.com")
        assert deleted == 3

        # Verify all entries are gone
        hosts = db.list_hosts()
        assert len(hosts) == 0

    def test_revoke_by_hostname_preserves_other_hosts(
        self, tmp_path: Path, test_cert: x509.Certificate
    ):
        """Test revoking by hostname only removes entries for that hostname."""
        db_path = tmp_path / "tofu.db"
        db = TOFUDatabase(db_path)
        db.trust("example.com", 1965, test_cert)
        db.trust("example.com", 1966, test_cert)
        db.trust("other.com", 1965, test_cert)
        db.trust("another.org", 300, test_cert)

        deleted = db.revoke_by_hostname("example.com")
        assert deleted == 2

        # Verify other hosts are still there
        hosts = db.list_hosts()
        assert len(hosts) == 2
        hostnames = {h["hostname"] for h in hosts}
        assert "other.com" in hostnames
        assert "another.org" in hostnames
        assert "example.com" not in hostnames
