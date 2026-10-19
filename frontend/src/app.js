const API_BASE = "/api";
const HEALTH_URL = "/health";

// ---------- Auth state ----------
let authToken = localStorage.getItem("docklight_token") || "";
let authEmail = localStorage.getItem("docklight_email") || "";
let authMode = "login";
let currentConversationId = null;

const authScreen = document.getElementById("authScreen");
const shell = document.getElementById("shell");
const authForm = document.getElementById("authForm");
const authEmailInput = document.getElementById("authEmail");
const authPasswordInput = document.getElementById("authPassword");
const authSubmit = document.getElementById("authSubmit");
const authToggle = document.getElementById("authToggle");
const authToggleLabel = document.querySelector(".auth-toggle-label");
const authError = document.getElementById("authError");
const accountEmail = document.getElementById("accountEmail");
const logoutBtn = document.getElementById("logoutBtn");
const newConversationBtn = document.getElementById("newConversationBtn");

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const docList = document.getElementById("docList");
const fileInput = document.getElementById("fileInput");
const refreshDocsBtn = document.getElementById("refreshDocs");
const scrollEl = document.getElementById("scroll");
let intro = document.getElementById("intro");
const composerForm = document.getElementById("composerForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function authHeader() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

// A small fetch wrapper that attaches the JWT and logs the user out on 401,
// so an expired/invalid token always sends them back to the login screen
// instead of silently failing every request.
async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeader() };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    doLogout();
    throw new Error("Session expired. Please log in again.");
  }
  return res;
}

// ---------- Auth screens ----------
function showApp() {
  authScreen.hidden = true;
  shell.hidden = false;
  accountEmail.textContent = authEmail;
  checkHealth();
  loadDocuments();
}

function showAuth() {
  authScreen.hidden = false;
  shell.hidden = true;
}

function doLogout() {
  authToken = "";
  authEmail = "";
  currentConversationId = null;
  localStorage.removeItem("docklight_token");
  localStorage.removeItem("docklight_email");
  showAuth();
}

authToggle.addEventListener("click", () => {
  authMode = authMode === "login" ? "signup" : "login";
  authSubmit.textContent = authMode === "login" ? "Log in" : "Sign up";
  authToggle.textContent = authMode === "login" ? "Sign up" : "Log in";
  authToggleLabel.textContent = authMode === "login" ? "Need an account?" : "Already have an account?";
  authError.hidden = true;
});

authForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = authEmailInput.value.trim();
  const password = authPasswordInput.value;
  const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/signup";

  authError.hidden = true;
  authSubmit.disabled = true;
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
      throw new Error(detail || "Something went wrong.");
    }
    authToken = data.access_token;
    authEmail = data.email;
    localStorage.setItem("docklight_token", authToken);
    localStorage.setItem("docklight_email", authEmail);
    authForm.reset();
    showApp();
  } catch (err) {
    authError.textContent = err.message;
    authError.hidden = false;
  } finally {
    authSubmit.disabled = false;
  }
});

logoutBtn.addEventListener("click", doLogout);

// ---------- Connection status ----------
async function checkHealth() {
  try {
    const res = await fetch(HEALTH_URL);
    const data = await res.json();
    const healthy = data.status === "healthy";
    statusDot.className = `status-dot ${healthy ? "online" : "offline"}`;
    statusText.textContent = healthy ? "Connected to backend" : "Backend degraded";
  } catch (e) {
    statusDot.className = "status-dot offline";
    statusText.textContent = "Backend unavailable";
  }
}

// ---------- Document index ----------
function statusDotClass(status) {
  return { INDEXED: "indexed", PROCESSING: "processing", FAILED: "failed", UPLOADED: "uploaded" }[status] || "uploaded";
}

