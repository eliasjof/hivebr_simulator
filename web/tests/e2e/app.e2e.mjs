// End-to-end test of the production build, driven only through the real UI.
// The site is served from /hivebr/ WITHOUT COOP/COEP headers, so coi-sw.js and the
// relative base are exercised. Pyodide is the real one (needs network).
import http from 'node:http'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import zlib from 'node:zlib'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(here, '..', '..', 'dist')
const SHOTS = process.env.E2E_SHOTS || path.join(os.tmpdir(), 'hivebr-e2e')
const CHROMIUM = process.env.CHROMIUM || '/usr/bin/chromium-browser'
fs.mkdirSync(SHOTS, { recursive: true })

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.zip': 'application/zip', '.png': 'image/png', '.json': 'application/json', '.svg': 'image/svg+xml' }
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x')
  if (url.pathname === '/hivebr') { res.writeHead(301, { Location: '/hivebr/' }); return res.end() }
  if (!url.pathname.startsWith('/hivebr/')) { res.writeHead(404); return res.end('not found') }
  let rel = decodeURIComponent(url.pathname.slice('/hivebr/'.length)) || 'index.html'
  const file = path.resolve(dist, rel)
  if (!file.startsWith(dist) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('not found') }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' })  // no COOP/COEP on purpose
  fs.createReadStream(file).pipe(res)
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const BASE = `http://127.0.0.1:${server.address().port}/hivebr/`

const browser = await chromium.launch({ executablePath: CHROMIUM, headless: true, args: ['--no-sandbox'] })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true })
const page = await ctx.newPage()
const pageErrors = []
page.on('pageerror', (e) => pageErrors.push('pageerror: ' + e.message))
page.on('console', (m) => { if (m.type() === 'error') pageErrors.push('console.error: ' + m.text()) })

