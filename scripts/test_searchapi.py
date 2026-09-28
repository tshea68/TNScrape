from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlparse

import httpx


API_URL = "https://www.searchapi.io/api/v1/search"
DEFAULT_QUERY = 'site:thomasnet.com/suppliers "Robotic Automation"'


def main() -> int:
    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        print("ERROR: SEARCHAPI_API_KEY is not set.")
        print("Set it in your environment, then rerun this script.")
        return 2

    query = " ".join(sys.argv[1:]).strip() or DEFAULT_QUERY

    params = {
        "engine": "google",
        "q": query,
        "num": 100,
        "gl": "us",
        "hl": "en",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(API_URL, params=params, headers=headers)

    print(f"status: {response.status_code}")
    if response.status_code != 200:
        print(response.text[:2000])
        return 1

    data = response.json()
    organic = data.get("organic_results") or []

    thomas = []
    for item in organic:
        link = item.get("link") or ""
        host = urlparse(link).netloc.lower()
        if host.endswith("thomasnet.com"):
            thomas.append({
                "position": item.get("position"),
                "title": item.get("title"),
                "link": link,
                "snippet": item.get("snippet"),
            })

    print(f"query: {query}")
    print(f"organic_results: {len(organic)}")
    print(f"thomasnet_results: {len(thomas)}")

    for item in thomas[:25]:
        print("\n---")
        print(f"position: {item['position']}")
        print(f"title:    {item['title']}")
        print(f"link:     {item['link']}")
        print(f"snippet:  {item['snippet']}")

    os.makedirs("data/output", exist_ok=True)
    out_path = "data/output/searchapi_test.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved full response to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
