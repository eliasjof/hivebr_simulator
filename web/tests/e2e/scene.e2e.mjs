// End-to-end test for Restart scene: user edits made while idle are discarded
// and the active script runs again, restoring the scene from the run file.
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(here, '..', '..', 'dist')
const CHROMIUM = process.env.CHROMIUM
  || (process.platform === 'win32' ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' : '/usr/bin/chromium-browser')
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.zip': 'application/zip', '.png': 'image/png', '.json': 'application/json', '.svg': 'image/svg+xml' }
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x')
  if (url.pathname === '/hivebr') { res.writeHead(301, { Location: '/hivebr/' }); return res.end() }
  if (!url.pathname.startsWith('/hivebr/')) { res.writeHead(404); return res.end('not found') }
  const rel = decodeURIComponent(url.pathname.slice('/hivebr/'.length)) || 'index.html'
  const file = path.resolve(dist, rel)
  if (!file.startsWith(dist) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('not found') }
  res.writeHead(200, {
    'Content-Type': MIME[path.extname(file)] || 'application/octet-stream',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp',
  })
  fs.createReadStream(file).pipe(res)
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const BASE = `http://127.0.0.1:${server.address().port}/hivebr/`

const browser = await chromium.launch({ executablePath: CHROMIUM, headless: true, args: ['--no-sandbox'] })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'pt-BR' })
await ctx.addInitScript(() => { try { localStorage.clear() } catch { /* ignore */ } })
const page = await ctx.newPage()
const pageErrors = []
page.on('pageerror', (e) => pageErrors.push('pageerror: ' + e.message))
page.on('console', (m) => { if (m.type() === 'error') pageErrors.push('console.error: ' + m.text()) })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
function check(cond, msg) { if (!cond) throw new Error('assertion failed: ' + msg) }
const results = []
async function test(name, fn) {
  try { await fn(); results.push({ name, ok: true }); console.log('  ok', name) }
  catch (e) { results.push({ name, ok: false, err: e.message }); console.log('  FAIL', name, '-', e.message) }
}
const pillText = async () => ((await page.locator('[data-testid="pill"]').textContent()) || '').trim()
const count = async (name) => Number((((await page.locator(`[data-testid="cnt-${name}"]`).textContent()) || '0').trim()))
async function waitCount(name, pred, timeout = 15000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (pred(await count(name))) return
    await sleep(150)
  }
  throw new Error(`count ${name} did not reach the expectation (now ${await count(name)})`)
}
async function waitPill(re, timeout = 60000) {
  await page.waitForFunction((src) => new RegExp(src, 'i').test(document.querySelector('[data-testid="pill"]')?.textContent || ''), re.source, { timeout })
}
async function loadQuickStart() {
  await page.locator('.tb').getByRole('button', { name: /^Exemplos/ }).click()
  const modal = page.locator('[aria-modal="true"]')
  const card = modal.locator('.card', { has: page.locator('h3', { hasText: /^Início rápido$/ }) })
  await card.getByRole('button', { name: 'Carregar no editor' }).click()
  const replace = page.getByRole('button', { name: 'Substituir' })
  if (await replace.isVisible().catch(() => false)) await replace.click()
  await modal.waitFor({ state: 'detached' })
}
async function run() {
  await page.locator('.tb').getByRole('button', { name: /^Executar/ }).click()
  await waitPill(/executando|pausado/, 60000)
}
async function stop() {
  if (/pronto/i.test(await pillText())) return
  await page.locator('.tb').getByRole('button', { name: /^Parar/ }).click()
  await waitPill(/pronto/, 30000)
}

await page.goto(BASE)
await page.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })

await test('restart scene discards canvas edits and reruns the active script', async () => {
  await loadQuickStart()
  await run()
  await waitCount('waypoints', (n) => n === 4)
  const baseline = { obstacles: await count('obstacles'), waypoints: await count('waypoints') }
  await stop()

  const box = await page.locator('.cv canvas').first().boundingBox()
  await page.locator('.tb').getByRole('radio', { name: 'Obstáculo' }).click()
  await page.mouse.click(box.x + box.width * 0.35, box.y + box.height * 0.4)
  await page.locator('#pf-r').waitFor({ timeout: 5000 })
  await page.locator('#pf-r').fill('0.5')
  await page.keyboard.press('Enter')
  await waitCount('obstacles', (n) => n === baseline.obstacles + 1)

  await page.locator('.tb').getByRole('radio', { name: 'Waypoint' }).click()
  await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.6)
  await waitCount('waypoints', (n) => n === baseline.waypoints + 1)
  await page.locator('.tb').getByRole('radio', { name: 'Selecionar' }).click()

  await page.locator('button[aria-label="Reiniciar cena"]').click()
  const modal = page.locator('[role="dialog"]:has-text("Reiniciar a cena")')
  await modal.waitFor({ timeout: 5000 })
  await modal.getByRole('button', { name: 'Reiniciar cena' }).click()

  // It runs the active script again, so the run-file scene comes back.
  await waitPill(/executando|pausado/, 60000)
  await waitCount('obstacles', (n) => n === baseline.obstacles, 20000)
  await waitCount('waypoints', (n) => n === baseline.waypoints, 20000)
  check(await page.locator('.banner.err').count() === 0, 'restart must not leave an error banner')
  await stop()
})

await test('Simulation menu offers restart scene and restart page', async () => {
  await page.locator('[data-menu="sim"]').click()
  check(await page.getByRole('menuitem', { name: 'Reiniciar cena' }).isVisible(), 'missing "Reiniciar cena" menu item')
  check(await page.getByRole('menuitem', { name: 'Reiniciar página' }).isVisible(), 'missing "Reiniciar página" menu item')
  await page.keyboard.press('Escape')
})

const failed = results.filter((r) => !r.ok)
if (pageErrors.length) console.log('\nPage errors:\n' + pageErrors.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (pageErrors.length ? `, ${pageErrors.length} page error(s)` : ''))
for (const f of failed) console.log(' - ' + f.name + ': ' + f.err)
await browser.close()
server.close()
process.exit(failed.length || pageErrors.length ? 1 : 0)
