import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      // Vite's file watcher must not touch src-tauri/target: cargo locks/
      // rewrites files there while building (e.g. the tauri-plugin-log
      // build script exe), which crashes the watcher with EBUSY and kills
      // `tauri dev` entirely. This is the standard Tauri + Vite guidance.
      ignored: ['**/src-tauri/**'],
    },
  },
})