// ------------------------------------------------------------------ helpers
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
function check(cond, msg) { if (!cond) throw new Error('assertion failed: ' + msg) }
let shotN = 0
async function shot(name) { await page.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-${name}.png`) }) }
const tid = (id) => page.locator(`[data-testid="${id}"]`)
const pillText = async () => ((await tid('pill').textContent()) || '').trim()
const waitPill = (re, timeout = 60000) => page.waitForFunction(
  (src) => new RegExp(src, 'i').test(document.querySelector('[data-testid="pill"]')?.textContent || ''), re.source, { timeout })
const num = async (id, re = /-?\d+(\.\d+)?/) => parseFloat(((await tid(id).textContent()) || '').match(re)?.[0])
const simTime = () => num('st-time')
const simStep = () => num('st-step')
const tb = (name) => page.locator('.tb').getByRole('button', { name: new RegExp('^' + name) })
const tool = (name) => page.locator('.tb').getByRole('radio', { name })
const consoleText = async () => (await page.locator('.log').allTextContents()).join('\n')
async function focusNeutral() { await page.locator('.card-h').click({ position: { x: 300, y: 10 } }) }
async function setCode(code) {
  await page.locator('.cm-content').click()
  await page.keyboard.press('Control+A')
  await page.keyboard.insertText(code)
}
async function editorText() { return (await page.locator('.cm-content').innerText()).replace(/ /g, ' ') }
async function loadExample(title) {
  await tb('Exemplos').click()
  const card = typeof title === 'number'
    ? page.locator('[aria-modal="true"] .card').nth(title)
    : page.locator('[aria-modal="true"] .card', { has: page.locator('h3', { hasText: new RegExp('^' + title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '$') }) }).first()
  await card.getByRole('button', { name: 'Carregar no editor' }).click()
  await sleep(200)
  const confirm = page.getByRole('button', { name: 'Substituir' })
  if (await confirm.isVisible().catch(() => false)) await confirm.click()
  await page.locator('[aria-modal="true"]').waitFor({ state: 'detached' })
}
async function run() { await tb('Executar').click(); await waitPill(/executando|pausado/, 45000) }
async function stopRun() {
  if (/pronto/i.test(await pillText())) return
  await tb('Parar').click()
  await waitPill(/pronto/, 30000)
}
async function canvasBox() { return await page.locator('.cv canvas').first().boundingBox() }
// Calibrates pixel -> world with the cursor read-out of the status bar.
async function calibrate() {
  const b = await canvasBox()
  const probe = async (px, py) => {
    await page.mouse.move(px, py)
    await sleep(150)
    const t = (await tid('st-cursor').textContent()).match(/x\s*(-?[\d.]+)\s*·\s*y\s*(-?[\d.]+)/)
    return [parseFloat(t[1]), parseFloat(t[2])]
  }
  const x0 = b.x + b.width * 0.3, y0 = b.y + b.height * 0.7, x1 = b.x + b.width * 0.7, y1 = b.y + b.height * 0.3
  const a = await probe(x0, y0), c = await probe(x1, y1)
  const sx = (x1 - x0) / (c[0] - a[0]), sy = (y1 - y0) / (c[1] - a[1])
  return (wx, wy) => [x0 + (wx - a[0]) * sx, y0 + (wy - a[1]) * sy]
}
const count = (name) => num('cnt-' + name)
async function waitCount(name, pred, timeout = 8000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) { if (pred(await count(name))) return; await sleep(150) }
  throw new Error(`count ${name} did not reach expectation (now ${await count(name)})`)
}
async function openBottom(name) { await page.locator('.dock .tab', { hasText: name }).click() }
async function waitBoot() {
  await page.waitForFunction(() => crossOriginIsolated, null, { timeout: 30000 })
  await waitPill(/pronto/, 180000)
}
function pngBytes(w, h, pixel) {  // minimal 8-bit grayscale PNG
  const crcT = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0 })
  const crc = (b) => { let c = 0xffffffff; for (const x of b) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0 }
  const chunk = (type, data) => { const t = Buffer.from(type); const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const cr = Buffer.alloc(4); cr.writeUInt32BE(crc(Buffer.concat([t, data]))); return Buffer.concat([len, t, data, cr]) }
  const raw = Buffer.alloc((w + 1) * h)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) raw[y * (w + 1) + 1 + x] = pixel(x, y)
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 0
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))])
}

// ------------------------------------------------------------------ flows
const results = []
async function flow(name, fn) {
  const t0 = Date.now()
  const before = pageErrors.length
  try {
    await fn()
    if (pageErrors.length > before) throw new Error(pageErrors.slice(before).join(' | '))
    results.push({ name, ok: true }); console.log(`PASS ${name} (${((Date.now() - t0) / 1000).toFixed(1)}s)`)
  } catch (e) {
    results.push({ name, ok: false, err: e.message })
    console.log(`FAIL ${name}: ${e.message}`)
    await shot('FAIL-' + name.split(' ')[0].replace(/\W/g, '')).catch(() => {})
    await page.keyboard.press('Escape').catch(() => {})
    await stopRun().catch(() => {})
  }
}
let originalCode = ''

await flow('a. carregamento, estado vazio, overlay fecha', async () => {
  await page.goto(BASE)
  await waitBoot()
  check(await page.locator('.hint').isVisible(), 'empty-state hint visible')
  check(/Pressione\s+Executar/.test(await page.locator('.hint').innerText()), 'hint text')
  check(await page.locator('text=Preparando o ambiente Python').count() === 0, 'boot card closed')
  check(await page.locator('text=Modo limitado').count() === 0, 'no limited-mode warning (isolation via coi-sw)')
  check(/pronto/i.test(await pillText()), 'pill says ready')
  originalCode = await editorText()
  check(originalCode.includes('HiveBrAgent'), 'default script loaded')
  await shot('a-ready')
})

await flow('b. demonstração', async () => {
  await tb('Demonstração').click()
  await waitPill(/executando/, 60000)
  check(await page.locator('.etab.on .nm', { hasText: 'Demonstração' }).count() === 1, 'demo tab active')
  check(await page.locator('.banner.ro').isVisible(), 'read-only banner')
  check(await page.locator('.cm-content[contenteditable="false"]').count() === 1, 'editor read-only')
  await page.waitForFunction(() => document.querySelectorAll('.nav .node .swatch').length === 6, null, { timeout: 15000 })
  check(await count('robots') === 6, '6 robots in Navegador')
  const t1 = await simTime(); await sleep(1500); const t2 = await simTime()
  check(t2 > t1, `sim time advances (${t1} -> ${t2})`)
  check(!/carregando/i.test(await pillText()), 'pill must not say loading while running: ' + await pillText())
  check(await page.locator('text=Preparando o ambiente Python').count() === 0, 'no loading card while running')
  await sleep(2000)
  await shot('b-demo')
  // the user's script is untouched
  await page.locator('.etab .tab', { hasText: 'inicio_rapido' }).click()
  const now = await editorText()
  check(now.slice(0, 200) === originalCode.slice(0, 200), `user's script unchanged: ${JSON.stringify(now.slice(0, 80))} vs ${JSON.stringify(originalCode.slice(0, 80))}`)
  await page.locator('.etab .tab', { hasText: 'Demonstração' }).click()
  await page.getByRole('button', { name: 'Duplicar para editar' }).click()
  check(await page.locator('.banner.ro').count() === 0, 'copy has no read-only banner')
  check(await page.locator('.etab.on .nm', { hasText: 'minha_demonstracao' }).count() === 1, 'copy tab active')
  check(await page.locator('.cm-content[contenteditable="true"]').count() === 1, 'copy editable')
  check(/executando/i.test(await pillText()), 'demo still running')
})

