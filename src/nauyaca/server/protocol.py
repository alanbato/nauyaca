"""Low-level Gemini and Titan server protocol implementation.

This module implements the Gemini and Titan server protocols using asyncio's
Protocol/Transport pattern for efficient, non-blocking I/O.

Supports both protocols on the same port:
- Gemini (gemini://): Read-only content fetch
- Titan (titan://): Upload content to server
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from cryptography import x509

from ..protocol.constants import CRLF, MAX_REQUEST_SIZE
from ..protocol.request import GeminiRequest, TitanRequest
from ..protocol.response import GeminiResponse
from ..protocol.status import StatusCode
from ..utils.logging import get_logger

if TYPE_CHECKING:
    from .handler import UploadHandler

logger = get_logger(__name__)

# Connection timeout in seconds
REQUEST_TIMEOUT = 30.0


class GeminiServerProtocol(asyncio.Protocol):
    """Server-side protocol for handling Gemini and Titan requests.

    This class implements asyncio.Protocol for handling server connections.
    It manages the connection lifecycle, receives requests, and sends responses.
    Supports both Gemini (read) and Titan (upload) protocols on the same port.

    The protocol flow:
    1. Client connects via TLS (TLS is required)
    2. Client sends URL + CRLF
       - For Gemini: URL starts with gemini://
       - For Titan: URL starts with titan:// and includes ;size=N parameter
    3. For Titan: Client sends content bytes (N bytes as specified)
    4. Server sends status + meta + CRLF
    5. Server sends response body (if status is 2x)
    6. Connection closes

    Attributes:
        request_handler: Callback function that takes a GeminiRequest and
            returns a GeminiResponse.
        upload_handler: Optional handler for Titan uploads.
        transport: The transport handling the connection.
        buffer: Buffer for accumulating incoming data.
        peer_name: Remote peer address information.
    """

    def __init__(
        self,
        request_handler: Callable[
            [GeminiRequest], GeminiResponse | Awaitable[GeminiResponse]
        ],
        middleware: object = None,
        upload_handler: "UploadHandler | None" = None,
    ) -> None:
        """Initialize the server protocol.

        Args:
            request_handler: Callback that processes requests and returns responses.
                Should have signature: (GeminiRequest) -> GeminiResponse
                or async signature: (GeminiRequest) -> Awaitable[GeminiResponse]
            middleware: Optional middleware chain for request processing.
            upload_handler: Optional handler for Titan uploads. If None, Titan
                requests will be rejected with 50 PERMANENT FAILURE.
        """
        self.request_handler = request_handler
        self.middleware = middleware
        self.upload_handler = upload_handler
        self.transport: asyncio.Transport | None = None
        self.buffer = b""
        self.peer_name: tuple[str, int] | None = None
        self.request_start_time: float | None = None
        self.timeout_handle: asyncio.TimerHandle | None = None

        # Titan-specific state
        self.titan_request: TitanRequest | None = None
        self.url_line_received = False
        self.awaiting_titan_content = False

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
        data in a buffer until we receive a complete request.

        For Gemini: URL + CRLF
        For Titan: URL + CRLF + content_bytes

        Args:
            data: Raw bytes received from the client.
        """
        self.buffer += data

        # State 1: Waiting for URL line (Gemini or Titan)
        if not self.url_line_received:
            # Check if buffer exceeds maximum size without CRLF (DoS protection)
            if len(self.buffer) > MAX_REQUEST_SIZE and CRLF not in self.buffer:
                self._send_error_response(
                    StatusCode.BAD_REQUEST, "Request exceeds maximum size (1024 bytes)"
                )
                return

            # Check if we have a complete URL line (ends with CRLF)
            if CRLF in self.buffer:
                url_line, remaining = self.buffer.split(CRLF, 1)

                # Check if URL line itself exceeds maximum size
                # MAX_REQUEST_SIZE includes CRLF, so check url_line + 2
                if len(url_line) + 2 > MAX_REQUEST_SIZE:
                    self._send_error_response(
                        StatusCode.BAD_REQUEST,
                        "Request exceeds maximum size (1024 bytes)",
                    )
                    return

                self.buffer = remaining
                self.url_line_received = True

                try:
                    url = url_line.decode("utf-8")
                except UnicodeDecodeError:
                    self._send_error_response(
                        StatusCode.BAD_REQUEST, "Invalid UTF-8 encoding"
                    )
                    return

                # Protocol detection: Titan vs Gemini
                if url.startswith("titan://"):
                    self._handle_titan_url(url)
                else:
                    # Cancel timeout - we got the complete Gemini request
                    if self.timeout_handle:
                        self.timeout_handle.cancel()
                        self.timeout_handle = None
                    self._handle_gemini_request(url)
            return

        # State 2: Waiting for Titan content
        if self.awaiting_titan_content and self.titan_request:
            if len(self.buffer) >= self.titan_request.size:
                # Cancel timeout - we got all the content
                if self.timeout_handle:
                    self.timeout_handle.cancel()
                    self.timeout_handle = None

                # Extract exactly the expected number of bytes
                self.titan_request.content = self.buffer[: self.titan_request.size]
                self._process_titan_upload()

    def _handle_gemini_request(self, url: str) -> None:
        """Process a Gemini request and send response.

        Args:
            url: The URL string (already decoded).
        """
        try:
            # Parse request
            request = GeminiRequest.from_line(url)
        except ValueError as e:
            self._send_error_response(StatusCode.BAD_REQUEST, str(e))
            return

        # Extract client certificate if present
        client_cert = self.get_peer_certificate()
        client_cert_fingerprint: str | None = None
        if client_cert:
            from ..security.certificates import get_certificate_fingerprint

            client_cert_fingerprint = get_certificate_fingerprint(client_cert)

        # Attach certificate info to request
        request.client_cert = client_cert
        request.client_cert_fingerprint = client_cert_fingerprint

        client_ip = self.peer_name[0] if self.peer_name else "unknown"

        # Process through middleware if present
        if self.middleware:
            try:
                # Create async task for middleware processing
                task = asyncio.create_task(
                    self.middleware.process_request(
                        request.normalized_url, client_ip, client_cert_fingerprint
                    )
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
        # FIX: Handle both text (str) and binary (bytes) content
        if response.body:
            if isinstance(response.body, bytes):
                self.transport.write(response.body)
            else:
                self.transport.write(response.body.encode("utf-8"))

        # Close connection (Gemini/Titan: one request per connection)
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
        Supports both sync and async request handlers.

        Args:
            request: The parsed Gemini request.
            client_ip: The client's IP address.
        """
        try:
            # Call request handler to get response
            result = self.request_handler(request)

            # Check if handler returned a coroutine (async handler)
            if asyncio.iscoroutine(result):
                try:
                    # Create async task for handler processing
                    task = asyncio.create_task(result)
                    # Add callback to handle result when task completes
                    task.add_done_callback(
                        lambda t: self._handle_async_handler_result(t, request, client_ip)
                    )
                    # Return early - callback will handle the rest
                    return
                except RuntimeError:
                    # No event loop running (probably in tests)
                    logger.warning(
                        "async_handler_skipped",
                        client_ip=client_ip,
                        reason="no_event_loop",
                    )
                    self._send_error_response(
                        StatusCode.TEMPORARY_FAILURE,
                        "Server error: async handler requires event loop",
                    )
                    return

            # Sync handler - result is the response directly
            response = result

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

    def _handle_async_handler_result(
        self, task: asyncio.Task, request: GeminiRequest, client_ip: str
    ) -> None:
        """Handle the result of an async request handler.

        This is called as a callback when the async handler task completes.

        Args:
            task: The completed asyncio task.
            request: The parsed Gemini request.
            client_ip: The client's IP address.
        """
        try:
            # Get the response from the completed task
            response = task.result()

            # Set the URL in the response for logging (if not already set)
            if not response.url:
                response = GeminiResponse(
                    status=response.status,
                    meta=response.meta,
                    body=response.body,
                    url=request.normalized_url,
                )

            # Send the response
            self._send_response(response)

        except Exception as e:
            logger.error(
                "async_handler_error",
                client_ip=client_ip,
                error=str(e),
                exception_type=type(e).__name__,
            )
            self._send_error_response(
                StatusCode.TEMPORARY_FAILURE, f"Server error: {str(e)}"
            )

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

    def get_peer_certificate(self) -> x509.Certificate | None:
        """Get the client's certificate from the SSL transport.

        Returns:
            The client's X.509 certificate, or None if not available
            (e.g., client didn't present a certificate or connection isn't TLS).
        """
        if self.transport is None:
            return None

        # Get the SSL object from the transport
        ssl_object = self.transport.get_extra_info("ssl_object")
        if ssl_object is None:
            return None

        try:
            # Get certificate in DER binary format
            der_cert = ssl_object.getpeercert(binary_form=True)
            if der_cert:
                return x509.load_der_x509_certificate(der_cert)
        except Exception:
            # If we can't load the certificate, return None
            return None

        return None

    # -------------------------------------------------------------------------
    # Titan Protocol Support
    # -------------------------------------------------------------------------

    def _handle_titan_url(self, url: str) -> None:
        """Parse a Titan URL and prepare to receive content.

        Args:
            url: The Titan URL string (already decoded).
        """
        # Check if uploads are supported
        if not self.upload_handler:
            self._send_error_response(
                StatusCode.PERMANENT_FAILURE,
                "Titan uploads not supported on this server",
            )
            return

        try:
            self.titan_request = TitanRequest.from_line(url)
        except ValueError as e:
            self._send_error_response(StatusCode.BAD_REQUEST, f"Invalid Titan URL: {e}")
            return

        # Extract client certificate if present
        client_cert = self.get_peer_certificate()
        if client_cert:
            from ..security.certificates import get_certificate_fingerprint

            self.titan_request.client_cert = client_cert
            self.titan_request.client_cert_fingerprint = get_certificate_fingerprint(
                client_cert
            )

        # If size is 0 (delete request), process immediately
        if self.titan_request.is_delete():
            # Cancel timeout
            if self.timeout_handle:
                self.timeout_handle.cancel()
                self.timeout_handle = None
            self._process_titan_upload()
        else:
            # Wait for content bytes
            self.awaiting_titan_content = True
            # Check if we already have enough content in the buffer
            if len(self.buffer) >= self.titan_request.size:
                if self.timeout_handle:
                    self.timeout_handle.cancel()
                    self.timeout_handle = None
                self.titan_request.content = self.buffer[: self.titan_request.size]
                self._process_titan_upload()

    def _process_titan_upload(self) -> None:
        """Process the Titan upload through the upload handler."""
        if not self.upload_handler or not self.titan_request:
            self._send_error_response(
                StatusCode.TEMPORARY_FAILURE, "Upload handler error"
            )
            return

        client_ip = self.peer_name[0] if self.peer_name else "unknown"

        try:
            # Create async task for upload handler
            task = asyncio.create_task(
                self.upload_handler.handle_upload(self.titan_request)
            )
            task.add_done_callback(
                lambda t: self._handle_titan_upload_result(t, client_ip)
            )
        except RuntimeError:
            # No event loop running (probably in tests)
            logger.warning(
                "titan_upload_skipped",
                client_ip=client_ip,
                reason="no_event_loop",
            )
            self._send_error_response(
                StatusCode.TEMPORARY_FAILURE,
                "Server error: upload handler requires event loop",
            )

    def _handle_titan_upload_result(self, task: asyncio.Task, client_ip: str) -> None:
        """Handle the result of a Titan upload.

        Args:
            task: The completed asyncio task.
            client_ip: The client's IP address.
        """
        try:
            response = task.result()

            # Set URL for logging if not already set
            if not response.url and self.titan_request:
                response = GeminiResponse(
                    status=response.status,
                    meta=response.meta,
                    body=response.body,
                    url=self.titan_request.raw_url,
                )

            self._send_response(response)

        except Exception as e:
            logger.error(
                "titan_upload_error",
                client_ip=client_ip,
                error=str(e),
                exception_type=type(e).__name__,
            )
            self._send_error_response(
                StatusCode.TEMPORARY_FAILURE, f"Upload error: {str(e)}"
            )
