"""Property-based tests for URL parsing and validation using Hypothesis."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from nauyaca.protocol.constants import DEFAULT_PORT, MAX_REQUEST_SIZE
from nauyaca.utils.url import normalize_url, parse_url, validate_url


# Custom strategies for Gemini URLs
@st.composite
def gemini_hostnames(draw):
    """Generate valid hostnames for Gemini URLs."""
    # Simple hostname: letters, numbers, dots, hyphens
    parts = draw(
        st.lists(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-"
                ),
                min_size=1,
                max_size=63,
            ).filter(lambda s: not s.startswith("-") and not s.endswith("-")),
            min_size=1,
            max_size=5,
        )
    )
    return ".".join(parts)


@st.composite
def gemini_paths(draw):
    """Generate valid URL paths."""
    # URL paths can contain various characters
    segments = draw(
        st.lists(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Ll", "Lu", "Nd"),
                    whitelist_characters="-_~.!$&'()*+,;=:@",
                ),
                max_size=50,
            ),
            max_size=10,
        )
    )
    path = "/" + "/".join(segments) if segments else "/"
    return path


@st.composite
def valid_gemini_urls(draw):
    """Generate valid Gemini URLs that should parse successfully."""
    hostname = draw(gemini_hostnames())
    port = draw(st.integers(min_value=1, max_value=65535) | st.just(DEFAULT_PORT))
    path = draw(gemini_paths())

    # Build URL
    if port == DEFAULT_PORT:
        url = f"gemini://{hostname}{path}"
    else:
        url = f"gemini://{hostname}:{port}{path}"

    # Ensure it doesn't exceed max size
    assume(len(url.encode("utf-8")) + 2 <= MAX_REQUEST_SIZE)  # +2 for CRLF

    return url


class TestURLParsingProperties:
    """Property-based tests for URL parsing."""

    @given(valid_gemini_urls())
    def test_parse_valid_url_always_succeeds(self, url):
        """Any valid Gemini URL should parse without raising an exception."""
        parsed = parse_url(url)
        assert parsed.scheme == "gemini"
        assert parsed.hostname is not None
        assert parsed.port > 0
        assert parsed.path is not None

    @given(valid_gemini_urls())
    def test_parsed_url_roundtrip_property(self, url):
        """Parsing a URL should produce components that can reconstruct it."""
        parsed = parse_url(url)

        # Reconstruct URL from parsed components
        if parsed.port == DEFAULT_PORT:
            reconstructed = f"{parsed.scheme}://{parsed.hostname}{parsed.path}"
        else:
            reconstructed = (
                f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
            )

        if parsed.query:
            reconstructed += f"?{parsed.query}"

        # The normalized versions should match
        assert normalize_url(reconstructed) == normalize_url(url)

    @given(valid_gemini_urls())
    def test_normalize_is_idempotent(self, url):
        """Normalizing a URL twice should give the same result as normalizing once."""
        normalized_once = normalize_url(url)
        normalized_twice = normalize_url(normalized_once)
        assert normalized_once == normalized_twice

    @given(valid_gemini_urls())
    def test_validate_url_accepts_valid_urls(self, url):
        """validate_url should not raise for valid URLs."""
        validate_url(url)  # Should not raise

    @given(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=20,
        )
    )
    def test_invalid_scheme_raises(self, scheme):
        """URLs with non-gemini schemes should raise ValueError."""
        assume(scheme != "gemini")
        url = f"{scheme}://example.com/"

        try:
            parse_url(url)
            raise AssertionError(f"Expected ValueError for scheme: {scheme}")
        except ValueError as e:
            assert "scheme" in str(e).lower() or "invalid" in str(e).lower()

    @given(gemini_hostnames(), st.integers(min_value=1, max_value=65535))
    def test_port_preserved_in_parsing(self, hostname, port):
        """Port numbers should be correctly preserved during parsing."""
        url = f"gemini://{hostname}:{port}/"
        assume(len(url.encode("utf-8")) + 2 <= MAX_REQUEST_SIZE)

        parsed = parse_url(url)
        assert parsed.port == port

    @given(valid_gemini_urls())
    def test_parsed_url_scheme_always_gemini(self, url):
        """The scheme of a parsed valid Gemini URL is always 'gemini'."""
        parsed = parse_url(url)
        assert parsed.scheme == "gemini"

    @given(gemini_hostnames())
    def test_default_port_omitted_in_normalized(self, hostname):
        """Normalized URLs should omit the default port (1965)."""
        url = f"gemini://{hostname}:{DEFAULT_PORT}/"
        assume(len(url.encode("utf-8")) + 2 <= MAX_REQUEST_SIZE)

        normalized = normalize_url(url)
        assert f":{DEFAULT_PORT}" not in normalized

    @given(gemini_hostnames(), st.integers(min_value=1, max_value=65535))
    def test_custom_port_included_in_normalized(self, hostname, port):
        """Normalized URLs should include non-default ports."""
        assume(port != DEFAULT_PORT)
        url = f"gemini://{hostname}:{port}/"
        assume(len(url.encode("utf-8")) + 2 <= MAX_REQUEST_SIZE)

        normalized = normalize_url(url)
        assert f":{port}" in normalized

    @given(gemini_hostnames())
    def test_path_defaults_to_slash(self, hostname):
        """URLs without a path should default to '/'."""
        url = f"gemini://{hostname}"
        assume(len(url.encode("utf-8")) + 2 <= MAX_REQUEST_SIZE)

        parsed = parse_url(url)
        assert parsed.path == "/"

    @given(
        st.text(alphabet=st.characters(min_codepoint=1, max_codepoint=1000), min_size=1)
    )
    def test_empty_url_raises(self, _):
        """Empty URLs should raise ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            parse_url("")

    @given(st.text(min_size=MAX_REQUEST_SIZE))
    def test_url_too_long_raises(self, long_text):
        """URLs exceeding MAX_REQUEST_SIZE should raise ValueError."""
        # Create a URL that's definitely too long
        url = f"gemini://example.com/{long_text}"

        with pytest.raises(ValueError, match="URL too long"):
            validate_url(url)
