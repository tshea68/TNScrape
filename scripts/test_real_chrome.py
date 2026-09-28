from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright


DEFAULT_URL = "https://www.thomasnet.com/suppliers/search?searchterm=Robotic%20Automation"
KNOWN_COMPANIES = ["ROI Industries Group", "CIM SYSTEMS"]


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    profile_dir = Path(".chrome-test-profile").resolve()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
        )

        page = context.pages[0] if context.pages else await context.new_page()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        html = await page.content()
        text = await page.locator("body").inner_text()
        title = await page.title()

        print(f"requested_url: {url}")
        print(f"final_url:     {page.url}")
        print(f"status:        {response.status if response else 'NO RESPONSE'}")
        print(f"title:         {title!r}")
        print(f"html_bytes:    {len(html.encode('utf-8')):,}")

        total_match = re.search(
            r"Displaying\s+\d+[–-]\d+\s+of\s+([\d,]+)\s+results",
            text,
            re.I,
        )
        print(f"results_total: {total_match.group(1) if total_match else 'NOT FOUND'}")

        for company in KNOWN_COMPANIES:
            print(f"{company}: {'FOUND' if company.lower() in text.lower() else 'NOT FOUND'}")

        if response and response.status == 200 and any(
            company.lower() in text.lower() for company in KNOWN_COMPANIES
        ):
            print("\nPASS: Thomas supplier content works in real Chrome with a persistent profile.")
            print("This profile can be reused across scraper runs.")
            await context.close()
            return 0

        print("\nStill blocked in automated real Chrome.")
        print("Leave the Chrome window open long enough to inspect what Thomas returned.")
        input("Press Enter here to close Chrome...")
        await context.close()
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
