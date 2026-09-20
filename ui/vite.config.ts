import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5174,
    proxy: { "/api": "http://127.0.0.1:7420" },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
