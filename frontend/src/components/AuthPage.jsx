import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { login, signup } from "../api";

const SUGGESTIONS = ["calm", "gentle", "present", "open", "whole"];

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [tab, setTab] = useState(location.pathname === "/signup" ? "signup" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (tab === "signup") {
      if (!email || !password || !confirm) {
        setError("Please fill in all fields.");
        return;
      }
      if (password.length < 8) {
        setError("Password must be at least 8 characters.");
        return;
      }
      if (password !== confirm) {
        setError("Passwords do not match.");
        return;
      }
    } else {
      if (!email || !password) {
        setError("Please fill in all fields.");
        return;
      }
    }

    setLoading(true);
    try {
      const data =
        tab === "signup" ? await signup(email, password) : await login(email, password);
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("email", email);
      navigate("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchTab(t) {
    setTab(t);
    setError("");
  }

  return (
    <div className="flex min-h-screen bg-[var(--color-bg)]">
      {/* ─── Decorative panel ─── */}
      <div className="hidden lg:flex lg:w-2/5 flex-col items-center justify-center relative overflow-hidden bg-gradient-to-b from-sage-50 to-cream-100 p-12">
        {/* Floating decor blobs */}
        <div className="absolute top-20 left-10 w-64 h-64 auth-blob bg-sage-200/40" />
        <div
          className="absolute bottom-32 right-10 w-48 h-48 auth-blob bg-sky-200/30"
          style={{ animationDelay: "-4s" }}
        />

        <div className="relative z-10 text-center">
          <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-sage-300 to-sky-300 auth-blob flex items-center justify-center">
            <span className="text-3xl text-white font-light">&#x2726;</span>
          </div>
          <h1 className="text-3xl font-bold text-charcoal mb-3">Sanctuary</h1>
          <p className="text-warm-gray text-lg max-w-sm leading-relaxed">
            A quiet space to reflect, untangle your thoughts, and check in with how you're really doing.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-2">
            {SUGGESTIONS.map((w) => (
              <span
                key={w}
                className="px-3 py-1 rounded-full bg-white/60 text-sm text-warm-gray"
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Form panel ─── */}
      <div className="flex-1 flex items-center justify-center px-6 sm:px-10">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-gradient-to-br from-sage-300 to-sky-300 auth-blob flex items-center justify-center">
              <span className="text-2xl text-white font-light">&#x2726;</span>
            </div>
            <h1 className="text-2xl font-bold text-charcoal">Sanctuary</h1>
          </div>

          {/* Tabs */}
          <div className="flex mb-8 border-b border-[var(--color-border)]">
            <button
              onClick={() => switchTab("login")}
              className={`pb-3 px-4 text-sm font-medium transition-colors relative ${
                tab === "login" ? "text-sage-600" : "text-warm-gray hover:text-charcoal"
              }`}
            >
              Sign In
              {tab === "login" && (
                <motion.div
                  layoutId="tab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-sage-400"
                />
              )}
            </button>
            <button
              onClick={() => switchTab("signup")}
              className={`pb-3 px-4 text-sm font-medium transition-colors relative ${
                tab === "signup" ? "text-sage-600" : "text-warm-gray hover:text-charcoal"
              }`}
            >
              Create Account
              {tab === "signup" && (
                <motion.div
                  layoutId="tab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-sage-400"
                />
              )}
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              <form onSubmit={handleSubmit}>
                {error && (
                  <div className="mb-4 px-4 py-3 rounded-lg bg-rose-300/15 border border-rose-300/30 text-rose-500 text-sm">
                    {error}
                  </div>
                )}

                <div className="space-y-4">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-charcoal mb-1.5">
                      Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoFocus
                      className="w-full px-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-charcoal placeholder-warm-gray-light text-sm outline-none transition-all focus:border-sage-400 focus:ring-2 focus:ring-sage-200/40"
                    />
                  </div>

                  <div>
                    <label htmlFor="password" className="block text-sm font-medium text-charcoal mb-1.5">
                      Password
                    </label>
                    <input
                      id="password"
                      type="password"
                      placeholder={tab === "signup" ? "At least 8 characters" : "Enter your password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-charcoal placeholder-warm-gray-light text-sm outline-none transition-all focus:border-sage-400 focus:ring-2 focus:ring-sage-200/40"
                    />
                  </div>

                  {tab === "signup" && (
                    <div>
                      <label htmlFor="confirm" className="block text-sm font-medium text-charcoal mb-1.5">
                        Confirm Password
                      </label>
                      <input
                        id="confirm"
                        type="password"
                        placeholder="Re-enter your password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-charcoal placeholder-warm-gray-light text-sm outline-none transition-all focus:border-sage-400 focus:ring-2 focus:ring-sage-200/40"
                      />
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="mt-6 w-full py-2.5 rounded-xl bg-sage-400 text-white font-medium text-sm transition-all hover:bg-sage-500 focus:ring-2 focus:ring-sage-300/50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                      {tab === "login" ? "Signing in..." : "Creating account..."}
                    </span>
                  ) : tab === "login" ? (
                    "Sign In"
                  ) : (
                    "Create Account"
                  )}
                </button>
              </form>
            </motion.div>
          </AnimatePresence>

          {/* Mobile switch hint */}
          <p className="mt-8 text-center text-sm text-warm-gray lg:hidden">
            {tab === "login" ? (
              <>
                Don't have an account?{" "}
                <button onClick={() => switchTab("signup")} className="text-sage-500 font-medium hover:underline">
                  Create one
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button onClick={() => switchTab("login")} className="text-sage-500 font-medium hover:underline">
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}