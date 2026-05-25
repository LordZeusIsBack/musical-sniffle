const API_BASE = "";

function getToken() {
  return localStorage.getItem("token");
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // Don't set Content-Type for FormData; let fetch set it automatically
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function health() {
  return request("/health");
}

export async function signup(email, password) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email, password) {
  const body = new FormData();
  body.append("username", email);
  body.append("password", password);
  return request("/auth/login", {
    method: "POST",
    body,
  });
}

export async function logout() {
  return request("/auth/logout", { method: "POST" });
}

export async function listConversations() {
  return request("/chat/conversations");
}

export async function getEmotionalState() {
  return request("/chat/state");
}

export async function sendMessage(message, conversationId = null) {
  const body = { message };
  if (conversationId) body.conversation_id = conversationId;
  return request("/chat/message", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function buildStreamUrl(message, conversationId = null) {
  let url = `/chat/stream?message=${encodeURIComponent(message)}`;
  if (conversationId) url += `&conversation_id=${conversationId}`;
  return url;
}