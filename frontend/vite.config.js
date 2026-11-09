import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api -> FastAPI backend so the browser has no CORS/host coupling in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // Use 127.0.0.1 (not "localhost"): Node 18 resolves localhost to IPv6 ::1,
        // but uvicorn binds IPv4, which causes ECONNREFUSED ::1:8000.
        target: process.env.BACKEND_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