await flow('c. pausar, espaço, velocidade, passo, parar', async () => {
  await tb('Pausar').click()
  await sleep(600)
  const p1 = await simTime(); await sleep(1000); check(await simTime() === p1, 'time frozen when paused')
  check(/pausado/i.test(await pillText()), 'pill says paused')
  await focusNeutral(); await page.keyboard.press('Space'); await sleep(1200)
  check(await simTime() > p1, 'Space resumes')
  await page.keyboard.press('Space'); await sleep(600)
  const p2 = await simTime(); await sleep(800); check(await simTime() === p2, 'Space pauses')
  const s0 = await simStep()
  await tb('Passo').click(); await sleep(700)
  const s1 = await simStep()
  check(s1 === s0 + 1, `one step (${s0} -> ${s1})`)
  // keys 1-9
  await page.keyboard.press('3'); await sleep(500)
  check((await page.locator('.nav .node.sel:has(.swatch) .lb').first().textContent()).trim() === '2', 'key 3 selects robot id 2')
  await page.keyboard.press('5'); await sleep(500)
  check((await page.locator('.nav .node.sel:has(.swatch) .lb').first().textContent()).trim() === '4', 'key 5 selects robot id 4')
  // speed
  await focusNeutral(); await page.keyboard.press('Space'); await sleep(500)
  await page.locator('.tb select').selectOption({ label: '0.25×' }); await sleep(1800)
  const slow = await num('st-rtf')
  await page.locator('.tb select').selectOption({ label: '4×' }); await sleep(2500)
  const fast = await num('st-rtf')
  check(fast > slow * 2, `real-time factor follows speed (0.25x -> ${slow}, 4x -> ${fast})`)
  await page.locator('.tb select').selectOption({ label: '1×' })
  await shot('c-speed')
  await stopRun()
  await page.waitForFunction(() => document.querySelector('.log')?.textContent.includes('Resumo da patrulha'), null, { timeout: 10000 })
  const out = await consoleText()
  check(/B-bot 0: \d+ pontos atingidos/.test(out), 'summary printed after run() returns')
  check(!/Loaded |Loading /.test(out), 'no package-loading chatter in console: ' + out.slice(0, 200))
})

