"""Tests for protocol constants."""

import pytest

from nauyaca.protocol.constants import (
    CRLF,
    DEFAULT_PORT,
    MAX_REDIRECTS,
    MAX_REQUEST_SIZE,
    MAX_RESPONSE_BODY_SIZE,
    MIME_TYPE_GEMTEXT,
    STATUS_CLIENT_CERT_REQUIRED,
    STATUS_INPUT,
    STATUS_PERMANENT_FAILURE,
    STATUS_REDIRECT,
    STATUS_SUCCESS,
    STATUS_TEMPORARY_FAILURE,
)


class TestConstants:
    """Test protocol constants."""

    def test_default_port(self):
        """Test that default port is 1965."""
        assert DEFAULT_PORT == 1965

    def test_max_request_size(self):
        """Test that max request size is 1024 bytes."""
        assert MAX_REQUEST_SIZE == 1024

    def test_max_redirects(self):
        """Test that max redirects is 5."""
        assert MAX_REDIRECTS == 5

    def test_crlf(self):
        """Test CRLF is correct."""
        assert CRLF == b"\r\n"

    def test_mime_type_gemtext(self):
        """Test gemtext MIME type."""
        assert MIME_TYPE_GEMTEXT == "text/gemini"

    def test_status_ranges(self):
        """Test status code ranges are correct."""
        assert 10 in STATUS_INPUT
        assert 19 in STATUS_INPUT
        assert 20 not in STATUS_INPUT

        assert 20 in STATUS_SUCCESS
        assert 29 in STATUS_SUCCESS
        assert 30 not in STATUS_SUCCESS

        assert 30 in STATUS_REDIRECT
        assert 39 in STATUS_REDIRECT
        assert 40 not in STATUS_REDIRECT

        assert 40 in STATUS_TEMPORARY_FAILURE
        assert 49 in STATUS_TEMPORARY_FAILURE
        assert 50 not in STATUS_TEMPORARY_FAILURE

        assert 50 in STATUS_PERMANENT_FAILURE
        assert 59 in STATUS_PERMANENT_FAILURE
        assert 60 not in STATUS_PERMANENT_FAILURE

        assert 60 in STATUS_CLIENT_CERT_REQUIRED
        assert 69 in STATUS_CLIENT_CERT_REQUIRED
        assert 70 not in STATUS_CLIENT_CERT_REQUIRED
