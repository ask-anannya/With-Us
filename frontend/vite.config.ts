import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend runs on 8787 by default (8000 is often taken). Override with API_PORT.
const apiPort = process.env.API_PORT ?? "8787";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": `http://127.0.0.1:${apiPort}` },
  },
});
