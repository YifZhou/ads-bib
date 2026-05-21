# ads-bib

A local MCP server that retrieves verified BibTeX entries directly from NASA ADS, with a skill for Claude Desktop. Works with **Claude Desktop** and **Gemini CLI**. Every entry comes from a live ADS API call — no fabricated bibcodes or citation keys.

**Features**
- Search NASA ADS with full query syntax (`author:`, `title:`, `abs:`, `year:`, `bibstem:`, etc.)
- Cite keys formatted as `LastYYYY` (e.g. `Zhou2021`), with `a/b/c` suffixes for same-author-year collisions (e.g. `Zhou2022a`, `Zhou2022b`)
- BibTeX output is verbatim from ADS — no fields added, removed, or reformatted

---

## What you need

- [Claude Desktop](https://claude.ai/download) **or** [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- Python 3.10+ (Conda recommended)
- A NASA ADS API token (free)

---

## Step 1 — Get a NASA ADS API token

1. Go to https://ui.adsabs.harvard.edu and sign in (or create a free account).
2. Navigate to **Settings → API Token**.
3. Copy the token — you'll need it in Step 4.

---

## Step 2 — Create a Conda environment

We recommend a dedicated environment to keep dependencies isolated:

```bash
conda create -n ads-bib python=3.11
conda activate ads-bib
pip install mcp requests
```

Note the full path to this environment's Python — you'll need it in Step 5:

```bash
conda activate ads-bib
which python   # e.g. /Users/yourname/opt/anaconda3/envs/ads-bib/bin/python
```

---

## Step 3 — Download the MCP server script

Clone this repo or download `ads_mcp_server.py` directly:

```bash
git clone https://github.com/YifZhou/ads-bib.git ~/Documents/ads-bib
```

---

## Step 4 — Add your API token

Open `ads_mcp_server.py` and replace the placeholder:

```python
API_KEY  = "YOUR_ADS_API_TOKEN_HERE"
```

with your actual token from Step 1.

---

## Step 5 — Register the MCP server

### Claude Desktop

Open the config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the `"ads"` entry inside `"mcpServers"`:

```json
{
  "mcpServers": {
    "ads": {
      "command": "/Users/yourname/opt/anaconda3/envs/ads-bib/bin/python",
      "args": ["/Users/yourname/Documents/ads-bib/ads_mcp_server.py"]
    }
  }
}
```

Use the full Python path from Step 2. If you already have other MCP servers configured, add `"ads"` alongside them.

### Gemini CLI

Gemini CLI supports local stdio MCP servers natively. Add the server to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "ads": {
      "command": "/Users/yourname/opt/anaconda3/envs/ads-bib/bin/python",
      "args": ["/Users/yourname/Documents/ads-bib/ads_mcp_server.py"]
    }
  }
}
```

Alternatively, if you have FastMCP installed (v2.12.3+), you can install it directly:

```bash
conda activate ads-bib
fastmcp install gemini-cli ads_mcp_server.py
```

### ChatGPT

ChatGPT currently only supports **remote** HTTPS MCP endpoints, not local stdio servers. Connecting `ads_mcp_server.py` to ChatGPT requires exposing it as a remote endpoint (e.g. via `mcp-remote` or a hosted server), which is significantly more complex. This is not recommended for most users.

---

## Step 6 — Install the Claude skill (Claude Desktop only)

1. Download `ads-bib.skill` from this repo.
2. Open Claude Desktop → **Settings → Skills**.
3. Drag and drop `ads-bib.skill` into the Skills panel.

> Gemini CLI users: the skill file is not needed. The MCP server registration in Step 5 is sufficient — Gemini will discover the `ads_search` and `ads_bibtex` tools automatically.

---

## Step 7 — Restart your AI assistant

Quit and relaunch Claude Desktop or Gemini CLI. The `ads` MCP server should now be connected.

---

## Usage

Ask naturally — no special syntax needed:

```
Find the bib entry for the Morley 2012 cloud paper
```
```
Add citations for direct imaging of PDS 70 b
```
```
Find all my first-author papers and output the bib entries
```
```
Draft an introduction about brown dwarf variability with proper citations
```

The assistant will call `ads_search` to find matching papers and `ads_bibtex` to retrieve the entries, then output a ready-to-use BibTeX block with `LastYYYY` cite keys.

---

## File overview

| File | Purpose |
|---|---|
| `SKILL.md` | Instructions that tell Claude how to use the ADS tools |
| `ads_mcp_server.py` | Local Python MCP server — wraps the ADS search and BibTeX export API |
| `ads-bib.skill` | Packaged skill file for Claude Desktop (contains `SKILL.md`) |

---

## Troubleshooting

**The `ads` tools don't appear**
- Check that the `"ads"` entry is correctly nested inside `"mcpServers"`.
- Verify the Python path points to the `ads-bib` conda environment: `conda activate ads-bib && which python`.
- Confirm `mcp` and `requests` are installed in that environment: `pip list | grep -E "mcp|requests"`.
- Restart the AI assistant after any config change.

**HTTP 401 error**
- Your API token is invalid or expired. Get a new one from https://ui.adsabs.harvard.edu/user/settings/token and update `ads_mcp_server.py`.

**HTTP 429 error**
- ADS rate limit hit. Wait a few seconds and retry. The free tier allows 5,000 requests/day.

**Zero results**
- Broaden the query: remove the year filter, or switch from `title:` to `abs:` with 3–4 distinctive keywords.
