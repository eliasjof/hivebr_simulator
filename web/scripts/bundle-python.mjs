// Builds public/hivebr-py.zip with the filesystem layout extracted to /hivebr in Pyodide.
import { zipSync } from 'fflate'
import { readdirSync, readFileSync, writeFileSync, mkdirSync, statSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const web = path.resolve(here, '..')
const repo = path.resolve(web, '..')

const EXCLUDED_DIRS = new Set(['__pycache__', 'tests', 'test', '.pytest_cache'])
const EXCLUDED_FILES = new Set(['explosion.png', 'recharge_place.png', 'default copy.yaml'])

// [source dir, destination prefix inside the zip]
const MAPPINGS = [
  [path.join(repo, 'src', 'hivebr'), 'src/hivebr'],
  [path.join(repo, 'config'), 'config'],
  [path.join(repo, 'examples'), 'examples'],
  [path.join(web, 'templates'), 'templates'],
  [path.join(web, 'python'), 'web'],
]

const files = {}
let count = 0

function walk(dir, prefix) {
  for (const name of readdirSync(dir).sort()) {
    const full = path.join(dir, name)
    const st = statSync(full)
    if (st.isDirectory()) {
      if (EXCLUDED_DIRS.has(name)) continue
      walk(full, `${prefix}/${name}`)
    } else {
      if (EXCLUDED_FILES.has(name) || name.endsWith('.pyc')) continue
      files[`${prefix}/${name}`] = [new Uint8Array(readFileSync(full)), { mtime: new Date(2020, 0, 1) }]
      count++
    }
  }
}

for (const [src, dst] of MAPPINGS) {
  if (!existsSync(src)) {
    console.warn(`[bundle] ignorando diretorio ausente: ${path.relative(repo, src)}`)
    continue
  }
  walk(src, dst)
}

const out = path.join(web, 'public', 'hivebr-py.zip')
mkdirSync(path.dirname(out), { recursive: true })
const zip = zipSync(files, { level: 9 })
writeFileSync(out, zip)
console.log(`[bundle] ${count} arquivos -> public/hivebr-py.zip (${(zip.length / 1024).toFixed(0)} KiB)`)
