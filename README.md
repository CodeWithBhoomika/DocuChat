# DocuChat – RAG Document Assistant

Upload PDFs and ask questions. Answers come only from your documents and cite the **file and page** they were taken from.

**Live demo:** [add your Vercel link] · **API:** [add your Render link]

## How it works (RAG pipeline)
1. **Upload** – PDF text is extracted page by page (`pypdf`).
2. **Chunk** – each page is split into ~800-character overlapping chunks that keep file name + page number.
3. **Embed + store** – chunks are converted to vectors (all-MiniLM-L6-v2, ONNX) and stored in **ChromaDB**, one collection per browser session.
4. **Retrieve** – the question is embedded and the closest chunks are found with cosine similarity; weak matches are dropped.
5. **Generate** – the top chunks are sent to the **Groq API** with a prompt that only allows answers from those passages and asks for `[1]`, `[2]` citations.

## Tech stack
Python · FastAPI · ChromaDB · Groq API · React (Vite) · Docker · pytest · GitHub Actions

## Security
- The Groq key exists only as a server environment variable; the browser only talks to this backend.
- CORS limited to the frontend URL, per-IP rate limit, 10 MB / 5-file / 200-page upload limits.
- Uploads are checked by file content (`%PDF`), not just the extension; file names are sanitised.
- Sessions are isolated; documents can be deleted from the UI.
- The prompt treats document text as untrusted (basic prompt-injection defence).
- `/docs` is disabled when `ENV=production`.

## Run locally
```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then put your Groq key in .env
uvicorn app.main:app --reload
# tests
pytest -q

# frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev                 # http://localhost:5173
```
Load `.env` for the backend with `export $(cat .env | xargs)` (or set the variables in your shell) before `uvicorn`.

## Deploy (free tiers)
**Backend → Render:** New Web Service → connect this repo → Root Directory `backend` → Runtime *Docker*. Environment variables: `GROQ_API_KEY`, `ALLOWED_ORIGINS` (your Vercel URL), `ENV=production`.
**Frontend → Vercel:** Import repo → Root Directory `frontend` → Environment variable `VITE_API_URL` = your Render URL.
Then update `ALLOWED_ORIGINS` on Render with the final Vercel URL. Free Render services sleep when idle (first request can take about a minute) and storage resets on redeploy.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/upload` | upload PDFs (`session_id`, `files`) |
| POST | `/api/ask` | `{session_id, question}` → answer + sources |
| GET | `/api/documents` | list documents in a session |
| DELETE | `/api/session/{id}` | delete a session's documents |
| GET | `/health` | health check |
