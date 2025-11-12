"""URL routing for Gemini server.

This module provides the Router class for matching URLs to request handlers.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from ..protocol.request import GeminiRequest
from ..protocol.response import GeminiResponse


class RouteType(Enum):
    """Type of route pattern matching."""

    EXACT = auto()  # Exact path match
    PREFIX = auto()  # Path prefix match
    REGEX = auto()  # Regular expression match


@dataclass
class Route:
    """Represents a URL route.

    Attributes:
        pattern: The URL pattern to match against.
        handler: The callable handler that processes matching requests.
        route_type: The type of matching to perform.
        compiled_regex: For regex routes, the compiled pattern.
    """

    pattern: str
    handler: Callable[[GeminiRequest], GeminiResponse]
    route_type: RouteType
    compiled_regex: re.Pattern | None = None


class Router:
    """Routes incoming requests to appropriate handlers.

    The Router supports three types of route matching:
    - Exact: Path must match exactly
    - Prefix: Path must start with the pattern
    - Regex: Path must match the regular expression

    Routes are matched in the order they were registered.

    Examples:
        >>> router = Router()
        >>> router.add_route("/", index_handler)
        >>> router.add_route("/static/", static_handler, route_type=RouteType.PREFIX)
        >>> router.add_route(r"^/user/\\d+$", user_handler, route_type=RouteType.REGEX)
    """

    def __init__(self):
        """Initialize an empty router."""
        self.routes: list[Route] = []
        self.default_handler: Callable[[GeminiRequest], GeminiResponse] | None = None

    def add_route(
        self,
        pattern: str,
        handler: Callable[[GeminiRequest], GeminiResponse],
        route_type: RouteType = RouteType.EXACT,
    ) -> None:
        """Register a new route.

        Args:
            pattern: The URL pattern to match.
            handler: Callable that takes a GeminiRequest and returns a GeminiResponse.
            route_type: Type of matching to perform (default: EXACT).

        Raises:
            ValueError: If the pattern is invalid (e.g., invalid regex).

        Examples:
            >>> router.add_route("/", index_handler)
            >>> router.add_route("/blog/", blog_handler, RouteType.PREFIX)
        """
        compiled_regex = None

        if route_type == RouteType.REGEX:
            try:
                compiled_regex = re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

        route = Route(
            pattern=pattern,
            handler=handler,
            route_type=route_type,
            compiled_regex=compiled_regex,
        )
        self.routes.append(route)

    def set_default_handler(
        self, handler: Callable[[GeminiRequest], GeminiResponse]
    ) -> None:
        """Set the default handler for unmatched routes.

        Args:
            handler: Callable that handles requests not matching any route.
                Typically returns a 404 NOT FOUND response.
        """
        self.default_handler = handler

    def route(self, request: GeminiRequest) -> GeminiResponse:
        """Route a request to the appropriate handler.

        Routes are matched in the order they were registered.
        If no route matches, the default handler is called (if set),
        otherwise a 404 response is returned.

        Args:
            request: The incoming request to route.

        Returns:
            The response from the matched handler.
        """
        path = request.path

        # Try to match against registered routes
        for route in self.routes:
            if self._matches(path, route):
                return route.handler(request)

        # No match found, use default handler or return 404
        if self.default_handler:
            return self.default_handler(request)

        # No default handler, return generic 404
        return GeminiResponse(status=51, meta="Not found")

    def _matches(self, path: str, route: Route) -> bool:
        """Check if a path matches a route.

        Args:
            path: The request path to check.
            route: The route to match against.

        Returns:
            True if the path matches the route, False otherwise.
        """
        if route.route_type == RouteType.EXACT:
            return path == route.pattern

        elif route.route_type == RouteType.PREFIX:
            return path.startswith(route.pattern)

        elif route.route_type == RouteType.REGEX:
            if route.compiled_regex is None:
                return False
            return route.compiled_regex.match(path) is not None

        return False
