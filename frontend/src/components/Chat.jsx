import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  listConversations,
  sendMessage,
  getEmotionalState,
  logout as apiLogout,
  buildStreamUrl,
} from "../api";
import MoodBloom from "./MoodBloom";
import AmbientAura from "./AmbientAura";
import useEmotion from "../hooks/useEmotion";

// ─── Suggested starter chips ───
const STARTERS = [
  "I've been feeling overwhelmed lately",
  "I had a rough day today",
  "I need help sorting through my thoughts",
  "I want to practice gratitude",
  "I'm feeling anxious about something",
];

// ─── Date grouping helper ───
function groupConversations(list) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups = { Today: [], Yesterday: [], "This Week": [], Earlier: [] };
  for (const c of list) {
    const d = new Date(c.updated_at);
    const date = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    if (date >= today) groups.Today.push(c);
    else if (date >= yesterday) groups.Yesterday.push(c);
    else if (date >= weekAgo) groups["This Week"].push(c);
    else groups.Earlier.push(c);
  }
  return Object.entries(groups).filter(([, items]) => items.length > 0);
}

// ─── Inline typing dots ───
function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 px-2">
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-current" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-current" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-current" />
    </span>
  );
}

// ─── Suggested chip ───
function StarterChip({ label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]
                 text-sm text-warm-gray hover:text-charcoal hover:border-sage-300
                 transition-all shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-elevated)]"
    >
      {label}
    </button>
  );
}