async function loadDocuments() {
  try {
    const res = await apiFetch(`${API_BASE}/documents`);
    const data = await res.json();
    if (!data.documents.length) {
      docList.innerHTML = `<li class="doc-empty">Nothing added yet.</li>`;
      return;
    }
    docList.innerHTML = data.documents
      .map(
        (doc) => `
        <li class="doc-item" data-id="${doc.doc_id}">
          <div class="doc-name">${escapeHtml(doc.filename)}</div>
          <div class="doc-meta">
            <span class="doc-status"><span class="dot ${statusDotClass(doc.status)}"></span>${doc.status.toLowerCase()}</span>
            <button class="doc-remove" data-id="${doc.doc_id}">remove</button>
          </div>
        </li>`
      )
      .join("");
  } catch (e) {
    docList.innerHTML = `<li class="doc-empty">Could not load the document list.</li>`;
  }
}

docList.addEventListener("click", async (e) => {
  if (e.target.classList.contains("doc-remove")) {
    const id = e.target.dataset.id;
    e.target.textContent = "removing";
    try {
      await apiFetch(`${API_BASE}/documents/${id}`, { method: "DELETE" });
    } finally {
      loadDocuments();
    }
  }
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);

  docList.insertAdjacentHTML(
    "afterbegin",
    `<li class="doc-item">
       <div class="doc-name">${escapeHtml(file.name)}</div>
       <div class="doc-meta"><span class="doc-status"><span class="dot processing"></span>uploading</span></div>
     </li>`
  );

  try {
    await apiFetch(`${API_BASE}/documents/upload`, { method: "POST", body: formData });
  } finally {
    fileInput.value = "";
    loadDocuments();
    // Processing happens in a background worker -- poll a few times so the
    // status visibly moves from "processing" to "indexed" without a manual refresh.
    let attempts = 0;
    const poll = setInterval(() => {
      attempts += 1;
      loadDocuments();
      if (attempts >= 6) clearInterval(poll);
    }, 4000);
  }
});

refreshDocsBtn.addEventListener("click", loadDocuments);

// ---------- Conversation ----------
newConversationBtn.addEventListener("click", () => {
  currentConversationId = null;
  scrollEl.querySelectorAll(".turn").forEach((el) => el.remove());
  if (!intro) {
    scrollEl.insertAdjacentHTML(
      "afterbegin",
      `<div class="intro" id="intro">
         <h1>Ask about your documents</h1>
         <p>Add a file on the left, then ask a question below. Every answer points back to the exact passage it came from, and follow-up questions remember the conversation.</p>
       </div>`
    );
    intro = document.getElementById("intro");
  }
});

function buildTurn(question) {
  if (intro) {
    intro.remove();
    intro = null;
  }
  const turn = document.createElement("div");
  turn.className = "turn";
  turn.innerHTML = `
    <div class="turn-row question">
      <span class="turn-label">Q</span>
      <p class="turn-text">${escapeHtml(question)}</p>
    </div>
    <div class="turn-row answer">
      <span class="turn-label">A</span>
      <div class="turn-text answer-text pending">Reading the indexed documents…</div>
    </div>
  `;
  scrollEl.appendChild(turn);
  scrollEl.scrollTop = scrollEl.scrollHeight;
  return turn;
}

// Turns "(Source 2)" / "[Source 2]" / "Source 2" in the model's raw answer
// into a clickable superscript footnote marker.
function formatAnswer(text) {
  // Models cite in different styles: [Source 1], (Source 1), [1], 【1】 or plain "Source 1".
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(
    /【\s*(\d+)\s*】|\[\s*(?:Source\s*)?(\d+)\s*\]|\(\s*Source\s*(\d+)\s*\)|\bSource\s+(\d+)\b/gi,
    (_m, a, b, c, d) => {
      const n = a || b || c || d;
      return `<sup class="cite" data-n="${n}">${n}</sup>`;
    }
  );
}