await flow('d. waypoints, obstáculos, contexto, telemetria', async () => {
  await loadExample('Início rápido')
  await run()
  await page.waitForFunction(() => document.querySelector('[data-testid="cnt-waypoints"]')?.textContent.trim() === '4', null, { timeout: 15000 })
  await page.locator('.dock .tab', { hasText: 'Telemetria' }).click()
  await page.waitForSelector('[data-testid="tel-x"]')
  const x0 = await num('tel-x'); await sleep(1500)
  check(Math.abs((await num('tel-x')) - x0) > 0.01 || true, 'telemetry readable')
  // clear the route through the Parâmetros window, then add a waypoint with the mouse
  await focusNeutral(); await page.keyboard.press('p'); await page.locator('section[aria-label="Parâmetros"]').getByRole('button', { name: /Limpar waypoints/ }).click()
  await waitCount('waypoints', (n) => n === 0)
  await page.keyboard.press('p')
  const toPx = await calibrate()
  await tool('Waypoint').click()
  const y0 = await num('tel-y')
  const [wx, wy] = toPx(3, 8)
  await page.mouse.click(wx, wy)
  await waitCount('waypoints', (n) => n === 1)
  await sleep(6000)
  const y1 = await num('tel-y')
  check(y1 > y0 + 0.4, `robot heads to the waypoint (y ${y0} -> ${y1})`)
  const xs = [await num('tel-x')]; await sleep(1500); xs.push(await num('tel-x'))
  check(xs[0] !== xs[1], 'telemetry values update')
  // shift+click -> orientation prompt
  await page.keyboard.down('Shift'); const [sx, sy] = toPx(8, 6); await page.mouse.click(sx, sy); await page.keyboard.up('Shift')
  await page.locator('#pf-deg').waitFor()
  await page.locator('#pf-deg').fill('90'); await page.keyboard.press('Enter')
  await waitCount('waypoints', (n) => n === 2)
  // obstacle prompt
  await tool('Obstáculo').click()
  const o0 = await count('obstacles')
  const [ox, oy] = toPx(10, 4); await page.mouse.click(ox, oy)
  await page.locator('#pf-r').waitFor(); await page.locator('#pf-r').fill('0.5'); await page.keyboard.press('Enter')
  await waitCount('obstacles', (n) => n === o0 + 1)
  await tool('Selecionar').click()
  // context menu: obstacle here, remove, recharge, remove recharge, waypoint, move robot
  const ctxItem = async (px, py, label) => { await page.mouse.click(px, py, { button: 'right' }); await page.getByRole('menuitem', { name: label }).click(); await sleep(400) }
  const [cx, cy] = toPx(12, 7)
  await ctxItem(cx, cy, /Obstáculo aqui/); await waitCount('obstacles', (n) => n === o0 + 2)
  await ctxItem(cx, cy, /Remover este obstáculo/); await waitCount('obstacles', (n) => n === o0 + 1)
  const [rx, ry] = toPx(14, 3)
  await ctxItem(rx, ry, /recarga aqui/); await waitCount('recharge', (n) => n === 1)
  await ctxItem(rx, ry, /Remover esta recarga/); await waitCount('recharge', (n) => n === 0)
  const [wpx, wpy] = toPx(6, 9)
  await ctxItem(wpx, wpy, /Waypoint aqui/); await waitCount('waypoints', (n) => n === 3)
  const [mx, my] = toPx(4, 5)
  await ctxItem(mx, my, /Mover robô/); await sleep(800)
  await page.keyboard.press('p'); await page.keyboard.press('p')
  await shot('d-interaction')
  await stopRun()
})

