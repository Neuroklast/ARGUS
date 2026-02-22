import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://localhost:7373",
      "/ws": {
        target: "ws://localhost:7373",
        ws: true,
      },
    },
  },
  build: {
    outDir: "../src/static",
    emptyOutDir: true,
  },
});
