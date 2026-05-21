# ads-bib

A Claude Desktop skill + local MCP server that retrieves verified BibTeX entries directly from NASA ADS. Claude will never fabricate bibcodes or citation keys — every entry comes from a live ADS API call.

**Features**
- Search NASA ADS with full query syntax (`author:`, `title:`, `abs:`, `year:`, `bibstem:`, etc.)
- Cite keys formatted as `LastYYYY` (e.g. `Zhou2021`), with `a/b/c` suffixes for same-author-year collisions (e.g. `Zhou2022a`, `Zhou2022b`)
- BibTeX output is verbatim from ADS — no fields added, removed, or reformatted
- Works seamlessly while drafting LaTeX papers and proposals in Claude Desktop

---

## What you need

- [Claude Desktop](https://claude.ai/download) (free or Pro)
- Python 3.10+ with `pip`
- A NASA ADS API token (free)

---

## Step 1 — Get a NASA ADS API token

1. Go to https://ui.adsabs.harvard.edu and sign in (or create a free account).
2. Navigate to **Settings → API Token**.
3. Copy the token — you'll need it in Step 4.

---

## Step 2 — Install Python dependencies

Open a terminal and run:

```bash
pip install mcp requests
```

If you use Conda, activate your environment first:

```bash
conda activate your_env
pip install mcp requests
```

---

## Step 3 — Download the MCP server script

Download `ads_mcp_server.py` from this repo and save it somewhere permanent, for example:

```
~/Documents/ads_mcp_server.py
```

Or clone the whole repo:

```bash
git clone https://github.com/YifZhou/ads-bib.git ~/Documents/ads-bib
```

---

## Step 4 — Add your API token

Open `ads_mcp_server.py` in a text editor and replace the placeholder on this line:

```python
API_KEY  = "YOUR_ADS_API_TOKEN_HERE"
```

with your actual token from Step 1.

---

## Step 5 — Register the MCP server with Claude Desktop

Open the Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following entry inside the `"mcpServers"` block. Use the **full path** to your Python interpreter and the script:

```json
{
  "mcpServers": {
    "ads": {
      "command": "/full/path/to/python",
      "args": ["/full/path/to/ads_mcp_server.py"]
    }
  }
}
```

**Finding your Python path:**

```bash
# Standard Python
which python3

# Conda environment
conda activate your_env && which python
```

**Example** (macOS with Anaconda):

```json
{
  "mcpServers": {
    "ads": {
      "command": "/Users/yourname/opt/anaconda3/bin/python",
      "args": ["/Users/yourname/Documents/ads_mcp_server.py"]
    }
  }
}
```

If you already have other MCP servers configured, add `"ads"` alongside them — don't replace the existing entries.

---

## Step 6 — Install the Claude skill

1. Download `ads-bib.skill` from this repo.
2. Open Claude Desktop → **Settings → Skills**.
3. Drag and drop `ads-bib.skill` into the Skills panel, or click the install button.

---

## Step 7 — Restart Claude Desktop

Quit and relaunch Claude Desktop. The `ads` MCP server should now appear as connected.

---

## Usage

Once installed, ask Claude naturally — no special syntax needed:

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

Claude will call `ads_search` to find matching papers and `ads_bibtex` to retrieve the entries, then output a ready-to-use BibTeX block with `LastYYYY` cite keys.

---

## File overview

| File | Purpose |
|---|---|
| `SKILL.md` | Instructions that tell Claude how to use the ADS tools |
| `ads_mcp_server.py` | Local Python MCP server — wraps the ADS search and BibTeX export API |
| `ads-bib.skill` | Packaged skill file for Claude Desktop (contains `SKILL.md`) |

---

## Troubleshooting

**The `ads` tools don't appear in Claude Desktop**
- Check that the `"ads"` entry is inside `"mcpServers"` (not outside the block).
- Verify the Python path is correct: run `which python` in your terminal.
- Make sure `mcp` and `requests` are installed in the Python environment you pointed to.
- Restart Claude Desktop after any config change.

**HTTP 401 error**
- Your API token is invalid or expired. Get a new one from https://ui.adsabs.harvard.edu/user/settings/token and update `ads_mcp_server.py`.

**HTTP 429 error**
- ADS rate limit hit. Wait a few seconds and retry. The free tier allows 5,000 requests/day.

**Zero results**
- Broaden the query: remove the year filter, or switch from `title:` to `abs:` with 3–4 distinctive keywords.
