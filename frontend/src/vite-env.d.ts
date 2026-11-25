/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** Build identity injected by `vite.config.ts` (see `define.__BUILD__`). */
declare const __BUILD__: {
  version: string
  commit: string
  time: string
}
