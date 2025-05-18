import subprocess
import tempfile
import pathlib
import socket
import atexit
import time
import logging
import threading


def _free_port() -> int:
    """
    Find and return a free port number on localhost.

    Returns:
        int: A port number that is currently available.
    """
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TorProxy:
    """
    Manages a Tor proxy process.

    This class handles starting, monitoring, and stopping a Tor process.
    It implements the context manager protocol so it can be used with 'with' statements.

    Example:
        with TorProxy('/path/to/tor') as proxy:
            # Use proxy.socks_addr in your HTTP client
            requests.get('https://check.torproject.org', proxies={'https': proxy.socks_addr})
    """

    def __init__(
        self,
        tor_exe_path: str,
        socks_port: int | None = None,
        ctrl_port: int | None = None,
        logger: logging.Logger = None,
        **spawn_kwargs,
    ):
        """
        Initialize a Tor proxy manager.

        Args:
            tor_exe_path: Path to the Tor executable
            socks_port: Port for the SOCKS proxy (random if None)
            ctrl_port: Port for the control interface (random if None)
            logger: Custom logger instance (creates one if None)
            **spawn_kwargs: Additional arguments to pass to Tor as command line options

        Raises:
            FileNotFoundError: If the Tor executable does not exist
        """
        self.logger = logger or logging.getLogger(__name__)
        self.tor_path = pathlib.Path(tor_exe_path)
        if not self.tor_path.exists():
            self.logger.error(f"Tor executable not found at {self.tor_path}")
            raise FileNotFoundError(f"Tor executable not found at {self.tor_path}")

        self.socks_port = socks_port or _free_port()
        self.ctrl_port = ctrl_port or _free_port()
        self.spawn_kwargs = spawn_kwargs
        self.logger.info(
            f"TorProxy initialized with SOCKS port {self.socks_port} and control port {self.ctrl_port}"
        )

        self.process = None

    def __enter__(self):
        """
        Start the Tor process when entering the context manager.

        This method starts Tor, waits for it to be ready, and sets up logging.

        Returns:
            self: The TorProxy instance

        Raises:
            RuntimeError: If Tor fails to start within the timeout period
        """
        self.logger.info("Starting Tor process")
        cmd = [
            str(self.tor_path),
            f"--SocksPort",
            f"{self.socks_port}",
            f"--ControlPort",
            f"{self.ctrl_port}",
            f"--DataDirectory",
            str(pathlib.Path(tempfile.mkdtemp(prefix="tor_data_"))),
        ]
        if self.spawn_kwargs:
            for key, value in self.spawn_kwargs.items():
                cmd.append(f"--{key}")
                cmd.append(str(value))

        self.logger.debug(f"Tor command: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )

        self._stop_logging = False
        self._log_thread = threading.Thread(
            target=self._log_process_output, daemon=True
        )
        self._log_thread.start()

        atexit.register(self.cleanup)
        self.logger.debug("Tor process started, waiting for it to be ready")

        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                s = socket.create_connection(("127.0.0.1", self.socks_port), 1)
                s.close()
                self.logger.info(
                    f"Tor successfully started and listening on port {self.socks_port}"
                )
                break
            except OSError:
                time.sleep(0.2)
        else:
            self.logger.error("Timeout while waiting for Tor to start")
            raise RuntimeError("Tor failed to start within 30 s")
        return self

    def __exit__(self, exc_type, exc, tb):
        """
        Clean up resources when exiting the context manager.

        This method stops the Tor process and related resources.

        Args:
            exc_type: The exception type if an exception was raised
            exc: The exception instance if an exception was raised
            tb: The traceback if an exception was raised
        """
        self.logger.info("Exiting Tor proxy context")
        self.cleanup()

    @property
    def socks_addr(self) -> str:
        """
        Get the SOCKS proxy address for use with HTTP clients.

        Returns:
            str: The SOCKS5 proxy URL in the format 'socks5://127.0.0.1:port'
        """
        return f"socks5://127.0.0.1:{self.socks_port}"

    def _log_process_output(self):
        """
        Continuously read and log the Tor process output.

        This method runs in a separate thread to consume and log the
        output from the Tor process until the process terminates or
        _stop_logging is set to True.
        """
        if not self.process:
            return

        while not self._stop_logging and self.process.poll() is None:
            line = self.process.stdout.readline()
            if line:
                line = line.strip()
                if line:
                    self.logger.debug(line)
            else:
                time.sleep(0.1)

    def cleanup(self):
        """
        Clean up resources associated with the Tor process.

        This method stops the logging thread and terminates the Tor process
        gracefully if possible, or forcefully if necessary.
        """
        self._stop_logging = True
        if self._log_thread and self._log_thread.is_alive():
            self._log_thread.join(timeout=1)

        if self.process and self.process.poll() is None:
            self.logger.info("Terminating Tor process")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                self.logger.debug("Tor process terminated gracefully")
            except subprocess.TimeoutExpired:
                self.logger.warning(
                    "Tor process did not terminate gracefully, killing it"
                )
                self.process.kill()
        if self.process:
            self.process = None
            self.logger.info("Tor process cleanup completed")
