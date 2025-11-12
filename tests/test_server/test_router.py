"""Tests for Router class."""

import pytest

from nauyaca.protocol.request import GeminiRequest
from nauyaca.protocol.response import GeminiResponse
from nauyaca.server.router import Route, Router, RouteType


class TestRouter:
    """Test Router class."""

    def test_add_exact_route(self):
        """Test adding an exact match route."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Index")

        router = Router()
        router.add_route("/", handler)

        assert len(router.routes) == 1
        assert router.routes[0].pattern == "/"
        assert router.routes[0].route_type == RouteType.EXACT

    def test_exact_route_matching(self):
        """Test exact route matching."""

        def index_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Index")

        def about_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="About")

        router = Router()
        router.add_route("/", index_handler)
        router.add_route("/about", about_handler)

        # Test index route
        request = GeminiRequest.from_line("gemini://example.com/")
        response = router.route(request)
        assert response.body == "Index"

        # Test about route
        request = GeminiRequest.from_line("gemini://example.com/about")
        response = router.route(request)
        assert response.body == "About"

    def test_exact_route_no_partial_match(self):
        """Test that exact routes don't match partial paths."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Matched")

        router = Router()
        router.add_route("/about", handler)

        # Should not match "/about/page"
        request = GeminiRequest.from_line("gemini://example.com/about/page")
        response = router.route(request)
        assert response.status == 51  # Default 404

    def test_prefix_route_matching(self):
        """Test prefix route matching."""

        def static_handler(request):
            return GeminiResponse(
                status=20, meta="text/plain", body=f"Serving {request.path}"
            )

        router = Router()
        router.add_route("/static/", static_handler, route_type=RouteType.PREFIX)

        # Should match any path starting with /static/
        request = GeminiRequest.from_line("gemini://example.com/static/file.txt")
        response = router.route(request)
        assert "Serving /static/file.txt" in response.body

        request = GeminiRequest.from_line("gemini://example.com/static/css/style.css")
        response = router.route(request)
        assert "Serving /static/css/style.css" in response.body

    def test_prefix_route_no_match(self):
        """Test that prefix routes don't match unrelated paths."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Matched")

        router = Router()
        router.add_route("/static/", handler, route_type=RouteType.PREFIX)

        # Should not match "/other/"
        request = GeminiRequest.from_line("gemini://example.com/other/file.txt")
        response = router.route(request)
        assert response.status == 51  # Default 404

    def test_regex_route_matching(self):
        """Test regex route matching."""

        def user_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="User profile")

        router = Router()
        router.add_route(r"^/user/\d+$", user_handler, route_type=RouteType.REGEX)

        # Should match /user/123
        request = GeminiRequest.from_line("gemini://example.com/user/123")
        response = router.route(request)
        assert response.body == "User profile"

        # Should not match /user/abc
        request = GeminiRequest.from_line("gemini://example.com/user/abc")
        response = router.route(request)
        assert response.status == 51  # Default 404

    def test_regex_route_invalid_pattern(self):
        """Test that invalid regex patterns raise ValueError."""

        def handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="OK")

        router = Router()

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            router.add_route(r"[invalid(", handler, route_type=RouteType.REGEX)

    def test_route_order_priority(self):
        """Test that routes are matched in registration order."""

        def first_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="First")

        def second_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Second")

        router = Router()
        router.add_route("/test", first_handler)
        router.add_route("/test", second_handler)  # Same path

        # Should match the first registered route
        request = GeminiRequest.from_line("gemini://example.com/test")
        response = router.route(request)
        assert response.body == "First"

    def test_default_handler(self):
        """Test setting and using a default handler."""

        def default_handler(request):
            return GeminiResponse(status=51, meta=f"Not found: {request.path}")

        router = Router()
        router.set_default_handler(default_handler)

        # Unmatched route should use default handler
        request = GeminiRequest.from_line("gemini://example.com/nonexistent")
        response = router.route(request)
        assert response.status == 51
        assert "Not found: /nonexistent" in response.meta

    def test_no_default_handler_returns_404(self):
        """Test that routes without matches return generic 404."""
        router = Router()

        request = GeminiRequest.from_line("gemini://example.com/notfound")
        response = router.route(request)
        assert response.status == 51
        assert response.meta == "Not found"

    def test_mixed_route_types(self):
        """Test router with multiple route types."""

        def exact_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Exact")

        def prefix_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Prefix")

        def regex_handler(request):
            return GeminiResponse(status=20, meta="text/gemini", body="Regex")

        router = Router()
        router.add_route("/", exact_handler, route_type=RouteType.EXACT)
        router.add_route("/static/", prefix_handler, route_type=RouteType.PREFIX)
        router.add_route(r"^/api/\w+$", regex_handler, route_type=RouteType.REGEX)

        # Test exact match
        request = GeminiRequest.from_line("gemini://example.com/")
        response = router.route(request)
        assert response.body == "Exact"

        # Test prefix match
        request = GeminiRequest.from_line("gemini://example.com/static/file.txt")
        response = router.route(request)
        assert response.body == "Prefix"

        # Test regex match
        request = GeminiRequest.from_line("gemini://example.com/api/users")
        response = router.route(request)
        assert response.body == "Regex"

    def test_empty_router(self):
        """Test router with no routes."""
        router = Router()

        request = GeminiRequest.from_line("gemini://example.com/")
        response = router.route(request)
        assert response.status == 51  # Default 404
