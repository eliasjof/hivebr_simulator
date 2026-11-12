// End-to-end test of the editor behaviour (Tab indentation) on the production build.
// The site is served from /hivebr/ like the real deployment.
import http from 'node:http'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(here, '..', '..', 'dist')
const SHOTS = process.env.E2E_SHOTS || path.join(os.tmpdir(), 'hivebr-e2e-editor')
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
    // Interactive mode: cross-origin isolation enables the SharedArrayBuffer
    // ring used by pause/resume and the other live commands.
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp',
  })
  fs.createReadStream(file).pipe(res)
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const BASE = `http://127.0.0.1:${server.address().port}/hivebr/`

const browser = await chromium.launch({ executablePath: CHROMIUM, headless: true, args: ['--no-sandbox'] })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'pt-BR' })
const page = await ctx.newPage()
const pageErrors = []
page.on('pageerror', (e) => pageErrors.push('pageerror: ' + e.message))
page.on('console', (m) => { if (m.type() === 'error') pageErrors.push('console.error: ' + m.text()) })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
function check(cond, msg) { if (!cond) throw new Error('assertion failed: ' + msg) }
// texto do editor, linha a linha (o CodeMirror virtualiza as linhas fora da tela)
const editorText = () => page.evaluate(() => [...document.querySelectorAll('.cm-line')].map((l) => l.textContent).join('\n'))

const results = []
async function test(name, fn) {
  try { await fn(); results.push({ name, ok: true }); console.log('  ok', name) }
  catch (e) { results.push({ name, ok: false, err: e.message }); console.log('  FAIL', name, '-', e.message) }
}

await page.goto(BASE)
await page.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })

await test('config editor selects the searched word and replaces the right occurrence', async () => {
  const yaml = 'a: alpha\nb: beta\nc: alpha\nd: ALPHA\n'
  await page.keyboard.press('p')
  await page.getByRole('button', { name: 'Editar YAML' }).click()
  const ta = page.locator('textarea.yaml')
  await ta.waitFor({ timeout: 10000 })
  await page.locator('[role="dialog"] input[type="file"]').setInputFiles({
    name: 'find.yaml', mimeType: 'text/yaml', buffer: Buffer.from(yaml),
  })
  await page.waitForFunction((expected) => document.querySelector('textarea.yaml')?.value === expected, yaml, { timeout: 10000 })

  const sel = () => ta.evaluate((el) => ({
    start: el.selectionStart, end: el.selectionEnd, text: el.value.slice(el.selectionStart, el.selectionEnd),
  }))
  const selectionIs = (start, text) => page.waitForFunction(([s, w]) => {
    const el = document.querySelector('textarea.yaml')
    return el && el.selectionStart === s && el.value.slice(el.selectionStart, el.selectionEnd) === w
  }, [start, text], { timeout: 5000 })

  await page.getByRole('button', { name: 'Procurar e substituir' }).click()
  const find = page.getByLabel('Procurar', { exact: true })
  await find.fill('alpha')
  await find.press('Enter')
  await selectionIs(3, 'alpha')
  check((await sel()).start === 3, `first match at 3, got ${JSON.stringify(await sel())}`)

  // F3 / Shift+F3 walk through matches while the editor has focus.
  await page.keyboard.press('F3')
  await selectionIs(20, 'alpha')
  await page.keyboard.press('Shift+F3')
  await selectionIs(3, 'alpha')

  await page.getByLabel('Substituir por', { exact: true }).fill('omega')
  await page.getByRole('button', { name: 'Substituir', exact: true }).click()
  await selectionIs(20, 'alpha')
  check((await ta.inputValue()).startsWith('a: omega\n'), 'the first occurrence was not replaced')

  await page.getByRole('button', { name: 'Substituir tudo', exact: true }).click()
  await page.waitForFunction(() => document.querySelector('textarea.yaml')?.value === 'a: omega\nb: beta\nc: omega\nd: omega\n', null, { timeout: 5000 })
  check((await page.locator('.find-count').innerText()) === '0', 'the match count should be 0 after replacing all')

  await page.keyboard.press('Escape')
  await page.locator('[role="dialog"][aria-label="Editar config do cliente"]').waitFor({ state: 'detached', timeout: 5000 })
  await page.keyboard.press('p')
  await page.locator('section[aria-label="Parâmetros"]').waitFor({ state: 'detached', timeout: 5000 })
})

