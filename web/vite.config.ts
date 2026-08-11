import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 单进程部署：构建到 ../web/dist 由 FastAPI StaticFiles 挂载
// Electron 生产模式：base: './' 确保 file:// 加载时资源路径正确
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
