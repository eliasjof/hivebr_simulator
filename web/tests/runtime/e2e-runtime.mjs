// End-to-end runtime test: Vite dev server + headless Chromium + real Pyodide from the CDN.
// Uses the real Python runner when web/python/hivebr_web/runner.py exists; otherwise a
// minimal fake runner (tests/runtime/fake_py) is bundled instead and the run says so.
import { chromium } from 'playwright-core'
import { spawn } from 'node:child_process'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { zipSync } from 'fflate'

const here = path.dirname(fileURLToPath(import.meta.url))
const web = path.resolve(here, '../..')
const PORT = 5199
const COI_PORT = 5198
const base = `http://localhost:${PORT}`
const realRunner = path.join(web, 'python', 'hivebr_web', 'runner.py')

async function waitFor(fn, ms, label) {
  const t0 = Date.now()
  for (;;) {
    const v = await fn()
    if (v) return v
    if (Date.now() - t0 > ms) throw new Error(`timeout: ${label}`)
    await new Promise((r) => setTimeout(r, 100))
  }
}

// Waits briefly for the Python agent's files.
let real = false
for (let i = 0; i < 20 && !(real = fs.existsSync(realRunner)); i++) await new Promise((r) => setTimeout(r, 500))
console.log(real ? 'MODE: real Python runtime (web/python)' : 'MODE: FAKE python runtime (web/python/hivebr_web/runner.py not found)')

let zipPath = '/hivebr-py.zip'
const fakeZip = path.join(here, 'fake-py.zip')
if (real) {
  await new Promise((res, rej) => spawn(process.execPath, [path.join(web, 'scripts/bundle-python.mjs')], { stdio: 'inherit' }).on('exit', (c) => (c ? rej(new Error('bundle failed')) : res())))
} else {
  const files = {}
  const root = path.join(here, 'fake_py')
  for (const f of fs.readdirSync(path.join(root, 'hivebr_web'))) {
    if (f.endsWith('.py')) files[`web/hivebr_web/${f}`] = new Uint8Array(fs.readFileSync(path.join(root, 'hivebr_web', f)))
  }
  fs.writeFileSync(fakeZip, zipSync(files))
  zipPath = '/tests/runtime/fake-py.zip'
}

const vite = spawn(process.execPath, [path.join(web, 'node_modules/vite/bin/vite.js'), '--port', String(PORT), '--strictPort'], { cwd: web, env: { ...process.env, HIVEBR_NO_REBUNDLE: '1' }, stdio: ['ignore', 'pipe', 'pipe'] })
vite.stdout.on('data', () => {})
vite.stderr.on('data', (d) => process.stderr.write(d))

// Static server without isolation headers, to exercise coi-sw.js.
const coiServer = http.createServer((req, res) => {
  const u = req.url.split('?')[0]
  const f = u === '/coi.html' ? path.join(here, 'coi.html') : path.join(web, 'public', u)
  if (!f.startsWith(web) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end() }
  res.writeHead(200, { 'Content-Type': f.endsWith('.js') ? 'text/javascript' : 'text/html' })
  res.end(fs.readFileSync(f))
}).listen(COI_PORT)

let browser
const results = []
const ok = (name) => { results.push(name); console.log('  ok -', name) }
let failed = null

