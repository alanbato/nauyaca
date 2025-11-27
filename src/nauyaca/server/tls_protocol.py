"""Manual TLS layer using PyOpenSSL and MemoryBIO for asyncio integration.

This module provides a protocol wrapper that handles TLS manually using PyOpenSSL,
allowing us to accept arbitrary self-signed client certificates (which Python's
standard ssl module with OpenSSL 3.x rejects).

The key insight is that we accept raw TCP connections and handle TLS at the
protocol level using PyOpenSSL's memory BIO interface.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from OpenSSL import SSL

from ..security.pyopenssl_tls import (
    get_peer_certificate_from_connection,
    x509_to_cryptography,
)
from ..utils.logging import get_logger
from .protocol import GeminiServerProtocol

logger = get_logger(__name__)


class TLSServerProtocol(asyncio.Protocol):
    """Wraps GeminiServerProtocol with manual PyOpenSSL TLS handling.

    This protocol handles TLS handshake and encryption/decryption manually,
    then passes decrypted data to the inner GeminiServerProtocol.

    The flow is:
    1. TCP connection established (no TLS yet)
    2. This protocol receives encrypted data in data_received()
    3. We feed data to PyOpenSSL via bio_write()
    4. PyOpenSSL decrypts and we pass to inner protocol
    5. Inner protocol writes response, we encrypt and send

    Attributes:
        inner_protocol_factory: Factory function to create inner protocol.
        ssl_context: PyOpenSSL SSL.Context for creating connections.
        transport: The underlying TCP transport.
        tls_conn: PyOpenSSL SSL.Connection handling encryption.
        handshake_complete: Whether TLS handshake is done.
        inner_protocol: The wrapped GeminiServerProtocol instance.
    """

    def __init__(
        self,
        inner_protocol_factory: Callable[[], GeminiServerProtocol],
        ssl_context: SSL.Context,
    ) -> None:
        """Initialize the TLS protocol wrapper.

        Args:
            inner_protocol_factory: Factory to create the inner protocol.
            ssl_context: PyOpenSSL context for TLS connections.
        """
        self.inner_protocol_factory = inner_protocol_factory
        self.ssl_context = ssl_context
        self.transport: asyncio.Transport | None = None

        # PyOpenSSL connection with memory BIOs
        self.tls_conn: SSL.Connection | None = None
        self.handshake_complete = False

        # Inner protocol (created after handshake)
        self.inner_protocol: GeminiServerProtocol | None = None

        # Peer address for logging
        self._peer_name: tuple[str, int] | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Initialize TLS connection when TCP connection is established.

        Args:
            transport: The underlying TCP transport.
        """
        self.transport = transport  # type: ignore[assignment]
        self._peer_name = self.transport.get_extra_info("peername")

        # Create PyOpenSSL connection in server mode with memory BIO
        self.tls_conn = SSL.Connection(self.ssl_context, None)
        self.tls_conn.set_accept_state()

        logger.debug(
            "tls_connection_started",
            client_ip=self._peer_name[0] if self._peer_name else "unknown",
        )

    def data_received(self, data: bytes) -> None:
        """Handle incoming encrypted data.

        Args:
            data: Raw encrypted bytes from the network.
        """
        if self.tls_conn is None or self.transport is None:
            return

        try:
            # Feed encrypted data to TLS layer
            self.tls_conn.bio_write(data)

            if not self.handshake_complete:
                self._do_handshake()
            else:
                self._process_application_data()

        except SSL.Error as e:
            # TLS error - close connection
            self._close_with_error(f"TLS error: {e}")

    def _do_handshake(self) -> None:
        """Perform TLS handshake."""
        if self.tls_conn is None:
            return

        try:
            self.tls_conn.do_handshake()
            self.handshake_complete = True

            logger.debug(
                "tls_handshake_complete",
                client_ip=self._peer_name[0] if self._peer_name else "unknown",
            )

            # Handshake complete - create inner protocol
            self._initialize_inner_protocol()

        except SSL.WantReadError:
            # Handshake needs more data - send what we have
            self._flush_outgoing()
        except SSL.Error as e:
            self._close_with_error(f"Handshake failed: {e}")

    def _process_pending_after_handshake(self) -> None:
        """Process any application data that arrived with the final handshake message.

        After the TLS handshake completes, there may be buffered application data
        that was sent together with the client's final handshake message. We need
        to try reading this data and passing it to the inner protocol.
        """
        if self.tls_conn is None or self.inner_protocol is None:
            return

        try:
            while True:
                decrypted = self.tls_conn.recv(8192)
                if decrypted:
                    self.inner_protocol.data_received(decrypted)
                else:
                    break
        except SSL.WantReadError:
            pass  # No pending data - this is normal
        except SSL.ZeroReturnError:
            self._handle_close()

        self._flush_outgoing()

    def _initialize_inner_protocol(self) -> None:
        """Initialize inner protocol after successful handshake."""
        if self.tls_conn is None:
            return

        self.inner_protocol = self.inner_protocol_factory()

        # Create a wrapper transport that handles TLS
        inner_transport = TLSTransportWrapper(self)

        # Extract client certificate and attach to transport wrapper
        peer_cert = get_peer_certificate_from_connection(self.tls_conn)
        if peer_cert:
            inner_transport.peer_certificate = x509_to_cryptography(peer_cert)
            logger.debug(
                "client_certificate_received",
                client_ip=self._peer_name[0] if self._peer_name else "unknown",
            )

        # Notify inner protocol of connection
        self.inner_protocol.connection_made(inner_transport)

        # Flush any pending outgoing data from handshake
        self._flush_outgoing()

        # Process any application data that arrived with the final handshake message
        self._process_pending_after_handshake()

    def _process_application_data(self) -> None:
        """Decrypt and forward application data to inner protocol."""
        if self.tls_conn is None:
            return

        try:
            while True:
                decrypted = self.tls_conn.recv(8192)
                if decrypted and self.inner_protocol:
                    self.inner_protocol.data_received(decrypted)
        except SSL.WantReadError:
            pass  # No more data available
        except SSL.ZeroReturnError:
            # Clean TLS shutdown
            self._handle_close()

        self._flush_outgoing()

    def _flush_outgoing(self) -> None:
        """Send any pending encrypted data to the network."""
        if self.transport is None or self.tls_conn is None:
            return

        try:
            while True:
                pending = self.tls_conn.bio_read(8192)
                if not pending:
                    break
                self.transport.write(pending)
        except SSL.WantReadError:
            # No more data available - this is normal
            pass
        except SSL.Error:
            pass

    def _close_with_error(self, message: str) -> None:
        """Close connection due to error.

        Args:
            message: Error message for logging.
        """
        logger.warning(
            "tls_error",
            client_ip=self._peer_name[0] if self._peer_name else "unknown",
            error=message,
        )
        if self.transport:
            self.transport.close()

    def _handle_close(self) -> None:
        """Handle connection close."""
        if self.inner_protocol:
            self.inner_protocol.connection_lost(None)
        if self.transport:
            self.transport.close()

    def connection_lost(self, exc: Exception | None) -> None:
        """Handle connection close from network layer.

        Args:
            exc: Exception if connection closed due to error, None for clean close.
        """
        if self.inner_protocol:
            self.inner_protocol.connection_lost(exc)


