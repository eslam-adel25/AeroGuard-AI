import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          secure: false,
        },
        "/ws": {
          target,
          changeOrigin: true,
          secure: false,
          ws: true,
        },
        "/uploads": {
          target,
          changeOrigin: true,
          secure: false,
        },
        "/go2rtc": {
          target: "http://127.0.0.1:1984",
          changeOrigin: true,
          ws: true,
          rewrite: (path) => path.replace(/^\/go2rtc/, ""),
          rewriteWsOrigin: true,
        },
      },
    },
  };
});