// a aba de demonstração é somente leitura: abre um script novo para editar
await page.locator('.ed').getByRole('button', { name: 'Novo script', exact: true }).click()
await sleep(300)
await page.locator('.cm-content').click()
await page.keyboard.press('Control+A')

await test('Enter after ":" indents with 4 spaces (PEP 8)', async () => {
  await page.keyboard.type('def foo():')
  await page.keyboard.press('Enter')
  await sleep(200)
  check((await editorText()) === 'def foo():\n    ', `got ${JSON.stringify(await editorText())}`)
})

await test('Tab inside the indentation adds one level', async () => {
  await page.keyboard.press('Tab')
  await sleep(200)
  check((await editorText()) === 'def foo():\n        ', `got ${JSON.stringify(await editorText())}`)
})

await test('Shift+Tab removes one level', async () => {
  await page.keyboard.press('Shift+Tab')
  await sleep(200)
  check((await editorText()) === 'def foo():\n    ', `got ${JSON.stringify(await editorText())}`)
})

await test('Tab inside the leading whitespace indents the line', async () => {
  await page.keyboard.type('x = 1')
  await page.keyboard.press('Home')
  await page.keyboard.press('Tab')
  await sleep(200)
  check((await editorText()) === 'def foo():\n        x = 1', `got ${JSON.stringify(await editorText())}`)
})

await test('Tab after code inserts spaces at the cursor (line is not shifted)', async () => {
  await page.keyboard.press('End')
  await page.keyboard.press('Tab')
  await sleep(200)
  check((await editorText()) === 'def foo():\n        x = 1    ', `got ${JSON.stringify(await editorText())}`)
})

await test('Tab with a selection indents the selected lines', async () => {
  await page.keyboard.press('Control+A')
  await page.keyboard.type('a = 1')
  await page.keyboard.press('Enter')
  await page.keyboard.type('b = 2')
  await page.keyboard.press('Enter')
  await page.keyboard.type('c = 3')
  await sleep(200)
  check((await editorText()) === 'a = 1\nb = 2\nc = 3', `got ${JSON.stringify(await editorText())}`)
  await page.keyboard.press('ArrowUp')
  await page.keyboard.press('ArrowUp')
  await page.keyboard.press('Home')
  await page.keyboard.press('Shift+ArrowDown')
  await page.keyboard.press('Shift+End')
  await page.keyboard.press('Tab')
  await sleep(200)
  check((await editorText()) === '    a = 1\n    b = 2\nc = 3', `got ${JSON.stringify(await editorText())}`)
})

await test('the demo (read-only) tab is not changed by Tab', async () => {
  // a toolbar abre (e executa) um exemplo em uma aba somente leitura
  await page.locator('.tb').getByRole('button', { name: 'Demonstração' }).click()
  await sleep(500)
  await page.locator('.etab .tab').filter({ hasText: 'Demonstração' }).click()
  await sleep(300)
  await page.locator('.banner.ro').waitFor({ timeout: 10000 })
  const cm = page.locator('.cm-content')
  check((await cm.getAttribute('contenteditable')) === 'false', 'the demo editor is editable')
  const before = (await editorText()).split('\n')[0]
  await cm.click()
  await page.keyboard.type('x')
  await page.keyboard.press('Tab')
  await sleep(200)
  check((await editorText()).split('\n')[0] === before, 'the read-only demo changed')
})

