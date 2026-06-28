import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

const currentSessionId = import.meta.env.VITE_SESSION_ID;
const storedSessionId = localStorage.getItem("session_id");
if (storedSessionId !== currentSessionId) {
  localStorage.removeItem("token");
  localStorage.removeItem("email");
  localStorage.setItem("session_id", currentSessionId || "");
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);