import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// The API has no CORS, so in dev the browser talks to Vite and Vite forwards /api to the gateway.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_PROXY_TARGET || "http://localhost:8000";
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, "") },
      },
    },
  };
});
