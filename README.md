# Sheep Bot

> An AI-powered document assistant — upload your files, ask questions in plain English, and get cited, theme-grouped answers in seconds.

Sheep Bot extracts text from PDFs and images via OCR, indexes them with semantic embeddings, and uses Google Gemini to synthesize multi-document answers organized by theme — each one traceable back to the exact paragraph it came from.

---

## What It Does

1. **Upload** a PDF or image — text is extracted automatically via Tesseract OCR.
2. **Ask a question** in the chat interface.
3. **Get a themed answer** — related chunks are clustered, summarized by Gemini, and returned with paragraph-level citations.

---

## Demo Media

| Type | Link |
|------|------|
| Full folder | [Google Drive](https://drive.google.com/drive/folders/1wmRE1AhAQsZBopTXXE_s2dp81Hb5SBil?usp=share_link) |
| Demo videos | [Google Drive](https://drive.google.com/drive/folders/1CFnADz2myb82HCp8jaEbTVe7i5I4aX61?usp=share_link) |
| Demo screenshots | [Google Drive](https://drive.google.com/drive/folders/1VDaE7lynVCuuHKyXLB3pPKdwxJmS9qq9?usp=share_link) |

---

## Features

| Feature | Detail |
|---------|--------|
| Document Upload | PDFs and images (PNG/JPG); OCR via Tesseract |
| Conversational Q&A | Natural-language questions answered from your documents only |
| Semantic Search | `all-MiniLM-L6-v2` embeddings matched in ChromaDB |
| Theme Identification | KMeans clusters chunks into up to 5 themes per query |
| Paragraph Citations | Every answer cites exact document and paragraph |
| Sentiment Analysis | VADER sentiment scored on upload |
| Document Management | View, download, delete from the sidebar |
| Light / Dark Mode | OS-aware, persisted via `localStorage` |
| Upload Progress | Real-time progress bar during upload |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Axios |
| Backend | FastAPI, Uvicorn |
| OCR | Tesseract (`pytesseract`), `pdf2image`, Pillow |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| Vector store | ChromaDB |
| Clustering | scikit-learn KMeans |
| LLM | Google Gemini 1.5 Flash |
| Sentiment | NLTK VADER |
| Database | SQLite via SQLAlchemy |
| Containerisation | Docker |

---

## Architecture

### Project layout

```
frontend/            React 19 SPA (Create React App)
backend/
  app/
    main.py          FastAPI app — all routes and business logic
    models/
      document.py    SQLAlchemy ORM model
    core/
      database.py    Engine + session factory (SQLite)
  requirements.txt
  Dockerfile
  init_db.py         One-time DB init script
data/
  uploaded_files/    Persisted uploaded documents
Procfile             Process definition (Heroku / Railway)
```

### Request flow

```
User question
    │
    ▼
React frontend  ──POST /query/──►  FastAPI
                                       │
                                  Encode question
                                  (SentenceTransformer)
                                       │
                                  ChromaDB semantic search
                                  (top-50 paragraph chunks)
                                       │
                                  KMeans clustering
                                  (up to 5 themes)
                                       │
                                  Gemini 1.5 Flash
                                  (theme summaries + citations)
                                       │
    React renders chat bubble  ◄───────┘
```

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Tesseract OCR — `brew install tesseract` / `apt install tesseract-ocr`
- Poppler (PDF rendering) — `brew install poppler` / `apt install poppler-utils`
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

echo "GOOGLE_API_KEY=your_key_here" > .env

uvicorn app.main:app --reload --port 8000
```

API available at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm start
```

App opens at `http://localhost:3000`.

> To point the frontend at your local backend, update `API_BASE` in `frontend/src/App.js`:
> ```js
> const API_BASE = "http://localhost:8000";
> ```

### Docker (backend only)

```bash
cd backend
docker build -t sheep-bot-backend .
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key_here sheep-bot-backend
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Health check |
| `POST` | `/upload/` | Upload one or more files |
| `GET` | `/documents/` | List all documents |
| `GET` | `/documents/{id}` | Get document details and extracted text |
| `DELETE` | `/documents/{id}` | Delete a document |
| `GET` | `/documents/{id}/download` | Download the original file |
| `POST` | `/query/` | Query documents with a natural-language question |

### POST `/upload/`

Multipart form, field name `files` (multiple files supported).

```json
{
  "results": [
    {
      "filename": "report.pdf",
      "message": "File uploaded and text extracted successfully!",
      "document_id": 1,
      "sentiment": { "neg": 0.05, "neu": 0.82, "pos": 0.13, "compound": 0.42 }
    }
  ]
}
```

### POST `/query/`

Request:
```json
{
  "question": "What are the key findings?",
  "selected_doc_ids": [1, 2]
}
```

`selected_doc_ids` is optional — omit it to search across all documents.

Response:
```json
{
  "answer": "Identified Themes:\n\nTheme 1: ...",
  "themes": [
    {
      "theme_summary": "...",
      "supporting_chunks": [{ "doc_id": 1, "chunk_index": 3 }],
      "num_chunks": 12
    }
  ],
  "chunks": [...]
}
```

---

## Notes

- `data/uploaded_files/` and `chroma_db/` are auto-created and not committed to git.
- The sentence transformer model and ChromaDB client are lazily initialised to keep startup fast.
- `allow_origins=["*"]` is fine for development — restrict to your frontend domain in production.
- ChromaDB is file-backed and single-process; swap it for a hosted vector DB at production scale.

---

## Developer Notes

Building Sheep Bot involved stitching together OCR, semantic search, vector storage, clustering, and LLM generation into one coherent pipeline — each layer with its own learning curve. Deployment was the hardest part: most suggested platforms had memory limits incompatible with model loading. With outside help, the project was hosted on a custom domain and confirmed stable. The experience sharpened practical skills across API design, asynchronous Python, and cloud deployment.

---

## Contact

- **Developer:** Rohit Yadav
- **Email:** rohityadav.0620@gmail.com
- **GitHub:** [@rohit-yadav5](https://github.com/rohit-yadav5)
- **Portfolio:** [rohit-yadav5.github.io](https://rohit-yadav5.github.io)
