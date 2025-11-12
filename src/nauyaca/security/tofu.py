"""Trust-On-First-Use (TOFU) certificate validation.

This module implements TOFU certificate validation for Gemini protocol clients.
Instead of relying on Certificate Authorities, TOFU stores the fingerprint of
certificates seen for each host and validates subsequent connections against
the stored fingerprints.
"""

import datetime
import sqlite3
from pathlib import Path

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
        self._conn: sqlite3.Connection | None = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Create the database schema if it doesn't exist."""
        conn = self._get_connection()
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

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection.

        Returns:
            Active SQLite connection.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

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

        conn = self._get_connection()
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

        conn = self._get_connection()
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
                "UPDATE known_hosts SET last_seen = ? WHERE hostname = ? AND port = ?",
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
        conn = self._get_connection()
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
        conn = self._get_connection()
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
        conn = self._get_connection()
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
        conn = self._get_connection()
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

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "TOFUDatabase":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Context manager exit."""
        self.close()


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