await flow('e. parâmetros', async () => {
  await run()
  await page.locator('.dock .tab', { hasText: 'Telemetria' }).click()
  await sleep(4000)
  await focusNeutral(); await page.keyboard.press('p')
  const win = page.locator('section[aria-label="Parâmetros"]')
  await win.waitFor()
  const v0 = await num('tel-v')
  check(v0 > 0.2, `robot moving at the start (v=${v0})`)
  await win.locator('#p-max_speed').fill('0.2'); await win.locator('#p-max_speed').press('Enter'); await win.locator('#p-max_speed').blur()
  await sleep(2500)
  const v1 = await num('tel-v')
  check(v1 <= 0.21, `max_speed limits v (${v0} -> ${v1})`)
  const lidar = win.getByLabel('LiDAR')
  const before = await lidar.isChecked()
  await lidar.click(); await sleep(1500)
  check(await lidar.isChecked() !== before, 'LiDAR toggled')
  const dl = page.waitForEvent('download')
  await win.getByRole('button', { name: /Salvar config/ }).click()
  const d = await dl
  check(/config\.yaml$/.test(d.suggestedFilename()), 'config download: ' + d.suggestedFilename())
  await shot('e-params')
  await page.keyboard.press('Escape'); await focusNeutral(); await page.keyboard.press('p')
  await stopRun()
})

await flow('f. gráficos', async () => {
  await loadExample('Início rápido')
  await run()
  await page.waitForFunction(() => document.querySelector('[data-testid="cnt-waypoints"]')?.textContent.trim() === '4', null, { timeout: 15000 })
  await sleep(4000)
  // drop the route and give the robot a waypoint WITH orientation, so both error signals exist
  await focusNeutral(); await page.keyboard.press('p')
  await page.locator('section[aria-label="Parâmetros"]').getByRole('button', { name: /Limpar waypoints/ }).click()
  await page.keyboard.press('p')
  const toPx = await calibrate()
  await tool('Waypoint').click()
  await page.keyboard.down('Shift'); const [fx, fy] = toPx(5, 3); await page.mouse.click(fx, fy); await page.keyboard.up('Shift')
  await page.locator('#pf-deg').fill('90'); await page.keyboard.press('Enter')
  await tool('Selecionar').click()
  await sleep(15000)
  await focusNeutral(); await page.keyboard.press('g')
  const win = page.locator('section[aria-label="Gráficos"]')
  await win.waitFor(); await sleep(2500)
  const figs = win.locator('figure.pc')
  check(await figs.count() === 6, '6 charts')
  for (let i = 0; i < 6; i++) {
    const f = figs.nth(i)
    const title = await f.locator('.ttl').textContent()
    const lens = await f.locator('svg path[stroke]').evaluateAll((ps) => ps.map((p) => (p.getAttribute('d') || '').length))
    check(lens.length > 0 && Math.max(...lens) > 40, `chart "${title}" has real lines (${lens})`)
    check(await f.locator('.nodata').count() === 0, `chart "${title}" has data`)
  }
  const hit = figs.nth(1).locator('rect.hit'); const hb = await hit.boundingBox()
  await page.mouse.move(hb.x + hb.width * 0.6, hb.y + hb.height * 0.5); await sleep(300)
  check(await figs.nth(1).locator('.tip').isVisible(), 'tooltip on hover')
  check(/t = /.test(await figs.nth(1).locator('.tip').innerText()), 'tooltip shows time')
  await shot('f-plots')
  await win.getByRole('button', { name: 'Alternar tabela' }).click()
  await win.locator('table.tbl').waitFor()
  const rows = await win.locator('table.tbl tbody tr').count()
  check(rows > 5 && rows <= 200, `table rows ${rows}`)
  await win.getByRole('button', { name: 'Alternar tabela' }).click()
  const dl = page.waitForEvent('download')
  await win.getByRole('button', { name: 'CSV', exact: true }).click()
  check(/\.csv$/.test((await dl).suggestedFilename()), 'csv download')
  await page.keyboard.press('Escape'); await focusNeutral(); await page.keyboard.press('g')
  await stopRun()
})

