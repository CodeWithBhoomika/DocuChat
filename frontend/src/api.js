// All calls go to our own backend. The browser never talks to Groq directly,
// so the AI key stays on the server.
const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch {
    throw new Error("Cannot reach the server. If it was idle, wait a minute and try again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
  return data;
}

export const getSessionId = () => {
  let id = localStorage.getItem("docuchat-session");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("docuchat-session", id);
  }
  return id;
};

export const uploadFiles = (sessionId, files) => {
  const form = new FormData();
  form.append("session_id", sessionId);
  files.forEach((f) => form.append("files", f));
  return request("/api/upload", { method: "POST", body: form });
};

export const listDocuments = (sessionId) =>
  request(`/api/documents?session_id=${encodeURIComponent(sessionId)}`);

export const askQuestion = (sessionId, question) =>
  request("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question }),
  });

export const clearSession = (sessionId) =>
  request(`/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
