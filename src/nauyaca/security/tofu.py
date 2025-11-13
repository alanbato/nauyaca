"""Trust-On-First-Use (TOFU) certificate validation.

This module implements TOFU certificate validation for Gemini protocol clients.
Instead of relying on Certificate Authorities, TOFU stores the fingerprint of
certificates seen for each host and validates subsequent connections against
the stored fingerprints.
"""

import datetime
import re
import sqlite3
import tomllib
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import tomli_w
from cryptography import x509

from .certificates import get_certificate_fingerprint


class TOFUDatabase:
    """SQLite-backed TOFU certificate database.

    This class manages a database of known host certificates and provides
    methods for trusting, verifying, and revoking certificates.
    """

    def __init__(self, db_path: Path | None = None):
        """Initialize the TOFU database.

        Args:
            db_path: Path to the SQLite database file. If None, uses
                    ~/.nauyaca/tofu.db (creates directory if needed).
        """
        if db_path is None:
            # Use default location in user's home directory
            home = Path.home()
            nauyaca_dir = home / ".nauyaca"
            nauyaca_dir.mkdir(parents=True, exist_ok=True)
            db_path = nauyaca_dir / "tofu.db"

        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Create the database schema if it doesn't exist."""
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS known_hosts (
                    hostname TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    PRIMARY KEY (hostname, port)
                )
                """
            )

            conn.commit()

    @contextmanager
    def _connection(self):
        """Context manager for database connections.

        Opens a new connection for each operation and ensures it's closed.

        Yields:
            Active SQLite connection with row_factory configured.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def trust(self, hostname: str, port: int, cert: x509.Certificate) -> None:
        """Trust a certificate for a host.

        This stores the certificate fingerprint in the database. If a certificate
        already exists for this host, it will be replaced.

        Args:
            hostname: The hostname (e.g., "example.com").
            port: The port number.
            cert: The certificate to trust.
        """
        fingerprint = get_certificate_fingerprint(cert)
        now = datetime.datetime.now(datetime.UTC).isoformat()  # type: ignore[attr-defined]

        with self._connection() as conn:
            cursor = conn.cursor()

            # Check if host already exists
            cursor.execute(
                "SELECT fingerprint FROM known_hosts WHERE hostname = ? AND port = ?",
                (hostname, port),
            )
            row = cursor.fetchone()

            if row is None:
                # First time seeing this host
                cursor.execute(
                    """
                    INSERT INTO known_hosts
                    (hostname, port, fingerprint, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (hostname, port, fingerprint, now, now),
                )
            else:
                # Update existing entry
                cursor.execute(
                    """
                    UPDATE known_hosts
                    SET fingerprint = ?, last_seen = ?
                    WHERE hostname = ? AND port = ?
                    """,
                    (fingerprint, now, hostname, port),
                )

            conn.commit()

    def verify(
        self, hostname: str, port: int, cert: x509.Certificate
    ) -> tuple[bool, str]:
        """Verify a certificate against the TOFU database.

        Args:
            hostname: The hostname to verify.
            port: The port number.
            cert: The certificate to verify.

        Returns:
            Tuple of (is_valid, message):
            - (True, "") if certificate matches stored fingerprint
            - (True, "first_use") if this is first connection to host
            - (False, "changed") if certificate has changed
        """
        fingerprint = get_certificate_fingerprint(cert)

        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT fingerprint FROM known_hosts WHERE hostname = ? AND port = ?",
                (hostname, port),
            )
            row = cursor.fetchone()

            if row is None:
                # First time seeing this host
                return True, "first_use"

            stored_fingerprint = row["fingerprint"]

            if stored_fingerprint == fingerprint:
                # Certificate matches - update last_seen
                now = datetime.datetime.now(datetime.UTC).isoformat()  # type: ignore[attr-defined]
                cursor.execute(
                    "UPDATE known_hosts SET last_seen = ? "
                    "WHERE hostname = ? AND port = ?",
                    (now, hostname, port),
                )
                conn.commit()
                return True, ""

            # Certificate has changed
            return False, "changed"

    def revoke(self, hostname: str, port: int) -> bool:
        """Remove a host from the TOFU database.

        Args:
            hostname: The hostname to revoke.
            port: The port number.

        Returns:
            True if the host was removed, False if it wasn't in the database.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM known_hosts WHERE hostname = ? AND port = ?",
                (hostname, port),
            )
            conn.commit()

            return cursor.rowcount > 0

    def list_hosts(self) -> list[dict[str, str]]:
        """List all known hosts in the database.

        Returns:
            List of dictionaries containing host information.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT hostname, port, fingerprint, first_seen, last_seen
                FROM known_hosts
                ORDER BY last_seen DESC
                """
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear(self) -> int:
        """Clear all entries from the TOFU database.

        Returns:
            Number of entries removed.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM known_hosts")
            conn.commit()

            return cursor.rowcount

    def get_host_info(self, hostname: str, port: int) -> dict[str, str] | None:
        """Get information about a specific host.

        Args:
            hostname: The hostname to look up.
            port: The port number.

        Returns:
            Dictionary containing host information, or None if not found.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT hostname, port, fingerprint, first_seen, last_seen
                FROM known_hosts
                WHERE hostname = ? AND port = ?
                """,
                (hostname, port),
            )

            row = cursor.fetchone()
            if row is None:
                return None

            return dict(row)

    def export_toml(self, file_path: Path) -> int:
        """Export the TOFU database to a TOML file.

        Args:
            file_path: Path to the output TOML file.

        Returns:
            Number of hosts exported.

        Raises:
            IOError: If the file cannot be written.
        """
        hosts = self.list_hosts()

        # Build TOML structure
        data: dict[str, Any] = {
            "_metadata": {
                "exported_at": datetime.datetime.now(datetime.UTC).isoformat(),  # type: ignore[attr-defined]
                "version": "1.0",
            },
            "hosts": {},
        }

        for host in hosts:
            key = f"{host['hostname']}:{host['port']}"
            data["hosts"][key] = {
                "hostname": host["hostname"],
                "port": int(host["port"]),
                "fingerprint": host["fingerprint"],
                "first_seen": host["first_seen"],
                "last_seen": host["last_seen"],
            }

        # Write TOML file
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)

        return len(hosts)

    def import_toml(
        self,
        file_path: Path,
        merge: bool = True,
        on_conflict: Callable[[str, int, str, str], bool] | None = None,
    ) -> tuple[int, int, int]:
        """Import hosts from a TOML file into the TOFU database.

        Args:
            file_path: Path to the input TOML file.
            merge: If True, merge with existing entries. If False, replace all.
            on_conflict: Callback for resolving fingerprint conflicts.
                Called with (hostname, port, old_fingerprint, new_fingerprint).
                Should return True to update, False to skip.
                If None, conflicts are skipped.

        Returns:
            Tuple of (added_count, updated_count, skipped_count).

        Raises:
            FileNotFoundError: If the TOML file doesn't exist.
            ValueError: If the TOML structure is invalid.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"TOML file not found: {file_path}")

        # Load TOML file
        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        # Validate structure
        if "hosts" not in data:
            raise ValueError("Invalid TOML: missing 'hosts' section")

        if not isinstance(data["hosts"], dict):
            raise ValueError("Invalid TOML: 'hosts' must be a table")

        # Clear database if not merging
        if not merge:
            self.clear()

        added_count = 0
        updated_count = 0
        skipped_count = 0

        with self._connection() as conn:
            cursor = conn.cursor()

            for key, host_data in data["hosts"].items():
                # Validate required fields
                required_fields = [
                    "hostname",
                    "port",
                    "fingerprint",
                    "first_seen",
                    "last_seen",
                ]
                for field in required_fields:
                    if field not in host_data:
                        raise ValueError(
                            f"Invalid TOML: host '{key}'"
                            f" missing required field '{field}'"
                        )

                hostname = host_data["hostname"]
                port = host_data["port"]
                fingerprint = host_data["fingerprint"]
                first_seen = host_data["first_seen"]

                # Validate port
                if not isinstance(port, int) or not (1 <= port <= 65535):
                    raise ValueError(
                        f"Invalid TOML: host '{key}' has invalid port: {port}"
                    )

                # Validate fingerprint format
                if not self._validate_fingerprint(fingerprint):
                    raise ValueError(
                        f"Invalid TOML: host '{key}' "
                        f"has invalid fingerprint format: {fingerprint}"
                    )

                # Check if host already exists
                existing = self.get_host_info(hostname, port)

                if existing is None:
                    # New host - add it
                    now = datetime.datetime.now(datetime.UTC).isoformat()  # type: ignore[attr-defined]
                    cursor.execute(
                        """
                        INSERT INTO known_hosts
                        (hostname, port, fingerprint, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (hostname, port, fingerprint, first_seen, now),
                    )
                    added_count += 1
                elif existing["fingerprint"] == fingerprint:
                    # Same fingerprint - skip
                    skipped_count += 1
                else:
                    # Fingerprint mismatch - check if we should update
                    should_update = False
                    if on_conflict:
                        should_update = on_conflict(
                            hostname, port, existing["fingerprint"], fingerprint
                        )

                    if should_update:
                        # Update with new fingerprint
                        # Preserve first_seen, update last_seen
                        now = datetime.datetime.now(datetime.UTC).isoformat()  # type: ignore[attr-defined]
                        cursor.execute(
                            """
                            UPDATE known_hosts
                            SET fingerprint = ?, last_seen = ?
                            WHERE hostname = ? AND port = ?
                            """,
                            (fingerprint, now, hostname, port),
                        )
                        updated_count += 1
                    else:
                        skipped_count += 1

            conn.commit()
            return (added_count, updated_count, skipped_count)

    def _validate_fingerprint(self, fingerprint: str) -> bool:
        """Validate that a fingerprint matches the expected format.

        Args:
            fingerprint: The fingerprint string to validate.

        Returns:
            True if valid, False otherwise.
        """
        # Expected format: sha256:64_hex_chars
        pattern = r"^sha256:[0-9a-f]{64}$"
        return bool(re.match(pattern, fingerprint.lower()))


class CertificateChangedError(Exception):
    """Exception raised when a certificate has changed unexpectedly.

    This indicates a potential MITM attack or legitimate certificate renewal.
    """

    def __init__(
        self,
        hostname: str,
        port: int,
        old_fingerprint: str,
        new_fingerprint: str,
    ):
        """Initialize the exception.

        Args:
            hostname: The hostname where certificate changed.
            port: The port number.
            old_fingerprint: The previously stored fingerprint.
            new_fingerprint: The new certificate fingerprint.
        """
        self.hostname = hostname
        self.port = port
        self.old_fingerprint = old_fingerprint
        self.new_fingerprint = new_fingerprint

        super().__init__(
            f"Certificate for {hostname}:{port} has changed!\n"
            f"Old fingerprint: {old_fingerprint}\n"
            f"New fingerprint: {new_fingerprint}\n"
            f"This could indicate a man-in-the-middle attack or a legitimate "
            f"certificate renewal. Verify the new certificate before continuing."
        )