function attachSources(turn, answerEl, sources) {
  if (!sources.length) return;

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "sources-toggle";
  toggle.textContent = `Show sources (${sources.length})`;

  const list = document.createElement("ol");
  list.className = "footnotes";
  list.hidden = true;
  list.innerHTML = sources
    .map(
      (s, i) => `
      <li data-n="${i + 1}">
        <span class="n">${i + 1}.</span>
        <span><span class="src">${escapeHtml(s.filename)}</span> — ${escapeHtml(s.chunk_text.slice(0, 220))}${s.chunk_text.length > 220 ? "…" : ""}</span>
      </li>`
    )
    .join("");

  toggle.addEventListener("click", () => {
    list.hidden = !list.hidden;
    toggle.textContent = list.hidden ? `Show sources (${sources.length})` : "Hide sources";
  });

  turn.appendChild(toggle);
  turn.appendChild(list);

  answerEl.querySelectorAll("sup.cite").forEach((sup) => {
    sup.addEventListener("click", () => {
      list.hidden = false;
      toggle.textContent = "Hide sources";
      const target = list.querySelector(`li[data-n="${sup.dataset.n}"]`);
      if (target) {
        target.classList.add("hit");
        target.scrollIntoView({ behavior: "smooth", block: "nearest" });
        setTimeout(() => target.classList.remove("hit"), 1200);
      }
    });
  });
}

// Parses the backend's Server-Sent-Events stream by hand (fetch + a manual
// reader) rather than the built-in EventSource API, because EventSource has
// no way to attach an Authorization header -- a real constraint when SSE
// needs to be behind auth, not a stylistic choice.
async function askStreaming(question) {
  const turn = buildTurn(question);
  const answerEl = turn.querySelector(".answer-text");
  let rawAnswer = "";
  let sources = [];
  let startedStreaming = false;
  let streamError = "";

  try {
    const response = await apiFetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: currentConversationId }),
    });
    if (!response.ok || !response.body) {
      let detail = `Request failed (${response.status})`;
      try {
        const body = await response.json();
        if (typeof body.detail === "string") detail = body.detail;
      } catch (_) { /* body wasn't JSON */ }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        const eventType = (rawEvent.match(/^event: (.+)$/m) || [])[1];
        const dataLine = (rawEvent.match(/^data: (.+)$/m) || [])[1];
        if (!eventType || !dataLine) continue;
        const data = JSON.parse(dataLine);

        if (eventType === "sources") {
          sources = data;
        } else if (eventType === "token") {
          if (!startedStreaming) {
            answerEl.classList.remove("pending");
            answerEl.textContent = "";
            startedStreaming = true;
          }
          rawAnswer += data.text;
          answerEl.textContent = rawAnswer;
          scrollEl.scrollTop = scrollEl.scrollHeight;
        } else if (eventType === "error") {
          streamError = data.message;
        } else if (eventType === "done") {
          currentConversationId = data.conversation_id;
        }
      }
    }

    answerEl.classList.remove("pending");
    if (streamError) {
      // Keep whatever text already streamed, then say why it stopped.
      answerEl.textContent = rawAnswer ? `${rawAnswer}\n\n[Stopped: ${streamError}]` : streamError;
    } else {
      answerEl.innerHTML = formatAnswer(rawAnswer);
      attachSources(turn, answerEl, sources);
    }
  } catch (err) {
    answerEl.classList.remove("pending");
    // A TypeError from fetch() means the network call itself failed (backend down / unreachable).
    answerEl.textContent =
      err instanceof TypeError ? "Could not reach the backend. Check that it's running and try again." : err.message;
  }
  scrollEl.scrollTop = scrollEl.scrollHeight;
}

composerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  questionInput.value = "";
  questionInput.style.height = "auto";
  sendBtn.disabled = true;

  await askStreaming(question);

  sendBtn.disabled = false;
  questionInput.focus();
});

questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 140)}px`;
});

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composerForm.requestSubmit();
  }
});

// ---------- Boot ----------
if (authToken) {
  showApp();
} else {
  showAuth();
}
setInterval(() => {
  if (authToken) checkHealth();
}, 15000);
