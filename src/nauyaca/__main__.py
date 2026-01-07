"""Nauyaca Gemini Protocol Client CLI.

This module provides a command-line interface for the Nauyaca Gemini client.
"""

import asyncio
from importlib.metadata import version as get_version
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .client.session import GeminiClient
from .protocol.constants import DEFAULT_PORT, MAX_REDIRECTS
from .protocol.response import GeminiResponse
from .protocol.status import interpret_status
from .security.tofu import CertificateChangedError
from .server.config import ServerConfig
from .server.server import start_server

# Create console instances
console = Console()
error_console = Console(stderr=True, style="bold red")

app = typer.Typer(
    name="nauyaca",
    help="Nauyaca - A modern Gemini protocol client",
    add_completion=True,
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
def get(
    url: str = typer.Argument(..., help="Gemini URL to get"),
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
    trust_on_first_use: bool = typer.Option(
        True,
        "--trust/--no-trust",
        help="Enable Trust-On-First-Use certificate validation (recommended for Gemini)",
    ),
    verify_ssl: bool = typer.Option(
        False,
        "--verify-ssl/--no-verify-ssl",
        help="Use CA-based SSL verification instead of TOFU (not recommended for Gemini)",
    ),
    client_cert: Path | None = typer.Option(
        None,
        "--client-cert",
        help="Path to client certificate file (PEM format) for authentication",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    client_key: Path | None = typer.Option(
        None,
        "--client-key",
        help="Path to client private key file (PEM format) for authentication",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
) -> None:
    """Get a Gemini resource and display it.

    Examples:

        # Get a URL
        $ nauyaca get gemini://gemini.circumlunar.space/

        # Get with verbose output
        $ nauyaca get -v gemini://example.com/

        # Don't follow redirects
        $ nauyaca get --no-redirects gemini://example.com/

        # Custom timeout
        $ nauyaca get -t 10 gemini://example.com/

        # Authenticate with client certificate
        $ nauyaca get gemini://secure.example.com/ \\
            --client-cert ~/.nauyaca/certs/myidentity.pem \\
            --client-key ~/.nauyaca/certs/myidentity.key
    """
    # Validate client cert/key pair
    if client_cert and not client_key:
        error_console.print(
            "[red]Error:[/] --client-key is required when --client-cert is provided"
        )
        raise typer.Exit(code=1)
    if client_key and not client_cert:
        error_console.print(
            "[red]Error:[/] --client-cert is required when --client-key is provided"
        )
        raise typer.Exit(code=1)

    async def _get() -> None:
        try:
            async with GeminiClient(
                timeout=timeout,
                max_redirects=max_redirects,
                verify_ssl=verify_ssl,
                trust_on_first_use=trust_on_first_use,
                client_cert=client_cert,
                client_key=client_key,
            ) as client:
                response = await client.get(
                    url,
                    follow_redirects=not no_redirects,
                )

                # Format and display response
                _format_response(response, verbose=verbose)

                # Exit with non-zero status for errors
                if response.status >= 40:
                    raise typer.Exit(code=1)

        except CertificateChangedError as e:
            error_console.print("\n[bold red]Certificate Changed![/]")
            error_console.print(f"Host: {e.hostname}:{e.port}")
            error_console.print(f"Old fingerprint: {e.old_fingerprint}")
            error_console.print(f"New fingerprint: {e.new_fingerprint}")
            error_console.print("\n[yellow]This could indicate:[/]")
            error_console.print("  1. A man-in-the-middle attack")
            error_console.print("  2. Legitimate certificate renewal")
            error_console.print("\n[cyan]To trust the new certificate, run:[/]")
            error_console.print(f"  nauyaca tofu trust {e.hostname} --port {e.port}")
            raise typer.Exit(code=1) from e
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
    asyncio.run(_get())


@app.command()
def serve(
    root: Path | None = typer.Argument(
        None,
        help="Document root directory to serve files from (optional if using --config)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    config_file: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to TOML configuration file (overrides other options)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="Server host address (overrides config file)",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="Server port (overrides config file)",
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
    hash_ips: bool = typer.Option(
        True,
        "--hash-ips/--no-hash-ips",
        help="Hash client IP addresses in logs for privacy (default: enabled)",
    ),
    max_file_size: int | None = typer.Option(
        None,
        "--max-file-size",
        help="Maximum file size to serve in bytes (default: 100 MiB)",
    ),
    require_client_cert: bool = typer.Option(
        False,
        "--require-client-cert",
        help="Require client certificates for all connections (status 60 if missing)",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload: restart server when source files change (dev only)",
    ),
    reload_dir: list[Path] | None = typer.Option(
        None,
        "--reload-dir",
        help="Directories to watch for changes (can specify multiple times). "
        "Defaults to document_root and src/nauyaca",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    reload_ext: list[str] | None = typer.Option(
        None,
        "--reload-ext",
        help="File extensions to watch for changes (can specify multiple times). "
        "Defaults to .py and .gmi",
    ),
) -> None:
    """Start a Gemini server to serve files from a directory.

    Examples:

        # Serve current directory on default port (1965)
        $ nauyaca serve .

        # Serve using TOML configuration file
        $ nauyaca serve --config config.toml

        # Serve with config file and CLI overrides
        $ nauyaca serve --config config.toml --port 8080

        # Serve with directory listings enabled
        $ nauyaca serve ./capsule --enable-directory-listing

        # Serve with custom logging
        $ nauyaca serve ./capsule --log-level DEBUG

        # Serve with JSON logs to file
        $ nauyaca serve ./capsule --log-file server.log --json-logs

        # Serve with custom TLS certificate
        $ nauyaca serve ./capsule --cert cert.pem --key key.pem

        # Serve with hot-reload for development
        $ nauyaca serve ./capsule --reload

        # Hot-reload with custom watch directories
        $ nauyaca serve ./capsule --reload --reload-dir ./src
    """
    # Handle reload mode - runs supervisor that spawns server subprocesses
    if reload:
        # Determine document root for watch directories
        doc_root: Path | None = root
        if doc_root is None and config_file is not None:
            # Try to load document root from config file
            try:
                temp_config = ServerConfig.from_toml(config_file)
                doc_root = Path(temp_config.document_root)
            except Exception:
                pass

        if doc_root is None:
            error_console.print(
                "[red]Error:[/] Document root is required for --reload "
                "(either as argument or via --config)"
            )
            raise typer.Exit(code=1)

        # Build watch directories
        watch_dirs: list[Path] = []
        if reload_dir:
            watch_dirs.extend(reload_dir)
        else:
            # Default: watch document root and nauyaca source
            watch_dirs.append(doc_root)
            nauyaca_src = Path(__file__).parent
            if nauyaca_src.exists():
                watch_dirs.append(nauyaca_src)

        # Deduplicate and filter to existing directories
        watch_dirs = list({d.resolve() for d in watch_dirs if d.exists()})

        if not watch_dirs:
            error_console.print("[red]Error:[/] No valid watch directories found")
            raise typer.Exit(code=1)

        # Build server args - filter out reload-related flags
        import sys

        server_args: list[str] = ["serve"]
        skip_next = False

        for arg in sys.argv[2:]:  # Skip 'nauyaca' and 'serve'
            if skip_next:
                skip_next = False
                continue

            if arg == "--reload":
                continue
            if arg == "--reload-dir":
                skip_next = True
                continue
            if arg.startswith("--reload-dir="):
                continue
            if arg == "--reload-ext":
                skip_next = True
                continue
            if arg.startswith("--reload-ext="):
                continue

            server_args.append(arg)

        # Build watch extensions
        watch_extensions: list[str] | None = None
        if reload_ext:
            watch_extensions = list(reload_ext)

        # Display reload info
        console.print("[bold cyan][Reload][/] Hot-reload enabled")
        console.print(
            f"[cyan][Reload][/] Watching: {', '.join(str(d) for d in watch_dirs)}"
        )

        # Run with reload supervisor
        from .server.reload import ReloadConfig, run_with_reload

        try:
            if watch_extensions:
                reload_config = ReloadConfig(
                    watch_dirs=watch_dirs, watch_extensions=watch_extensions
                )
            else:
                reload_config = ReloadConfig(watch_dirs=watch_dirs)

            # Display extensions being watched
            exts = ", ".join(reload_config.watch_extensions)
            console.print(f"[cyan][Reload][/] Extensions: {exts}")

            run_with_reload(reload_config, server_args)
        except KeyboardInterrupt:
            console.print("\n[bold blue][Reload][/] Shutting down...")
            raise typer.Exit(code=0) from None
        except Exception as e:
            error_console.print(f"Reload error: {e}")
            raise typer.Exit(code=1) from e

        return  # Never reached, but makes type checker happy

    async def _serve() -> None:
        try:
            # Load environment variable overrides (highest priority)
            env_overrides = ServerConfig.from_env()

            # Load configuration from file if provided
            if config_file:
                config = ServerConfig.from_toml(config_file)

                # CLI arguments override config file values
                if host is not None:
                    config.host = host
                if port is not None:
                    config.port = port
                if root is not None:
                    config.document_root = root
                if cert is not None:
                    config.certfile = cert
                if key is not None:
                    config.keyfile = key
            else:
                # No config file - check for document root from CLI or env
                effective_root = root or env_overrides.get("document_root")
                if effective_root is None:
                    error_console.print(
                        "[red]Error:[/] Document root is required "
                        "(via argument, --config, or NAUYACA_DOCUMENT_ROOT env var)"
                    )
                    raise typer.Exit(code=1)

                # Create config from CLI arguments
                config = ServerConfig(
                    host=host or "localhost",
                    port=port or DEFAULT_PORT,
                    document_root=effective_root,
                    certfile=cert,
                    keyfile=key,
                )

            # Apply environment variable overrides (ENV > CLI > TOML)
            for env_key, env_value in env_overrides.items():
                setattr(config, env_key, env_value)

            # Build certificate auth config from CLI flag or config file
            cert_auth_config = config.get_certificate_auth_config()
            if require_client_cert and cert_auth_config is None:
                # CLI flag overrides - create minimal config requiring cert
                from .server.middleware import CertificateAuthConfig

                cert_auth_config = CertificateAuthConfig(require_cert=True)

            # Start server with all configuration
            await start_server(
                config,
                enable_directory_listing=enable_directory_listing,
                log_level=log_level,
                log_file=log_file,
                json_logs=json_logs,
                enable_rate_limiting=config.enable_rate_limiting,
                rate_limit_config=config.get_rate_limit_config(),
                access_control_config=config.get_access_control_config(),
                certificate_auth_config=cert_auth_config,
                hash_ips=hash_ips,
                max_file_size=max_file_size,
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
    console.print(f"[bold]Version:[/] {get_version('nauyaca')}")
    console.print("[bold]Protocol:[/] Gemini (gemini://)")


# Create TOFU command group
tofu_app = typer.Typer(
    help="Manage TOFU certificate database",
    no_args_is_help=True,
)
app.add_typer(tofu_app, name="tofu")


@tofu_app.command("list")
def tofu_list() -> None:
    """List all known hosts in TOFU database.

    Examples:

        # List all known hosts
        $ nauyaca tofu list
    """
    from .security.tofu import TOFUDatabase

    db = TOFUDatabase()
    hosts = db.list_hosts()

    if not hosts:
        console.print("[yellow]No known hosts in TOFU database.[/]")
        return

    table = Table(title="Known Hosts (TOFU)")
    table.add_column("Hostname", style="cyan")
    table.add_column("Port", justify="right")
    table.add_column("Fingerprint", style="dim")
    table.add_column("First Seen")
    table.add_column("Last Seen")

    for host in hosts:
        table.add_row(
            host["hostname"],
            str(host["port"]),
            host["fingerprint"][:16] + "...",
            host["first_seen"][:10],
            host["last_seen"][:10],
        )

    console.print(table)


@tofu_app.command("revoke")
def tofu_revoke(
    hostname: str = typer.Argument(..., help="Hostname to revoke"),
    port: int | None = typer.Option(
        None, "--port", "-p", help="Port number (omit to revoke all ports)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation for bulk revocation"
    ),
) -> None:
    """Remove a host from the TOFU database.

    When --port is specified, revokes only that specific host:port entry.
    When --port is omitted, revokes ALL entries for the hostname (with confirmation).

    Examples:

        # Revoke all entries for a host (with confirmation)
        $ nauyaca tofu revoke example.com

        # Revoke all entries without confirmation
        $ nauyaca tofu revoke example.com --force

        # Revoke a specific port only
        $ nauyaca tofu revoke example.com --port 1965
    """
    from .security.tofu import TOFUDatabase

    db = TOFUDatabase()

    if port is not None:
        # Specific port: revoke single entry (no confirmation needed)
        if db.revoke(hostname, port):
            console.print(f"[green]Revoked certificate for {hostname}:{port}[/]")
        else:
            console.print(f"[yellow]Host {hostname}:{port} not in database[/]")
    else:
        # No port specified: revoke all entries for hostname
        count = db.count_by_hostname(hostname)

        if count == 0:
            console.print(f"[yellow]Host {hostname} not in database[/]")
            return

        # Confirm bulk deletion
        if not force:
            confirm = typer.confirm(f"Revoke all {count} entries for {hostname}?")
            if not confirm:
                raise typer.Abort()

        deleted = db.revoke_by_hostname(hostname)
        console.print(f"[green]Revoked {deleted} entries for {hostname}[/]")


@tofu_app.command("trust")
def tofu_trust(
    hostname: str = typer.Argument(..., help="Hostname to trust"),
    port: int = typer.Option(DEFAULT_PORT, "--port", "-p", help="Port number"),
) -> None:
    """Manually trust a certificate for a host.

    This command connects to the host, retrieves its certificate,
    and adds it to (or updates it in) the TOFU database.

    This is useful after a certificate change that you've verified
    is legitimate.

    Examples:

        # Trust a host
        $ nauyaca tofu trust example.com

        # Trust with custom port
        $ nauyaca tofu trust example.com --port 1965
    """
    from .security.tofu import TOFUDatabase

    async def _trust() -> None:
        try:
            console.print(f"[cyan]Fetching certificate from {hostname}:{port}...[/]")

            # Connect with TOFU disabled to get the new certificate
            async with GeminiClient(
                verify_ssl=False,
                trust_on_first_use=False,
            ) as client:
                # Create connection to get certificate
                url = f"gemini://{hostname}:{port}/"
                loop = asyncio.get_running_loop()
                response_future: asyncio.Future = loop.create_future()

                from .client.protocol import GeminiClientProtocol

                protocol = GeminiClientProtocol(url, response_future)

                transport, protocol = await loop.create_connection(
                    lambda: protocol,
                    host=hostname,
                    port=port,
                    ssl=client.ssl_context,
                    server_hostname=hostname,
                )

                try:
                    cert = protocol.get_peer_certificate()
                    if cert:
                        # Add to TOFU database
                        db = TOFUDatabase()
                        db.trust(hostname, port, cert)
                        console.print(
                            f"[green]Certificate trusted for {hostname}:{port}[/]"
                        )
                    else:
                        error_console.print(
                            "[red]Error: Could not retrieve certificate[/]"
                        )
                        raise typer.Exit(code=1)
                finally:
                    transport.close()

        except Exception as e:
            error_console.print(f"[red]Error: {e}[/]")
            raise typer.Exit(code=1) from e

    asyncio.run(_trust())


@tofu_app.command("clear")
def tofu_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Clear all entries from the TOFU database.

    Examples:

        # Clear with confirmation
        $ nauyaca tofu clear

        # Clear without confirmation
        $ nauyaca tofu clear --force
    """
    from .security.tofu import TOFUDatabase

    if not force:
        confirm = typer.confirm("Clear all known hosts from TOFU database?")
        if not confirm:
            raise typer.Abort()

    db = TOFUDatabase()
    count = db.clear()
    console.print(f"[green]Cleared {count} entries from TOFU database[/]")


@tofu_app.command("info")
def tofu_info(
    hostname: str = typer.Argument(..., help="Hostname to inspect"),
    port: int = typer.Option(DEFAULT_PORT, "--port", "-p", help="Port number"),
) -> None:
    """Show detailed information about a known host.

    Examples:

        # Show info for a host
        $ nauyaca tofu info example.com

        # Show info with custom port
        $ nauyaca tofu info example.com --port 1965
    """
    from .security.tofu import TOFUDatabase

    db = TOFUDatabase()
    info = db.get_host_info(hostname, port)

    if info is None:
        console.print(f"[yellow]Host {hostname}:{port} not in database[/]")
        raise typer.Exit(code=1)

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    table.add_row("Hostname", info["hostname"])
    table.add_row("Port", str(info["port"]))
    table.add_row("Fingerprint (SHA-256)", info["fingerprint"])
    table.add_row("First Seen", info["first_seen"])
    table.add_row("Last Seen", info["last_seen"])

    console.print(table)


@tofu_app.command("export")
def tofu_export(
    file: Path = typer.Argument(..., help="Output TOML file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing file"),
) -> None:
    """Export TOFU database to a TOML file.

    This creates a human-readable backup of your trusted hosts that can be
    edited, shared, or imported on another machine.

    Examples:

        # Export to a file
        $ nauyaca tofu export backup.toml

        # Overwrite existing file
        $ nauyaca tofu export backup.toml --force
    """
    from .security.tofu import TOFUDatabase

    # Check if file exists
    if file.exists() and not force:
        error_console.print(
            f"[red]Error: File {file} already exists. Use --force to overwrite.[/]"
        )
        raise typer.Exit(code=1)

    try:
        db = TOFUDatabase()
        count = db.export_toml(file)
        console.print(f"[green]Exported {count} hosts to {file}[/]")
    except Exception as e:
        error_console.print(f"[red]Error exporting database: {e}[/]")
        raise typer.Exit(code=1) from e


@tofu_app.command("import")
def tofu_import(
    file: Path = typer.Argument(
        ..., help="Input TOML file path", exists=True, file_okay=True, dir_okay=False
    ),
    replace: bool = typer.Option(
        False, "--replace", help="Replace all existing entries (default: merge)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip all confirmations and auto-accept conflicts"
    ),
) -> None:
    """Import TOFU database from a TOML file.

    By default, entries are merged with existing database. Use --replace to
    clear the database first. When fingerprint conflicts occur, you'll be
    prompted unless --force is used.

    Examples:

        # Import and merge with existing database
        $ nauyaca tofu import backup.toml

        # Replace entire database
        $ nauyaca tofu import backup.toml --replace

        # Auto-accept all conflicts
        $ nauyaca tofu import backup.toml --force
    """
    from .security.tofu import TOFUDatabase

    # Confirm replace mode if not forced
    if replace and not force:
        confirm = typer.confirm(
            "[bold yellow]Replace mode will clear all existing entries. Continue?[/]"
        )
        if not confirm:
            raise typer.Abort()

    # Create conflict handler
    def conflict_handler(hostname: str, port: int, old_fp: str, new_fp: str) -> bool:
        """Handle fingerprint conflicts."""
        if force:
            # Auto-accept in force mode
            return True

        # Show conflict to user
        console.print(f"\n[bold yellow]Fingerprint conflict for {hostname}:{port}[/]")

        conflict_table = Table(show_header=True, box=None)
        conflict_table.add_column("Source", style="bold")
        conflict_table.add_column("Fingerprint")

        conflict_table.add_row("Current (database)", old_fp[:32] + "...")
        conflict_table.add_row("New (TOML file)", new_fp[:32] + "...")

        console.print(conflict_table)

        # Prompt user
        accept = typer.confirm("Accept new fingerprint?", default=False)
        return accept

    try:
        db = TOFUDatabase()
        added, updated, skipped = db.import_toml(
            file, merge=not replace, on_conflict=conflict_handler
        )

        # Show summary
        console.print("\n[bold green]Import complete![/]")

        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Metric", style="bold cyan")
        summary_table.add_column("Count", justify="right")

        summary_table.add_row("Added", str(added))
        summary_table.add_row("Updated", str(updated))
        summary_table.add_row("Skipped", str(skipped))

        console.print(summary_table)

    except FileNotFoundError as e:
        error_console.print(f"[red]Error: {e}[/]")
        raise typer.Exit(code=1) from e
    except ValueError as e:
        error_console.print(f"[red]Invalid TOML file: {e}[/]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        error_console.print(f"[red]Error importing database: {e}[/]")
        raise typer.Exit(code=1) from e


# Create cert command group
cert_app = typer.Typer(
    help="Manage client certificates for authentication",
    no_args_is_help=True,
)
app.add_typer(cert_app, name="cert")


@cert_app.command("generate")
def cert_generate(
    name: str = typer.Argument(..., help="Name for the certificate (used in filename)"),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory (default: ~/.nauyaca/certs/)",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    valid_days: int = typer.Option(
        365,
        "--valid-days",
        help="Certificate validity in days",
    ),
    key_size: int = typer.Option(
        2048,
        "--key-size",
        help="RSA key size in bits",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing certificate files",
    ),
) -> None:
    """Generate a client certificate for Gemini authentication.

    Creates a self-signed certificate and private key that can be used
    with the --client-cert and --client-key options of the get command.

    The certificate is generated with the given name as the Common Name (CN),
    which some Gemini servers may display as your identity.

    Examples:

        # Generate a certificate named 'myidentity'
        $ nauyaca cert generate myidentity

        # Generate with custom validity and output location
        $ nauyaca cert generate myidentity --valid-days 730 -o ./certs/

        # Overwrite existing certificate
        $ nauyaca cert generate myidentity --force
    """
    import os
    import stat

    from .security.certificates import (
        generate_self_signed_cert,
        get_certificate_fingerprint,
        load_certificate,
    )

    # Determine output directory
    if output_dir is None:
        output_dir = Path.home() / ".nauyaca" / "certs"

    # Create directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output file paths
    cert_file = output_dir / f"{name}.pem"
    key_file = output_dir / f"{name}.key"

    # Check for existing files
    if cert_file.exists() and not force:
        error_console.print(
            f"[red]Error:[/] Certificate file already exists: {cert_file}"
        )
        error_console.print("Use --force to overwrite")
        raise typer.Exit(code=1)

    if key_file.exists() and not force:
        error_console.print(f"[red]Error:[/] Key file already exists: {key_file}")
        error_console.print("Use --force to overwrite")
        raise typer.Exit(code=1)

    try:
        # Generate certificate
        console.print(f"[cyan]Generating certificate for '{name}'...[/]")
        cert_pem, key_pem = generate_self_signed_cert(
            hostname=name,
            key_size=key_size,
            valid_days=valid_days,
        )

        # Write certificate file
        cert_file.write_bytes(cert_pem)

        # Write key file with restrictive permissions
        key_file.write_bytes(key_pem)
        os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        # Load cert to get fingerprint
        cert = load_certificate(cert_file)
        fingerprint = get_certificate_fingerprint(cert)

        # Calculate expiration date
        from datetime import datetime, timedelta

        expiry_date = datetime.now() + timedelta(days=valid_days)

        # Display results
        console.print("\n[bold green]Certificate generated successfully![/]\n")

        table = Table(show_header=False, box=None)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")

        table.add_row("Certificate", str(cert_file))
        table.add_row("Private key", str(key_file))
        table.add_row("Fingerprint", fingerprint[:32] + "...")
        table.add_row("Valid until", expiry_date.strftime("%Y-%m-%d"))

        console.print(table)

        console.print("\n[dim]Use with:[/]")
        console.print("  nauyaca get gemini://example.com/ \\")
        console.print(f"    --client-cert {cert_file} \\")
        console.print(f"    --client-key {key_file}")

    except Exception as e:
        error_console.print(f"[red]Error generating certificate:[/] {e}")
        raise typer.Exit(code=1) from e


@cert_app.command("info")
def cert_info(
    cert_file: Path = typer.Argument(
        ...,
        help="Path to certificate file (PEM format)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
) -> None:
    """Show information about a certificate file.

    Examples:

        $ nauyaca cert info ~/.nauyaca/certs/myidentity.pem
    """
    from .security.certificates import (
        get_certificate_fingerprint,
        get_certificate_info,
        load_certificate,
    )

    try:
        cert = load_certificate(cert_file)
        info = get_certificate_info(cert)
        fingerprint = get_certificate_fingerprint(cert)

        table = Table(show_header=False, box=None)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")

        table.add_row("Subject", info["subject"])
        table.add_row("Issuer", info["issuer"])
        table.add_row("Serial", str(info["serial_number"]))
        table.add_row("Not Before", info["not_before"])
        table.add_row("Not After", info["not_after"])
        table.add_row("Fingerprint (SHA-256)", fingerprint)

        console.print(table)

    except Exception as e:
        error_console.print(f"[red]Error reading certificate:[/] {e}")
        raise typer.Exit(code=1) from e


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
