# 🐢 TerpAdvisor — AI course advisor for UMD

TerpAdvisor is a chatbot for UMD students that answers questions about courses, professors, and grade distributions using real PlanetTerp data. A Gemini agent decides which tools to call on a **Model Context Protocol (MCP)** server, which serves live PlanetTerp data and semantic search over a Qdrant vector index.

---

## ✨ Features

- **Tool-using agent** — Gemini picks which MCP tools to call (and in what order) to answer each question, then writes a grounded reply
- **Real MCP server** — built on the official MCP Python SDK; usable by any MCP client (Claude Desktop, Cursor, MCP Inspector) over stdio or streamable HTTP
- **Semantic search** — course and professor embeddings (`all-MiniLM-L6-v2` via fastembed) in Qdrant, enriched with GPAs, professor ratings, and review snippets
- **Grade analytics** — per-professor GPA breakdowns over recent semesters for "who should I take?" questions
- **Multi-turn memory** — follow-ups like "what about him specifically?" use the conversation history
- **Graceful degradation** — falls back to plain search results if Gemini is unavailable, and to PlanetTerp's name search if the vector index is

---

## 🏗️ Architecture

```
Browser (Next.js) ──POST /chat──► FastAPI (app/main.py)
                                     │
                                     ▼
                               Gemini agent (app/agent.py)
                                 │  MCP client: list_tools / call_tool
                                 ▼
                     PlanetTerp MCP server (planetterp_mcp/server.py)
                       ├─ search_courses ─────────┐
                       ├─ search_professors ──────┴─► Qdrant (semantic index)
                       ├─ get_course ─────────────┐
                       ├─ get_grade_distribution ─┼─► PlanetTerp API (cached)
                       └─ get_professor ──────────┘

External MCP clients ──streamable HTTP──► /mcp/   (same server)
```

The agent talks to the MCP server over an in-memory transport by default, or over streamable HTTP when `MCP_SERVER_URL` is set. Each turn, Gemini gets the tool schemas from `list_tools`, issues function calls (in parallel when independent), and gets the results back until it can answer (max 6 rounds).

```
backend/
├── app/
│   ├── main.py              # FastAPI: /chat, /health, mounts MCP at /mcp
│   └── agent.py             # Gemini tool-calling loop over an MCP ClientSession
├── planetterp_mcp/
│   ├── server.py            # FastMCP server + the 5 tools
│   ├── planetterp_api.py    # Async PlanetTerp client with TTL cache
│   ├── vector_store.py      # Qdrant (cloud or local) + fastembed search
│   └── config.py            # Env settings
└── scripts/
    ├── scrape_and_index.py  # Build the Qdrant index from PlanetTerp
    └── check_qdrant.py      # Inspect the index
frontend/                    # Next.js chat UI
```

---

## 🚀 Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+, a [Gemini API key](https://aistudio.google.com/).

```bash
# 1. Configure
cp env.example .env          # set GEMINI_API_KEY (and Qdrant Cloud creds if you have them)

# 2. Install
cd backend
pip install -r requirements.txt

# 3. Build the search index (no Qdrant creds -> local store in backend/.qdrant)
py scripts/scrape_and_index.py --departments CMSC,MATH,ASTR   # quick
py scripts/scrape_and_index.py                                # full catalog

# 4. Run the API (also serves MCP at /mcp/)
py -m uvicorn app.main:app --port 8000 --reload   # or .\start.ps1 from the repo root

# 5. Run the frontend
cd ../frontend && npm install && npm run dev      # http://localhost:3000
```

### Use the MCP server from Claude Desktop

```json
{
  "mcpServers": {
    "planetterp": {
      "command": "py",
      "args": ["-m", "planetterp_mcp.server"],
      "env": { "PYTHONPATH": "C:/path/to/planetterpcb/backend" }
    }
  }
}
```

Or run it standalone over HTTP: `py -m planetterp_mcp.server --http` (serves `http://127.0.0.1:8001/mcp`).

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Gemini API key |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` | Gemini model. Free-tier `gemini-flash-latest` is limited to 20 requests/day |
| `GEMINI_THINKING_LEVEL` | `low` | Thinking level; empty for models without one |
| `QDRANT_URL` / `QDRANT_API_KEY` | — | Qdrant Cloud; if unset, uses the local store |
| `QDRANT_MODE` | `auto` | `local` forces the on-disk store |
| `QDRANT_PATH` | `backend/.qdrant` | Local store location |
| `MCP_SERVER_URL` | — | Use a remote MCP server instead of the in-process one |
| `MCP_ALLOWED_HOSTS` | localhost | Hostnames allowed to call `/mcp` when deployed (`*` disables the check) |
| `FRONTEND_ORIGINS` | `*` | CORS origins for the chat API |

Set these in `.env` in the project root (or in `backend/`).

---

## 🔌 API

`POST /chat`

```json
{ "prompt": "Who should I take for CMSC330?", "history": [{ "role": "user", "text": "..." }, { "role": "bot", "text": "..." }] }
```

Returns `{ "reply": "...", "tools_used": [{ "name": "get_grade_distribution", "arguments": {...}, "ok": true }], "processing_time": "4.80s" }`.

`GET /health` reports the model, vector store status, and registered MCP tools.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Replies start with "TerpAdvisor's AI is temporarily unavailable" | Gemini quota or outage — check the server log for the error; try `gemini-flash-lite-latest` or enable billing |
| `/health` shows `vector_store_ready: false` | Build the index with `scripts/scrape_and_index.py`, or check your Qdrant Cloud cluster isn't suspended |
| Local Qdrant "already accessed by another instance" | The on-disk store allows one process at a time — stop the API before re-indexing |

---

**Made with ❤️ for UMD students** 🐢
