#!/usr/bin/env python3
"""
ADS MCP Server — exposes NASA ADS search and BibTeX export as MCP tools.
Add to claude_desktop_config.json under mcpServers.
"""

import json
import re
from collections import Counter
import requests
from mcp.server.fastmcp import FastMCP

ADS_API  = "https://api.adsabs.harvard.edu/v1/search/query"
ADS_BIB  = "https://api.adsabs.harvard.edu/v1/export/bibtex"
API_KEY  = "uAObYFklGKLq35CwQCjysY1oCTBX7spMeepcHGlQ"
HEADERS  = {"Authorization": f"Bearer {API_KEY}"}

mcp = FastMCP("ads")


def make_cite_keys(entries: list[dict]) -> dict[str, str]:
    """
    Generate LastYYYY cite keys with a/b/c suffixes for duplicates.
    Returns a dict mapping original ADS bibcode -> new cite key.
    """
    # Build base keys
    base_keys = []
    for e in entries:
        last = e["author"].split(",")[0].strip()
        # Remove non-ASCII and spaces, title-case
        last = re.sub(r"[^A-Za-z]", "", last)
        year = e["year"]
        base_keys.append(f"{last}{year}")

    # Count occurrences to detect duplicates
    counts = Counter(base_keys)
    seen = Counter()
    final_keys = {}
    for e, base in zip(entries, base_keys):
        if counts[base] > 1:
            suffix = chr(ord("a") + seen[base])
            seen[base] += 1
            final_keys[e["bibcode"]] = f"{base}{suffix}"
        else:
            final_keys[e["bibcode"]] = base

    return final_keys


def rewrite_cite_keys(bibtex: str, key_map: dict[str, str]) -> str:
    """Replace ADS bibcodes in BibTeX entry headers with author+year keys."""
    for bibcode, new_key in key_map.items():
        # Match @TYPE{bibcode, at the start of each entry
        bibtex = re.sub(
            r"(@\w+\{)" + re.escape(bibcode) + r",",
            r"\g<1>" + new_key + ",",
            bibtex
        )
    return bibtex


@mcp.tool()
def ads_search(query: str, max_results: int = 20) -> str:
    """Search NASA ADS. Returns a JSON list of results with bibcode, author, year, title, journal.

    Use ADS query syntax, e.g.:
      author:"^Zhou, Yifan" HST accreting planet
      title:"phase curve" year:2020-2024
      bibcode:2023ApJ...945L...5Z
    """
    params = {
        "q": query,
        "fl": "bibcode,title,author,year,pub",
        "rows": max_results,
        "sort": "date desc",
    }
    r = requests.get(ADS_API, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    docs = r.json().get("response", {}).get("docs", [])

    results = []
    for d in docs:
        authors = d.get("author", [])
        author_str = authors[0] if authors else "Unknown"
        if len(authors) > 1:
            author_str += " et al."
        title = d.get("title", ["Unknown"])[0]
        results.append({
            "bibcode": d.get("bibcode", ""),
            "author":  author_str,
            "year":    d.get("year", ""),
            "title":   title,
            "journal": d.get("pub", ""),
        })

    return json.dumps(results, indent=2)


@mcp.tool()
def ads_bibtex(bibcodes: list[str]) -> str:
    """Fetch BibTeX entries from NASA ADS for the given list of bibcodes.
    Cite keys are formatted as LastYYYY (e.g. Zhou2021), with a/b/c suffixes
    when multiple entries share the same first author and year.

    Example: ads_bibtex(["2023ApJ...945L...5Z", "2021AJ....161..244Z"])
    """
    # Fetch metadata to build cite keys
    params = {
        "q": " OR ".join(f"bibcode:{b}" for b in bibcodes),
        "fl": "bibcode,author,year",
        "rows": len(bibcodes),
    }
    r = requests.get(ADS_API, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    docs = r.json().get("response", {}).get("docs", [])

    # Preserve original bibcode order
    doc_map = {d["bibcode"]: d for d in docs}
    ordered = []
    for b in bibcodes:
        if b in doc_map:
            d = doc_map[b]
            authors = d.get("author", [])
            ordered.append({
                "bibcode": b,
                "author": authors[0] if authors else "Unknown",
                "year": d.get("year", "0000"),
            })

    key_map = make_cite_keys(ordered)

    # Fetch BibTeX
    r2 = requests.post(ADS_BIB, headers={**HEADERS, "Content-Type": "application/json"},
                       json={"bibcode": bibcodes}, timeout=15)
    r2.raise_for_status()
    bibtex = r2.json().get("export", "")

    return rewrite_cite_keys(bibtex, key_map)


if __name__ == "__main__":
    mcp.run(transport="stdio")
