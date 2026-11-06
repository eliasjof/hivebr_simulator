import { SimClient } from '/src/runtime/client.js'

const q = new URLSearchParams(location.search)
const zip = new URL(q.get('zip') || '/hivebr-py.zip', location.href).href
const client = new SimClient({ zipUrl: zip })
const log = { scene: [], frames: [], stdout: [], stderr: [], finished: [], boot: [], notices: [], restart: 0, fatal: [], ready: [], runStarted: 0 }
window.client = client
window.__log = log
client.on('scene', (s) => log.scene.push(s))
client.on('frame', (f) => {
  log.frames.push({ t: f.t, step: f.step, running: f.running, speed: f.speed, n: f.robots.length })
  if (log.frames.length > 5000) log.frames.splice(0, 2500)
})
client.on('stdout', (m) => log.stdout.push(m.text))
client.on('stderr', (m) => log.stderr.push(m.text))
client.on('finished', (m) => log.finished.push(m))
client.on('boot', (m) => log.boot.push(m.text))
client.on('notice', (m) => log.notices.push(m))
client.on('restart', () => log.restart++)
client.on('fatal', (m) => log.fatal.push(m.message))
client.on('ready', (m) => log.ready.push(m))
client.on('run_started', () => log.runStarted++)
window.__isolated = self.crossOriginIsolated
client.init().catch((e) => log.fatal.push(String(e)))
