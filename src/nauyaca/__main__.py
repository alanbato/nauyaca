"""Nauyaca Gemini Protocol Client CLI.

This module provides a command-line interface for the Nauyaca Gemini client.
"""

import asyncio
from pathlib import Path

import typer

from .client.session import GeminiClient
from .protocol.constants import DEFAULT_PORT, MAX_REDIRECTS
from .protocol.status import interpret_status
from .server.config import ServerConfig
from .server.server import start_server

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
def serve(
    root: Path = typer.Argument(
        ...,
        help="Document root directory to serve files from",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    host: str = typer.Option(
        "localhost",
        "--host",
        "-h",
        help="Server host address",
    ),
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Server port",
    ),
    cert: Path | None = typer.Option(
        None,
        "--cert",
        help="Path to TLS certificate file (optional, generates self-signed if omitted)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    key: Path | None = typer.Option(
        None,
        "--key",
        help="Path to TLS private key file (optional)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
):
    """Start a Gemini server to serve files from a directory.

    Examples:

        # Serve current directory on default port (1965)
        $ python -m nauyaca serve .

        # Serve specific directory with custom port
        $ python -m nauyaca serve /var/gemini/capsule -p 1965

        # Serve with custom host and port
        $ python -m nauyaca serve ./capsule --host 0.0.0.0 --port 1965

        # Serve with custom TLS certificate
        $ python -m nauyaca serve ./capsule --cert cert.pem --key key.pem
    """

    async def _serve():
        try:
            # Create server configuration
            config = ServerConfig(
                host=host,
                port=port,
                document_root=root,
                certfile=cert,
                keyfile=key,
            )

            # Start server
            await start_server(config)

        except ValueError as e:
            typer.echo(f"Configuration error: {e}", err=True)
            raise typer.Exit(code=1) from e
        except OSError as e:
            typer.echo(f"Server error: {e}", err=True)
            raise typer.Exit(code=1) from e
        except KeyboardInterrupt:
            typer.echo("\n[Server] Shutting down...")
            raise typer.Exit(code=0)
        except Exception as e:
            typer.echo(f"Unexpected error: {e}", err=True)
            raise typer.Exit(code=1) from e

    # Run the async function
    asyncio.run(_serve())


@app.command()
def version():
    """Show version information."""
    typer.echo("Nauyaca Gemini Protocol Client & Server")
    typer.echo("Version: 0.1.0 (MVP)")
    typer.echo("Protocol: Gemini (gemini://)")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
