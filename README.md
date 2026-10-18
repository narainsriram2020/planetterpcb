# 🐢 TerpGuide — AI course advisor for UMD

TerpGuide is a chatbot for UMD students that answers questions about courses, professors, and grade distributions using real PlanetTerp data. A Gemini agent decides which tools to call on a **Model Context Protocol (MCP)** server, which serves live PlanetTerp data and semantic search over a Qdrant vector index.

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

The deployed server is public at `https://terpadvisor-api-9glv.onrender.com/mcp/` (streamable HTTP, no auth) — the landing page has copy-paste setup for Cursor, Claude Code, VS Code, and the Claude app.

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
| `SUPABASE_URL` / `SUPABASE_SECRET_KEY` | — | Accounts + saved chats; when set, chat requires Google sign-in |
| `REQUIRE_AUTH` | `true` if Supabase is set | `false` allows anonymous chat (local testing) |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | — | Frontend sign-in (Vercel / `frontend/.env.local`) |

Set these in `.env` in the project root (or in `backend/`).

---

## 🔌 API

`POST /chat`

```json
{ "prompt": "Who should I take for CMSC330?", "history": [{ "role": "user", "text": "..." }, { "role": "bot", "text": "..." }] }
```

Returns `{ "reply": "...", "tools_used": [{ "name": "get_grade_distribution", "arguments": {...}, "ok": true }], "cards": [...], "processing_time": "4.80s" }`. `cards` are display-ready summaries of the data the agent fetched (grade distributions, professors, courses, search results).

`POST /chat/stream` takes the same body and streams newline-delimited JSON events as the agent works — this is what the web UI uses:

```
{"type": "tool_start", "id": 0, "name": "get_grade_distribution", "arguments": {"course_id": "MATH141"}}
{"type": "tool_end", "id": 0, "name": "get_grade_distribution", "ok": true}
{"type": "card", "card": {"kind": "grades", "course_id": "MATH141", ...}}
{"type": "answer", "text": "..."}
{"type": "done", "processing_time": "6.90s"}
```

`GET /health` reports the model, vector store status, and registered MCP tools.

The frontend calls the API at `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`).

---

## ☁️ Deployment

Backend on [Render](https://render.com) (free web service), frontend on [Vercel](https://vercel.com), data in Qdrant Cloud.

1. **Backend (Render).** New → Blueprint → select this repo; it reads [`render.yaml`](render.yaml). Fill in `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and leave `FRONTEND_ORIGINS` for step 3. Check `https://<service>.onrender.com/health`.
2. **Frontend (Vercel).** Add New → Project → this repo, set **Root Directory** to `frontend`, and add `NEXT_PUBLIC_API_URL=https://<service>.onrender.com`.
3. **CORS.** Set `FRONTEND_ORIGINS` on Render to your Vercel URL (e.g. `https://terpguide.vercel.app`) and redeploy.
4. **Keep-alive.** Add a repository variable `BACKEND_URL` (Settings → Secrets and variables → Actions → Variables) so [`keepalive.yml`](.github/workflows/keepalive.yml) pings the API daily and keeps the free Qdrant cluster active.

Free-tier notes: Render sleeps after 15 minutes idle (the first request after that takes ~30–60s), chat is rate-limited per client (`CHAT_RATE_LIMIT`, default 15 per 10 minutes), opening questions are cached for 6 hours to save Gemini quota, and Gemini's free tier has its own daily caps.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Replies start with "TerpGuide's AI is temporarily unavailable" | Gemini quota or outage — check the server log for the error; try `gemini-flash-lite-latest` or enable billing |
| `/health` shows `vector_store_ready: false` | Build the index with `scripts/scrape_and_index.py`, or check your Qdrant Cloud cluster isn't suspended |
| Local Qdrant "already accessed by another instance" | The on-disk store allows one process at a time — stop the API before re-indexing |

---

**Made with ❤️ for UMD students** 🐢
