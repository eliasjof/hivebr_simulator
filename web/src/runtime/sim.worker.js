// Worker that hosts Pyodide and runs the hiveBr simulator.
// While Python runs, this thread is blocked: UI commands arrive through the SAB ring.
import { RingReader } from './ring.js'
import { safeFileName } from '../utils/fileNames.js'

let pyodide = null
let reader = null
let interruptView = null
let scipyPromise = null
let scipyDone = false
let runner = null
let running = false

const USER_DIR = '/hivebr/user_scripts'

const send = (type, payload = {}) => self.postMessage({ type, payload })
// `stage` is a stable key the UI translates; `text` is an optional raw detail (package-loader output).
const boot = (stage, progress, text) => send('boot', text ? { stage, progress, text } : { stage, progress })
// Package-loading chatter goes to the boot status only, never to the user's stdout.
const quiet = (stage, progress) => ({
  messageCallback: (text) => boot(stage, progress, String(text)),
  errorCallback: (text) => boot(stage, progress, String(text)),
})

function bytesToBase64(bytes) {
  let bin = ''
  const chunk = 0x8000
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk))
  }
  return btoa(bin)
}

const host = {
  // Python -> UI. `json` is already a JS string (primitive), forwarded untouched.
  post(type, json) {
    self.postMessage({ type: String(type), payload: json })
  },
  poll() {
    // `undefined` (not null) so Python receives None; JS null arrives as JsNull.
    const m = reader ? reader.pop() : null
    return m === null ? undefined : m
  },
  sleep(ms) {
    if (reader) {
      reader.waitForCommand(ms)
    } else {
      const end = performance.now() + Math.min(ms, 4)
      while (performance.now() < end) { /* short busy wait */ }
    }
  },
  now() {
    return performance.now()
  },
}

async function init({ zipUrl, sab, pyodideUrl, clientConfig }) {
  try {
    if (sab) {
      reader = new RingReader(sab.ring, sab.control)
      interruptView = new Uint8Array(sab.interrupt)
    }
    boot('runtime', 0.05)
    const mod = await import(/* @vite-ignore */ `${pyodideUrl}pyodide.mjs`)
    pyodide = await mod.loadPyodide({ indexURL: pyodideUrl })
    pyodide.setStdout({ batched: (text) => send('stdout', { text }) })
    pyodide.setStderr({ batched: (text) => send('stderr', { text }) })

    boot('packages', 0.4)
    await pyodide.loadPackage(['numpy', 'pyyaml', 'pillow'], quiet('packages', 0.4))

    boot('files', 0.8)
    const res = await fetch(zipUrl)
    if (!res.ok) throw new Error(`Failed to download ${zipUrl}: HTTP ${res.status}`)
    const buf = await res.arrayBuffer()
    pyodide.FS.mkdirTree('/hivebr')
    pyodide.unpackArchive(buf, 'zip', { extractDir: '/hivebr' })
    // Keep the pristine bundled config so Python can restore it later. The
    // persisted user config (if any) is written on top of it below.
    try {
      const pristine = pyodide.FS.readFile('/hivebr/config/default.yaml')
      pyodide.FS.writeFile('/hivebr/config/.default.orig.yaml', pristine)
    } catch (e) {
      console.warn('could not keep a copy of the default config', e)
    }
    if (clientConfig && clientConfig.b64) {
      try {
        const path = clientConfig.path && clientConfig.path.startsWith('/')
          ? clientConfig.path
          : '/hivebr/' + (clientConfig.path || 'config/default.yaml').replace(/^\/+/, '')
        pyodide.FS.writeFile(path, Uint8Array.from(atob(clientConfig.b64), (c) => c.charCodeAt(0)))
      } catch (e) {
        send('notice', { level: 'warn', text: `Could not restore the client config (${(e && e.message) || e})` })
      }
    }
    pyodide.runPython(
      "import sys, os\n" +
      "for _p in ('/hivebr', '/hivebr/src', '/hivebr/web'):\n" +
      "    if _p in sys.path: sys.path.remove(_p)\n" +
      "    sys.path.insert(0, _p)\n" +
      "os.chdir('/hivebr')\n",
    )

    if (interruptView) pyodide.setInterruptBuffer(interruptView)

    boot('python', 0.92)
    const hostMod = pyodide.pyimport('hivebr_web.host')
    hostMod.set_host(host)
    hostMod.destroy()
    runner = pyodide.pyimport('hivebr_web.runner')
    runner.boot()

    // The idle editor exists from the start, so the scene can be edited before
    // the first run. It is replaced by the last run simulator when a run ends.
    try {
      const ed = runner.ensure_editor()
      if (ed && ed.destroy) ed.destroy()
    } catch (e) {
      send('notice', { level: 'warn', code: 'editor_failed', params: { error: String((e && e.message) || e) }, text: `Could not create the editor (${(e && e.message) || e})` })
    }

    send('ready', { pyodide_version: pyodide.version, interactive: !!reader })

    // scipy is imported by the occupancy-grid code while Python is blocked, so it
    // must already be loaded by then.
    scipyPromise = pyodide.loadPackage('scipy', quiet('scipy', 0.97)).then(() => { scipyDone = true; boot('done', 1) }, (e) => {
      scipyDone = true
      boot('done', 1)
      send('notice', { level: 'warn', code: 'scipy_failed', params: { error: String((e && e.message) || e) }, text: `scipy failed to load (${(e && e.message) || e})` })
    })
  } catch (e) {
    send('fatal', { message: String((e && e.message) || e) })
  }
}

