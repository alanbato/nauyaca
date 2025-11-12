"""Nauyaca Gemini Protocol Client CLI.

This module provides a command-line interface for the Nauyaca Gemini client.
"""

import asyncio

import typer

from .client.session import GeminiClient
from .protocol.constants import MAX_REDIRECTS
from .protocol.status import interpret_status

app = typer.Typer(
    name="nauyaca",
    help="Nauyaca - A modern Gemini protocol client",
    add_completion=False,
)


def _format_response(response, verbose: bool = False):
    """Format a Gemini response for display.

    Args:
        response: GeminiResponse object to format.
        verbose: Whether to show verbose output with headers.

    Returns:
        Formatted string representation of the response.
    """
    output = []

    if verbose:
        # Show full response details
        output.append(
            f"Status: {response.status} ({interpret_status(response.status)})"
        )
        output.append(f"Meta: {response.meta}")
        if response.url:
            output.append(f"URL: {response.url}")
        if response.mime_type:
            output.append(f"MIME Type: {response.mime_type}")
        output.append("")  # Blank line before body

    if response.body:
        output.append(response.body)
    elif not response.is_success():
        # For non-success responses, show the meta as the message
        if not verbose:
            output.append(f"[{response.status}] {response.meta}")

    return "\n".join(output)


@app.command()
def fetch(
    url: str = typer.Argument(..., help="Gemini URL to fetch"),
    max_redirects: int = typer.Option(
        MAX_REDIRECTS,
        "--max-redirects",
        "-r",
        help="Maximum number of redirects to follow",
    ),
    no_redirects: bool = typer.Option(
        False,
        "--no-redirects",
        help="Do not follow redirects",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        "-t",
        help="Request timeout in seconds",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose output with response headers",
    ),
):
    """Fetch a Gemini resource and display it.

    Examples:

        # Fetch a URL
        $ python -m nauyaca fetch gemini://gemini.circumlunar.space/

        # Fetch with verbose output
        $ python -m nauyaca fetch -v gemini://example.com/

        # Don't follow redirects
        $ python -m nauyaca fetch --no-redirects gemini://example.com/

        # Custom timeout
        $ python -m nauyaca fetch -t 10 gemini://example.com/
    """

    async def _fetch():
        try:
            async with GeminiClient(
                timeout=timeout,
                max_redirects=max_redirects,
                verify_ssl=False,  # Testing mode for MVP
            ) as client:
                response = await client.fetch(
                    url,
                    follow_redirects=not no_redirects,
                )

                # Format and display response
                output = _format_response(response, verbose=verbose)
                typer.echo(output)

                # Exit with non-zero status for errors
                if response.status >= 40:
                    raise typer.Exit(code=1)

        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from e
        except TimeoutError as e:
            typer.echo(f"Timeout: {e}", err=True)
            raise typer.Exit(code=1) from e
        except ConnectionError as e:
            typer.echo(f"Connection error: {e}", err=True)
            raise typer.Exit(code=1) from e
        except Exception as e:
            typer.echo(f"Unexpected error: {e}", err=True)
            raise typer.Exit(code=1) from e

    # Run the async function
    asyncio.run(_fetch())


@app.command()
def version():
    """Show version information."""
    typer.echo("Nauyaca Gemini Protocol Client")
    typer.echo("Version: 0.1.0 (MVP)")
    typer.echo("Protocol: Gemini (gemini://)")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
