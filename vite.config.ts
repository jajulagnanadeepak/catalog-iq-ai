import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  ssrErrorLogger: false,
  serverFnErrorLogger: false,

  tanstackStart: {
    server: { entry: "server" },
  },

  vite: {
    server: {
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          secure: false,
        },
      },
    },
  },
});