// Editor tabs are written to a dedicated folder so the entry script can import
// its siblings (`from my_module import ...`). The folder is cleared every run,
// so removing a tab also removes the module. Helper extensions (.json, .csv,
// .txt…) are kept so scripts can read them too.
const safeName = safeFileName

function syncUserFiles(files, mainName, mainCode) {
  pyodide.FS.mkdirTree(USER_DIR)
  for (const name of pyodide.FS.readdir(USER_DIR)) {
    if (name === '.' || name === '..') continue
    try { pyodide.FS.unlink(`${USER_DIR}/${name}`) } catch { /* ignore */ }
  }
  const written = new Set()
  for (const f of files || []) {
    if (!f || typeof f.code !== 'string') continue
    const name = safeName(f.name)
    if (written.has(name)) continue
    written.add(name)
    pyodide.FS.writeFile(`${USER_DIR}/${name}`, f.code, { encoding: 'utf8' })
  }
  const main = safeName(mainName)
  pyodide.FS.writeFile(`${USER_DIR}/${main}`, String(mainCode ?? ''), { encoding: 'utf8' })
  return main
}

async function run({ code, autostart, files, mainName }) {
  running = true
  try {
    if (!scipyDone && scipyPromise) {
      boot('scipy', 0.97)
      await scipyPromise
    }
    const main = syncUserFiles(files, mainName, code)
    const scan = [code, ...(files || []).map((f) => f?.code)].filter((s) => typeof s === 'string').join('\n')
    try {
      await pyodide.loadPackagesFromImports(scan, quiet('imports', 0.98))
    } catch (e) {
      send('notice', { level: 'warn', code: 'packages_failed', params: { error: String((e && e.message) || e) }, text: `Packages not loaded (${(e && e.message) || e})` })
    }
    boot('done', 1)
    if (interruptView) interruptView[0] = 0
    send('run_started', {})
    let result
    try {
      const json = runner.run_user_code(code, !!autostart, main)
      result = JSON.parse(json)
    } catch (e) {
      result = {
        ok: false, stopped: false, files: [],
        error: { type: 'PythonError', message: String((e && e.message) || e), traceback: String((e && e.message) || e), line: null },
      }
    }
    if (interruptView) interruptView[0] = 0
    // Discard commands left over from this run.
    if (reader) while (reader.pop() !== null) { /* drain */ }
    send('finished', result)
  } catch (e) {
    send('fatal', { message: String((e && e.message) || e) })
  } finally {
    running = false
  }
}

// Idle editing: the Python side owns the editor simulator, so this only needs
// to forward one command (the reply arrives as scene/frame messages).
function edit({ cmd }) {
  if (!runner || running) return
  try {
    runner.dispatch_edit(JSON.stringify(cmd))
  } catch (e) {
    send('notice', { level: 'warn', code: 'edit_failed', params: { error: String((e && e.message) || e) }, text: `Edit failed (${(e && e.message) || e})` })
  }
}

// Forget the edits made while idle and rebuild the editor from the config, so
// the next run starts from the scene defined by the user's script alone.
function resetEdits() {
  if (!runner || running) return
  try {
    runner.reset_edits()
  } catch (e) {
    send('notice', { level: 'warn', code: 'edit_reset_failed', params: { error: String((e && e.message) || e) }, text: `Could not reset the scene (${(e && e.message) || e})` })
  }
}

function readFile({ id, path }) {
  try {
    const bytes = pyodide.FS.readFile(path)
    send('file_content', { id, b64: bytesToBase64(bytes) })
  } catch (e) {
    send('file_content', { id, b64: null, error: String((e && e.message) || e) })
  }
}

// Validates YAML in Python, writes it to the client FS and reports back. Also
// goes through `client_config`, so the UI persists it for the next boot.
function writeConfig({ yaml, path }) {
  try {
    if (typeof yaml !== 'string') throw new Error('invalid YAML text')
    const target = path || '/hivebr/config/default.yaml'
    if (!/^\/hivebr\/config\/[^/]+\.ya?ml$/i.test(target)) throw new Error(`invalid config path: ${target}`)
    pyodide.globals.set('_hivebr_yaml_text', yaml)
    pyodide.globals.set('_hivebr_yaml_path', target)
    pyodide.runPython(
      "import yaml\n" +
      "try:\n" +
      "    _hivebr_cfg = yaml.safe_load(_hivebr_yaml_text)\n" +
      "    if not isinstance(_hivebr_cfg, dict):\n" +
      "        raise ValueError('the YAML root must be a mapping')\n" +
      "    with open(_hivebr_yaml_path, 'w', encoding='utf-8') as _f:\n" +
      "        _f.write(_hivebr_yaml_text)\n" +
      "    _hivebr_err = ''\n" +
      "except Exception as _e:\n" +
      "    _hivebr_err = f'{type(_e).__name__}: {_e}'\n",
    )
    const err = pyodide.globals.get('_hivebr_err')
    if (err) {
      send('config_write', { ok: false, error: String(err) })
      return
    }
    send('client_config', { path: target, b64: bytesToBase64(pyodide.FS.readFile(target)) })
    send('config_write', { ok: true, path: target })
  } catch (e) {
    send('config_write', { ok: false, error: String((e && e.message) || e) })
  }
}

self.onmessage = (ev) => {
  const m = ev.data
  if (!m) return
  switch (m.type) {
    case 'init': init(m); break
    case 'run': run(m); break
    case 'edit': edit(m); break
    case 'reset_edits': resetEdits(); break
    case 'read_file': readFile(m); break
    case 'write_config': writeConfig(m); break
  }
}
