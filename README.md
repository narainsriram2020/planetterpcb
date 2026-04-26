# 🐢 PlanetTerp Navigator

An intelligent chatbot for UMD students powered by real PlanetTerp data and Google Gemini AI. Ask anything about courses, professors, grade distributions, and GenEds — and get concise, data-grounded answers.

---

## ✨ Features

- **🤖 AI-Powered Chat** — Conversational responses via Google Gemini, grounded in live PlanetTerp data
- **📚 Semantic Course Search** — Vector-based search finds the most relevant courses for any query
- **👨‍🏫 Professor Profiles** — Ratings, review highlights, and courses taught
- **📊 Grade Analytics** — Average GPA and recent grade distribution data
- **🧠 Multi-Turn Memory** — Gemini keeps context across the whole conversation
- **⚡ Fallback Formatter** — Structured data summary if Gemini is unavailable
- **🎨 Dark UI** — Minimal, responsive chat interface with animations

---

## 🏗️ Architecture

```
planetterpcb/
├── backend/
│   ├── app/
│   │   ├── main.py              # Entrypoint — re-exports main_fast.py
│   │   └── main_fast.py         # FastAPI app: /chat endpoint + Gemini orchestration
│   ├── planetterp_mcp/
│   │   ├── planetterp_server.py # MCP tool definitions (search, details, professor)
│   │   ├── vector_store.py      # FAISS-based semantic search index
│   │   ├── mcp_http_server.py   # HTTP sidecar exposing MCP tools at port 8001
│   │   ├── mcp_stub.py          # Lightweight MCPServer stub (no real MCP SDK needed)
│   │   └── planetterp_core.py   # Raw PlanetTerp API helpers
│   └── requirements.txt
├── frontend/
│   └── src/app/
│       ├── page.tsx             # Landing page
│       └── chat/page.tsx        # Chat interface
├── start.ps1                    # Startup script (runs both backend servers)
└── env.example                  # Environment variable template
```

### Request Flow

```
Browser → Next.js frontend → POST /chat (port 8000) → main_fast.py
  → MCP HTTP sidecar (port 8001)
      → semantic_course_search (FAISS vector search)
      → get_course_details (PlanetTerp API)
      → get_professor_profile (PlanetTerp API)
  → Gemini AI (with data + conversation history)
  → response with reply + course_details
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key ([get one here](https://aistudio.google.com/))

### 1. Environment Setup

Copy the example env file and add your API key:

```bash
cp env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

### 2. Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

> **Note:** `faiss-cpu` and `sentence-transformers` are required for semantic search. The first startup will download the embedding model (~80 MB).

### 3. Start the Backend

Run **both** the main API and the MCP sidecar together:

```powershell
# From the project root
.\start.ps1
```

Or start them manually in separate terminals:

```bash
# Terminal 1 — MCP sidecar (port 8001)
cd backend
uvicorn planetterp_mcp.mcp_http_server:app --host 127.0.0.1 --port 8001 --reload

# Terminal 2 — Main API (port 8000)
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash-lite` | Gemini model to use |
| `SENTENCE_TRANSFORMER_MODEL` | `all-MiniLM-L6-v2` | Embedding model for semantic search |

Set in a `.env` file in the **project root** (or in `backend/`).

---

## 💬 Example Queries

| Category | Examples |
|---|---|
| Course Info | "Tell me about CMSC131" · "What's MATH140 like?" |
| Professor Help | "Who should I take for CMSC330?" · "Tell me about Nelson Padua-Perez" |
| Grade Data | "What's the average GPA for CMSC216?" · "Is ECON200 grade-friendly?" |
| GenEds | "Show me easy DSHS GenEds" · "Best science GenEd?" |
| Recommendations | "What are the most popular CS courses at UMD?" |

---

## 🛠️ Development Notes

- **Semantic search** uses FAISS with `all-MiniLM-L6-v2` embeddings. The index is built from the full PlanetTerp course catalog on first startup and cached in memory for 1 hour.
- **Gemini fallback** — if Gemini is rate-limited or unavailable, the app returns a structured plain-text summary from PlanetTerp data directly.
- **Conversation history** — the frontend sends the full message history with each request. The backend includes the last 10 messages in the Gemini prompt.
- **MCP sidecar** must be running on port 8001 before the main API can serve chat requests. Use `start.ps1` to ensure both start together.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Chat returns no PlanetTerp data | Make sure the MCP sidecar is running on port 8001 |
| `GEMINI_API_KEY not set` error | Add your key to `.env` in the project root |
| Slow first response | Normal — the embedding model loads on first startup |
| Port 8000/8001 already in use | Kill existing processes or change ports in `start.ps1` |

---

**Made with ❤️ for UMD students** 🐢