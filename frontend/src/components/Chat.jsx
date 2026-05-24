import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  listConversations,
  sendMessage,
  getEmotionalState,
  logout as apiLogout,
  buildStreamUrl,
} from "../api";
import EmotionalState from "./EmotionalState";

export default function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const [conversations, setConversations] = useState([]);
  const [activeConvoId, setActiveConvoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [emotionalVector, setEmotionalVector] = useState([0, 0, 0, 0]);
  const [error, setError] = useState("");
  const email = localStorage.getItem("email") || "User";

  // Load conversations and emotional state on mount
  useEffect(() => {
    loadConversations();
    loadEmotionalState();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function loadConversations() {
    try {
      const data = await listConversations();
      setConversations(data);
    } catch {
      // silently fail
    }
  }

  async function loadEmotionalState() {
    try {
      const data = await getEmotionalState();
      setEmotionalVector(data.vector);
    } catch {
      // silently fail
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || loading || streaming) return;

    setInput("");
    setError("");

    // Optimistically add the user message
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      // Try streaming first
      try {
        await doStream(text);
      } catch {
        // Fallback to non-streaming
        await doNonStream(text);
      }
    } catch (err) {
      setError(err.message);
      setMessages((prev) => prev.filter((m) => m !== userMsg));
    } finally {
      setLoading(false);
      await loadEmotionalState();
      await loadConversations();
    }
  }

  async function doStream(text) {
    setStreaming(true);

    const token = localStorage.getItem("token");
    const url = buildStreamUrl(text, activeConvoId);

    const response = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!response.ok) throw new Error("Stream failed");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let botMsg = { role: "bot", content: "" };
    let newConvoId = activeConvoId;

    setMessages((prev) => [...prev, botMsg]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));

          if (data.token) {
            botMsg = { role: "bot", content: botMsg.content + data.token };
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = botMsg;
              return updated;
            });
          }

          if (data.done) {
            newConvoId = data.conversation_id;
            if (data.vector) setEmotionalVector(data.vector);
          }
        } catch {
          // skip malformed JSON
        }
      }
    }

    setActiveConvoId(newConvoId);
    setStreaming(false);
  }

  async function doNonStream(text) {
    const data = await sendMessage(text, activeConvoId);
    setMessages((prev) => [
      ...prev,
      { role: "bot", content: data.reply },
    ]);
    setActiveConvoId(data.conversation_id);
    if (data.emotional_vector) {
      setEmotionalVector(data.emotional_vector);
    }
  }

  function selectConversation(convo) {
    setActiveConvoId(convo.id);
    setMessages([]);
  }

  function newConversation() {
    setActiveConvoId(null);
    setMessages([]);
    setInput("");
    setError("");
  }

  async function handleLogout() {
    try {
      await apiLogout();
    } catch {
      // ignore
    }
    localStorage.removeItem("token");
    localStorage.removeItem("email");
    navigate("/login");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-layout">
      {/* ─── Sidebar ─── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Therapy Chat</h2>
        </div>

        <button className="new-chat-btn" onClick={newConversation}>
          + New Conversation
        </button>

        <div className="conversation-list">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`conversation-item ${c.id === activeConvoId ? "active" : ""}`}
              onClick={() => selectConversation(c)}
            >
              <h4>{c.title}</h4>
              <span>{new Date(c.updated_at).toLocaleDateString()}</span>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <span className="user-email">{email}</span>
          <button className="btn btn-danger" style={{ fontSize: "0.8rem", padding: "0.4rem 0.75rem" }} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      {/* ─── Main Chat ─── */}
      <main className="chat-main">
        {activeConvoId && (
          <div className="chat-header">
            <h3>{conversations.find((c) => c.id === activeConvoId)?.title || "Conversation"}</h3>
          </div>
        )}

        <div className="messages-area">
          {messages.length === 0 && !loading ? (
            <div className="empty-state">
              <h2>How are you feeling today?</h2>
              <p>Start a conversation by typing a message below. Everything you share is confidential.</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                {msg.content || (msg.role === "bot" && streaming && i === messages.length - 1 ? (
                  <div className="typing">
                    <span /><span /><span />
                  </div>
                ) : (
                  msg.content
                ))}
              </div>
            ))
          )}

          {loading && !streaming && (
            <div className="message bot">
              <div className="typing">
                <span /><span /><span />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && <div className="error-msg" style={{ margin: "0 1.5rem 0.5rem" }}>{error}</div>}

        <div className="input-area">
          <div className="input-row">
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading || streaming}
            />
            <button onClick={handleSend} disabled={loading || streaming || !input.trim()}>
              {streaming ? "..." : "Send"}
            </button>
          </div>
        </div>

        <EmotionalState vector={emotionalVector} />
      </main>
    </div>
  );
}