await test('Run button toggles run ↔ pause (stop lives in the toolbar)', async () => {
  // the demo test above left a run active
  const pauseBtn = page.locator('.efoot .run-pause')
  await pauseBtn.waitFor({ timeout: 15000 })
  await pauseBtn.click()
  const resumeBtn = page.locator('.efoot .run-go')
  await resumeBtn.waitFor({ timeout: 15000 })
  await resumeBtn.click()
  await page.locator('.efoot .run-pause').waitFor({ timeout: 15000 })
  await page.locator('.tb .act.stop').click()
  await page.locator('.efoot .run-go').waitFor({ timeout: 15000 })
})

await test('Clear works at idle after the run stops', async () => {
  await page.locator('.tb').getByRole('button', { name: 'Demonstração' }).click()
  await page.locator('.efoot .run-pause').waitFor({ timeout: 30000 })
  await page.keyboard.press('k')
  const win = page.locator('section[aria-label="Mapa"]')
  await win.waitFor({ timeout: 10000 })
  await win.getByRole('button', { name: 'Mapa 1', exact: true }).click()
  await win.locator('.prev img').waitFor({ timeout: 10000 })
  await win.getByRole('button', { name: 'Aplicar', exact: true }).first().click()
  await page.waitForFunction(() => /Ocupação/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 15000 })

  // run → pause → resume → stop, then clear the map the stopped run left on screen
  await page.locator('.efoot .run-pause').click()
  await page.locator('.efoot .run-go').click()
  await page.locator('.tb .act.stop').click()
  await page.locator('.efoot .run-go').waitFor({ timeout: 15000 })
  const remove = win.getByRole('button', { name: 'Remover mapa' })
  check(await remove.isEnabled(), 'remove map should stay enabled at idle')
  await remove.click()
  await page.waitForFunction(() => !/Ocupação/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 10000 })
  await page.keyboard.press('k')
})

await test('opens helper files (JSON/py) next to the main script', async () => {
  await page.locator('.ed').getByRole('button', { name: 'Novo script', exact: true }).click()
  await sleep(200)
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.locator('.tabs').getByRole('button', { name: 'Abrir arquivo', exact: true }).click(),
  ])
  await chooser.setFiles([
    { name: 'helper_data.json', mimeType: 'application/json', buffer: Buffer.from('{"answer": 42}') },
    { name: 'helper_module.py', mimeType: 'text/x-python', buffer: Buffer.from('VALUE = 7\n') },
  ])
  await sleep(500)
  const tabs = (await page.locator('.etab .tab').allTextContents()).join('|')
  check(tabs.includes('helper_data.json'), `JSON helper tab missing: ${tabs}`)
  check(tabs.includes('helper_module.py'), `Python helper tab missing: ${tabs}`)
  await page.locator('.etab .tab').filter({ hasText: 'helper_data.json' }).click()
  await sleep(300)
  check((await editorText()) === '{"answer": 42}', `JSON content not shown as text: ${JSON.stringify(await editorText())}`)
})

await test('running a non-Python helper warns that the entry must be .py', async () => {
  // Stop any active run so the footer shows the run button.
  const toolbarStop = page.locator('.tb .act.stop')
  if (await toolbarStop.isEnabled().catch(() => false)) await toolbarStop.click()
  const runBtn = page.locator('.efoot .run-go')
  await runBtn.waitFor({ timeout: 15000 })
  await runBtn.click()
  await sleep(400)
  const warnings = (await page.locator('.toast.warn').allTextContents()).join(' ')
  check(warnings.includes('.py'), `expected a .py warning, got: ${warnings}`)
})

const failed = results.filter((r) => !r.ok)
if (pageErrors.length) console.log('\nPage errors:\n' + pageErrors.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (pageErrors.length ? `, ${pageErrors.length} page error(s)` : ''))
for (const f of failed) console.log(' - ' + f.name + ': ' + f.err)
await browser.close()
server.close()
process.exit(failed.length || pageErrors.length ? 1 : 0)
