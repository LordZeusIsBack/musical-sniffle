import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://localhost:8000",
      "/chat": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  define: {
    "import.meta.env.VITE_SESSION_ID": JSON.stringify(Date.now().toString()),
  },
});