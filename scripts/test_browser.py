from __future__ import annotations

import asyncio
import re
import sys

from playwright.async_api import async_playwright


DEFAULT_URL = "https://www.thomasnet.com/suppliers/search?searchterm=Robotic%20Automation"
KNOWN_COMPANIES = ["ROI Industries Group", "CIM SYSTEMS"]


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
        )
        page = await context.new_page()

        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

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

        block_markers = [
            "access denied",
            "captcha",
            "verify you are human",
            "unusual traffic",
            "temporarily blocked",
        ]
        found_blocks = [m for m in block_markers if m in text.lower()]
        print(f"block_markers: {found_blocks if found_blocks else 'none obvious'}")

        await page.screenshot(path="browser_test.png", full_page=False)
        await browser.close()

        if response and response.status == 200 and any(
            company.lower() in text.lower() for company in KNOWN_COMPANIES
        ):
            print("\nPASS: supplier content rendered in a clean browser session.")
            print("No pre-existing cookies were needed for this page.")
            return 0

        print("\nINCONCLUSIVE/BLOCKED: clean browser session did not expose supplier content.")
        print("See browser_test.png for what Thomas returned.")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