export default function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const [conversations, setConversations] = useState([]);
  const [activeConvoId, setActiveConvoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [emotionalVector, setEmotionalVector] = useState([0, 0, 0, 0]);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [moodOpen, setMoodOpen] = useState(false);

  const emotion = useEmotion(emotionalVector);
  const email = localStorage.getItem("email") || "User";

  // ── Load data ──
  useEffect(() => {
    loadConversations();
    loadEmotionalState();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function loadConversations() {
    try {
      const data = await listConversations();
      setConversations(data);
    } catch {
      /* ignore */
    }
  }

  async function loadEmotionalState() {
    try {
      const data = await getEmotionalState();
      setEmotionalVector(data.vector);
    } catch {
      /* ignore */
    }
  }

  // ── Send / Stream ──
  async function handleSend(text) {
    const msg = (text ?? input).trim();
    if (!msg || loading || streaming) return;
    setInput("");
    setError("");

    const userMsg = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      try {
        await doStream(msg);
      } catch {
        await doNonStream(msg);
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
          /* skip */
        }
      }
    }
    setActiveConvoId(newConvoId);
    setStreaming(false);
  }

  async function doNonStream(text) {
    const data = await sendMessage(text, activeConvoId);
    setMessages((prev) => [...prev, { role: "bot", content: data.reply }]);
    setActiveConvoId(data.conversation_id);
    if (data.emotional_vector) setEmotionalVector(data.emotional_vector);
  }

  // ── Navigation ──
  function selectConversation(convo) {
    setActiveConvoId(convo.id);
    setMessages([]);
    if (window.innerWidth < 768) setSidebarOpen(false);
  }

  function newConversation() {
    setActiveConvoId(null);
    setMessages([]);
    setInput("");
    setError("");
    inputRef.current?.focus();
  }

  async function handleLogout() {
    try {
      await apiLogout();
    } catch {
      /* ignore */
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

  // ── Render helpers ──
  const activeTitle = conversations.find((c) => c.id === activeConvoId)?.title || null;
  const groupedConvos = groupConversations(conversations);

  return (
    <div className="flex h-screen bg-[var(--color-bg)] relative">
      <AmbientAura vector={emotionalVector} />

      {/* ─── Sidebar backdrop (mobile) ─── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ─── Sidebar ─── */}
      <aside
        className={`
          fixed md:relative z-30 h-full w-72 flex flex-col bg-[var(--color-surface)]
          border-r border-[var(--color-border)] transition-transform duration-300
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0 md:w-0 md:min-w-0 md:overflow-hidden md:border-0"}
        `}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-sage-300 to-sky-300 flex items-center justify-center">
              <span className="text-xs text-white font-light">&#x2726;</span>
            </div>
            <span className="font-semibold text-sm text-charcoal">Sanctuary</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden text-warm-gray hover:text-charcoal transition-colors"
            aria-label="Close sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* New chat button */}
        <button
          onClick={newConversation}
          className="mx-3 mt-3 py-2 rounded-xl bg-sage-400 text-white text-sm font-medium
                     transition-all hover:bg-sage-500 active:scale-[0.98]
                     flex items-center justify-center gap-2"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New Conversation
        </button>

        {/* Conversation list */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
          {groupedConvos.length === 0 && (
            <p className="text-center text-sm text-warm-gray pt-8">
              No conversations yet
            </p>
          )}
          {groupedConvos.map(([group, items]) => (
            <div key={group}>
              <h4 className="px-3 mb-1 text-xs font-medium text-warm-gray uppercase tracking-wider">
                {group}
              </h4>
              <div className="space-y-0.5">
                {items.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => selectConversation(c)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors
                      ${
                        c.id === activeConvoId
                          ? "bg-sage-100 text-sage-800 border-l-2 border-sage-400"
                          : "text-charcoal hover:bg-[var(--color-surface-hover)] border-l-2 border-transparent"
                      }`}
                  >
                    <div className="truncate font-medium">{c.title}</div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* User footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--color-border)]">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-sage-200 flex items-center justify-center text-xs font-semibold text-sage-700 shrink-0">
              {email[0].toUpperCase()}
            </div>
            <span className="text-sm text-charcoal truncate">{email}</span>
          </div>
          <button
            onClick={handleLogout}
            className="text-warm-gray hover:text-rose-400 transition-colors p-1"
            aria-label="Sign out"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
          </button>
        </div>
      </aside>

      {/* ─── Main chat area ─── */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Top bar */}
        <header className="flex items-center gap-3 px-5 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur-sm z-10">
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden text-warm-gray hover:text-charcoal transition-colors"
            aria-label="Open sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <div className="flex-1 min-w-0">
            {activeTitle ? (
              <h2 className="text-sm font-semibold text-charcoal truncate">{activeTitle}</h2>
            ) : (
              <h2 className="text-sm font-semibold text-warm-gray">New conversation</h2>
            )}
          </div>
          {/* Mood toggle */}
          <button
            onClick={() => setMoodOpen((o) => !o)}
            className="flex items-center gap-2 text-xs text-warm-gray hover:text-charcoal transition-colors"
          >
            <span className="hidden sm:inline">Mood</span>
            <div
              className="w-5 h-5 rounded-full transition-colors duration-700"
              style={{ backgroundColor: emotion.color }}
            />
          </button>
        </header>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6">
          {messages.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-6">
              <MoodBloom vector={emotionalVector} size={96} />
              <div>
                <h2 className="text-xl font-semibold text-charcoal mb-1">
                  How are you feeling today?
                </h2>
                <p className="text-sm text-warm-gray max-w-xs mx-auto leading-relaxed">
                  Start a conversation. Everything you share stays between us.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-md">
                {STARTERS.map((s) => (
                  <StarterChip key={s} label={s} onClick={() => handleSend(s)} />
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-4">
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] sm:max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-sage-400 text-white rounded-br-md"
                          : "bg-[var(--color-surface)] border border-[var(--color-border)] text-charcoal rounded-bl-md shadow-[var(--shadow-card)]"
                      }`}
                    >
                      {msg.content || (msg.role === "bot" && streaming && i === messages.length - 1) ? (
                        <span className={!msg.content && streaming && i === messages.length - 1 ? "" : ""}>
                          {msg.content}
                          {streaming && i === messages.length - 1 && (
                            <span className="cursor-blink" />
                          )}
                        </span>
                      ) : msg.role === "bot" ? (
                        <span className="inline-flex items-center">
                          Thinking <TypingDots />
                        </span>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {loading && !streaming && (
                <div className="flex justify-start">
                  <div className="max-w-[70%] px-4 py-3 rounded-2xl rounded-bl-md bg-[var(--color-surface)] border border-[var(--color-border)] shadow-[var(--shadow-card)]">
                    <TypingDots />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="mx-4 sm:mx-6 mb-2 px-4 py-2 rounded-xl bg-rose-300/15 border border-rose-300/30 text-rose-500 text-xs text-center"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input bar + Mood Bloom */}
        <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur-sm">
          {/* Mood bloom detail expand */}
          <AnimatePresence>
            {moodOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden border-b border-[var(--color-border)]"
              >
                <div className="flex items-center gap-5 px-5 py-4">
                  <MoodBloom vector={emotionalVector} size={64} />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-warm-gray uppercase tracking-wider">Mood</span>
                      <div className="flex gap-1.5">
                        {emotion.moodWords.map((w) => (
                          <span
                            key={w}
                            className="px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{
                              backgroundColor: `${emotion.color}20`,
                              color: emotion.color,
                            }}
                          >
                            {w}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-warm-gray">
                      <span>Distress</span>
                      <div className="flex-1 h-1 rounded-full bg-[var(--color-border)] max-w-[80px]">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${((emotionalVector[0] + 1) / 2) * 100}%`, backgroundColor: emotion.color }}
                        />
                      </div>
                      <span className="text-charcoal font-medium">{emotionalVector[0].toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Input */}
          <div className="flex items-end gap-3 px-4 sm:px-6 py-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                rows={1}
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading || streaming}
                className="w-full resize-none px-4 py-2.5 rounded-xl border border-[var(--color-border)]
                           bg-[var(--color-surface)] text-charcoal placeholder-warm-gray-light text-sm
                           outline-none transition-all focus:border-sage-400 focus:ring-2 focus:ring-sage-200/40
                           disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={loading || streaming || !input.trim()}
              className="shrink-0 w-10 h-10 rounded-xl bg-sage-400 text-white flex items-center justify-center
                         transition-all hover:bg-sage-500 active:scale-95
                         disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              {streaming ? (
                <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 11-6.219-8.56" strokeLinecap="round" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}