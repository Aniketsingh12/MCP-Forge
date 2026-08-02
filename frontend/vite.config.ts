import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend always talks to a relative `/api`. In dev, proxy it to the
// FastAPI backend. In production the same FastAPI process serves the built
// static files, so `/api` is same-origin and no proxy is needed.
const API_TARGET = process.env.VITE_API_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
  },
});