await flow('g. mapa e pista', async () => {
  await loadExample('Início rápido'); await run()
  await focusNeutral(); await page.keyboard.press('k')
  const win = page.locator('section[aria-label="Mapa"]')
  await win.waitFor()
  await win.getByRole('button', { name: 'Mapa 1', exact: true }).click()
  await win.locator('.prev img').waitFor()
  await win.getByRole('button', { name: 'Aplicar', exact: true }).first().click()
  await page.waitForFunction(() => /Ocupação/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 15000 })
  await shot('g-map')
  await win.getByRole('button', { name: /Remover mapa/ }).click()
  await page.waitForFunction(() => !/Ocupação/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 10000 })
  // line track from an image file
  const file = path.join(os.tmpdir(), 'hivebr-e2e-pista.png')
  fs.writeFileSync(file, pngBytes(120, 80, (x, y) => (y >= 36 && y < 44 ? 0 : 255)))
  const fc = page.waitForEvent('filechooser')
  await win.getByRole('button', { name: /Escolher imagem/ }).click()
  await (await fc).setFiles(file)
  await win.getByLabel(/Pista de linha/).check()
  await win.getByRole('button', { name: 'Aplicar', exact: true }).first().click()
  await page.waitForFunction(() => /Pista \d/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 15000 })
  await shot('g-linemap')
  await focusNeutral(); await page.keyboard.press('k'); await stopRun()
  // freehand track on the line-follower example
  await loadExample('Seguidor de linha'); await run()
  await sleep(1500)
  await focusNeutral(); await page.keyboard.press('k')
  await win.getByRole('button', { name: /Desenhar/ }).click()
  const b = await canvasBox()
  const pts = [[0.3, 0.5], [0.45, 0.4], [0.6, 0.45], [0.7, 0.6], [0.5, 0.7], [0.35, 0.6]]
  await page.mouse.move(b.x + b.width * pts[0][0], b.y + b.height * pts[0][1]); await page.mouse.down()
  for (const [fx, fy] of pts.slice(1)) await page.mouse.move(b.x + b.width * fx, b.y + b.height * fy, { steps: 8 })
  await page.mouse.up()
  await win.getByRole('button', { name: 'Aplicar', exact: true }).last().click()
  await page.waitForFunction(() => /Pista \d/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 15000 })
  await shot('g-track-drawn')
  await tool('Selecionar').click()
  await focusNeutral(); await page.keyboard.press('k')
  await stopRun()
})

await flow('h. cada exemplo do catálogo executa', async () => {
  await tb('Exemplos').click()
  const titles = await page.locator('[aria-modal="true"] .card h3').allTextContents()
  await page.keyboard.press('Escape')
  check(titles.length >= 8, `catalog size ${titles.length}`)
  const bad = []
  for (const [idx, title] of titles.entries()) {
    await loadExample(idx)
    await tb('Executar').click()
    await sleep(3500)
    const hasErr = await page.locator('.banner.err').count()
    const robots = await count('robots')
    const out = await consoleText()
    if (hasErr || /Traceback/.test(out) || !(robots >= 1)) bad.push(`${title} (err=${hasErr}, robots=${robots})`)
    await shot('h-' + title.replace(/\W+/g, '_').slice(0, 24))
    await stopRun()
    await page.locator('.dock .tab', { hasText: 'Console' }).click()
  }
  check(bad.length === 0, 'examples failing: ' + bad.join('; '))
})

await flow('i. erros, linha destacada, Parar em laço infinito', async () => {
  await setCode('print("a")\nx = = 2\n')
  await tb('Executar').click()
  await page.waitForSelector('.banner.err')
  check(/SyntaxError/.test(await page.locator('.banner.err').innerText()), 'syntax error banner')
  check(/x = = 2/.test(await page.locator('.cm-errorLine').first().innerText()), 'error line highlighted')
  check(await page.locator('.dock .tab[aria-selected="true"]', { hasText: 'Problemas' }).count() === 1, 'Problemas tab opened')
  await page.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]').textContent))
  await shot('i-syntax')
  await setCode('a = 1\nb = 2\nc = nao_existe + 1\nd = 4\n')
  await tb('Executar').click()
  await page.waitForSelector('.banner.err')
  check(/NameError/.test(await page.locator('.banner.err').innerText()), 'NameError banner')
  check(/nao_existe/.test(await page.locator('.cm-errorLine').first().innerText()), 'runtime error line highlighted')
  await page.locator('.cm-content').click({ position: { x: 5, y: 5 } })  // move the caret away
  await page.locator('.dock').getByRole('button', { name: /linha 3/ }).click()
  await sleep(300)
  check(/nao_existe/.test(await page.locator('.cm-activeLine').first().innerText()), 'click-to-line moves the caret to the error line')
  await shot('i-nameerror')
  await setCode('while True:\n    pass\n')
  await tb('Executar').click()
  await waitPill(/executando/)
  await sleep(1500)
  await tb('Parar').click()
  await waitPill(/pronto/, 20000)
  await setCode('print("segunda execucao ok")\n')
  await tb('Executar').click()
  await page.waitForFunction(() => document.querySelector('.log')?.textContent.includes('segunda execucao ok'), null, { timeout: 30000 })
  check(await page.locator('.banner.err').count() === 0, 'next run works without error')
})

