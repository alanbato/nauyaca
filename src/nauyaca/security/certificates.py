"""Certificate generation and management utilities.

This module provides utilities for generating, loading, and validating TLS certificates
for use with Gemini protocol servers and clients.
"""

import datetime
import hashlib
from pathlib import Path
from typing import cast

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_self_signed_cert(
    hostname: str,
    key_size: int = 2048,
    valid_days: int = 365,
) -> tuple[bytes, bytes]:
    """Generate a self-signed TLS certificate.

    Args:
        hostname: Hostname for the certificate (CN and SAN).
        key_size: RSA key size in bits (default: 2048).
        valid_days: Certificate validity period in days (default: 365).

    Returns:
        Tuple of (certificate_pem, private_key_pem) as bytes.

    Example:
        >>> cert_pem, key_pem = generate_self_signed_cert("localhost")
        >>> Path("cert.pem").write_bytes(cert_pem)
        >>> Path("key.pem").write_bytes(key_pem)
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    # Create certificate subject
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, ""),
            x509.NameAttribute(NameOID.LOCALITY_NAME, ""),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Nauyaca Gemini Server"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ]
    )

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))  # type: ignore[attr-defined]
        .not_valid_after(
            datetime.datetime.now(datetime.UTC)  # type: ignore[attr-defined]
            + datetime.timedelta(days=valid_days)
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Serialize to PEM format
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return cert_pem, key_pem


def load_certificate(cert_path: Path) -> x509.Certificate:
    """Load a certificate from a PEM file.

    Args:
        cert_path: Path to the certificate file.

    Returns:
        The loaded certificate object.

    Raises:
        FileNotFoundError: If certificate file doesn't exist.
        ValueError: If certificate file is invalid.
    """
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")

    try:
        cert_data = cert_path.read_bytes()
        return x509.load_pem_x509_certificate(cert_data)
    except Exception as e:
        raise ValueError(f"Invalid certificate file: {e}") from e


def get_certificate_fingerprint(
    cert: x509.Certificate, algorithm: str = "sha256"
) -> str:
    """Calculate the fingerprint of a certificate.

    Args:
        cert: The certificate to fingerprint.
        algorithm: Hash algorithm to use (default: sha256).

    Returns:
        Fingerprint string in format "algorithm:hexdigest".

    Example:
        >>> cert = load_certificate(Path("cert.pem"))
        >>> fingerprint = get_certificate_fingerprint(cert)
        >>> print(fingerprint)
        'sha256:a1b2c3d4e5f6...'
    """
    cert_der = cert.public_bytes(serialization.Encoding.DER)

    if algorithm == "sha256":
        digest = hashlib.sha256(cert_der).hexdigest()
    elif algorithm == "sha1":
        digest = hashlib.sha1(cert_der).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    return f"{algorithm}:{digest}"


def get_certificate_fingerprint_from_path(
    cert_path: Path, algorithm: str = "sha256"
) -> str:
    """Calculate the fingerprint of a certificate file.

    Args:
        cert_path: Path to the certificate file.
        algorithm: Hash algorithm to use (default: sha256).

    Returns:
        Hex-encoded fingerprint string.
    """
    cert = load_certificate(cert_path)
    return get_certificate_fingerprint(cert, algorithm)


def is_certificate_expired(cert: x509.Certificate) -> bool:
    """Check if a certificate has expired.

    Args:
        cert: The certificate to check.

    Returns:
        True if the certificate has expired, False otherwise.
    """
    now = datetime.datetime.now(datetime.UTC)  # type: ignore[attr-defined]
    return now > cert.not_valid_after_utc


def is_certificate_valid_for_hostname(cert: x509.Certificate, hostname: str) -> bool:
    """Check if a certificate is valid for a given hostname.

    Args:
        cert: The certificate to check.
        hostname: The hostname to validate against.

    Returns:
        True if the certificate is valid for the hostname, False otherwise.
    """
    # Check CN (Common Name)
    try:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        if cn == hostname:
            return True
    except (IndexError, AttributeError):
        pass

    # Check SAN (Subject Alternative Name)
    try:
        san_extension = cert.extensions.get_extension_for_oid(
            x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )
        san = cast(x509.SubjectAlternativeName, san_extension.value)
        san_names = san.get_values_for_type(x509.DNSName)
        if hostname in san_names:
            return True
    except x509.ExtensionNotFound:
        pass

    return False


def get_certificate_info(cert: x509.Certificate) -> dict[str, str]:
    """Extract human-readable information from a certificate.

    Args:
        cert: The certificate to inspect.

    Returns:
        Dictionary containing certificate information.
    """
    # Get full fingerprints with algorithm prefix
    fp_sha256 = get_certificate_fingerprint(cert, "sha256")
    fp_sha1 = get_certificate_fingerprint(cert, "sha1")

    info = {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": str(cert.serial_number),
        "not_before": cert.not_valid_before_utc.isoformat(),
        "not_after": cert.not_valid_after_utc.isoformat(),
        "fingerprint_sha256": fp_sha256,
        "fingerprint_sha1": fp_sha1,
        "expired": str(is_certificate_expired(cert)),
    }

    # Extract SAN if present
    try:
        san_extension = cert.extensions.get_extension_for_oid(
            x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )
        san = cast(x509.SubjectAlternativeName, san_extension.value)
        san_names = san.get_values_for_type(x509.DNSName)
        info["san"] = ", ".join(san_names)
    except x509.ExtensionNotFound:
        info["san"] = ""

    return info


def validate_certificate_file(cert_path: Path) -> tuple[bool, str]:
    """Validate a certificate file.

    Args:
        cert_path: Path to the certificate file.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    try:
        cert = load_certificate(cert_path)

        if is_certificate_expired(cert):
            return False, "Certificate has expired"

        return True, ""
    except FileNotFoundError:
        return False, "Certificate file not found"
    except ValueError as e:
        return False, str(e)
