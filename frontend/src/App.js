import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const API_BASE = "https://mahindra-bot.biup.ai"; // Change if backend runs elsewhere

function App() {
  // Dark mode state
  const [darkMode, setDarkMode] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-theme",
      darkMode ? "dark" : "light"
    );
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  // App states
  const [documents, setDocuments] = useState([]);
  const [files, setFiles] = useState([]);
  const [uploadMsg, setUploadMsg] = useState("");
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docDetails, setDocDetails] = useState(null);
  const [query, setQuery] = useState("");
  const [themes, setThemes] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [selectedDocsForQuery, setSelectedDocsForQuery] = useState([]);
  const [showUploadCard, setShowUploadCard] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [chat, setChat] = useState([]); // For bubble chat

  const uploadInputRef = useRef();

  useEffect(() => {
    fetchDocuments();
    // eslint-disable-next-line
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API_BASE}/documents/`);
      setDocuments(res.data || []);
    } catch (err) {
      setUploadMsg("Could not fetch documents.");
    }
  };

  const handleFileChange = (e) => setFiles(Array.from(e.target.files));

  const handleUpload = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;
    setUploadProgress(0);
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    try {
      const res = await axios.post(`${API_BASE}/upload/`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        },
      });
      setUploadMsg(
        (res.data.results || [])
          .map((r) => `${r.filename}: ${r.message || "Uploaded!"}`)
          .join("\n")
      );
      setFiles([]);
      setUploadProgress(0);
      setShowUploadCard(false);
      fetchDocuments();
    } catch (err) {
      setUploadMsg("Upload failed.");
      setUploadProgress(0);
    }
  };

  const handleDownload = (id) => {
    window.open(`${API_BASE}/documents/${id}/download`, "_blank");
  };

  const handleDelete = async (id) => {
    await axios.delete(`${API_BASE}/documents/${id}`);
    fetchDocuments();
    if (selectedDoc === id) {
      setDocDetails(null);
      setSelectedDoc(null);
    }
    setSelectedDocsForQuery((prev) => prev.filter((docId) => docId !== id));
  };

  const handleShowDetails = async (id) => {
    setSelectedDoc(id);
    const res = await axios.get(`${API_BASE}/documents/${id}`);
    setDocDetails(res.data);
  };

  // Helper to show chunk text for a given doc ID and chunk index
  const getChunkText = (docId, chunkIndex) => {
    const chunk = (chunks || []).find(
      (c) => c.doc_id === docId && c.chunk_index === chunkIndex - 1
    );
    return chunk ? chunk.text : "(not loaded)";
  };

  // Query input handling (bubble chat only)
  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      setChat((prev) => [
        ...prev,
        { sender: "user", text: query },
        { sender: "bot", text: "Please enter a question." }
      ]);
      return;
    }
    setThemes([]);
    setChunks([]);
    setChat((prev) => [...prev, { sender: "user", text: query }]);
    try {
      const res = await axios.post(`${API_BASE}/query/`, {
        question: query,
        selected_doc_ids: selectedDocsForQuery.length > 0 ? selectedDocsForQuery : undefined,
      });
      if (res.data && res.data.answer) {
        setThemes(res.data.themes || []);
        setChunks(res.data.chunks || []);
        setChat((prev) => [...prev, { sender: "bot", text: res.data.answer }]);
      } else {
        setThemes([]);
        setChunks([]);
        setChat((prev) => [...prev, { sender: "bot", text: "Error: Response missing 'answer' field." }]);
      }
    } catch (err) {
      setThemes([]);
      setChunks([]);
      setChat((prev) => [...prev, { sender: "bot", text: "Error: Could not process query." }]);
    }
    setQuery("");
  };

  // Handle document selection toggle for querying
  const toggleDocSelection = (docId) => {
    setSelectedDocsForQuery((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  // File preview for images
  const filePreview = files.length > 0 && files[0].type.startsWith("image/")
    ? URL.createObjectURL(files[0])
    : null;

  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
    return (
    <div className="app-root">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-documents">
          <h3>Documents</h3>
          <ul>
            {(documents || []).map((doc) => (
              <li key={doc.id}>
                <span className="doc-name">
                  <input
                    type="checkbox"
                    checked={selectedDocsForQuery.includes(doc.id)}
                    onChange={() => toggleDocSelection(doc.id)}
                  />
                  <b>{doc.filename}</b>
                </span>
                <span className="doc-actions">
                  <button onClick={() => handleDownload(doc.id)} title="Download">⬇️</button>
                  <button onClick={() => handleDelete(doc.id)} title="Delete">🗑️</button>
                  <button onClick={() => handleShowDetails(doc.id)} title="Details">ℹ️</button>
                </span>
              </li>
            ))}
          </ul>
        </div>
        {/* Floating upload button */}
        <button
          className="floating-upload-btn"
          onClick={() => setShowUploadCard((v) => !v)}
          aria-label="Upload"
          title="Upload"
        >
          +
        </button>
        {/* Floating upload card */}
        {showUploadCard && (
          <div className="floating-upload-card">
            <form onSubmit={handleUpload}>
              <label>
                <input
                  type="file"
                  multiple
                  onChange={handleFileChange}
                  accept=".pdf,.png,.jpg,.jpeg"
                  ref={uploadInputRef}
                />
              </label>
              {filePreview && (
                <div className="file-preview">
                  <img src={filePreview} alt="preview" />
                </div>
              )}
              {uploadProgress > 0 && (
                <div className="upload-progress-bar">
                  <div style={{ width: `${uploadProgress}%` }} />
                </div>
              )}
              <button type="submit" disabled={files.length === 0}>
                {uploadProgress > 0 ? `Uploading... (${uploadProgress}%)` : "Upload"}
              </button>
              <div style={{ color: "green", margin: "10px 0", whiteSpace: "pre-line" }}>
                {uploadMsg}
              </div>
            </form>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="main-content">
        {/* Dark mode toggle */}
        <div style={{ display: "flex", justifyContent: "flex-end", padding: "1rem" }}>
          <button
            onClick={() => setDarkMode((d) => !d)}
            style={{
              background: "none",
              border: "none",
              fontSize: "2rem",
              cursor: "pointer",
              color: "var(--accent)"
            }}
            aria-label="Toggle dark mode"
            title="Toggle dark mode"
          >
            {darkMode ? "🌙" : "☀️"}
          </button>
        </div>
        {/* --- NEW HEADER --- */}
        <h1 className="sheep-header">
          <span className="sig-emoji">🌾</span>
          Sheep 
          Bot
          <span className="sig-emoji">🐑</span>
        </h1>
        <div className="tagline">Your soft and smart document helper</div>
        <div className="chat-area">
          {/* Bubble chat */}
          <div className="chat-bubbles">
            {chat.map((msg, idx) => (
              <div
                key={idx}
                  className={`chat-bubble ${msg.sender === "user" ? "user" : "bot"}`}
                 >
                      {msg.sender === "bot"
                       ? msg.text.split('\n').map((str, i) =>
                     <p key={i} style={{ margin: '0 0 15px 0' }}>{str}</p>
                  )
                 : msg.text}

              </div>
            ))}
          </div>
          {/* Document Details */}
          {docDetails && (
            <div className="doc-details-card">
              <h4>Details for: {docDetails.filename}</h4>
              <strong>Extracted Text:</strong>
              <pre
                style={{
                  background: "#f9f9f9",
                  padding: 8,
                  maxHeight: 200,
                  overflow: "auto",
                }}
              >
                {docDetails.extracted_text}
              </pre>
              <strong>Sentiment:</strong>
              <pre>{JSON.stringify(docDetails.sentiment, null, 2)}</pre>
              <button
                onClick={() => {
                  setDocDetails(null);
                  setSelectedDoc(null);
                }}
              >
                Close
              </button>
            </div>
          )}

          {/* Themes Section */}
          {(themes || []).length > 0 && (
            <div style={{ marginTop: 32 }}>
              <h4>Identified Themes (with Paragraph-level Citations)</h4>
              <ol className="theme-list">
                {(themes || []).map((theme, idx) => (
                  <li key={idx}>
                    <div>
                      <b>Theme {idx + 1}:</b> {theme.theme_summary}
                    </div>
                    <div>
                      <span>Supporting Citations: </span>
                      {(theme.supporting_chunks || []).map((ref, i) => (
                        <span key={i}>
                          <button
                            style={{
                              margin: "0 3px",
                              padding: "2px 7px",
                              fontSize: "0.95em",
                              cursor: "pointer",
                              background: "#e0eaff",
                              border: "1px solid #b2c4e6",
                              borderRadius: "4px",
                            }}
                            title={getChunkText(ref.doc_id, ref.chunk_index)}
                            onClick={() => {
                              setSelectedDoc(ref.doc_id);
                              setDocDetails({
                                ...docDetails,
                                extracted_text: getChunkText(ref.doc_id, ref.chunk_index),
                              });
                            }}
                          >
                            Doc {ref.doc_id}, Para {ref.chunk_index}
                          </button>
                          {i < theme.supporting_chunks.length - 1 ? "," : ""}
                        </span>
                      ))}
                    </div>
                    <div style={{ fontSize: "0.93em", color: "#666" }}>
                      Chunks: {theme.num_chunks}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>

        {/* Chat input at the bottom */}
        <form className="chat-input" onSubmit={handleQuery}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about your documents..."
          />
          <button type="submit">Ask</button>
        </form>
      </main>
    </div>
  );
}

export default App;