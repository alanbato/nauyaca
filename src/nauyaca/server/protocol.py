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

# Connection timeout in seconds
REQUEST_TIMEOUT = 30.0


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
        self,
        request_handler: Callable[[GeminiRequest], GeminiResponse],
        middleware: object = None,
    ) -> None:
        """Initialize the server protocol.

        Args:
            request_handler: Callback that processes requests and returns responses.
                Should have signature: (GeminiRequest) -> GeminiResponse
            middleware: Optional middleware chain for request processing.
        """
        self.request_handler = request_handler
        self.middleware = middleware
        self.transport: asyncio.Transport | None = None
        self.buffer = b""
        self.peer_name: tuple[str, int] | None = None
        self.request_start_time: float | None = None
        self.timeout_handle: asyncio.TimerHandle | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when a client connects.

        Args:
            transport: The transport handling this connection.
        """
        self.transport = transport  # type: ignore[assignment]
        if self.transport:
            self.peer_name = self.transport.get_extra_info("peername")
        self.request_start_time = time.time()

        # Set timeout for receiving request
        try:
            loop = asyncio.get_running_loop()
            self.timeout_handle = loop.call_later(REQUEST_TIMEOUT, self._handle_timeout)
        except RuntimeError:
            # No event loop running (probably in tests)
            self.timeout_handle = None

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
            # Cancel timeout - we got the request
            if self.timeout_handle:
                self.timeout_handle.cancel()
                self.timeout_handle = None

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

        client_ip = self.peer_name[0] if self.peer_name else "unknown"

        # Process through middleware if present
        if self.middleware:
            try:
                # Create async task for middleware processing
                task = asyncio.create_task(
                    self.middleware.process_request(request.normalized_url, client_ip)
                )
                # Add callback to handle result when task completes
                # Use lambda to pass request and client_ip to callback
                task.add_done_callback(
                    lambda t: self._handle_middleware_result(t, request, client_ip)
                )
                # Return early - callback will handle the rest
                return
            except RuntimeError:
                # No event loop running (probably in tests) - skip middleware
                logger.warning(
                    "middleware_skipped",
                    client_ip=client_ip,
                    reason="no_event_loop",
                )

        # No middleware or middleware skipped - route directly
        self._route_request(request, client_ip)

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

    def _handle_timeout(self) -> None:
        """Handle request timeout."""
        if self.transport and not self.transport.is_closing():
            if self.request_start_time:
                duration = time.time() - self.request_start_time
            else:
                duration = 0
            logger.warning(
                "request_timeout",
                client_ip=self.peer_name[0] if self.peer_name else "unknown",
                duration_ms=round(duration * 1000, 2),
            )
            # Send timeout response
            response = "40 Request timeout\r\n"
            self.transport.write(response.encode("utf-8"))
            self.transport.close()

    def _route_request(self, request: GeminiRequest, client_ip: str) -> None:
        """Route the request and send response.

        This method handles the actual request routing after middleware processing.

        Args:
            request: The parsed Gemini request.
            client_ip: The client's IP address.
        """
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
                client_ip=client_ip,
                error=str(e),
                exception_type=type(e).__name__,
            )
            self._send_error_response(
                StatusCode.TEMPORARY_FAILURE, f"Server error: {str(e)}"
            )
            return

        # Send the response
        self._send_response(response)

    def _handle_middleware_result(
        self, task: asyncio.Task, request: GeminiRequest, client_ip: str
    ) -> None:
        """Handle the result of middleware processing.

        This is called as a callback when the middleware task completes.

        Args:
            task: The completed asyncio task.
            request: The parsed Gemini request.
            client_ip: The client's IP address.
        """
        try:
            # Get the result from the completed task
            allow, error_response = task.result()

            if not allow:
                # Middleware rejected request - send error response
                if self.transport and error_response:
                    self.transport.write(error_response.encode("utf-8"))
                    self.transport.close()
                return

            # Middleware allowed request - continue routing
            self._route_request(request, client_ip)

        except Exception as e:
            logger.error(
                "middleware_error",
                client_ip=client_ip,
                error=str(e),
                exception_type=type(e).__name__,
            )
            self._send_error_response(StatusCode.TEMPORARY_FAILURE, "Middleware error")

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the connection is closed.

        Args:
            exc: Exception if connection closed due to error, None for clean close.
        """
        # Cancel timeout if still active
        if self.timeout_handle:
            self.timeout_handle.cancel()
            self.timeout_handle = None

        # Cleanup
        self.transport = None
