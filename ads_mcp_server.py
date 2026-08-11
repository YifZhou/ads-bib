#!/usr/bin/env python3
"""
ADS MCP Server — exposes NASA ADS search, BibTeX export, and library tools.
Add to claude_desktop_config.json under mcpServers.
"""

import json
import os
import re
from collections import Counter
from typing import Any, Optional
import requests
from mcp.server.fastmcp import FastMCP

ADS_API  = "https://api.adsabs.harvard.edu/v1/search/query"
ADS_BIB  = "https://api.adsabs.harvard.edu/v1/export/bibtex"
ADS_LIB  = "https://api.adsabs.harvard.edu/v1/biblib"
API_KEY  = 'YOUR_ADS_API_TOKEN_HERE'  # Replace with your actual ADS API key or set via environment variable
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


def _require_api_key() -> None:
    if not API_KEY:
        raise RuntimeError(
            "ADS API token is not configured. Set ADS_DEV_KEY, "
            "NASA_ADS_TOKEN, ADS_API_KEY, or ADS_API_TOKEN in the environment "
            "used to launch this MCP server."
        )


def _ads_request(
    method: str,
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 30,
) -> Any:
    """Make an ADS API request and return decoded JSON."""
    _require_api_key()
    headers = dict(HEADERS)
    if payload is not None:
        headers["Content-Type"] = "application/json"
    response = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    if not response.text.strip():
        return {}
    return response.json()


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _confirmation_required(action: str, details: dict[str, Any]) -> str:
    return _json({
        "confirmation_required": True,
        "action": action,
        "details": details,
        "how_to_confirm": "Call this tool again with confirm=True only after the user explicitly confirms this exact action.",
    })


def _batch(items: list[str], size: int = 200) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _raw_bibtex_for_bibcodes(bibcodes: list[str]) -> str:
    """Fetch ADS BibTeX without rewriting keys."""
    chunks = []
    for group in _batch(bibcodes):
        data = _ads_request(
            "POST",
            ADS_BIB,
            payload={"bibcode": group},
            timeout=30,
        )
        chunks.append(data.get("export", ""))
    return "\n".join(chunk.rstrip() for chunk in chunks if chunk).rstrip() + "\n"


def _library_bibcodes(library_id: str) -> tuple[list[str], dict[str, Any]]:
    data = _ads_request(
        "GET",
        f"{ADS_LIB}/libraries/{library_id}",
        params={"raw": "true"},
    )
    return data.get("documents", []), data.get("metadata", {})


@mcp.tool()
def ads_search(query: str, max_results: int = 20) -> str:
    """Search NASA ADS. Returns a JSON list of results with bibcode, author, year, title, journal.

    Use ADS query syntax, e.g.:
      author:"^Zhou, Yifan" HST accreting planet
      title:"phase curve" year:2020-2024
      bibcode:2023ApJ...945L...5Z
    """
    _require_api_key()
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
    _require_api_key()
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


@mcp.tool()
def ads_library_list(
    start: int = 0,
    rows: int = 100,
    sort: str = "date_created",
    order: str = "asc",
) -> str:
    """List ADS libraries for the authenticated ADS user.

    Returns library names, IDs, document counts, permissions, public/private
    state, owners, and timestamps. Requires the ADS API token configured for
    this MCP server.
    """
    params = {
        "start": start,
        "rows": rows,
        "sort": sort,
        "order": order,
    }
    return _json(_ads_request("GET", f"{ADS_LIB}/libraries", params=params))


@mcp.tool()
def ads_library_get(library_id: str, raw: bool = True) -> str:
    """Read one ADS library by ID.

    By default `raw=True` returns the exact bibcodes stored in the library. Use
    `raw=False` when the full ADS/Solr response is needed.
    """
    params = {"raw": "true"} if raw else None
    return _json(_ads_request("GET", f"{ADS_LIB}/libraries/{library_id}", params=params))


@mcp.tool()
def ads_library_bibtex(library_id: str, key_style: str = "bibcode") -> str:
    """Export one ADS library as BibTeX.

    key_style:
      - "bibcode": preserve ADS bibcodes as BibTeX keys; best for Zotero import.
      - "authoryear": rewrite keys like ads_bibtex, e.g. Zhou2021/Zhou2021a.
    """
    bibcodes, metadata = _library_bibcodes(library_id)
    if key_style == "bibcode":
        return _raw_bibtex_for_bibcodes(bibcodes)
    if key_style == "authoryear":
        return ads_bibtex(bibcodes)
    return _json({
        "error": "invalid_key_style",
        "allowed_values": ["bibcode", "authoryear"],
        "library_id": library_id,
        "library_name": metadata.get("name"),
    })


