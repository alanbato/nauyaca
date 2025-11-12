"""Property-based tests for status code handling using Hypothesis."""

from hypothesis import assume, given
from hypothesis import strategies as st

from nauyaca.protocol.status import (
    interpret_status,
    is_error,
    is_input_required,
    is_redirect,
    is_success,
)


class TestStatusCodeProperties:
    """Property-based tests for status code interpretation."""

    @given(st.integers(min_value=10, max_value=69))
    def test_all_valid_status_codes_interpreted(self, status):
        """All valid Gemini status codes (10-69) should be interpretable."""
        result = interpret_status(status)
        assert result in (
            "INPUT",
            "SUCCESS",
            "REDIRECT",
            "TEMPORARY FAILURE",
            "PERMANENT FAILURE",
            "CLIENT CERTIFICATE REQUIRED",
        )

    @given(st.integers(min_value=10, max_value=19))
    def test_1x_codes_always_input(self, status):
        """All 1x status codes should be interpreted as INPUT."""
        assert interpret_status(status) == "INPUT"
        assert is_input_required(status)
        assert not is_success(status)
        assert not is_redirect(status)
        assert not is_error(status)

    @given(st.integers(min_value=20, max_value=29))
    def test_2x_codes_always_success(self, status):
        """All 2x status codes should be interpreted as SUCCESS."""
        assert interpret_status(status) == "SUCCESS"
        assert is_success(status)
        assert not is_input_required(status)
        assert not is_redirect(status)
        assert not is_error(status)

    @given(st.integers(min_value=30, max_value=39))
    def test_3x_codes_always_redirect(self, status):
        """All 3x status codes should be interpreted as REDIRECT."""
        assert interpret_status(status) == "REDIRECT"
        assert is_redirect(status)
        assert not is_success(status)
        assert not is_input_required(status)
        assert not is_error(status)

    @given(st.integers(min_value=40, max_value=49))
    def test_4x_codes_always_temporary_failure(self, status):
        """All 4x status codes should be interpreted as TEMPORARY FAILURE."""
        assert interpret_status(status) == "TEMPORARY FAILURE"
        assert is_error(status)
        assert not is_success(status)
        assert not is_redirect(status)
        assert not is_input_required(status)

    @given(st.integers(min_value=50, max_value=59))
    def test_5x_codes_always_permanent_failure(self, status):
        """All 5x status codes should be interpreted as PERMANENT FAILURE."""
        assert interpret_status(status) == "PERMANENT FAILURE"
        assert is_error(status)
        assert not is_success(status)
        assert not is_redirect(status)
        assert not is_input_required(status)

    @given(st.integers(min_value=60, max_value=69))
    def test_6x_codes_always_cert_required(self, status):
        """All 6x status codes should be interpreted as CLIENT CERTIFICATE REQUIRED."""
        assert interpret_status(status) == "CLIENT CERTIFICATE REQUIRED"
        assert is_error(status)
        assert not is_success(status)
        assert not is_redirect(status)
        assert not is_input_required(status)

    @given(st.integers())
    def test_invalid_status_codes_return_unknown(self, status):
        """Status codes outside 10-69 range should return UNKNOWN."""
        assume(status < 10 or status > 69)
        assert interpret_status(status) == "UNKNOWN"

    @given(st.integers(min_value=10, max_value=69))
    def test_status_mutually_exclusive(self, status):
        """A status code should match exactly one category."""
        categories = [
            is_success(status),
            is_redirect(status),
            is_input_required(status),
            is_error(status),
        ]
        # Exactly one should be True
        assert sum(categories) == 1, (
            f"Status {status} matched {sum(categories)} categories"
        )

    @given(st.integers(min_value=10, max_value=69))
    def test_error_codes_exclude_success_and_redirect(self, status):
        """Error codes (4x, 5x, 6x) should never be success or redirect."""
        if is_error(status):
            assert not is_success(status)
            assert not is_redirect(status)
            assert status >= 40

    @given(st.integers(min_value=20, max_value=29))
    def test_success_codes_are_never_errors(self, status):
        """Success codes (2x) should never be classified as errors."""
        assert is_success(status)
        assert not is_error(status)

    @given(st.integers(min_value=10, max_value=69))
    def test_status_in_range_never_unknown(self, status):
        """Valid status codes (10-69) should never be UNKNOWN."""
        assert interpret_status(status) != "UNKNOWN"
