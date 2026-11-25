import { readFileSync } from "fs"
import path from "path"

import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
// Where the dev/preview proxy forwards /api. Override for a different
// local port (the Playwright suite runs the API on 8010).
const API_TARGET = process.env.VITE_PROXY_TARGET || "http://localhost:8000"

// Build identity, injected so the app can show what is running and when
// it was built. Render sets RENDER_GIT_COMMIT on every build; fall back
// to a local marker for dev machines.
const pkg = JSON.parse(readFileSync(path.resolve(__dirname, "./package.json"), "utf8"))
const BUILD_INFO = {
  version: pkg.version,
  commit: process.env.RENDER_GIT_COMMIT || process.env.COMMIT_REF || "local",
  time: new Date().toISOString(),
}

export default defineConfig({
  define: {
    __BUILD__: JSON.stringify(BUILD_INFO),
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  // `vite preview` serves the production build but does not inherit
  // `server.proxy`. Without this the built bundle's relative "/api/v1" base
  // URL is served by the preview server itself and every API call answers
  // with the SPA shell instead of JSON.
  preview: {
    port: 4173,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-table': ['@tanstack/react-table'],
          'vendor-virtual': ['@tanstack/react-virtual'],
          'vendor-radix': [
            '@radix-ui/react-checkbox',
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-label',
            '@radix-ui/react-popover',
            '@radix-ui/react-progress',
            '@radix-ui/react-slot',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip',
          ],
          'vendor-dates': ['date-fns'],
          'vendor-ui': ['lucide-react', 'sonner', 'clsx', 'class-variance-authority', 'tailwind-merge'],
          'vendor-utils': ['axios', 'cmdk'],
        },
      },
    },
    chunkSizeWarningLimit: 500,
  },
})
