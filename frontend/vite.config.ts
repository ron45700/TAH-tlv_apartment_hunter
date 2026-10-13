import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The site's front end (PHASE_3.md 3.7 (l)). The build goes to frontend/dist, which FastAPI serves
// beside /api on one origin (tlv_hunter/web/app.py). In development, `npm run dev` proxies /api to
// `serve` on 127.0.0.1:8000. Every font file is kept as a file (no data: inlining), so the
// unicode-range of each subset loads only the files the page uses.
export default defineConfig({
  plugins: [react()],
  build: {
    assetsInlineLimit: 0,
  },
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000' },
    },
  },
  test: {
    environment: 'node',
  },
})
