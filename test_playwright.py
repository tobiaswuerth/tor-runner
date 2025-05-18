import logging
import sys
from tor.proxy import TorProxy
from playwright.sync_api import sync_playwright
import time

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def ensure_browsers_installed(logger):
    try:
        import subprocess
        from playwright._impl._driver import (
            compute_driver_executable,
            get_driver_env,
        )

        driver_executable, driver_cli = compute_driver_executable()
        subprocess.run(
            [driver_executable, driver_cli, "install", "firefox"],
            env=get_driver_env(),
            check=True,
        )
    except Exception as e:
        logger.error(f"Browser installed failed: {e}", exc_info=True)
        exit(1)


def main():
    logger = logging.getLogger(__name__)
    ensure_browsers_installed(logger)

    tor_path = r"D:\_app\Tor Browser\Browser\TorBrowser\Tor\tor.exe"
    logger.info("Starting Tor proxy test")

    with TorProxy(tor_path) as proxy:
        logger.info("Proxy open, starting Playwright")

        with sync_playwright() as p:
            browser = p.firefox.launch(
                headless=False,
                proxy={"server": proxy.socks_addr},
            )

            logger.info("Browser launched, opening page")
            page1 = browser.new_page()
            page1.goto("https://check.torproject.org/")
            page2 = browser.new_page()
            page2.goto("https://check.torproject.org/")

            logger.info("Page loaded, waiting for 10 seconds")
            time.sleep(10)  # some time to interact with the browser

            logger.info("Closing browser")
            page1.close()
            page2.close()
            browser.close()


if __name__ == "__main__":
    main()
