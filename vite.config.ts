import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        format: 'es', // ✅ important!
      },
    },
  },
  worker: {
    format: 'es', // ✅ this tells Vite to use ES modules for workers
  },
})
