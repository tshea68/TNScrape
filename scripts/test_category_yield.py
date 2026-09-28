from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx


API_URL = "https://www.searchapi.io/api/v1/search"
DEFAULT_CATEGORY_URL = "https://www.thomasnet.com/suppliers/usa/all-cities/robotic-systems-integrators-68643543"
DEFAULT_CATEGORY_NAME = "Robotic Systems Integrators"
MAX_PAGES = 10


def google_search(client: httpx.Client, api_key: str, q: str, page: int = 1) -> dict:
    params = {
        "engine": "google",
        "q": q,
        "page": page,
        "gl": "us",
        "hl": "en",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    r = client.get(API_URL, params=params, headers=headers)
    r.raise_for_status()
    return r.json()


def main() -> int:
    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        print("ERROR: SEARCHAPI_API_KEY is not set.")
        return 2

    category_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CATEGORY_URL
    category_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CATEGORY_NAME

    parsed = urlparse(category_url)
    canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    queries = [
        f'site:{parsed.netloc}{parsed.path} "{category_name}"',
        f'"{canonical}"',
        f'site:thomasnet.com/suppliers "{category_name}"',
    ]

    Path("data/output").mkdir(parents=True, exist_ok=True)

    seen_links: dict[str, dict] = {}
    rows: list[dict] = []

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for query_idx, query in enumerate(queries, start=1):
            print(f"\n=== QUERY {query_idx}: {query}")
            empty_streak = 0

            for page in range(1, MAX_PAGES + 1):
                data = google_search(client, api_key, query, page=page)
                organic = data.get("organic_results") or []
                print(f"page {page}: {len(organic)} organic results")

                if not organic:
                    empty_streak += 1
                    if empty_streak >= 2:
                        break
                else:
                    empty_streak = 0

                for item in organic:
                    link = item.get("link") or ""
                    if "thomasnet.com" not in link:
                        continue
                    record = {
                        "query": query,
                        "serp_page": page,
                        "position": item.get("position"),
                        "title": item.get("title"),
                        "link": link,
                        "snippet": item.get("snippet"),
                    }
                    rows.append(record)
                    seen_links.setdefault(link, record)

                time.sleep(0.25)

    print(f"\nUnique Thomas URLs found: {len(seen_links)}")

    same_category_pages = []
    other_thomas = []
    for link, rec in seen_links.items():
        lp = urlparse(link)
        if lp.path.rstrip("/") == parsed.path.rstrip("/"):
            same_category_pages.append(rec)
        else:
            other_thomas.append(rec)

    print(f"Same category URL family: {len(same_category_pages)}")
    print(f"Other Thomas URLs:        {len(other_thomas)}")

    print("\n--- SAME CATEGORY FAMILY ---")
    for rec in same_category_pages[:50]:
        print(f"{rec['link']}\n  {rec['title']}\n  {rec['snippet']}\n")

    print("\n--- OTHER THOMAS URLS ---")
    for rec in other_thomas[:50]:
        print(f"{rec['link']}\n  {rec['title']}\n  {rec['snippet']}\n")

    out = {
        "category_url": category_url,
        "category_name": category_name,
        "queries": queries,
        "unique_thomas_urls": list(seen_links.values()),
        "all_rows": rows,
    }
    out_path = Path("data/output/category_yield_test.json")
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved full results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
