import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// On-prem kurulumda Node çalışma zamanı istemiyoruz: Vite statik dosya üretir,
// üretimde bu dosyalar FastAPI tarafından servis edilir (bkz. §3).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Geliştirmede CORS'a takılmamak için API istekleri backend'e iletilir.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
