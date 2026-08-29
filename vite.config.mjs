import { defineConfig } from "vite";
import { sites } from "@openai/sites-vite-plugin";

export default defineConfig({
  plugins: [sites()],
  build: {
    target: "es2022",
    ssr: "scripts/sites-worker.mjs",
    outDir: "dist/server",
    emptyOutDir: false,
    rollupOptions: { output: { entryFileNames: "index.js" } },
  },
});
