"""Nauyaca Gemini Protocol Client CLI.

This module provides a command-line interface for the Nauyaca Gemini client.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .client.session import GeminiClient
from .protocol.constants import DEFAULT_PORT, MAX_REDIRECTS
from .protocol.response import GeminiResponse
from .protocol.status import interpret_status
from .server.config import ServerConfig
from .server.server import start_server

# Create console instances
console = Console()
error_console = Console(stderr=True, style="bold red")

app = typer.Typer(
    name="nauyaca",
    help="Nauyaca - A modern Gemini protocol client",
    add_completion=False,
    no_args_is_help=True,
)


def _format_response(response: GeminiResponse, verbose: bool = False) -> None:
    """Format and print a Gemini response for display.

    Args:
        response: GeminiResponse object to format.
        verbose: Whether to show verbose output with headers.
    """
    if verbose:
        # Show full response details in a table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="bold cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Determine status color based on status code
        status_str = str(response.status)
        if status_str.startswith("2"):
            status_style = "bold green"
        elif status_str.startswith("3"):
            status_style = "bold yellow"
        elif status_str.startswith("4"):
            status_style = "bold orange1"
        else:
            status_style = "bold red"

        status_text = interpret_status(response.status)
        table.add_row(
            "Status",
            f"[{status_style}]{response.status}[/] ({status_text})",
        )
        table.add_row("Meta", response.meta)

        if response.url:
            table.add_row("URL", response.url)
        if response.mime_type:
            table.add_row("MIME Type", response.mime_type)

        console.print(table)
        console.print()  # Blank line before body

    if response.body:
        console.print(response.body)
    elif not response.is_success():
        # For non-success responses, show the meta as the message
        if not verbose:
            status_str = str(response.status)
            if status_str.startswith("3"):
                console.print(f"[bold yellow][{response.status}][/] {response.meta}")
            elif status_str.startswith("4"):
                console.print(f"[bold orange1][{response.status}][/] {response.meta}")
            else:
                console.print(f"[bold red][{response.status}][/] {response.meta}")


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
) -> None:
    """Fetch a Gemini resource and display it.

    Examples:

        # Fetch a URL
        $ nauyaca fetch gemini://gemini.circumlunar.space/

        # Fetch with verbose output
        $ nauyaca fetch -v gemini://example.com/

        # Don't follow redirects
        $ nauyaca fetch --no-redirects gemini://example.com/

        # Custom timeout
        $ nauyaca fetch -t 10 gemini://example.com/
    """

    async def _fetch() -> None:
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
                _format_response(response, verbose=verbose)

                # Exit with non-zero status for errors
                if response.status >= 40:
                    raise typer.Exit(code=1)

        except ValueError as e:
            error_console.print(f"Error: {e}")
            raise typer.Exit(code=1) from e
        except TimeoutError as e:
            error_console.print(f"Timeout: {e}")
            raise typer.Exit(code=1) from e
        except ConnectionError as e:
            error_console.print(f"Connection error: {e}")
            raise typer.Exit(code=1) from e
        except Exception as e:
            error_console.print(f"Unexpected error: {e}")
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
        help=(
            "Path to TLS certificate file (optional, generates self-signed if omitted)"
        ),
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
    enable_directory_listing: bool = typer.Option(
        False,
        "--enable-directory-listing",
        "-d",
        help="Enable automatic directory listings for directories without index files",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
    log_file: Path | None = typer.Option(
        None,
        "--log-file",
        help="Path to log file (default: stdout)",
        dir_okay=False,
        resolve_path=True,
    ),
    json_logs: bool = typer.Option(
        False,
        "--json-logs",
        help="Output logs in JSON format (useful for log aggregation)",
    ),
) -> None:
    """Start a Gemini server to serve files from a directory.

    Examples:

        # Serve current directory on default port (1965)
        $ nauyaca serve .

        # Serve with directory listings enabled
        $ nauyaca serve ./capsule --enable-directory-listing

        # Serve with custom logging
        $ nauyaca serve ./capsule --log-level DEBUG

        # Serve with JSON logs to file
        $ nauyaca serve ./capsule --log-file server.log --json-logs

        # Serve with custom TLS certificate
        $ nauyaca serve ./capsule --cert cert.pem --key key.pem
    """

    async def _serve() -> None:
        try:
            # Create server configuration
            config = ServerConfig(
                host=host,
                port=port,
                document_root=root,
                certfile=cert,
                keyfile=key,
            )

            # Start server with logging and directory listing options
            await start_server(
                config,
                enable_directory_listing=enable_directory_listing,
                log_level=log_level,
                log_file=log_file,
                json_logs=json_logs,
            )

        except ValueError as e:
            error_console.print(f"Configuration error: {e}")
            raise typer.Exit(code=1) from e
        except OSError as e:
            error_console.print(f"Server error: {e}")
            raise typer.Exit(code=1) from e
        except KeyboardInterrupt:
            console.print("\n[bold blue][Server][/] Shutting down...")
            raise typer.Exit(code=0) from None
        except Exception as e:
            error_console.print(f"Unexpected error: {e}")
            raise typer.Exit(code=1) from e

    # Run the async function
    asyncio.run(_serve())


@app.command()
def version() -> None:
    """Show version information."""
    console.print("[bold cyan]Nauyaca[/] Gemini Protocol Client & Server")
    console.print("[bold]Version:[/] 0.1.0 (MVP)")
    console.print("[bold]Protocol:[/] Gemini (gemini://)")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
