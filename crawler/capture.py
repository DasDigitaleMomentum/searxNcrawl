"""Interactive session capture for authenticated crawling.

Opens a headed (visible) Playwright browser, lets the user complete
a login flow (including OAuth, SSO, MFA), then exports the browser
storage state to a JSON file for reuse.

Example usage:

    # CLI
    crawl capture-auth --url https://login.example.com --output auth_state.json

    # Python
    from crawler.capture import capture_auth_state
    path = await capture_auth_state(
        url="https://login.example.com",
        output_path="auth_state.json",
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


async def capture_auth_state(
    url: str,
    output_path: str = "auth_state.json",
    wait_for_url: Optional[str] = None,
    timeout: int = 300,
) -> str:
    """Open a headed browser, let the user login, export storage state.

    The browser window will remain open until one of:
    1. The browser navigates to a URL matching ``wait_for_url`` (regex).
    2. The user closes the browser window manually.
    3. The ``timeout`` (in seconds) is reached.

    Args:
        url: The login page URL to navigate to.
        output_path: Path to save the storage state JSON.
        wait_for_url: Optional regex pattern. When the browser URL
            matches this pattern, assume login is complete.
        timeout: Maximum seconds to wait for login completion.

    Returns:
        Absolute path to the saved storage state file.

    Raises:
        TimeoutError: If login was not completed within the timeout.
        RuntimeError: If Playwright is not installed.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for capture-auth. "
            "Install it with: pip install playwright && playwright install chromium"
        ) from exc

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Opening browser for login at: %s", url)
    LOGGER.info("Timeout: %d seconds", timeout)
    if wait_for_url:
        LOGGER.info("Will auto-capture when URL matches: %s", wait_for_url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("\U0001f510 INTERACTIVE LOGIN")
        print("=" * 60)
        print(f"\nBrowser opened at: {url}")
        print("Complete the login flow in the browser window.")
        if wait_for_url:
            print(f"Auto-capture when URL matches: {wait_for_url}")
        else:
            print("Close the browser window when done, or press Ctrl+C.")
        print(f"Timeout: {timeout}s")
        print("=" * 60 + "\n")

        login_complete = False

        try:
            if wait_for_url:
                # Poll for URL match
                pattern = re.compile(wait_for_url)
                elapsed = 0
                poll_interval = 0.5
                while elapsed < timeout:
                    try:
                        current_url = page.url
                    except Exception:
                        # Browser was closed
                        break

                    if pattern.search(current_url):
                        LOGGER.info("URL match detected: %s", current_url)
                        login_complete = True
                        # Give time for cookies to settle
                        await asyncio.sleep(2)
                        break

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
            else:
                # Wait for browser close or timeout
                elapsed = 0
                poll_interval = 0.5
                while elapsed < timeout:
                    try:
                        # Check if page/context is still alive
                        _ = page.url
                    except Exception:
                        login_complete = True
                        break

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

        except KeyboardInterrupt:
            LOGGER.info("Capture interrupted by user")
            login_complete = True

        # Export storage state before closing
        try:
            state = await context.storage_state()
            with open(output, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)

            cookie_count = len(state.get("cookies", []))
            origin_count = len(state.get("origins", []))
            LOGGER.info(
                "Saved storage state: %d cookies, %d origins -> %s",
                cookie_count,
                origin_count,
                output,
            )

            print(f"\n\u2705 Storage state saved to: {output}")
            print(f"   Cookies: {cookie_count}")
            print(f"   Origins (localStorage): {origin_count}")
            print("\nUsage:")
            print(f"  crawl --storage-state {output} https://protected-page.example.com")

        except Exception as exc:
            LOGGER.error("Failed to export storage state: %s", exc)
            raise
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    return str(output)


def capture_auth_state_sync(
    url: str,
    output_path: str = "auth_state.json",
    wait_for_url: Optional[str] = None,
    timeout: int = 300,
) -> str:
    """Synchronous wrapper for capture_auth_state."""
    return asyncio.run(
        capture_auth_state(
            url=url,
            output_path=output_path,
            wait_for_url=wait_for_url,
            timeout=timeout,
        )
    )
