// End-to-end regression test for panel layout:
// - maximizing a panel must keep it visible and restoring must bring the rest back
// - closing a maximized panel must not leave the app without any panel
// - widening the window after narrow mode must restore the side panels
// - the navigator header button hides it and the rail reopens it
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
const visible = (sel) => page.locator(sel).first().isVisible().catch(() => false)
async function widthOf(sel) {
  const box = await page.locator(sel).first().boundingBox().catch(() => null)
  return box?.width || 0
}
async function openReports() {
  await page.locator('.mb .top:has-text("Exibir"), .mb .top:has-text("View")').first().click()
  await sleep(150)
  await page.locator('.mb .drop[role="menu"] .it:has-text("Relatórios"), .mb .drop[role="menu"] .it:has-text("Reports")').first().click()
  await sleep(300)
}

await page.goto(BASE)
await page.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })
await sleep(300)

await test('maximizing reports keeps it visible and closing restores the panels', async () => {
  await openReports()
  await page.locator('.reports-panel button[aria-label="Maximizar painel"]').click()
  await sleep(300)
  check(await visible('.reports-panel'), 'reports panel disappeared when maximized')
  check(await widthOf('.reports-panel') > 1000, 'maximized reports panel did not fill the window')
  check(!(await visible('.side.left')), 'navigator should be hidden while a panel is maximized')

  await page.locator('.reports-panel button[aria-label="Fechar painel"]').click()
  await sleep(300)
  check(await visible('.side.left'), 'navigator did not come back after closing the maximized reports panel')
  check(await visible('.center'), 'center did not come back after closing the maximized reports panel')
  check(!(await visible('.reports-panel')), 'reports panel should be closed')
  check(await visible('.rail.right[aria-label="Relatórios"]'), 'reports rail is missing, so the panel could not be reopened')

  await page.locator('.rail.right[aria-label="Relatórios"]').first().click()
  await sleep(300)
  check(await visible('.reports-panel'), 'reports panel did not reopen from the rail')
})

await test('closing a maximized code panel restores the navigator and reports', async () => {
  await page.keyboard.press('e') // open the code panel too
  await sleep(300)
  check(await visible('.side.right.code'), 'code panel did not open')
  await page.locator('.side.right.code button[aria-label="Maximizar"]').click()
  await sleep(300)
  check(await visible('.side.right.code'), 'code panel disappeared when maximized')
  check(await widthOf('.side.right.code') > 1000, 'maximized code panel did not fill the window')

  await page.locator('.side.right.code button[aria-label="Recolher painel de código"]').click()
  await sleep(300)
  check(await visible('.side.left'), 'navigator did not come back after collapsing the maximized code panel')
  check(await visible('.reports-panel'), 'reports panel did not come back after collapsing the maximized code panel')
})

await test('widening the window restores the side panels', async () => {
  // Known starting point: navigator and code panel open (reports may also be open).
  await page.keyboard.press('e')
  await sleep(300)
  check(await visible('.side.right.code'), 'code panel should be open before narrowing')

  await page.setViewportSize({ width: 1000, height: 800 })
  await sleep(500)
  check(!(await visible('.side.left')), 'navigator should be collapsed in narrow mode')
  check(await visible('.rail.left'), 'navigator rail should be visible in narrow mode')

  await page.setViewportSize({ width: 1440, height: 900 })
  await sleep(600)
  check(await visible('.side.left'), 'navigator did not come back after widening the window')
  check(await visible('.side.right.code'), 'code panel did not come back after widening the window')
})

await test('navigator header button hides it and the rail reopens it', async () => {
  await page.locator('.nav button[aria-label="Ocultar painel"]').click()
  await sleep(300)
  check(!(await visible('.side.left')), 'navigator is still visible after clicking hide')
  check(await visible('.rail.left'), 'navigator rail is missing after hiding the panel')

  await page.locator('.rail.left').click()
  await sleep(300)
  check(await visible('.side.left'), 'navigator did not reopen from the rail')
})

await test('code and reports panels can grow much wider than the old 720px cap', async () => {
  await page.reload()
  await page.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })
  await sleep(400)
  const dragLeft = async (label, dx) => {
    const sep = page.locator(`[role="separator"][aria-label="${label}"]`)
    const sb = await sep.boundingBox()
    const y = sb.y + sb.height / 2
    await page.mouse.move(sb.x + 2, y)
    await page.mouse.down()
    await page.mouse.move(sb.x + 2 - dx, y, { steps: 8 })
    await page.mouse.up()
    await sleep(300)
  }

  check(await visible('.side.right.code'), 'the code panel should start open')
  await dragLeft('Redimensionar código', 400)
  let w = await widthOf('.side.right.code')
  check(w > 720, `code panel is still capped at ${w}px`)
  check(w < 1300, `code panel swallowed the canvas: ${w}px`)

  await openReports()
  check(await visible('.reports-panel'), 'the reports panel did not open')
  await dragLeft('Redimensionar relatórios', 400)
  w = await widthOf('.reports-panel')
  check(w > 720, `reports panel is still capped at ${w}px`)
  check(w < 1300, `reports panel swallowed the canvas: ${w}px`)
  check(await widthOf('.center') >= 200, 'the simulation panel lost all its room')
})

const failed = results.filter((r) => !r.ok)
if (pageErrors.length) console.log('\nPage errors:\n' + pageErrors.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (pageErrors.length ? `, ${pageErrors.length} page error(s)` : ''))
for (const f of failed) console.log(' - ' + f.name + ': ' + f.err)
await browser.close()
server.close()
process.exit(failed.length || pageErrors.length ? 1 : 0)
