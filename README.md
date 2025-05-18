# tor-runner

A Python utility for managing Tor processes to enable anonymous web browsing through SOCKS5 proxies.

## Installation

[![PyPI version](https://badge.fury.io/py/py-tor-runner.svg?icon=si%3Apython)](https://badge.fury.io/py/py-tor-runner)

Requires local [Tor Browser](https://www.torproject.org/download/) to be installed.

```bash
pip install py-tor-runner
```

`requirements.txt` is only necessary if you want to run the provided test files. Otherwise, tor-runner is a standalone library compatible with default Python packages.

---

### Basic Usage with Requests
```python
import requests
from tor import TorProxy

with TorProxy("C:/path/to/tor/browser/tor.exe") as proxy:
    proxy_url = proxy.socks_addr  # Returns "socks5://127.0.0.1:{port}"
    
    # Example with requests
    response = requests.get('https://check.torproject.org', proxies={
        'http': proxy_url,
        'https': proxy_url
    })
    print(response.text)
```

### Basic Usage with Playwright

```python
import time
from tor import TorProxy
from playwright.sync_api import sync_playwright

with TorProxy("C:/path/to/tor/browser/tor.exe") as proxy:
    with sync_playwright() as p:
        browser = p.firefox.launch(
            headless=False,
            proxy={"server": proxy.socks_addr}
        )
        
        # Each page has its own IP through the Tor network
        page1 = browser.new_page()
        page1.goto("https://check.torproject.org")
        
        page2 = browser.new_page()
        page2.goto("https://check.torproject.org")
        
        time.sleep(5) # to let you check manually
        browser.close()
```
