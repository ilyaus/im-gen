import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = "http://127.0.0.1:8085";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/jobs": backend,
      "/models": backend,
      "/config": backend,
      "/health": backend,
      "/llm": backend,
    },
  },
});