try {
  await waitFor(async () => { try { return (await fetch(base + '/')).ok } catch { return false } }, 30000, 'vite up')
  browser = await chromium.launch({ executablePath: '/usr/bin/chromium-browser', headless: true, args: ['--no-sandbox'] })

  // --- coi-sw on a host without headers ---
  {
    const ctx = await browser.newContext()
    const p = await ctx.newPage()
    await p.goto(`http://localhost:${COI_PORT}/coi.html`)
    await p.waitForFunction(() => self.crossOriginIsolated === true, null, { timeout: 15000 })
    assert.equal(await p.evaluate(() => typeof SharedArrayBuffer), 'function')
    await p.waitForTimeout(1500)
    assert.equal(await p.evaluate(() => self.crossOriginIsolated), true)
    ok('coi-sw.js makes a header-less static host crossOriginIsolated (single reload)')
    await ctx.close()
  }

  const ctx = await browser.newContext()
  const page = await ctx.newPage()
  page.on('framenavigated', (f) => { if (f.parentFrame() === null) console.log('  [nav]', f.url()) })
  page.on('pageerror', (e) => console.log('  [pageerror]', e.message))
  await page.goto(`${base}/tests/runtime/e2e.html?zip=${encodeURIComponent(zipPath)}`)
  assert.equal(await page.evaluate(() => self.crossOriginIsolated), true)
  ok('crossOriginIsolated is true under vite dev headers')

  await page.waitForFunction(() => window.__log.ready.length > 0 || window.__log.fatal.length > 0, null, { timeout: 240000 })
  const fatal = await page.evaluate(() => window.__log.fatal)
  assert.deepEqual(fatal, [], 'fatal during boot: ' + fatal)
  const ready = await page.evaluate(() => window.__log.ready[0])
  assert.equal(ready.interactive, true)
  ok(`booted, pyodide ${ready.pyodide_version}, interactive=true`)

  const L = (fn, arg) => page.evaluate(fn, arg)
  const waitLog = (expr, ms, label) => page.waitForFunction(expr, null, { timeout: ms }).catch(() => { throw new Error('timeout: ' + label) })

  // --- script 1: real/fake run with commands ---
  const userCode = real
    ? `from hivebr import HiveBrAgent, SwarmExperiment

class Patrol(HiveBrAgent):
    def loop(self, state, neighbors):
        return 0.5, 0.0

exp = SwarmExperiment(robots=1, backend="navsim2d")
exp.assign_agent(robot_ids=[0], agent_class=Patrol)
exp.assign_route(0, [[5, 2, 0.0], [5, 6, 0.0]])
print("antes do run")
exp.run()
print("depois do run")
`
    : `print("antes do run")\nfake_run()\nprint("depois do run")\n`
  const runP = page.evaluate((c) => { window.__runP = window.client.run(c, { autostart: true }); return true }, userCode)
  await runP
  await waitLog(() => window.__log.scene.length > 0, 120000, 'scene')
  ok('scene received')
  await waitLog(() => window.__log.frames.length > 10 || window.__log.finished.length > 0, 60000, 'frames').catch(async (e) => { console.log(JSON.stringify(await L(() => ({ ...window.__log, frames: window.__log.frames.length })))); throw e })
  const fr = await L(() => window.__log.frames)
  if (!fr.length) console.log(JSON.stringify(await L(() => ({ f: window.__log.finished, e: window.__log.stderr }))))
  const moving = fr[fr.length - 1].t > fr[0].t
  assert.ok(moving, 'frame time does not advance')
  ok(`frames arrive and t advances (${fr.length} frames, t ${fr[0].t} -> ${fr[fr.length - 1].t})`)
  assert.ok((await L(() => window.__log.stdout)).includes('antes do run'))
  ok('stdout forwarded')

  assert.equal(await L(() => window.client.send({ cmd: 'pause' })), true)
  await waitLog(() => window.__log.frames.slice(-3).some((f) => f.running === false), 20000, 'paused frame')
  const stepA = await L(() => window.__log.frames.at(-1).step)
  await page.waitForTimeout(600)
  const stepB = await L(() => window.__log.frames.at(-1).step)
  assert.ok(stepB - stepA <= 1, `still stepping while paused (${stepA} -> ${stepB})`)
  ok('pause freezes the simulation')

  await L(() => window.client.send({ cmd: 'start' }))
  await L(() => window.client.send({ cmd: 'set_speed', factor: 2 }))
  await waitLog(() => window.__log.frames.slice(-3).every((f) => f.speed === 2 && f.running), 20000, 'speed 2')
  ok('set_speed applied and start resumes')

  const t0 = Date.now()
  const fin = await L(async () => { window.client.stop(); return await window.__runP })
  assert.equal(fin.ok, true, 'finished not ok: ' + JSON.stringify(fin.error))
  assert.ok((await L(() => window.__log.stdout)).includes('depois do run'))
  assert.equal(await L(() => window.client.state), 'ready')
  assert.equal(await L(() => window.__log.restart), 0)
  ok(`stop -> finished ok, code after run() executed (${Date.now() - t0} ms)`)

  // --- script 2: busy loop interrupted by level 2 ---
  const t1 = Date.now()
  const fin2 = await L(async () => {
    const p = window.client.run('print("loop")\nwhile True: pass\n')
    await new Promise((r) => setTimeout(r, 800))
    window.client.stop()
    return await p
  })
  const dt2 = Date.now() - t1
  assert.equal(fin2.stopped, true, 'expected stopped=true: ' + JSON.stringify(fin2))
  assert.equal(await L(() => window.__log.restart), 0, 'worker should not restart')
  assert.equal(await L(() => window.client.state), 'ready')
  assert.ok(dt2 > 1400 && dt2 < 5000, 'interrupt timing ' + dt2)
  ok(`while True: pass stopped by interrupt (${dt2} ms, stopped=${fin2.stopped}, ok=${fin2.ok})`)

  // --- script 3: swallows KeyboardInterrupt -> terminate + reboot ---
  const code3 = 'while True:\n    try:\n        while True: pass\n    except BaseException:\n        pass\n'
  const t2 = Date.now()
  const fin3b = await page.evaluate(async (c) => {
    const p = window.client.run(c)
    await new Promise((r) => setTimeout(r, 500))
    window.client.stop()
    return await p
  }, code3)
  assert.equal(fin3b.stopped, true)
  assert.equal(await L(() => window.__log.restart), 1)
  await page.waitForFunction(() => window.client.state === 'ready', null, { timeout: 240000 })
  ok(`unresponsive code terminated and runtime rebooted (${Date.now() - t2} ms)`)

  // --- run again after reboot ---
  const fin4 = await page.evaluate(() => window.client.run('print("ola")'))
  assert.equal(fin4.ok, true)
  assert.ok((await L(() => window.__log.stdout)).includes('ola'))
  ok('run works after reboot')
} catch (e) {
  failed = e
  console.error('FAILED:', e.stack || e)
} finally {
  if (browser) await browser.close()
  vite.kill()
  coiServer.close()
  if (fs.existsSync(fakeZip)) fs.unlinkSync(fakeZip)
}
console.log(`\n${results.length} checks passed${failed ? ', 1 FAILED' : ''}`)
process.exit(failed ? 1 : 0)
