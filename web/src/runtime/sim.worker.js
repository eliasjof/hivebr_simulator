// Worker that hosts Pyodide and runs the hiveBr simulator.
// While Python runs, this thread is blocked: UI commands arrive through the SAB ring.
import { RingReader } from './ring.js'

let pyodide = null
let reader = null
let interruptView = null
let scipyPromise = null
let scipyDone = false
let runner = null

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

async function init({ zipUrl, sab, pyodideUrl }) {
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

async function run({ code, autostart }) {
  try {
    if (!scipyDone && scipyPromise) {
      boot('scipy', 0.97)
      await scipyPromise
    }
    try {
      await pyodide.loadPackagesFromImports(code, quiet('imports', 0.98))
    } catch (e) {
      send('notice', { level: 'warn', code: 'packages_failed', params: { error: String((e && e.message) || e) }, text: `Packages not loaded (${(e && e.message) || e})` })
    }
    boot('done', 1)
    if (interruptView) interruptView[0] = 0
    send('run_started', {})
    let result
    try {
      const json = runner.run_user_code(code, !!autostart)
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

self.onmessage = (ev) => {
  const m = ev.data
  if (!m) return
  switch (m.type) {
    case 'init': init(m); break
    case 'run': run(m); break
    case 'read_file': readFile(m); break
  }
}
