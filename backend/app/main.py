import os
import re
import ast
import datetime
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from sklearn.cluster import KMeans
from collections import defaultdict
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

from app.models.document import Document, Base
from app.core.database import SessionLocal, engine


# ---------------------------------------------------------------------------
# Environment & DB setup
# ---------------------------------------------------------------------------
load_dotenv()

Base.metadata.create_all(bind=engine)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------
_embedder = None
_chroma_client = None
_collection = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_collection():
    global _chroma_client, _collection
    if _chroma_client is None or _collection is None:
        _chroma_client = chromadb.Client(Settings(persist_directory="./chroma_db"))
        _collection = _chroma_client.get_or_create_collection("documents")
    return _collection


_sia = None


def get_sentiment_analyzer() -> SentimentIntensityAnalyzer:
    global _sia
    if _sia is None:
        nltk.download('vader_lexicon', quiet=True)
        _sia = SentimentIntensityAnalyzer()
    return _sia


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.normpath(os.path.join(BASE_DIR, '../../data/uploaded_files'))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def paragraph_chunk(text: str) -> list:
    return [p.strip() for p in text.split('\n\n') if p.strip()]


def add_document_to_vector_db(doc_id: int, text: str):
    paras = paragraph_chunk(text)
    embeddings = get_embedder().encode(paras)
    ids = [f"{doc_id}_para_{i}" for i in range(len(paras))]
    metadatas = [
        {"doc_id": doc_id, "chunk_index": i, "chunk_type": "paragraph"}
        for i in range(len(paras))
    ]
    get_collection().add(
        documents=paras,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )


def cluster_chunks(chunks: list, n_clusters: int = 3) -> dict:
    texts = [c['text'] for c in chunks]
    embeddings = get_embedder().encode(texts)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(embeddings)
    clusters = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[label].append(chunks[idx])
    return clusters


