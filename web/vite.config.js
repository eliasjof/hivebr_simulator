import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '..')

const isolationHeaders = {
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Embedder-Policy': 'require-corp',
  'Cross-Origin-Resource-Policy': 'cross-origin',
}

// Re-runs scripts/bundle-python.mjs when Python sources change in dev.
function rebundlePython() {
  const watched = [
    path.join(repoRoot, 'src', 'hivebr'),
    path.join(repoRoot, 'config'),
    path.join(repoRoot, 'examples'),
    path.join(here, 'python'),
    path.join(here, 'templates'),
  ]
  return {
    name: 'hivebr-rebundle-python',
    apply: 'serve',
    // HIVEBR_NO_REBUNDLE=1 disables it (used by the e2e test, which bundles explicitly).
    configureServer(server) {
      if (process.env.HIVEBR_NO_REBUNDLE) return
      let timer = null
      let running = false
      let again = false
      const run = () => {
        if (running) { again = true; return }
        running = true
        const p = spawn(process.execPath, [path.join(here, 'scripts', 'bundle-python.mjs')], { stdio: 'inherit' })
        p.on('exit', () => {
          running = false
          server.ws.send({ type: 'full-reload' })
          if (again) { again = false; run() }
        })
      }
      const onChange = (file) => {
        if (!watched.some((w) => file.startsWith(w + path.sep))) return
        if (/__pycache__|\.pyc$/.test(file)) return
        clearTimeout(timer)
        timer = setTimeout(run, 200)
      }
      for (const w of watched) server.watcher.add(w)
      server.watcher.on('add', onChange)
      server.watcher.on('change', onChange)
      server.watcher.on('unlink', onChange)
    },
  }
}

export default defineConfig({
  base: './',
  plugins: [vue(), rebundlePython()],
  worker: { format: 'es' },
  server: {
    headers: isolationHeaders,
    fs: { allow: [repoRoot] },
  },
  preview: { headers: isolationHeaders },
  build: { target: 'es2022' },
})
