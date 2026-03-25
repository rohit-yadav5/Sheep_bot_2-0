# Sheep Bot

Sheep Bot is a sheep-themed AI document assistant that lets you upload PDFs and images, then ask natural-language questions about them. It uses semantic search, KMeans clustering, and Google Gemini to return themed, paragraph-cited answers in a conversational chat interface.

---

## Live Demo

> The hosted service is currently down due to server issues.

- **Web App:** [wasserstoff-aiinterntask.vercel.app](https://wasserstoff-aiinterntask.vercel.app/)
- **API Docs (Swagger):** [mahindra-bot.biup.ai/docs](https://mahindra-bot.biup.ai/docs#/)

---

## Demo Media

| Type | Link |
|------|------|
| Full folder | [Google Drive](https://drive.google.com/drive/folders/1wmRE1AhAQsZBopTXXE_s2dp81Hb5SBil?usp=share_link) |
| Demo videos | [Google Drive](https://drive.google.com/drive/folders/1CFnADz2myb82HCp8jaEbTVe7i5I4aX61?usp=share_link) |
| Demo screenshots | [Google Drive](https://drive.google.com/drive/folders/1VDaE7lynVCuuHKyXLB3pPKdwxJmS9qq9?usp=share_link) |

---

## Features

- **Document Upload** — Upload PDFs and images (PNG/JPG) via the sidebar. Text is extracted automatically via OCR (Tesseract).
- **Conversational Q&A** — Ask questions in plain English; Sheep Bot answers using only the content of your documents.
- **Semantic Search** — Queries are matched to document chunks using `all-MiniLM-L6-v2` embeddings stored in ChromaDB.
- **Theme Identification** — KMeans clustering groups related chunks into distinct themes, each answered separately by Gemini.
- **Paragraph Citations** — Every theme answer references specific documents and paragraph numbers so answers are traceable.
- **Sentiment Analysis** — Each uploaded document is scored with VADER sentiment on ingestion.
- **Document Management** — View, download, and delete uploaded documents from the sidebar.
- **Light / Dark Mode** — Persisted across sessions via `localStorage`, with automatic OS preference detection.
- **Upload Progress Bar** — Real-time upload progress feedback.

---

## Architecture

```
frontend/          React 19 single-page app (Create React App)
backend/
  app/
    main.py        FastAPI application — all routes and business logic
    models/
      document.py  SQLAlchemy ORM model (Document table)
    core/
      database.py  SQLAlchemy engine + session factory (SQLite)
  requirements.txt Python dependencies
  Dockerfile       Container definition
  init_db.py       One-time DB initialisation script
data/
  uploaded_files/  Persisted uploaded documents
Procfile           Heroku/Railway process definition
```

### Request flow

```
User question
    │
    ▼
React frontend  ──POST /query/──►  FastAPI backend
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
                                   Return themes + chunks
                                        │
    React renders chat bubble  ◄────────┘
```

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
| LLM | Google Gemini 1.5 Flash (`google-generativeai`) |
| Sentiment | NLTK VADER |
| Database | SQLite via SQLAlchemy |
| Containerisation | Docker |

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Tesseract OCR installed on your system (`brew install tesseract` / `apt install tesseract-ocr`)
- Poppler for PDF conversion (`brew install poppler` / `apt install poppler-utils`)
- A Google Gemini API key

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
echo "GOOGLE_API_KEY=your_key_here" > .env

# Run
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm start
```

The app will open at `http://localhost:3000`.

> By default, the frontend points to the hosted backend (`https://mahindra-bot.biup.ai`).
> To use your local backend, change `API_BASE` in `frontend/src/App.js`:
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
| `POST` | `/upload/` | Upload one or more files (PDF/PNG/JPG) |
| `GET` | `/documents/` | List all documents |
| `GET` | `/documents/{id}` | Get document details + extracted text |
| `DELETE` | `/documents/{id}` | Delete a document |
| `GET` | `/documents/{id}/download` | Download the original file |
| `POST` | `/query/` | Query documents with a natural-language question |

### POST `/upload/`

Multipart form — field name: `files` (supports multiple files).

**Response:**
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

```json
{
  "question": "What are the key findings?",
  "selected_doc_ids": [1, 2]   // optional — omit to search all documents
}
```

**Response:**
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

## Project Structure Notes

- `data/uploaded_files/` — uploaded files are stored here; not committed to git.
- `chroma_db/` — ChromaDB persistence directory; auto-created on first upload.
- `data/documents.db` — SQLite database; auto-created on startup.
- The backend uses lazy initialisation for the sentence transformer model and ChromaDB client to keep startup time low.

---

## Known Limitations

- Hosted service is currently offline due to infrastructure constraints.
- OCR quality depends on Tesseract and document scan quality; complex layouts may reduce accuracy.
- `allow_origins=["*"]` in CORS is suitable for development only — restrict to your frontend domain in production.
- ChromaDB is in-process and file-backed; replace with a hosted vector DB for production scale.

---

## Developer Notes

Building Sheep Bot was a challenging and rewarding full-stack project. Integrating NLP, vector search, LLM generation, and OCR into a single coherent pipeline involved significant learning across each layer. The biggest hurdle was deployment — many suggested platforms had resource limits incompatible with model loading. With external help, the project was hosted on a custom domain and confirmed stable. This project reinforced a lot of practical knowledge around API design, asynchronous Python, and cloud deployment.

---

## Contact

- **Developer:** Rohit Yadav
- **Email:** rohityadav.0620@gmail.com
- **GitHub:** [@rohit-yadav5](https://github.com/rohit-yadav5)
- **Portfolio:** [rohit-yadav5.github.io](https://rohit-yadav5.github.io)