def synthesize_theme_summary(chunks: list, question: str) -> str:
    context = "\n\n".join(
        [f"Doc {c['doc_id']}, Paragraph {c['chunk_index'] + 1}: {c['text']}" for c in chunks]
    )
    prompt = (
        f"You are a research assistant. Use ONLY the following context to answer the user's question.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}\n"
        f"INSTRUCTIONS: Provide a detailed, cited answer. If the context is insufficient, say so. "
        f"List supporting document IDs and paragraph numbers."
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def build_citations(supporting_chunks: list, db: Session):
    seen = {}
    citations = []
    for chunk in supporting_chunks:
        key = (chunk['doc_id'], chunk['chunk_index'])
        if key not in seen:
            number = len(citations) + 1
            doc = db.query(Document).filter(Document.id == chunk['doc_id']).first()
            document_name = doc.filename if doc else f"Document {chunk['doc_id']}"
            para = chunk['chunk_index'] + 1
            citations.append({
                "number": number,
                "doc_id": chunk['doc_id'],
                "document_name": document_name,
                "paragraph": para,
            })
            seen[key] = number
    return citations, seen


def process_themes_and_citations(themes: list, db: Session) -> list:
    citation_refs = []
    for theme in themes[:4]:
        matches = re.findall(r'\(Doc (\d+), Paragraph (\d+)\)', theme['theme_summary'])
        for doc_id, para in matches:
            citation_refs.append((int(doc_id), int(para) - 1))

    unique_citations = []
    seen = set()
    for ref in citation_refs:
        if ref not in seen:
            unique_citations.append(ref)
            seen.add(ref)

    citation_map = {ref: idx + 1 for idx, ref in enumerate(unique_citations)}

    new_themes = []
    for theme in themes[:4]:
        text = theme['theme_summary']

        def repl(match):
            doc_id, para = int(match.group(1)), int(match.group(2))
            ref = (doc_id, para - 1)
            n = citation_map.get(ref, '?')
            return f"[{n}]"

        text = re.sub(r'\(Doc (\d+), Paragraph (\d+)\)', repl, text)
        new_themes.append({**theme, "theme_summary": text})

    citation_lines = []
    for idx, (doc_id, chunk_index) in enumerate(unique_citations, 1):
        doc = db.query(Document).filter(Document.id == doc_id).first()
        document_name = doc.filename if doc else f"Document {doc_id}"
        para = chunk_index + 1
        citation_lines.append(f"[{idx}] {document_name}, Paragraph {para}")

    theme5 = {"theme_summary": "Citations\n" + "\n".join(citation_lines)}
    return new_themes + [theme5]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    results = []
    for file in files:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())

        extracted_text = ""
        if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image = Image.open(file_location)
            extracted_text = pytesseract.image_to_string(image)
        elif file.filename.lower().endswith('.pdf'):
            images = convert_from_path(file_location)
            for img in images:
                extracted_text += pytesseract.image_to_string(img)
        else:
            results.append({
                "filename": file.filename,
                "message": "Unsupported file type.",
                "extracted_text": "",
                "sentiment": {}
            })
            continue

        sentiment_scores = get_sentiment_analyzer().polarity_scores(extracted_text)

        doc = Document(
            filename=file.filename,
            filetype=file.filename.split('.')[-1],
            extracted_text=extracted_text,
            upload_time=datetime.datetime.utcnow(),
            sentiment=str(sentiment_scores)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        add_document_to_vector_db(doc.id, extracted_text)

        results.append({
            "filename": file.filename,
            "message": "File uploaded and text extracted successfully!",
            "extracted_text": extracted_text,
            "sentiment": sentiment_scores,
            "document_id": doc.id
        })

    return JSONResponse(content={"results": results})


@app.get("/documents/")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return [
        {"id": doc.id, "filename": doc.filename, "filetype": doc.filetype, "upload_time": doc.upload_time}
        for doc in docs
    ]


@app.get("/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        sentiment = ast.literal_eval(doc.sentiment) if doc.sentiment else {}
    except Exception:
        sentiment = {}
    return {
        "id": doc.id,
        "filename": doc.filename,
        "filetype": doc.filetype,
        "upload_time": doc.upload_time,
        "extracted_text": doc.extracted_text,
        "sentiment": sentiment,
    }


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.delete(doc)
    db.commit()
    return {"message": f"Document {doc_id} deleted successfully"}


@app.get("/documents/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(file_path, filename=doc.filename)


@app.post("/query/")
def query_documents(
    question: str = Body(..., embed=True),
    selected_doc_ids: Optional[List[int]] = Body(None),
    db: Session = Depends(get_db)
):
    try:
        embedder = get_embedder()
        collection = get_collection()

        query_embedding = embedder.encode([question])[0]

        filter_dict = {"doc_id": {"$in": selected_doc_ids}} if selected_doc_ids else None

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=50,
            where=filter_dict
        )

        chunks = []
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            chunks.append({
                "doc_id": meta['doc_id'],
                "chunk_index": meta['chunk_index'],
                "chunk_type": meta.get('chunk_type', 'paragraph'),
                "text": doc
            })

        if not chunks:
            return {"answer": "No relevant documents found.", "themes": [], "chunks": []}

        n_clusters = min(5, len(chunks))
        clusters = cluster_chunks(chunks, n_clusters=n_clusters)

        themes = []
        for label, theme_chunks in clusters.items():
            summary = synthesize_theme_summary(theme_chunks, question)
            doc_refs = [{"doc_id": c['doc_id'], "chunk_index": c['chunk_index']} for c in theme_chunks]
            themes.append({
                "theme_summary": summary,
                "supporting_chunks": doc_refs,
                "num_chunks": len(theme_chunks)
            })

        processed_themes = process_themes_and_citations(themes, db)

        final_answer = "Identified Themes:\n"
        for i, theme in enumerate(processed_themes, 1):
            final_answer += f"\nTheme {i}: {theme['theme_summary']}\n"

        return {"answer": final_answer, "themes": processed_themes, "chunks": chunks}

    except Exception as e:
        return {"answer": f"An error occurred: {str(e)}", "themes": [], "chunks": []}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
