"""Process supervisor for hot-reload.

This module provides the Supervisor class that manages the server subprocess
lifecycle, watching for file changes and restarting the server when needed.
"""

import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

from ...utils.logging import get_logger

if TYPE_CHECKING:
    from .config import ReloadConfig

logger = get_logger(__name__)

# Timeout for graceful shutdown before force-killing
SHUTDOWN_TIMEOUT = 10.0

# Brief pause after killing server to allow port release
PORT_RELEASE_DELAY = 0.5


class Supervisor:
    """Process supervisor for hot-reload functionality.

    Manages the server subprocess lifecycle:
    - Spawns the server as a subprocess
    - Monitors for file changes
    - Terminates and restarts the server on changes
    - Handles signals (SIGINT/SIGTERM) for graceful shutdown

    Examples:
        >>> from nauyaca.server.reload import ReloadConfig, Supervisor
        >>> config = ReloadConfig(watch_dirs=[Path("./src")])
        >>> supervisor = Supervisor(config, server_args=["serve", "./capsule"])
        >>> supervisor.run()  # Blocks until interrupted
    """

    def __init__(
        self,
        config: "ReloadConfig",
        server_args: list[str],
    ) -> None:
        """Initialize supervisor.

        Args:
            config: Reload configuration.
            server_args: Command-line arguments for the server subprocess.
                Should NOT include --reload flags (to prevent recursion).
        """
        from .watcher import FileWatcher

        self.config = config
        self.server_args = server_args
        self.watcher: FileWatcher = FileWatcher.create(config)
        self.process: subprocess.Popen[bytes] | None = None
        self._should_stop = False

    def run(self) -> None:
        """Run the supervisor (blocking).

        Starts the server and watches for file changes. Runs until interrupted
        by SIGINT or SIGTERM.
        """
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        logger.info(
            "supervisor_starting",
            watch_dirs=[str(d) for d in self.config.watch_dirs],
            extensions=self.config.watch_extensions,
        )

        try:
            while not self._should_stop:
                # Start/restart server
                self._start_server()

                if self._should_stop:
                    break

                # Wait for file changes
                changed_files = self.watcher.wait_for_changes()

                if self._should_stop:
                    break

                # Log the changes and restart
                logger.info(
                    "reload_triggered",
                    changed_files=[str(f) for f in changed_files[:5]],
                    total_changes=len(changed_files),
                )

                self._stop_server()

                # Brief pause to allow port release
                time.sleep(PORT_RELEASE_DELAY)

        except KeyboardInterrupt:
            # Signal received - server already stopped in signal handler
            logger.debug("supervisor_interrupted")

        except Exception as e:
            logger.error("supervisor_error", error=str(e))
            raise

        finally:
            self._stop_server()
            logger.info("supervisor_stopped")

    def _start_server(self) -> None:
        """Start the server subprocess."""
        cmd = self._build_command()

        logger.info("starting_server", command=" ".join(cmd))

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            logger.debug("server_started", pid=self.process.pid)

        except Exception as e:
            logger.error("server_start_failed", error=str(e))
            raise

    def _stop_server(self) -> None:
        """Stop the server subprocess gracefully."""
        if self.process is None:
            return

        if self.process.poll() is not None:
            # Process already exited
            self.process = None
            return

        logger.info("stopping_server", pid=self.process.pid)

        try:
            # Try graceful shutdown with SIGTERM
            self.process.terminate()

            try:
                self.process.wait(timeout=SHUTDOWN_TIMEOUT)
                logger.debug("server_stopped_gracefully", pid=self.process.pid)
            except subprocess.TimeoutExpired:
                # Force kill after timeout
                logger.warning("server_timeout", action="force_killing")
                self.process.kill()
                self.process.wait()
                logger.debug("server_killed", pid=self.process.pid)

        except ProcessLookupError:
            # Process already dead
            logger.debug("server_already_stopped")

        finally:
            self.process = None

    def _build_command(self) -> list[str]:
        """Build the command to spawn the server subprocess.

        Returns:
            List of command arguments.
        """
        # Use the current Python interpreter
        cmd = [sys.executable, "-m", "nauyaca"]
        cmd.extend(self.server_args)
        return cmd

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number.
            frame: Current stack frame (unused).
        """
        sig_name = signal.Signals(signum).name
        logger.info("signal_received", signal=sig_name)
        self._should_stop = True

        # Stop the server immediately
        self._stop_server()

        # Raise KeyboardInterrupt to break out of blocking watcher
        raise KeyboardInterrupt


def run_with_reload(
    config: "ReloadConfig",
    server_args: list[str],
) -> None:
    """Run the server with hot-reload enabled.

    This is the main entry point for the reload functionality.

    Args:
        config: Reload configuration.
        server_args: Arguments to pass to the server subprocess.
            Should NOT include --reload or --reload-dir flags.

    Examples:
        >>> from pathlib import Path
        >>> from nauyaca.server.reload import ReloadConfig, run_with_reload
        >>> config = ReloadConfig(watch_dirs=[Path("./src")])
        >>> run_with_reload(config, ["serve", "./capsule", "--port", "1965"])
    """
    supervisor = Supervisor(config, server_args)
    supervisor.run()
