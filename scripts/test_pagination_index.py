from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx

API_URL = "https://www.searchapi.io/api/v1/search"
CATEGORY_ID = "68643543"
BASE_URL = "https://www.thomasnet.com/suppliers/usa/all-cities/robotic-systems-integrators-68643543"
MAX_PAGE = 20


def normalize_url(url: str) -> str:
    p = urlparse(url)
    host = p.netloc.lower().replace("www.", "")
    path = p.path.rstrip("/")

    qs = parse_qs(p.query)
    pg = qs.get("pg", [None])[0]

    normalized = f"https://{host}{path}"
    if pg:
        normalized += f"?pg={pg}"
    return normalized


def expected_url(page_num: int) -> str:
    if page_num == 1:
        return BASE_URL
    return f"{BASE_URL}?pg={page_num}"


def search(client: httpx.Client, api_key: str, query: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    params = {
        "engine": "google",
        "q": query,
        "gl": "us",
        "hl": "en",
    }

    r = client.get(API_URL, params=params, headers=headers)
    return {
        "status": r.status_code,
        "data": r.json() if r.status_code == 200 else None,
        "text": r.text,
    }


def main() -> int:
    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        print("ERROR: SEARCHAPI_API_KEY is not set.")
        return 2

    Path("data/output").mkdir(parents=True, exist_ok=True)

    all_results = []
    csv_rows = []

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for page_num in range(1, MAX_PAGE + 1):
            exp = expected_url(page_num)
            exp_norm = normalize_url(exp)

            queries = [
                f'site:thomasnet.com/suppliers "{CATEGORY_ID}" "pg={page_num}"',
                f'"{exp}"',
            ]

            if page_num == 1:
                queries.append(f'"{BASE_URL}"')

            found = False
            matched_url = ""
            matched_position = ""
            matched_title = ""
            matched_snippet = ""
            matched_query = ""

            page_record = {
                "page_number": page_num,
                "expected_url": exp,
                "found": False,
                "queries": [],
            }

            for query in queries:
                result = search(client, api_key, query)

                qrecord = {
                    "query": query,
                    "status": result["status"],
                    "organic_result_count": 0,
                    "thomas_urls": [],
                }

                if result["status"] == 200 and result["data"]:
                    organic = result["data"].get("organic_results") or []
                    qrecord["organic_result_count"] = len(organic)

                    for item in organic:
                        link = item.get("link") or ""
                        if "thomasnet.com" not in link:
                            continue

                        entry = {
                            "position": item.get("position"),
                            "title": item.get("title"),
                            "link": link,
                            "snippet": item.get("snippet"),
                        }
                        qrecord["thomas_urls"].append(entry)

                        if normalize_url(link) == exp_norm and not found:
                            found = True
                            matched_url = link
                            matched_position = item.get("position") or ""
                            matched_title = item.get("title") or ""
                            matched_snippet = item.get("snippet") or ""
                            matched_query = query

                page_record["queries"].append(qrecord)
                time.sleep(0.35)

            page_record["found"] = found
            all_results.append(page_record)

            csv_rows.append({
                "page_number": page_num,
                "found": found,
                "expected_url": exp,
                "matched_url": matched_url,
                "serp_position": matched_position,
                "query": matched_query,
                "title": matched_title,
                "snippet": matched_snippet,
            })

            print(f"pg={page_num} {'FOUND' if found else 'NOT FOUND'}")

    found_count = sum(1 for r in csv_rows if r["found"])
    tested = len(csv_rows)
    missing = tested - found_count
    coverage = (found_count / tested * 100) if tested else 0

    print()
    print(f"pages tested:  {tested}")
    print(f"pages found:   {found_count}")
    print(f"pages missing: {missing}")
    print(f"coverage:      {coverage:.1f}%")

    json_path = Path("data/output/pagination_index_test.json")
    json_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    csv_path = Path("data/output/pagination_index_test.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "page_number",
                "found",
                "expected_url",
                "matched_url",
                "serp_position",
                "query",
                "title",
                "snippet",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    print()
    print(f"Saved: {json_path}")
    print(f"Saved: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
