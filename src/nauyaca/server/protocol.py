"""Low-level Gemini server protocol implementation.

This module implements the Gemini server protocol using asyncio's
Protocol/Transport pattern for efficient, non-blocking I/O.
"""

import asyncio
import time
from collections.abc import Callable

from ..protocol.constants import CRLF, MAX_REQUEST_SIZE
from ..protocol.request import GeminiRequest
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode
from ..utils.logging import get_logger

logger = get_logger(__name__)


class GeminiServerProtocol(asyncio.Protocol):
    """Server-side protocol for handling Gemini requests.

    This class implements asyncio.Protocol for handling Gemini server connections.
    It manages the connection lifecycle, receives requests, and sends responses.

    The protocol follows the Gemini specification:
    1. Client connects via TLS (TLS is required by Gemini)
    2. Client sends URL + CRLF
    3. Server sends status + meta + CRLF
    4. Server sends response body (if status is 2x)
    5. Connection closes

    Attributes:
        request_handler: Callback function that takes a GeminiRequest and
            returns a GeminiResponse.
        transport: The transport handling the connection.
        buffer: Buffer for accumulating incoming data.
        peer_name: Remote peer address information.
    """

    def __init__(
        self, request_handler: Callable[[GeminiRequest], GeminiResponse]
    ) -> None:
        """Initialize the server protocol.

        Args:
            request_handler: Callback that processes requests and returns responses.
                Should have signature: (GeminiRequest) -> GeminiResponse
        """
        self.request_handler = request_handler
        self.transport: asyncio.Transport | None = None
        self.buffer = b""
        self.peer_name: tuple[str, int] | None = None
        self.request_start_time: float | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when a client connects.

        Args:
            transport: The transport handling this connection.
        """
        self.transport = transport  # type: ignore
        self.peer_name = self.transport.get_extra_info("peername")
        self.request_start_time = time.time()

        logger.debug(
            "connection_established",
            client_ip=self.peer_name[0] if self.peer_name else "unknown",
            client_port=self.peer_name[1] if self.peer_name else 0,
        )

    def data_received(self, data: bytes) -> None:
        """Called when data is received from the client.

        This method may be called multiple times as data arrives. We accumulate
        data in a buffer until we receive a complete request (URL + CRLF).

        Args:
            data: Raw bytes received from the client.
        """
        self.buffer += data

        # Check if request exceeds maximum size (prevent DoS)
        if len(self.buffer) > MAX_REQUEST_SIZE:
            self._send_error_response(
                StatusCode.BAD_REQUEST, "Request exceeds maximum size (1024 bytes)"
            )
            return

        # Check if we have a complete request (ends with CRLF)
        if CRLF in self.buffer:
            request_line, _ = self.buffer.split(CRLF, 1)
            self._handle_request(request_line)

    def _handle_request(self, request_line: bytes) -> None:
        """Process the Gemini request and send response.

        Args:
            request_line: The request line (URL) as bytes.
        """
        try:
            # Decode request line
            url = request_line.decode("utf-8")
        except UnicodeDecodeError:
            self._send_error_response(StatusCode.BAD_REQUEST, "Invalid UTF-8 encoding")
            return

        try:
            # Parse request
            request = GeminiRequest.from_line(url)
        except ValueError as e:
            self._send_error_response(StatusCode.BAD_REQUEST, str(e))
            return

        try:
            # Call request handler to get response
            response = self.request_handler(request)

            # Set the URL in the response for logging (if not already set)
            if not response.url:
                # Create a new response with the URL
                response = GeminiResponse(
                    status=response.status,
                    meta=response.meta,
                    body=response.body,
                    url=request.normalized_url,
                )
        except Exception as e:
            # Catch any handler errors and return 40 TEMPORARY FAILURE
            logger.error(
                "handler_error",
                client_ip=self.peer_name[0] if self.peer_name else "unknown",
                error=str(e),
                exception_type=type(e).__name__,
            )
            self._send_error_response(
                StatusCode.TEMPORARY_FAILURE, f"Server error: {str(e)}"
            )
            return

        # Send the response
        self._send_response(response)

    def _send_response(self, response: GeminiResponse) -> None:
        """Send a GeminiResponse to the client.

        Args:
            response: The response to send.
        """
        if not self.transport:
            return

        # Calculate request duration
        duration_ms = 0.0
        if self.request_start_time:
            duration_ms = (time.time() - self.request_start_time) * 1000

        # Log the request
        logger.info(
            "request_completed",
            client_ip=self.peer_name[0] if self.peer_name else "unknown",
            status=response.status,
            path=response.url or "unknown",
            body_size=len(response.body) if response.body else 0,
            duration_ms=round(duration_ms, 2),
        )

        # Build response header: <STATUS><SPACE><META><CRLF>
        header = f"{response.status} {response.meta}\r\n"
        self.transport.write(header.encode("utf-8"))

        # Send body if present (only for 2x success responses)
        if response.body:
            self.transport.write(response.body.encode("utf-8"))

        # Close connection (Gemini requirement: one request per connection)
        self.transport.close()

    def _send_error_response(self, status: StatusCode, message: str) -> None:
        """Send an error response and close the connection.

        Args:
            status: The status code to send.
            message: The error message (becomes the meta field).
        """
        if not self.transport:
            return

        response = GeminiResponse(status=status.value, meta=message)
        self._send_response(response)

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the connection is closed.

        Args:
            exc: Exception if connection closed due to error, None for clean close.
        """
        # Cleanup can be done here if needed
        self.transport = None
