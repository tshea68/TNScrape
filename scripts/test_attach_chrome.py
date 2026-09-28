from __future__ import annotations

import asyncio
import re
import sys

from playwright.async_api import async_playwright


CDP_URL = "http://127.0.0.1:9222"
DEFAULT_URL = (
    "https://www.thomasnet.com/suppliers/search"
    "?searchterm=ROBOTICS%20%26%20AUTOMATION&pg=3"
)


async def main() -> int:
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    print(f"Connecting to existing Chrome at {CDP_URL} ...", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)

        if not browser.contexts:
            print("ERROR: no browser context found.")
            return 2

        context = browser.contexts[0]
        pages = context.pages

        print(f"Connected. Open tabs: {len(pages)}", flush=True)

        page = None
        for candidate in pages:
            if "thomasnet.com" in candidate.url:
                page = candidate
                break

        if page is None:
            page = pages[0] if pages else await context.new_page()

        print(f"Using tab: {page.url}", flush=True)
        print(f"Navigating to: {target_url}", flush=True)

        response = await page.goto(
            target_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(5000)

        status = response.status if response else None
        title = await page.title()
        body_text = await page.locator("body").inner_text()

        print(f"status: {status}")
        print(f"title:  {title!r}")
        print(f"url:    {page.url}")

        result_match = re.search(
            r"Displaying\s+([\d,]+)[–-]([\d,]+)\s+of\s+([\d,]+)\s+results",
            body_text,
            re.I,
        )
        if result_match:
            print(
                "results: "
                f"{result_match.group(1)}-{result_match.group(2)} "
                f"of {result_match.group(3)}"
            )
        else:
            print("results: NOT FOUND")

        block_markers = [
            "automated (bot) activity",
            "access denied",
            "verify you are human",
            "captcha",
            "unusual traffic",
        ]
        found_blocks = [x for x in block_markers if x in body_text.lower()]
        print(f"block_markers: {found_blocks if found_blocks else 'none obvious'}")

        # First-pass extraction: capture likely company/profile links visible on the page.
        links = await page.locator('a[href*="/company/"], a[href*="/profile/"]').all()
        companies = []
        seen = set()

        for link in links:
            try:
                name = (await link.inner_text()).strip()
                href = await link.get_attribute("href")
            except Exception:
                continue

            if not name or not href:
                continue

            key = (name, href)
            if key in seen:
                continue
            seen.add(key)
            companies.append({"name": name, "href": href})

        print(f"candidate company/profile links: {len(companies)}")
        for company in companies[:30]:
            print(f"- {company['name']} | {company['href']}")

        if status == 200 and not found_blocks:
            print("\nPASS: attached authenticated Chrome session can load the Thomas page.")
            print("Next step: inspect the page DOM and build the supplier-card parser.")
            return 0

        print("\nBLOCKED/INCONCLUSIVE: attached Chrome did not return a normal supplier page.")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
