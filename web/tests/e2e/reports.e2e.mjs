// End-to-end regression test for report export (HTML / Markdown / PDF).
// Guards against the export handlers receiving the click event as the report
// argument, which produced blank files and a blank print preview.
// The site is served from /hivebr/ like the real deployment.
import http from 'node:http'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(here, '..', '..', 'dist')
const SHOTS = process.env.E2E_SHOTS || path.join(os.tmpdir(), 'hivebr-e2e-reports')
const CHROMIUM = process.env.CHROMIUM
  || (process.platform === 'win32' ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' : '/usr/bin/chromium-browser')
fs.mkdirSync(SHOTS, { recursive: true })

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
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'pt-BR', acceptDownloads: true })
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

async function downloadText(clickLocator, timeout = 15000) {
  const pending = page.waitForEvent('download', { timeout }).catch(() => null)
  await clickLocator.click()
  const dl = await pending
  if (!dl) throw new Error('no download event')
  return fs.readFileSync(await dl.path(), 'utf8')
}

await page.goto(BASE)
await page.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })

// Open the reports panel through View > Relatórios.
await page.locator('.mb .top:has-text("Exibir"), .mb .top:has-text("View")').first().click()
await sleep(200)
await page.locator('.mb .drop[role="menu"] .it:has-text("Relatórios"), .mb .drop[role="menu"] .it:has-text("Reports")').first().click()
await sleep(400)

await test('HTML export contains the report body, not an empty page', async () => {
  await page.locator('button:has-text("boas_vindas.md")').first().click()
  await page.locator('.md-preview').waitFor({ timeout: 10000 })
  const html = await downloadText(page.locator('button[data-tip="Export HTML"]'))
  check(html.includes('Bem-vindo'), `exported HTML is missing the report heading (${html.length} bytes)`)
  check(html.includes('Comece a escrever'), 'exported HTML is missing the report body')
  check(html.includes('Gerado no hiveBr Web'), 'exported HTML is missing the footer')
})

await test('Markdown export contains the report source', async () => {
  const md = await downloadText(page.locator('button[data-tip="Export .md"]'))
  check(md.includes('Bem-vindo'), `exported Markdown is blank (${md.length} bytes)`)
})

await test('PDF export renders the report into the print document', async () => {
  await page.locator('button[data-tip="Export PDF"]').click()
  await sleep(1200)
  const info = await page.evaluate(() => {
    const frame = document.querySelector('iframe[data-hivebr-print]')
    const d = frame?.contentDocument
    return { text: d?.body?.innerText || '', bytes: d?.documentElement?.outerHTML?.length || 0 }
  })
  check(info.text.includes('Bem-vindo'), `print document body is blank (${info.bytes} bytes)`)
  check(info.text.includes('Comece a escrever'), 'print document is missing the report body')
})

await test('template report exports with tables and sections', async () => {
  await page.locator('button[aria-label="Novo relatório"]').click()
  const modal = page.locator('[role="dialog"]:has-text("Novo Relatório")')
  await modal.waitFor({ timeout: 5000 })
  await modal.locator('button:has-text("Criar")').click()
  await sleep(600)
  const html = await downloadText(page.locator('button[data-tip="Export HTML"]'))
  check(html.includes('<table'), 'template export has no table')
  check(html.includes('1. Robôs'), 'template export is missing its sections')
  check(html.length > 2000, `template export looks truncated (${html.length} bytes)`)
})

const failed = results.filter((r) => !r.ok)
if (pageErrors.length) console.log('\nPage errors:\n' + pageErrors.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (pageErrors.length ? `, ${pageErrors.length} page error(s)` : ''))
for (const f of failed) console.log(' - ' + f.name + ': ' + f.err)
await browser.close()
server.close()
process.exit(failed.length || pageErrors.length ? 1 : 0)