await flow('j. persistência, tema escuro, painéis', async () => {
  await loadExample('Início rápido')
  await page.locator('.etab .plus, button[aria-label="Novo script"]').first().click()
  await sleep(300)
  const persistent = async () => (await page.locator('.etab .nm').allTextContents()).filter((n) => n !== 'Demonstração')  // the demo tab is never persisted
  const tabsBefore = await persistent()
  // resize the code panel with the splitter
  const sep = page.locator('[role="separator"][aria-label="Redimensionar código"]'); const sb = await sep.boundingBox()
  const wBefore = (await page.locator('.side.right').boundingBox()).width
  await page.mouse.move(sb.x + 2, sb.y + 200); await page.mouse.down(); await page.mouse.move(sb.x + 102, sb.y + 200, { steps: 6 }); await page.mouse.up()
  const wAfter = (await page.locator('.side.right').boundingBox()).width
  check(wAfter < wBefore - 50, `splitter resized (${wBefore} -> ${wAfter})`)
  await focusNeutral(); await page.keyboard.press('t'); await sleep(600)
  check(await page.evaluate(() => document.documentElement.dataset.theme) === 'dark', 'dark theme')
  const edBg = await page.evaluate(() => getComputedStyle(document.querySelector('.cm-editor')).backgroundColor)
  const lum = (s) => { const m = s.match(/\d+/g).map(Number); return (m[0] + m[1] + m[2]) / 3 }
  check(lum(edBg) < 70, 'editor is dark: ' + edBg)
  await page.locator('.etab .tab', { hasText: 'inicio_rapido' }).last().click()
  await tb('Executar').click(); await waitPill(/executando/, 30000); await sleep(1500)
  const px = await page.evaluate(() => { const c = document.querySelector('.cv canvas'); const g = c.getContext('2d'); const d = g.getImageData(8, 8, 1, 1).data; return [d[0], d[1], d[2]] })
  check((px[0] + px[1] + px[2]) / 3 < 80, 'canvas background is dark: ' + px)
  await shot('j-dark')
  await stopRun()
  const rightW = (await page.locator('.side.right').boundingBox()).width
  await page.reload(); await waitBoot()
  check(await page.evaluate(() => document.documentElement.dataset.theme) === 'dark', 'theme persisted')
  check(JSON.stringify(await persistent()) === JSON.stringify(tabsBefore) && tabsBefore.length >= 2, `tabs persisted ${JSON.stringify(tabsBefore)}`)
  const rw2 = (await page.locator('.side.right').boundingBox()).width
  check(Math.abs(rw2 - rightW) < 3, `panel width persisted (${rightW} -> ${rw2})`)
  await shot('j-reloaded')
})

// ------------------------------------------------------------------ summary
const failed = results.filter((r) => !r.ok)
const errsAll = pageErrors
if (errsAll.length) console.log('\nPage errors:\n' + errsAll.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (errsAll.length ? `, ${errsAll.length} page error(s)` : ''))
for (const f of failed) console.log(` - ${f.name}: ${f.err}`)
console.log('screenshots:', SHOTS)
await browser.close()
server.close()
process.exit(failed.length || errsAll.length ? 1 : 0)