class TLSTransportWrapper:
    """Wrapper that makes TLS connection look like a regular transport.

    This allows GeminiServerProtocol to work unchanged - it writes
    plaintext data which we encrypt before sending.

    Attributes:
        tls_protocol: The parent TLSServerProtocol handling TLS.
        peer_certificate: Client certificate (if provided).
    """

    def __init__(self, tls_protocol: TLSServerProtocol) -> None:
        """Initialize the transport wrapper.

        Args:
            tls_protocol: The parent TLS protocol.
        """
        self.tls_protocol = tls_protocol
        self.peer_certificate: Any = None  # Set after handshake

    def write(self, data: bytes) -> None:
        """Encrypt and send data.

        Args:
            data: Plaintext data to encrypt and send.
        """
        if self.tls_protocol.tls_conn:
            self.tls_protocol.tls_conn.send(data)
            self.tls_protocol._flush_outgoing()

    def close(self) -> None:
        """Initiate TLS shutdown and close."""
        if self.tls_protocol.tls_conn:
            try:
                self.tls_protocol.tls_conn.shutdown()
                self.tls_protocol._flush_outgoing()
            except SSL.Error:
                pass
        if self.tls_protocol.transport:
            self.tls_protocol.transport.close()

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """Provide transport info expected by GeminiServerProtocol.

        Args:
            name: The info key to retrieve.
            default: Default value if key not found.

        Returns:
            The requested info or default.
        """
        if name == "peername":
            if self.tls_protocol.transport:
                return self.tls_protocol.transport.get_extra_info("peername")
            return None
        if name == "ssl_object":
            # Return a wrapper that provides getpeercert()
            return _SSLObjectWrapper(self.peer_certificate)
        return default

    def is_closing(self) -> bool:
        """Check if the transport is closing.

        Returns:
            True if the transport is closing, False otherwise.
        """
        if self.tls_protocol.transport:
            return self.tls_protocol.transport.is_closing()
        return True


class _SSLObjectWrapper:
    """Wrapper to provide getpeercert() interface expected by get_peer_certificate().

    GeminiServerProtocol.get_peer_certificate() expects to get an SSL object
    from the transport and call getpeercert(binary_form=True) on it. This
    wrapper provides that interface using the certificate we extracted from
    PyOpenSSL.

    Attributes:
        _cert: The cryptography Certificate object.
    """

    def __init__(self, cert: Any) -> None:
        """Initialize the wrapper.

        Args:
            cert: The cryptography Certificate, or None.
        """
        self._cert = cert

    def getpeercert(self, binary_form: bool = False) -> bytes | dict[str, Any] | None:
        """Get the peer certificate.

        Args:
            binary_form: If True, return DER-encoded bytes.

        Returns:
            Certificate in requested format, or None if no certificate.
        """
        if self._cert is None:
            return None
        if binary_form:
            from cryptography.hazmat.primitives import serialization

            return self._cert.public_bytes(serialization.Encoding.DER)
        # Non-binary form not needed for our use case
        return {}
