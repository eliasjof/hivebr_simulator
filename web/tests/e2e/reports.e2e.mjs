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

await test('export works while the reports panel is maximized', async () => {
  await page.locator('.reports-panel button[aria-label="Maximizar painel"]').click()
  await sleep(300)
  check(await page.locator('.reports-panel').isVisible(), 'reports panel is not visible after maximizing')
  const html = await downloadText(page.locator('button[data-tip="Export HTML"]'))
  check(html.includes('1. Robôs'), `maximized export is missing the report body (${html.length} bytes)`)
  await page.locator('.reports-panel button[aria-label="Restaurar painel"]').click()
  await sleep(300)
})

await test('IFMG template renders the institutional header and exports themed', async () => {
  await page.locator('.reports-panel button[aria-label="Novo relatório"]').click()
  const modal = page.locator('[role="dialog"]:has-text("Novo Relatório")')
  await modal.waitFor({ timeout: 5000 })
  await modal.locator('.template-card:has-text("Relatório IFMG")').click()
  await modal.locator('button:has-text("Criar")').click()
  await sleep(700)

  check(await page.locator('.md-preview.tpl-ifmg').count() === 1, 'preview is missing the IFMG template class')
  const source = await page.locator('.md-editor').inputValue()
  check(source.startsWith('<!-- ifmg-header -->'), `IFMG source does not start with the header marker: ${source.slice(0, 40)}`)
  check(!source.includes('data:image/png;base64'), 'IFMG source still embeds the logo data URI')
  check(source.length < 3000, `IFMG source is unexpectedly large (${source.length} bytes)`)
  const preview = page.locator('.md-preview.tpl-ifmg').first()
  const text = await preview.innerText()
  for (const s of ['INSTITUTO FEDERAL DE MINAS GERAIS', 'Data', 'Professor(a)', 'Matéria', 'Turma',
    'Estudante(s)', '1) Introdução', '2) Desenvolvimento', '3) Resultados e Discussão', '4) Conclusão', '5) Referências']) {
    check(text.includes(s), `IFMG preview is missing "${s}"`)
  }
  const logo = preview.locator('img[alt="Logo do IFMG"]')
  await logo.waitFor({ timeout: 5000 })
  check(await logo.evaluate((img) => img.complete && img.naturalWidth > 0), 'IFMG logo did not load in the preview')
  const pseudo = await preview.locator('h1').first().evaluate((h) => getComputedStyle(h, '::before').content)
  check(!/hiveBr/.test(pseudo), `IFMG heading still shows hiveBr branding: ${pseudo}`)

  const html = await downloadText(page.locator('button[data-tip="Export HTML"]'))
  check(html.includes('data:image/png;base64,'), 'IFMG export has no embedded logo')
  check(html.includes('INSTITUTO FEDERAL DE MINAS GERAIS'), 'IFMG export is missing the institutional header')
  check(html.includes('border-bottom-color: #2f6b3f'), 'IFMG export has no green theme CSS')
  check(html.includes('5) Referências'), 'IFMG export is missing the references section')
  check(html.includes('Gerado no hiveBr Web'), 'IFMG export is missing the footer')

  const md = await downloadText(page.locator('button[data-tip="Export .md"]'))
  check(md.startsWith('<!-- ifmg-header -->'), 'exported IFMG Markdown is missing the header marker')
  check(!md.includes('data:image/png;base64'), 'exported IFMG Markdown should not embed the logo')

  await page.locator('button[data-tip="Export PDF"]').click()
  await sleep(1500)
  const info = await page.evaluate(() => {
    const frame = document.querySelector('iframe[data-hivebr-print]')
    const doc = frame?.contentDocument
    const h1 = doc?.querySelector('h1')
    return {
      text: doc?.body?.innerText || '',
      logo: !!doc?.querySelector('img[alt="Logo do IFMG"]'),
      headingColor: h1 ? getComputedStyle(h1).color : '',
      accent: h1 ? getComputedStyle(h1, '::before').content : '',
    }
  })
  check(info.text.includes('INSTITUTO FEDERAL DE MINAS GERAIS'), 'IFMG print document is missing the header')
  check(info.logo, 'IFMG print document is missing the logo')
  check(info.headingColor === 'rgb(17, 17, 17)', `IFMG headings are not black in print: ${info.headingColor}`)
  check(!/hiveBr/.test(info.accent), `IFMG print still shows hiveBr branding: ${info.accent}`)
})

await test('capture images render in the preview and in both exports', async () => {
  await page.locator('button[aria-label="Capturar tela"]').first().click()
  await sleep(400)
  await page.locator('button[aria-label="Inserir captura de tela"]').click()
  await sleep(300)
  const item = page.locator('.capture-item').first()
  await item.waitFor({ timeout: 5000 })
  await item.click()
  await sleep(400)

  const img = page.locator('.md-preview img').last()
  await img.waitFor({ timeout: 5000 })
  const src = await img.getAttribute('src')
  check(src?.startsWith('data:image/png'), `preview image src is not a capture data URL: ${String(src).slice(0, 40)}`)

  const html = await downloadText(page.locator('button[data-tip="Export HTML"]'))
  check(html.includes('data:image/png;base64,'), 'exported HTML has no capture image')
  check(!html.includes('src="capture:'), 'exported HTML still has unresolved capture: URLs')

  await page.locator('button[data-tip="Export PDF"]').click()
  await sleep(1500)
  const info = await page.evaluate(() => {
    const frame = document.querySelector('iframe[data-hivebr-print]')
    const doc = frame?.contentDocument
    return {
      images: doc?.querySelectorAll('img').length || 0,
      captures: doc?.querySelectorAll('img[src^="data:image/png"]').length || 0,
    }
  })
  check(info.captures > 0, `print document has no capture image (${info.images} images)`)
})

const failed = results.filter((r) => !r.ok)
if (pageErrors.length) console.log('\nPage errors:\n' + pageErrors.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (pageErrors.length ? `, ${pageErrors.length} page error(s)` : ''))
for (const f of failed) console.log(' - ' + f.name + ': ' + f.err)
await browser.close()
server.close()
process.exit(failed.length || pageErrors.length ? 1 : 0)
