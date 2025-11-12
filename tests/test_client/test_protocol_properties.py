"""Property-based tests for GeminiClientProtocol using Hypothesis."""

import asyncio
from unittest.mock import Mock

from hypothesis import assume, given
from hypothesis import strategies as st

from nauyaca.client.protocol import GeminiClientProtocol
from nauyaca.protocol.constants import CRLF


class TestProtocolDataHandlingProperties:
    """Property-based tests for protocol data buffering and handling."""

    @given(st.integers(min_value=10, max_value=69), st.text(max_size=100))
    async def test_single_chunk_header_parsing(self, status, meta):
        """Headers sent in a single chunk should parse correctly."""
        # Meta cannot contain CRLF as it would break the protocol
        assume("\r\n" not in meta)
        assume("\r" not in meta)
        assume("\n" not in meta)

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Send complete header in one chunk
        header = f"{status} {meta}\r\n"
        protocol.data_received(header.encode())

        assert protocol.header_received
        assert protocol.status == status
        assert protocol.meta == meta

    @given(
        st.integers(min_value=10, max_value=69),
        st.text(max_size=100),
        st.integers(min_value=1, max_value=50),
    )
    async def test_chunked_header_parsing(self, status, meta, chunk_size):
        """Headers sent in multiple chunks should parse correctly."""
        # Meta cannot contain newlines as it would break the protocol
        assume("\r\n" not in meta)
        assume("\r" not in meta)
        assume("\n" not in meta)

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Build header and split into chunks
        header = f"{status} {meta}\r\n".encode()

        # Send in chunks
        for i in range(0, len(header), chunk_size):
            chunk = header[i : i + chunk_size]
            protocol.data_received(chunk)

        # Should eventually parse
        assert protocol.header_received
        assert protocol.status == status
        assert protocol.meta == meta

    @given(st.integers(min_value=20, max_value=29), st.text(max_size=1000))
    async def test_body_accumulation(self, status, body_text):
        """Response bodies should accumulate correctly across chunks."""
        assume("\r\n" not in body_text)  # Avoid CRLF in body for this test

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Send header
        protocol.data_received(f"{status} text/plain\r\n".encode())

        # Send body in chunks
        body_bytes = body_text.encode()
        chunk_size = max(1, len(body_bytes) // 5)

        for i in range(0, len(body_bytes), chunk_size):
            chunk = body_bytes[i : i + chunk_size]
            protocol.data_received(chunk)

        # Close and verify
        protocol.connection_lost(None)
        response = await future

        assert response.body == body_text

    @given(st.lists(st.binary(min_size=1, max_size=100), min_size=1, max_size=10))
    async def test_arbitrary_chunk_boundaries(self, chunks):
        """Protocol should handle arbitrary chunk boundaries correctly."""
        # Build a valid response with random chunk boundaries
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Create a valid response
        response_data = b"20 text/plain\r\nHello World"

        # Send in random chunks
        offset = 0
        for chunk_size in [len(c) for c in chunks]:
            if offset >= len(response_data):
                break
            chunk = response_data[offset : offset + chunk_size]
            protocol.data_received(chunk)
            offset += chunk_size

        # Send remainder if any
        if offset < len(response_data):
            protocol.data_received(response_data[offset:])

        # Should parse successfully
        protocol.connection_lost(None)
        response = await future

        assert response.status == 20

    @given(st.integers(min_value=10, max_value=69))
    async def test_empty_meta_field(self, status):
        """Protocol should handle empty meta fields correctly."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Send header with empty meta (just status and CRLF)
        protocol.data_received(f"{status} \r\n".encode())

        assert protocol.header_received
        assert protocol.status == status
        assert protocol.meta == ""

    @given(st.text(min_size=1, max_size=50))
    async def test_url_preserved_in_request(self, path):
        """The URL sent in the request should match the initialized URL."""
        # Build a simple URL
        url = f"gemini://example.com/{path}"
        assume(len(url.encode()) < 1000)  # Keep reasonable size

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol(url, future)

        transport = Mock()
        protocol.connection_made(transport)

        # Check what was written
        transport.write.assert_called_once()
        sent_data = transport.write.call_args[0][0]

        assert sent_data == f"{url}\r\n".encode()

    @given(st.integers(min_value=30, max_value=69))
    async def test_non_success_status_closes_immediately(self, status):
        """Non-2x status codes should trigger immediate connection close."""
        assume(not (20 <= status < 30))

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Send non-success header
        protocol.data_received(f"{status} Some meta\r\n".encode())

        # Should close immediately
        transport.close.assert_called_once()

    @given(st.text(max_size=100))
    async def test_buffer_reset_between_header_and_body(self, body_text):
        """Buffer should be properly managed between header and body."""
        assume("\r\n" not in body_text)

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        protocol = GeminiClientProtocol("gemini://example.com/", future)

        transport = Mock()
        protocol.connection_made(transport)

        # Send header + body together
        full_data = f"20 text/plain\r\n{body_text}".encode()
        protocol.data_received(full_data)

        # Close connection
        protocol.connection_lost(None)
        response = await future

        # Body should not include header
        assert response.body == body_text
        assert response.status == 20
