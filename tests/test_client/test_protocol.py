"""Tests for GeminiClientProtocol."""

import asyncio
from unittest.mock import Mock

import pytest

from nauyaca.client.protocol import GeminiClientProtocol
from nauyaca.protocol.constants import CRLF


class TestGeminiClientProtocol:
    """Test GeminiClientProtocol."""

    async def test_connection_made_sends_request(self):
        """Test that connection_made sends the URL request."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Verify request was sent
        transport.write.assert_called_once()
        sent_data = transport.write.call_args[0][0]
        assert sent_data == b"gemini://example.com/\r\n"

    async def test_data_received_success_response(self):
        """Test receiving a success response."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send response header
        protocol.data_received(b"20 text/gemini\r\n")

        # Verify header was parsed
        assert protocol.status == 20
        assert protocol.meta == "text/gemini"
        assert protocol.header_received is True

        # Send response body
        protocol.data_received(b"# Hello World\n")

        # Close connection (triggers connection_lost)
        protocol.connection_lost(None)

        # Verify response
        response = await future
        assert response.status == 20
        assert response.meta == "text/gemini"
        assert response.body == "# Hello World\n"

    async def test_data_received_in_chunks(self):
        """Test receiving data in multiple chunks."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send response in chunks
        protocol.data_received(b"20 text")
        protocol.data_received(b"/gemini\r\n")

        assert protocol.header_received is True
        assert protocol.status == 20
        assert protocol.meta == "text/gemini"

        # Send body in chunks
        protocol.data_received(b"Hello ")
        protocol.data_received(b"World")

        # Close connection
        protocol.connection_lost(None)

        # Verify response
        response = await future
        assert response.body == "Hello World"

    async def test_non_success_closes_immediately(self):
        """Test that non-success responses close immediately."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send error response
        protocol.data_received(b"51 Not found\r\n")

        # Verify connection was closed
        transport.close.assert_called_once()

        # Verify response (no body expected)
        protocol.connection_lost(None)
        response = await future
        assert response.status == 51
        assert response.meta == "Not found"
        assert response.body is None

    async def test_redirect_response(self):
        """Test handling redirect responses."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send redirect response
        protocol.data_received(b"30 gemini://example.com/new\r\n")

        # Verify connection was closed (redirects have no body)
        transport.close.assert_called_once()

        # Verify response
        protocol.connection_lost(None)
        response = await future
        assert response.status == 30
        assert response.meta == "gemini://example.com/new"
        assert response.body is None

    async def test_invalid_status_code(self):
        """Test handling invalid status code."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send invalid status
        protocol.data_received(b"invalid text/gemini\r\n")

        # Verify error was set
        protocol.connection_lost(None)
        with pytest.raises(ValueError, match="Invalid status code"):
            await future

    async def test_connection_closed_before_header(self):
        """Test handling connection closed before receiving header."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Close connection without sending data
        protocol.connection_lost(None)

        # Verify error
        with pytest.raises(ConnectionError, match="closed before receiving response"):
            await future

    async def test_connection_error(self):
        """Test handling connection errors."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Simulate connection error
        error = ConnectionError("Network error")
        protocol.connection_lost(error)

        # Verify error was propagated
        with pytest.raises(ConnectionError, match="Network error"):
            await future

    async def test_response_body_size_exceeded(self):
        """Test handling response body that exceeds maximum size."""
        from nauyaca.protocol.constants import MAX_RESPONSE_BODY_SIZE

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send success header
        protocol.data_received(b"20 text/gemini\r\n")

        # Send body that exceeds max size
        # We need to send enough data to exceed MAX_RESPONSE_BODY_SIZE
        large_chunk = b"x" * (MAX_RESPONSE_BODY_SIZE + 1)
        protocol.data_received(large_chunk)

        # Verify transport was closed
        transport.close.assert_called()

        # Verify error was set
        protocol.connection_lost(None)
        with pytest.raises(Exception, match="Response body exceeds maximum size"):
            await future

    async def test_empty_header_line(self):
        """Test handling completely empty header line."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send empty header (just CRLF)
        protocol.data_received(b"\r\n")

        # Verify connection was closed
        transport.close.assert_called()

        # Verify error was set
        protocol.connection_lost(None)
        with pytest.raises(ValueError, match="Invalid status code"):
            await future

    async def test_status_code_out_of_range_low(self):
        """Test handling status code below valid range."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send status code below 10
        protocol.data_received(b"05 text/gemini\r\n")

        # Verify connection was closed
        transport.close.assert_called()

        # Verify error was set
        protocol.connection_lost(None)
        with pytest.raises(ValueError, match="Status code out of range"):
            await future

    async def test_status_code_out_of_range_high(self):
        """Test handling status code above valid range."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send status code above 69
        protocol.data_received(b"70 text/gemini\r\n")

        # Verify connection was closed
        transport.close.assert_called()

        # Verify error was set
        protocol.connection_lost(None)
        with pytest.raises(ValueError, match="Status code out of range"):
            await future

    async def test_unicode_decode_error_in_body(self):
        """Test handling invalid UTF-8 in response body."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Send success header
        protocol.data_received(b"20 text/gemini\r\n")

        # Send invalid UTF-8 in body
        # 0xFF is not valid UTF-8
        protocol.data_received(b"Hello \xff World")

        # Close connection
        protocol.connection_lost(None)

        # Verify UnicodeDecodeError was raised
        with pytest.raises(UnicodeDecodeError):
            await future

    async def test_eof_received(self):
        """Test eof_received returns False to close connection."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        # Mock transport
        transport = Mock()
        protocol.connection_made(transport)

        # Call eof_received
        result = protocol.eof_received()

        # Should return False to indicate full connection close
        assert result is False
