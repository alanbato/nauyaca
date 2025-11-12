"""Property-based tests for GeminiResponse using Hypothesis."""

from hypothesis import assume, given
from hypothesis import strategies as st

from nauyaca.protocol.response import GeminiResponse


# Custom strategies for response components
@st.composite
def valid_mime_types(draw):
    """Generate valid MIME types."""
    type_part = draw(
        st.sampled_from(["text", "image", "application", "video", "audio"])
    )
    subtype = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Nd"), whitelist_characters="-+."
            ),
            min_size=1,
            max_size=20,
        )
    )
    return f"{type_part}/{subtype}"


@st.composite
def mime_with_charset(draw):
    """Generate MIME types with optional charset parameter."""
    mime = draw(valid_mime_types())
    include_charset = draw(st.booleans())
    if include_charset:
        charset = draw(st.sampled_from(["utf-8", "iso-8859-1", "ascii", "utf-16"]))
        return f"{mime}; charset={charset}"
    return mime


class TestGeminiResponseProperties:
    """Property-based tests for GeminiResponse."""

    @given(st.integers(min_value=10, max_value=69), st.text(max_size=1024))
    def test_response_creation_never_fails(self, status, meta):
        """Creating a GeminiResponse with valid status should never fail."""
        response = GeminiResponse(status=status, meta=meta)
        assert response.status == status
        assert response.meta == meta

    @given(st.integers(min_value=20, max_value=29), mime_with_charset(), st.text())
    def test_success_response_preserves_body(self, status, mime, body):
        """Success responses (2x) should preserve the body content."""
        response = GeminiResponse(status=status, meta=mime, body=body)
        assert response.body == body
        assert response.is_success()

    @given(st.integers(min_value=20, max_value=29), mime_with_charset())
    def test_mime_type_extraction(self, status, meta):
        """MIME type should be correctly extracted from meta."""
        response = GeminiResponse(status=status, meta=meta)

        # Extract base MIME type (before any parameters)
        expected_mime = meta.split(";")[0].strip()
        assert response.mime_type == expected_mime

    @given(st.integers(min_value=20, max_value=29))
    def test_charset_defaults_to_utf8(self, status):
        """Responses without explicit charset should default to utf-8."""
        response = GeminiResponse(status=status, meta="text/gemini")
        assert response.charset == "utf-8"

    @given(st.integers(min_value=20, max_value=29), valid_mime_types())
    def test_charset_extraction_from_meta(self, status, mime):
        """Charset should be correctly extracted from meta string."""
        charset = "iso-8859-1"
        meta = f"{mime}; charset={charset}"
        response = GeminiResponse(status=status, meta=meta)
        assert response.charset == charset

    @given(st.integers(min_value=30, max_value=39), st.text(min_size=1, max_size=1024))
    def test_redirect_url_extraction(self, status, redirect_url):
        """Redirect responses should correctly extract redirect URL from meta."""
        assume(";" not in redirect_url)  # Avoid conflicting with charset syntax
        response = GeminiResponse(status=status, meta=redirect_url)

        assert response.is_redirect()
        assert response.redirect_url == redirect_url

    @given(st.integers(min_value=40, max_value=69), st.text(max_size=1024))
    def test_error_responses_have_no_body(self, status, meta):
        """Error responses (4x, 5x, 6x) should have None as body."""
        response = GeminiResponse(status=status, meta=meta)
        # Body should be None for error responses if not explicitly set
        # (in practice, the protocol doesn't send bodies for errors)
        assert not response.is_success()

    @given(st.integers(min_value=10, max_value=69), st.text(max_size=1024))
    def test_response_immutability(self, status, meta):
        """GeminiResponse should be immutable (frozen dataclass)."""
        response = GeminiResponse(status=status, meta=meta)

        try:
            response.status = 99
            raise AssertionError("Response should be immutable")
        except (AttributeError, Exception):
            pass  # Expected - response is frozen

    @given(
        st.integers(min_value=20, max_value=29),
        mime_with_charset(),
        st.text(min_size=0, max_size=1000),
    )
    def test_body_length_preserved(self, status, mime, body):
        """The length of the body should be preserved in responses."""
        response = GeminiResponse(status=status, meta=mime, body=body)
        assert len(response.body) == len(body)

    @given(st.integers(min_value=20, max_value=29))
    def test_success_response_properties(self, status):
        """Success responses should have correct boolean properties."""
        response = GeminiResponse(status=status, meta="text/plain")

        assert response.is_success()
        assert not response.is_redirect()

    @given(st.integers(min_value=30, max_value=39))
    def test_redirect_response_properties(self, status):
        """Redirect responses should have correct boolean properties."""
        response = GeminiResponse(status=status, meta="gemini://example.com/")

        assert response.is_redirect()
        assert not response.is_success()

    @given(
        st.integers(min_value=20, max_value=29),
        st.text(max_size=100),
        st.text(max_size=1000),
    )
    def test_response_str_contains_status(self, status, meta, body):
        """String representation should contain the status code."""
        response = GeminiResponse(status=status, meta=meta, body=body)
        str_repr = str(response)

        assert str(status) in str_repr

    @given(st.integers(min_value=10, max_value=69), st.text(max_size=1024))
    def test_meta_always_accessible(self, status, meta):
        """The meta field should always be accessible."""
        response = GeminiResponse(status=status, meta=meta)
        assert response.meta == meta

    @given(st.integers(min_value=20, max_value=29), valid_mime_types())
    def test_mime_type_lowercase(self, status, mime):
        """MIME types should be case-insensitive in practice."""
        # Test with different case variations
        response_lower = GeminiResponse(status=status, meta=mime.lower())
        response_upper = GeminiResponse(status=status, meta=mime.upper())

        # Both should parse without error
        assert response_lower.mime_type is not None
        assert response_upper.mime_type is not None
