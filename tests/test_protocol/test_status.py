"""Tests for status code utilities."""

import pytest

from nauyaca.protocol.status import (
    StatusCode,
    interpret_status,
    is_error,
    is_input_required,
    is_redirect,
    is_success,
)


class TestStatusCode:
    """Test StatusCode enum."""

    def test_status_code_values(self):
        """Test that status codes have correct values."""
        assert StatusCode.INPUT == 10
        assert StatusCode.SENSITIVE_INPUT == 11
        assert StatusCode.SUCCESS == 20
        assert StatusCode.REDIRECT_TEMPORARY == 30
        assert StatusCode.REDIRECT_PERMANENT == 31
        assert StatusCode.TEMPORARY_FAILURE == 40
        assert StatusCode.SERVER_UNAVAILABLE == 41
        assert StatusCode.CGI_ERROR == 42
        assert StatusCode.PROXY_ERROR == 43
        assert StatusCode.SLOW_DOWN == 44
        assert StatusCode.PERMANENT_FAILURE == 50
        assert StatusCode.NOT_FOUND == 51
        assert StatusCode.GONE == 52
        assert StatusCode.PROXY_REQUEST_REFUSED == 53
        assert StatusCode.BAD_REQUEST == 59
        assert StatusCode.CLIENT_CERT_REQUIRED == 60
        assert StatusCode.CERT_NOT_AUTHORIZED == 61
        assert StatusCode.CERT_NOT_VALID == 62


class TestInterpretStatus:
    """Test interpret_status function."""

    @pytest.mark.parametrize(
        "status,expected",
        [
            (10, "INPUT"),
            (11, "INPUT"),
            (19, "INPUT"),
            (20, "SUCCESS"),
            (29, "SUCCESS"),
            (30, "REDIRECT"),
            (39, "REDIRECT"),
            (40, "TEMPORARY FAILURE"),
            (49, "TEMPORARY FAILURE"),
            (50, "PERMANENT FAILURE"),
            (59, "PERMANENT FAILURE"),
            (60, "CLIENT CERTIFICATE REQUIRED"),
            (69, "CLIENT CERTIFICATE REQUIRED"),
            (5, "UNKNOWN"),
            (70, "UNKNOWN"),
        ],
    )
    def test_interpret_status(self, status, expected):
        """Test status code interpretation."""
        assert interpret_status(status) == expected


class TestStatusChecks:
    """Test status check utility functions."""

    @pytest.mark.parametrize("status", [20, 21, 29])
    def test_is_success_true(self, status):
        """Test is_success returns True for 2x codes."""
        assert is_success(status) is True

    @pytest.mark.parametrize("status", [10, 30, 40, 50, 60])
    def test_is_success_false(self, status):
        """Test is_success returns False for non-2x codes."""
        assert is_success(status) is False

    @pytest.mark.parametrize("status", [30, 31, 39])
    def test_is_redirect_true(self, status):
        """Test is_redirect returns True for 3x codes."""
        assert is_redirect(status) is True

    @pytest.mark.parametrize("status", [20, 40, 50, 60])
    def test_is_redirect_false(self, status):
        """Test is_redirect returns False for non-3x codes."""
        assert is_redirect(status) is False

    @pytest.mark.parametrize("status", [10, 11, 19])
    def test_is_input_required_true(self, status):
        """Test is_input_required returns True for 1x codes."""
        assert is_input_required(status) is True

    @pytest.mark.parametrize("status", [20, 30, 40, 50, 60])
    def test_is_input_required_false(self, status):
        """Test is_input_required returns False for non-1x codes."""
        assert is_input_required(status) is False

    @pytest.mark.parametrize("status", [40, 44, 49, 50, 51, 59, 60, 62, 69])
    def test_is_error_true(self, status):
        """Test is_error returns True for 4x, 5x, 6x codes."""
        assert is_error(status) is True

    @pytest.mark.parametrize("status", [10, 20, 30])
    def test_is_error_false(self, status):
        """Test is_error returns False for non-error codes."""
        assert is_error(status) is False
