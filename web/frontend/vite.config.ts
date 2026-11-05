import { defineConfig } from 'vite'

import monacoEditorPlugin from 'vite-plugin-monaco-editor'

// Handle CommonJS default export
const plugin = typeof monacoEditorPlugin === 'function' 
  ? monacoEditorPlugin 
  : (monacoEditorPlugin.default || monacoEditorPlugin)

export default defineConfig({
  plugins: [
    plugin({
      languageWorkers: ['editorWorkerService', 'typescript'],
    })
  ],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ['monaco-editor'],
          uplot: ['uplot'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['monaco-editor', 'uplot', 'lz-string', 'js-yaml'],
  },
})