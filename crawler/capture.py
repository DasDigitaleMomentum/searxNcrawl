"""Interactive session capture for authenticated crawling.

Opens a headed (visible) Playwright browser, lets the user complete
a login flow (including OAuth, SSO, MFA), then exports the browser
storage state to a JSON file for reuse.

Example usage:

    # CLI — storage state file
    crawl capture-auth --url https://login.example.com --output auth_state.json

    # CLI — persistent browser profile
    crawl capture-auth --url https://login.example.com --profile my-site

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


def _resolve_profile_dir(profile: str) -> Path:
    """Resolve a profile name or path to an absolute directory."""
    p = Path(profile)
    if p.is_absolute():
        return p
    # Store named profiles under ~/.crawl4ai/profiles/<name>
    return Path.home() / ".crawl4ai" / "profiles" / profile


async def capture_auth_state(
    url: str,
    output_path: str = "auth_state.json",
    wait_for_url: Optional[str] = None,
    timeout: int = 300,
    profile: Optional[str] = None,
) -> str:
    """Open a headed browser, let the user login, export storage state.

    The browser window will remain open until one of:
    1. The browser navigates to a URL matching ``wait_for_url`` (regex).
    2. The user closes the browser window manually.
    3. The ``timeout`` (in seconds) is reached.

    Args:
        url: The login page URL to navigate to.
        output_path: Path to save the storage state JSON (ignored when
            *profile* is set — the file is saved inside the profile dir).
        wait_for_url: Optional regex pattern. When the browser URL
            matches this pattern, assume login is complete.
        timeout: Maximum seconds to wait for login completion.
        profile: Optional profile name or path. When set, uses a
            persistent Chromium user-data-dir so cookies, localStorage
            and service-workers survive across sessions.

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

    # Resolve output path
    if profile:
        profile_dir = _resolve_profile_dir(profile)
        profile_dir.mkdir(parents=True, exist_ok=True)
        output = profile_dir / "storage_state.json"
        LOGGER.info("Using persistent profile: %s", profile_dir)
    else:
        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Opening browser for login at: %s", url)
    LOGGER.info("Timeout: %d seconds", timeout)
    if wait_for_url:
        LOGGER.info("Will auto-capture when URL matches: %s", wait_for_url)

    async with async_playwright() as pw:
        if profile:
            # Persistent context — cookies/localStorage survive restarts
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            browser = None  # persistent context IS the browser
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
        else:
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



        try:
            if wait_for_url:
                # Poll for URL match
                pattern = re.compile(wait_for_url)
                elapsed = 0
                poll_interval = 0.5

                # Grace period: skip URL matching for the first few seconds
                # to avoid triggering on intermediate OAuth/SSO redirects
                # that may contain the target pattern in query params.
                grace_period = 5.0
                LOGGER.info(
                    "Waiting %.0fs grace period before URL matching "
                    "(to skip OAuth redirects)...",
                    grace_period,
                )
                await asyncio.sleep(grace_period)
                elapsed += grace_period

                while elapsed < timeout:
                    # Check if page/browser was closed
                    if page.is_closed():
                        LOGGER.info("Browser closed by user")
                        break
                    try:
                        current_url = page.url
                    except Exception:
                        break

                    if pattern.search(current_url):
                        LOGGER.info("URL match detected: %s", current_url)

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
                    # Check if page/browser was closed
                    if page.is_closed():
                        LOGGER.info("Browser closed by user")
                        break
                    try:
                        _ = page.url
                    except Exception:
                        break

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

        except KeyboardInterrupt:
            LOGGER.info("Capture interrupted by user")


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
            if profile:
                print("\nUsage (persistent profile):")
                print(f"  crawl --auth-profile {profile_dir} https://protected-page.example.com")
            else:
                print("\nUsage:")
                print(f"  crawl --storage-state {output} https://protected-page.example.com")

        except Exception as exc:
            LOGGER.error("Failed to export storage state: %s", exc)
            raise
        finally:
            try:
                if browser:
                    await browser.close()
                else:
                    await context.close()
            except Exception:
                pass

    return str(output)


def capture_auth_state_sync(
    url: str,
    output_path: str = "auth_state.json",
    wait_for_url: Optional[str] = None,
    timeout: int = 300,
    profile: Optional[str] = None,
) -> str:
    """Synchronous wrapper for capture_auth_state."""
    return asyncio.run(
        capture_auth_state(
            url=url,
            output_path=output_path,
            wait_for_url=wait_for_url,
            timeout=timeout,
            profile=profile,
        )
    )
