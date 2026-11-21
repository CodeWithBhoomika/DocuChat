import { useEffect, useRef, useState } from "react";
import { askQuestion, clearSession, getSessionId, listDocuments, uploadFiles } from "./api.js";

const sessionId = getSessionId();

// Turns "text [1] more [2]" into text + clickable citation chips
function AnswerText({ text, onCite }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p className="answer">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        return m ? (
          <button key={i} className="chip" onClick={() => onCite(Number(m[1]))} aria-label={`Show source ${m[1]}`}>
            {m[1]}
          </button>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </p>
  );
}

function Message({ msg }) {
  const [active, setActive] = useState(null);
  if (msg.role === "user") return <div className="bubble user">{msg.text}</div>;
  return (
    <div className="bubble bot">
      {msg.error ? <p className="error">{msg.text}</p> : <AnswerText text={msg.text} onCite={setActive} />}
      {msg.sources?.length > 0 && (
        <ul className="sources">
          {msg.sources.map((s) => (
            <li key={s.id} className={active === s.id ? "source open" : "source"}>
              <button onClick={() => setActive(active === s.id ? null : s.id)}>
                <span className="chip static">{s.id}</span>
                <span>{s.file}</span>
                <span className="page">page {s.page}</span>
              </button>
              {active === s.id && <blockquote><mark>{s.snippet}</mark></blockquote>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [drag, setDrag] = useState(false);
  const endRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    listDocuments(sessionId).then((d) => setDocs(d.documents)).catch(() => {});
  }, []);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);

  async function handleFiles(fileList) {
    const files = [...fileList].filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!files.length) return setNotice("Choose PDF files only.");
    setUploading(true);
    setNotice("");
    try {
      await uploadFiles(sessionId, files);
      setDocs((await listDocuments(sessionId)).documents);
    } catch (e) {
      setNotice(e.message);
    } finally {
      setUploading(false);
    }
  }

  async function send(e, preset) {
    e?.preventDefault();
    const q = (preset ?? question).trim();
    if (q.length < 2 || busy) return;
    setQuestion("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await askQuestion(sessionId, q);
      setMessages((m) => [...m, { role: "bot", text: res.answer, sources: res.sources }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "bot", text: err.message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  async function clearAll() {
    await clearSession(sessionId).catch(() => {});
    setDocs([]);
    setMessages([]);
  }

  const ready = docs.length > 0;

  return (
    <div className="layout">
      <aside className="library">
        <h1>DocuChat</h1>
        <p className="tagline">Upload PDFs, then ask questions. Every answer points to the page it came from.</p>

        <div
          className={drag ? "drop active" : "drop"}
          onClick={() => fileRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
          role="button" tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && fileRef.current.click()}
        >
          <input ref={fileRef} type="file" accept="application/pdf" multiple hidden
                 onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }} />
          <strong>{uploading ? "Reading your PDF…" : "Add PDFs"}</strong>
          <span>Drop files here or click to browse. Up to 10 MB each.</span>
        </div>
        {notice && <p className="error" role="alert">{notice}</p>}

        <h2>Your documents</h2>
        {ready ? (
          <ul className="docs">
            {docs.map((d) => (
              <li key={d.name}><span className="name">{d.name}</span><span className="meta">{d.pages} pages</span></li>
            ))}
          </ul>
        ) : <p className="muted">Nothing uploaded yet.</p>}
        {ready && <button className="link" onClick={clearAll}>Remove all documents</button>}
      </aside>

      <main className="chat">
        <div className="thread">
          {messages.length === 0 && (
            <div className="empty">
              <h2>{ready ? "Ask anything about your documents" : "Start by adding a PDF"}</h2>
              <p>{ready ? "Try one of these:" : "Notes, a paper, a policy, a manual. Text-based PDFs work best."}</p>
              {ready && (
                <div className="suggest">
                  {["Summarize this document in 5 points", "What are the key terms or definitions?", "What conclusions does it reach?"].map((s) => (
                    <button key={s} onClick={() => send(null, s)}>{s}</button>
                  ))}
                </div>
              )}
            </div>
          )}
          {messages.map((m, i) => <Message key={i} msg={m} />)}
          {busy && <div className="bubble bot muted">Searching your documents…</div>}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={send}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={1000}
                 placeholder={ready ? "Ask a question about your PDFs" : "Add a PDF first"}
                 disabled={!ready || busy} aria-label="Your question" />
          <button type="submit" disabled={!ready || busy || question.trim().length < 2}>Ask</button>
        </form>
      </main>
    </div>
  );
}
