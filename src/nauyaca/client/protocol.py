"""Low-level Gemini client protocol implementation.

This module implements the Gemini client protocol using asyncio's
Protocol/Transport pattern for efficient, non-blocking I/O.
"""

import asyncio

from cryptography import x509

from ..protocol.constants import CRLF, MAX_RESPONSE_BODY_SIZE
from ..protocol.response import GeminiResponse


class GeminiClientProtocol(asyncio.Protocol):
    """Client-side protocol for making Gemini requests.

    This class implements asyncio.Protocol for handling Gemini client connections.
    It manages the connection lifecycle, sends requests, and parses responses.

    The protocol follows the Gemini specification:
    1. Client connects via TLS
    2. Client sends URL + CRLF
    3. Server sends status + meta + CRLF
    4. Server sends response body (if status is 2x)
    5. Connection closes

    Attributes:
        url: The URL being requested.
        response_future: Future that will be set with the GeminiResponse.
        transport: The transport handling the connection.
        buffer: Buffer for accumulating incoming data.
        header_received: Whether the response header has been received.
        status: Response status code.
        meta: Response metadata string.
    """

    def __init__(self, url: str, response_future: asyncio.Future):
        """Initialize the client protocol.

        Args:
            url: The Gemini URL to request.
            response_future: Future to set with the final GeminiResponse.
        """
        self.url = url
        self.response_future = response_future
        self.transport: asyncio.Transport | None = None
        self.buffer = b""
        self.header_received = False
        self.status: int | None = None
        self.meta: str | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when connection to server is established.

        Sends the Gemini request (URL + CRLF).

        Args:
            transport: The transport handling this connection.
        """
        self.transport = transport  # type: ignore[assignment]

        # Send Gemini request (just the URL + CRLF)
        request = f"{self.url}\r\n"
        if self.transport:
            self.transport.write(request.encode("utf-8"))

    def data_received(self, data: bytes) -> None:
        """Called when data is received from the server.

        This method may be called multiple times as data arrives. We accumulate
        data in a buffer and parse it when complete.

        Args:
            data: Raw bytes received from the server.
        """
        self.buffer += data

        # Check if we've received the complete header
        if not self.header_received and CRLF in self.buffer:
            header_line, body = self.buffer.split(CRLF, 1)
            self._parse_header(header_line.decode("utf-8"))
            self.buffer = body
            self.header_received = True

            # If parsing failed, close immediately
            if self.status is None:
                self.transport.close()  # type: ignore
                return

            # If status is not success (20-29), close immediately
            # (no body expected for non-success responses)
            if not (20 <= self.status < 30):
                self.transport.close()  # type: ignore

        # Check if we've received too much data (prevent memory exhaustion)
        if len(self.buffer) > MAX_RESPONSE_BODY_SIZE:
            self._set_error(
                Exception(
                    f"Response body exceeds maximum size ({MAX_RESPONSE_BODY_SIZE} bytes)"
                )
            )
            self.transport.close()  # type: ignore

    def _parse_header(self, header_line: str) -> None:
        """Parse the Gemini response header.

        The header format is: <STATUS><SPACE><META>

        Args:
            header_line: The response header line (without CRLF).
        """
        parts = header_line.split(" ", 1)

        if len(parts) < 1:
            self._set_error(ValueError("Invalid response header: missing status"))
            return

        try:
            self.status = int(parts[0])
        except ValueError:
            self._set_error(ValueError(f"Invalid status code: {parts[0]}"))
            return

        # Meta is optional, default to empty string
        self.meta = parts[1] if len(parts) > 1 else ""

        # Validate status code range
        if not (10 <= self.status < 70):
            self._set_error(ValueError(f"Status code out of range: {self.status}"))

    def eof_received(self) -> bool:
        """Called when the server closes its write side (graceful shutdown).

        Returns:
            False to close our write side too (full connection close).
        """
        return False  # Don't keep connection open

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the connection is closed.

        Sets the response result in the future. This is where we deliver
        the final response to the higher-level async code.

        Args:
            exc: Exception if connection closed due to error, None for clean close.
        """
        # If the future is already done (error case), don't set it again
        if self.response_future.done():
            return

        # If there was a connection error, set the exception
        if exc:
            self.response_future.set_exception(exc)
            return

        # If we never received a header, the connection closed prematurely
        if not self.header_received:
            self.response_future.set_exception(
                ConnectionError("Connection closed before receiving response")
            )
            return

        # Decode body (only present for 2x success responses)
        body = None
        if 20 <= self.status < 30:  # type: ignore
            # Get charset from meta if specified, default to utf-8
            charset = "utf-8"
            # TODO: Parse charset from meta (e.g., "text/gemini; charset=iso-8859-1")
            try:
                body = self.buffer.decode(charset)
            except UnicodeDecodeError as e:
                self.response_future.set_exception(e)
                return

        # Create and set the response
        response = GeminiResponse(
            status=self.status,  # type: ignore
            meta=self.meta,  # type: ignore
            body=body,
            url=self.url,
        )
        self.response_future.set_result(response)

    def _set_error(self, exc: Exception) -> None:
        """Set an error in the response future.

        Args:
            exc: The exception to set.
        """
        if not self.response_future.done():
            self.response_future.set_exception(exc)

    def get_peer_certificate(self) -> x509.Certificate | None:
        """Get the peer's certificate from the SSL transport.

        Returns:
            The peer's X.509 certificate, or None if not available.
        """
        if self.transport is None:
            return None

        # Get the SSL object from the transport
        ssl_object = self.transport.get_extra_info("ssl_object")
        if ssl_object is None:
            return None

        try:
            # Get certificate in DER binary format
            # Note: binary_form=True returns the certificate as DER-encoded bytes
            der_cert = ssl_object.getpeercert(binary_form=True)
            if der_cert:
                return x509.load_der_x509_certificate(der_cert)
        except Exception:
            # If we can't load the certificate, return None
            return None

        return None
