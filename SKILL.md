---
name: ads-bib
description: >
  Use this skill for ANY request involving astronomical references, citations,
  BibTeX entries, or \cite{} keys — even if the paper seems well-known enough
  to recall from memory. Triggers include: "find the bib entry for...", "get me
  a reference to...", "add citations for...", "draft this with proper ADS references",
  "look up the paper by X about Y", or any request to include \cite{} keys in LaTeX.
  Also trigger when drafting or editing a scientific manuscript and references are
  needed — even if the user does not explicitly say "ADS" or "BibTeX". NEVER
  fabricate bibcodes or BibTeX fields, even for famous papers. NEVER use
  web search, memory, or any other source for bibliography data — ads_search
  and ads_bibtex are the ONLY permitted methods for all bibliography tasks,
  including LaTeX documents, papers, and proposals.
---

# ADS BibTeX Skill

Retrieve verified BibTeX entries from NASA ADS. **Never invent bibcodes or
BibTeX fields.** Every entry must come from a live ADS API response.

This skill uses the `ads` MCP server, which exposes two tools: `ads_search`
and `ads_bibtex`. These run locally on the user's machine and have full network
access to the ADS API.

---

## Workflow

### Step 1 — Build the ADS query

Translate the user's intent into ADS query syntax. Key field operators:

| Goal | Query syntax |
|---|---|
| Author | `author:"Last, F"` |
| First author only | `author:"^Last, F"` |
| Title keyword | `title:"keyword"` |
| Year range | `year:2020-2024` |
| Journal | `bibstem:ApJ` or `bibstem:MNRAS` |
| Object | `object:"Beta Pic b"` |
| Free-text abstract | `abs:"phase curve brown dwarf"` |
| Bibcode exact | `bibcode:2023ApJ...945L...5Z` |
| Restrict to astronomy | `database:astronomy` |
| Refereed only | `property:refereed` |

Combine operators with `AND`, `OR`. Default sort is `date desc`.

Common bibstems: `ApJ`, `ApJL`, `ApJS`, `AJ`, `MNRAS`, `A&A`, `Icar`, `NatAs`, `Sci`, `Natur`, `arXiv`.

### Step 2 — Search ADS

Call the `ads_search` tool:

```
ads_search(query="author:\"^Last, First\" keyword", max_results=20)
```

Returns a JSON list with fields: `bibcode`, `author`, `year`, `title`, `journal`.

Display results as a compact numbered list:
```
1. Last et al. (YEAR) – Title [journal]
2. ...
```

**Do not guess** which result is correct. For autonomous tasks, apply these
heuristics in order:
- Exact title match
- First-author + year match
- Highest relevance in the first 5 results

If ambiguous, list the top candidates and ask the user to select.

**Filtering tip**: Common author names return many false positives. Add
`database:astronomy property:refereed` and restrict to major bibstems
(`ApJ OR AJ OR MNRAS OR A&A OR NatAs`) to clean up results. Cross-check
that the full first name matches, not just initials.

### Step 3 — Fetch BibTeX

Call the `ads_bibtex` tool with the confirmed bibcodes:

```
ads_bibtex(bibcodes=["2023ApJ...945L...5Z", "2021AJ....161..244Z"])
```

The tool returns BibTeX entries with cite keys already formatted as `LastYYYY`
(e.g. `Zhou2021`), with `a/b/c` suffixes when multiple entries share the same
first author and year (e.g. `Zhou2022a`, `Zhou2022b`).

### Step 4 — Deliver results

**Output the BibTeX entries exactly as returned by `ads_bibtex`, with no
modifications whatsoever — no field additions, no field deletions, no
reformatting, no condensing.** The only change already applied by the tool
is the cite key on the first line (e.g. `@ARTICLE{Zhou2021,`). Every other
field — `author`, `title`, `journal`, `keywords`, `eprint`, `adsurl`,
`adsnote`, etc. — must be reproduced verbatim.

If the user is working in LaTeX, also show the cite keys so they can use
`\cite{key}` directly.

---

## Multi-paper requests (drafting manuscripts)

When the user asks to draft a paragraph or section with citations:

1. Identify all claims that need a reference.
2. For each claim, call `ads_search` with an appropriate query.
3. Draft the text using `\cite{key}` placeholders.
4. Append the full BibTeX block at the end, verbatim from `ads_bibtex`.

Do this iteratively — one search per claim if needed — rather than fabricating
entries to fill gaps.

---

## Error handling

| Situation | Action |
|---|---|
| `ads` tools not available | The ADS MCP server is not running. See setup instructions in the repo README. |
| Zero results | Broaden query: remove year filter, use `abs:` instead of `title:` |
| HTTP 429 (rate limit) | Wait ~2s and retry once |
| HTTP 401 | API key is invalid — user should update it in `ads_mcp_server.py` |
| Ambiguous results | Show top 5 and ask user to pick |

---

## ADS query tips

- Author names: ADS stores as "Last, First". Use `"Last, F"` for initials.
- For Chinese names, try both pinyin romanizations if the first fails.
- `arXiv` preprints are indexed; use `bibstem:arXiv` to restrict to them.
- To find a paper from a vague description, use `abs:` with 3–4 distinctive
  keywords rather than guessing the title.
- Year filter helps when an author has many papers: `author:"Zhou, Y" year:2020-2025`.
