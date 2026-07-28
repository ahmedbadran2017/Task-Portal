import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Per-machine proxy target. Defaults to production so the existing workflow
  // keeps working; point FRAPPE_DEV_URL at a local bench for offline dev.
  const target = env.FRAPPE_DEV_URL || process.env.FRAPPE_DEV_URL || "https://admin.justyol.com";

  return {
    plugins: [vue()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    build: {
      outDir: "../task_hub/public",
      emptyOutDir: false,
      target: "es2015",
      // Frappe's Jinja shell hard-codes one JS + one CSS filename — keep the
      // whole SPA in a single bundle.
      cssCodeSplit: false,
      rollupOptions: {
        input: path.resolve(__dirname, "src/main.js"),
        output: {
          entryFileNames: "task_hub.bundle.js",
          assetFileNames: "task_hub.bundle.css",
          inlineDynamicImports: true,
        },
      },
    },
    server: {
      port: 8083,
      proxy: {
        "^/(api|login|app|assets|socket\\.io)": {
          target,
          changeOrigin: true,
          secure: false,
          cookieDomainRewrite: { "*": "" },
          followRedirects: true,
        },
      },
    },
  };
});
