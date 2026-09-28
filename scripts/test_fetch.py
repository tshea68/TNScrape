from __future__ import annotations

import re
import sys

import httpx
from bs4 import BeautifulSoup


DEFAULT_URL = "https://www.thomasnet.com/suppliers/search?searchterm=Robotic%20Automation"
KNOWN_COMPANIES = [
    "ROI Industries Group",
    "CIM SYSTEMS",
]


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=30.0,
        http2=True,
    ) as client:
        response = client.get(url)

    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None

    text = soup.get_text(" ", strip=True)
    total_match = re.search(r"Displaying\s+\d+[–-]\d+\s+of\s+([\d,]+)\s+results", text, re.I)

    print(f"requested_url: {url}")
    print(f"final_url:     {response.url}")
    print(f"status:        {response.status_code}")
    print(f"bytes:         {len(response.content):,}")
    print(f"title:         {title!r}")
    print(f"results_total: {total_match.group(1) if total_match else 'NOT FOUND'}")

    for company in KNOWN_COMPANIES:
        print(f"{company}: {'FOUND' if company.lower() in html.lower() else 'NOT FOUND'}")

    likely_block_markers = [
        "access denied",
        "captcha",
        "verify you are human",
        "unusual traffic",
        "temporarily blocked",
    ]
    found_blocks = [marker for marker in likely_block_markers if marker in text.lower()]
    print(f"block_markers: {found_blocks if found_blocks else 'none obvious'}")

    if response.status_code != 200:
        return 2

    if any(company.lower() in html.lower() for company in KNOWN_COMPANIES):
        print("\nPASS: supplier content is present in plain HTTP HTML.")
        print("Next step: build the listing-card parser; no browser layer needed yet.")
        return 0

    print("\nINCONCLUSIVE: page loaded, but expected supplier names were absent.")
    print("Next step: inspect saved HTML / test Playwright with a persistent session.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