@mcp.tool()
def ads_library_create(
    name: str = "Untitled Library",
    description: str = "My ADS library",
    bibcodes: Optional[list[str]] = None,
    public: bool = False,
    confirm: bool = False,
) -> str:
    """Create an ADS library. This mutates ADS state and requires confirm=True."""
    bibcodes = bibcodes or []
    details = {
        "name": name,
        "description": description,
        "num_bibcodes": len(bibcodes),
        "public": public,
    }
    if not confirm:
        return _confirmation_required("create_ads_library", details)
    payload = {
        "name": name,
        "description": description,
        "public": public,
        "bibcode": bibcodes,
    }
    return _json(_ads_request("POST", f"{ADS_LIB}/libraries", payload=payload))


@mcp.tool()
def ads_library_add_bibcodes(
    library_id: str,
    bibcodes: list[str],
    confirm: bool = False,
) -> str:
    """Add bibcodes to an ADS library. This mutates ADS state and requires confirm=True."""
    details = {
        "library_id": library_id,
        "action": "add",
        "num_bibcodes": len(bibcodes),
        "bibcodes": bibcodes,
    }
    if not confirm:
        return _confirmation_required("add_bibcodes_to_ads_library", details)
    payload = {"bibcode": bibcodes, "action": "add"}
    return _json(_ads_request("POST", f"{ADS_LIB}/documents/{library_id}", payload=payload))


@mcp.tool()
def ads_library_remove_bibcodes(
    library_id: str,
    bibcodes: list[str],
    confirm: bool = False,
) -> str:
    """Remove bibcodes from an ADS library. This mutates ADS state and requires confirm=True."""
    details = {
        "library_id": library_id,
        "action": "remove",
        "num_bibcodes": len(bibcodes),
        "bibcodes": bibcodes,
    }
    if not confirm:
        return _confirmation_required("remove_bibcodes_from_ads_library", details)
    payload = {"bibcode": bibcodes, "action": "remove"}
    return _json(_ads_request("POST", f"{ADS_LIB}/documents/{library_id}", payload=payload))


@mcp.tool()
def ads_library_update_metadata(
    library_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    public: Optional[bool] = None,
    confirm: bool = False,
) -> str:
    """Update ADS library metadata. This mutates ADS state and requires confirm=True."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if public is not None:
        payload["public"] = public
    details = {"library_id": library_id, "updates": payload}
    if not payload:
        return _json({"error": "no_updates_requested", "library_id": library_id})
    if not confirm:
        return _confirmation_required("update_ads_library_metadata", details)
    return _json(_ads_request("PUT", f"{ADS_LIB}/documents/{library_id}", payload=payload))


@mcp.tool()
def ads_library_query(
    library_id: str,
    query: str,
    action: str = "add",
    rows: int = 100,
    confirm: bool = False,
) -> str:
    """Add or remove records from an ADS library using an ADS query.

    action must be "add" or "remove". This mutates ADS state and requires
    confirm=True.
    """
    if action not in {"add", "remove"}:
        return _json({"error": "invalid_action", "allowed_values": ["add", "remove"]})
    payload = {"params": {"q": query, "rows": rows}, "action": action}
    details = {
        "library_id": library_id,
        "query": query,
        "action": action,
        "rows": rows,
    }
    if not confirm:
        return _confirmation_required("ads_library_query_mutation", details)
    return _json(_ads_request("POST", f"{ADS_LIB}/query/{library_id}", payload=payload, timeout=60))


@mcp.tool()
def ads_library_set_operation(
    primary_library_id: str,
    action: str,
    libraries: Optional[list[str]] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    public: bool = False,
    confirm: bool = False,
) -> str:
    """Run an ADS library set operation.

    action must be one of: union, intersection, difference, copy, empty. This
    mutates ADS state and requires confirm=True.
    """
    allowed = {"union", "intersection", "difference", "copy", "empty"}
    if action not in allowed:
        return _json({"error": "invalid_action", "allowed_values": sorted(allowed)})
    libraries = libraries or []
    payload: dict[str, Any] = {"action": action, "libraries": libraries, "public": public}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    details = {
        "primary_library_id": primary_library_id,
        "action": action,
        "libraries": libraries,
        "name": name,
        "description": description,
        "public": public,
    }
    if not confirm:
        return _confirmation_required("ads_library_set_operation", details)
    return _json(_ads_request("POST", f"{ADS_LIB}/libraries/operations/{primary_library_id}", payload=payload, timeout=60))


@mcp.tool()
def ads_library_delete(library_id: str, confirm: bool = False) -> str:
    """Delete an ADS library. This is destructive and requires confirm=True."""
    details = {"library_id": library_id}
    if not confirm:
        return _confirmation_required("delete_ads_library", details)
    return _json(_ads_request("DELETE", f"{ADS_LIB}/documents/{library_id}"))


if __name__ == "__main__":
    mcp.run(transport="stdio")
