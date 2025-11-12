"""Tests for GeminiServerProtocol."""

from unittest.mock import Mock

import pytest

from nauyaca.protocol.request import GeminiRequest
from nauyaca.protocol.response import GeminiResponse
from nauyaca.protocol.status import StatusCode
from nauyaca.server.protocol import GeminiServerProtocol


def create_mock_transport():
    """Helper to create a mock transport with proper peer info."""
    transport = Mock()
    transport.get_extra_info.return_value = ("127.0.0.1", 12345)
    return transport


class TestGeminiServerProtocol:
    """Test GeminiServerProtocol class."""

    def test_connection_made(self):
        """Test connection_made callback."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Hello")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()

        protocol.connection_made(transport)

        assert protocol.transport is transport
        assert protocol.peer_name == ("127.0.0.1", 12345)

    def test_simple_request_response(self):
        """Test handling a simple valid request."""

        def handler(request):
            assert request.hostname == "example.com"
            assert request.path == "/"
            return GeminiResponse(
                status=20, meta="text/gemini", body="# Welcome\nHello World"
            )

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        # Send request
        protocol.data_received(b"gemini://example.com/\r\n")

        # Verify response was sent
        assert transport.write.call_count == 2  # Header + body
        header_call = transport.write.call_args_list[0]
        body_call = transport.write.call_args_list[1]

        assert b"20 text/gemini\r\n" in header_call[0]
        assert b"# Welcome\nHello World" in body_call[0]

        # Verify connection was closed
        transport.close.assert_called_once()

    def test_request_with_path_and_query(self):
        """Test handling request with path and query."""

        def handler(request):
            assert request.path == "/search"
            assert request.query == "q=test"
            return GeminiResponse(status=20, meta="text/gemini", body="Results")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        protocol.data_received(b"gemini://example.com/search?q=test\r\n")

        transport.close.assert_called_once()

    def test_fragmented_request(self):
        """Test that fragmented data is buffered correctly."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="OK")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        # Send request in fragments
        protocol.data_received(b"gemini://exa")
        protocol.data_received(b"mple.com/")
        protocol.data_received(b"\r\n")

        # Should only send response after complete request
        transport.close.assert_called_once()
        assert transport.write.call_count == 2

    def test_error_response_invalid_utf8(self):
        """Test error response for invalid UTF-8 encoding."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="OK")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        # Send invalid UTF-8
        protocol.data_received(b"\xff\xfe invalid \r\n")

        # Should send BAD_REQUEST error
        header_call = transport.write.call_args_list[0]
        assert b"59 " in header_call[0][0]  # Status 59 = BAD_REQUEST
        assert b"UTF-8" in header_call[0][0]
        transport.close.assert_called_once()

    def test_error_response_invalid_url(self):
        """Test error response for invalid URL."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="OK")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        # Send invalid URL (wrong scheme)
        protocol.data_received(b"http://example.com/\r\n")

        # Should send BAD_REQUEST error
        header_call = transport.write.call_args_list[0]
        assert b"59 " in header_call[0][0]  # Status 59 = BAD_REQUEST
        transport.close.assert_called_once()

    def test_error_response_request_too_long(self):
        """Test error response for request exceeding max size."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="OK")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        # Send request larger than 1024 bytes
        long_request = b"gemini://example.com/" + b"a" * 1100 + b"\r\n"
        protocol.data_received(long_request)

        # Should send BAD_REQUEST error
        header_call = transport.write.call_args_list[0]
        assert b"59 " in header_call[0][0]  # Status 59 = BAD_REQUEST
        assert b"maximum size" in header_call[0][0]
        transport.close.assert_called_once()

    def test_handler_exception(self):
        """Test that handler exceptions result in TEMPORARY_FAILURE."""

        def handler(request):
            raise RuntimeError("Something went wrong!")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        protocol.data_received(b"gemini://example.com/\r\n")

        # Should send TEMPORARY_FAILURE error
        header_call = transport.write.call_args_list[0]
        assert b"40 " in header_call[0][0]  # Status 40 = TEMPORARY_FAILURE
        assert b"Server error" in header_call[0][0]
        transport.close.assert_called_once()

    def test_response_without_body(self):
        """Test sending response without body (e.g., redirect)."""

        def handler(request):
            return GeminiResponse(status=30, meta="gemini://example.com/new", body=None)

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        protocol.data_received(b"gemini://example.com/old\r\n")

        # Should only send header (no body)
        assert transport.write.call_count == 1
        header_call = transport.write.call_args_list[0]
        assert b"30 gemini://example.com/new\r\n" in header_call[0]
        transport.close.assert_called_once()

    def test_connection_lost(self):
        """Test connection_lost callback."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="OK")

        protocol = GeminiServerProtocol(handler)
        transport = create_mock_transport()
        protocol.connection_made(transport)

        # Call connection_lost
        protocol.connection_lost(None)

        # Should clean up transport reference
        assert protocol.transport is None
