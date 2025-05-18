import logging
import requests
import sys
from tor.proxy import TorProxy

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_ip_info(proxy_url, logger):
    try:
        response = requests.get(
            "https://api.ipify.org?format=json",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get IP info. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching IP info: {e}")
        return None


def main():
    tor_path = r"D:\_app\Tor Browser\Browser\TorBrowser\Tor\tor.exe"

    logger = logging.getLogger(__name__)
    logger.info("Starting Tor proxy test")

    with TorProxy(tor_path) as proxy:
        logger.info(f"Tor proxy started at {proxy.socks_addr}")

        logger.info("Checking initial IP address...")
        initial_ip_info = get_ip_info(proxy.socks_addr, logger)
        logger.info(f"Initial IP: {initial_ip_info.get('ip', 'Unknown')}")

        logger.info("Checking new IP address...")
        new_ip_info = get_ip_info(proxy.socks_addr, logger)
        logger.info(f"New IP: {new_ip_info.get('ip', 'Unknown')}")

        if initial_ip_info and new_ip_info:
            initial_ip = initial_ip_info.get("ip")
            new_ip = new_ip_info.get("ip")

            if initial_ip != new_ip:
                logger.info("SUCCESS: IP address changed after circuit renewal")
                logger.info(f"Initial IP: {initial_ip} → New IP: {new_ip}")
            else:
                logger.warning(
                    "WARNING: IP address did not change after circuit renewal"
                )

    logger.info("Test completed, Tor proxy closed")


if __name__ == "__main__":
    main()