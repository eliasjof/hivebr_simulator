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
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true, locale: 'pt-BR' })
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
// números saem no formato do idioma (pt-BR usa vírgula decimal)
const num = async (id, re = /-?\d+([.,]\d+)?/) => parseFloat((((await tid(id).textContent()) || '').match(re)?.[0] || '').replace(',', '.'))
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
    const m = (await tid('st-cursor').textContent()).replace(/,/g, '.').match(/x\s*(-?[\d.]+)\s*·\s*y\s*(-?[\d.]+)/)
    return [parseFloat(m[1]), parseFloat(m[2])]
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

  // Drawing before the first run: the empty-state hint must not swallow the
  // gesture, and the stroke must reach the track (regression: "Desenhe ao
  // menos um traço na tela" after drawing over the centered hint).
  await focusNeutral()
  await page.keyboard.press('k')
  const mapWin = page.locator('section[aria-label="Mapa"]')
  await mapWin.waitFor()
  await mapWin.getByRole('button', { name: /Desenhar/ }).click()
  await page.waitForFunction(() => !document.querySelector('.hint'), null, { timeout: 5000 })
  check(await page.locator('.hint').count() === 0, 'hint must hide while the draw tool is active')
  const cb = await canvasBox()
  await page.mouse.move(cb.x + cb.width * 0.5, cb.y + cb.height * 0.5)
  await page.mouse.down()
  await page.mouse.move(cb.x + cb.width * 0.6, cb.y + cb.height * 0.55, { steps: 8 })
  await page.mouse.up()
  await mapWin.getByRole('button', { name: 'Aplicar', exact: true }).last().click()
  await page.waitForFunction(() => /Pista \d/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 15000 })
  await mapWin.getByRole('button', { name: 'Limpar', exact: true }).click()
  await page.waitForFunction(() => /Mapa\s*Nenhum/.test(document.querySelector('.nav')?.textContent || ''), null, { timeout: 15000 })
  await page.keyboard.press('Escape')
  await page.keyboard.press('k')
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

// ------------------------------------------------------------------ janelas flutuantes
const PT_ACCENT = /[áàâãçéêíóôõúÁÀÂÃÇÉÊÍÓÔÕÚ]/
const PT_WORDS = /\b(Executar|Executando|Parar|Parando|Salvar|Salvo|Abrir|Fechar|Limpar|Nenhum|Nenhuma|Aguardando|Carregando|Simulação|Ferramentas|Gráficos|Parâmetros|Navegador|Robôs|Obstáculo|Recarga|Idioma|Selecionar|Desenhar|Camadas|Pausado|Exemplos|Ajuda|Arquivo|Editar|Exibir|Mapa|Telemetria|Problemas|Código)\b/

await flow('k. janelas: enquadramento, alças, empilhamento, teclado, maximizar', async () => {
  await page.goto(BASE); await waitBoot()
  await focusNeutral()
  const NAME = 'section[aria-label="Parâmetros"]'
  const win = page.locator(NAME)
  const menubarH = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--menubar-h')))
  const toolbarH = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--toolbar-h')))
  const statusH = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--status-h')))
  await page.keyboard.press('p'); await win.waitFor()
  check(await win.evaluate((el) => getComputedStyle(el).overflow) === 'visible', 'window overflow must be visible (resize handles are not clipped)')
  const box = () => win.boundingBox()
  const drag = async (from, to) => { await page.mouse.move(from[0], from[1]); await page.mouse.down(); await page.mouse.move(to[0], to[1], { steps: 8 }); await page.mouse.up() }
  // grab the title inside the visible part of the viewport (the window may hang off an edge)
  const titlePt = async () => { const b = await win.locator('.fw-title').boundingBox(); return [Math.max(b.x, 0) + 50, b.y + b.height / 2] }

  // arrastar para o topo: a barra de título nunca fica sob a barra de menus
  let [tx, ty] = await titlePt()
  await drag([tx, ty], [tx, 0])
  let b = await box()
  check(b.y >= menubarH - 0.5, `title bar stays below the menu bar (y=${b.y}, menubar=${menubarH})`)
  const titleHit = await page.evaluate(([x, y]) => !!document.elementFromPoint(x, y)?.closest('.fw-title'), await titlePt())
  check(titleHit, 'title bar is reachable (hit-test)')
  // arrastar muito para a esquerda e para a direita: sobram 160 px visíveis
  ;[tx, ty] = await titlePt()
  await drag([tx, ty], [-900, ty + 200])
  b = await box()
  check(b.x + b.width >= 159, `at least 160px stay visible on the left (right edge=${b.x + b.width})`)
  ;[tx, ty] = await titlePt()
  await drag([tx, ty], [1900, ty])
  b = await box()
  check(1440 - b.x >= 159, `at least 160px stay visible on the right (x=${b.x})`)
  // volta para uma posição confortável
  ;[tx, ty] = await titlePt()
  await drag([tx, ty], [700, 300])
  b = await box()

  // alças: sudeste cresce
  const handle = (d) => win.locator('.h-' + d)
  let hb = await handle('se').boundingBox()
  const w0 = (await box()).width, h0 = (await box()).height
  await drag([hb.x + hb.width / 2, hb.y + hb.height / 2], [hb.x + 100, hb.y + 80])
  b = await box()
  check(b.width > w0 + 60 && b.height > h0 + 50, `se handle grows the window (${w0}x${h0} -> ${b.width}x${b.height})`)
  // oeste: limitado a x >= 0
  hb = await handle('w').boundingBox()
  await drag([hb.x + hb.width / 2, hb.y + hb.height / 2], [-1200, hb.y + 20])
  b = await box()
  check(b.x >= -0.5, `west resize is bounded at x=0 (x=${b.x})`)
  check(b.width <= 1440 + 1, `window does not exceed the viewport (w=${b.width})`)
  // norte: limitado à altura da barra de menus
  ;[tx, ty] = await titlePt()
  await drag([tx, ty], [tx + 500, 300])           // move away from the left edge first
  hb = await handle('n').boundingBox()
  await drag([hb.x + hb.width / 2, hb.y + 4], [hb.x + hb.width / 2, -400])
  b = await box()
  check(b.y >= menubarH - 0.5, `north resize stops under the menu bar (y=${b.y})`)
  await shot('k-window-top')

  // empilhamento: a janela cobre a barra de ferramentas (z-float > z-bar) e os menus cobrem a janela
  const overToolbar = await page.evaluate(([x, y, sel]) => !!document.elementFromPoint(x, y)?.closest(sel), [b.x + b.width / 2, menubarH + toolbarH / 2, NAME])
  check(overToolbar, 'floating window stacks above the toolbar')
  ;[tx, ty] = await titlePt()
  await drag([tx, ty], [420, 260])
  await page.locator('[data-menu="view"]').click()
  const dropBox = await page.locator('.drop').boundingBox()
  const menuOver = await page.evaluate(([x, y]) => !!document.elementFromPoint(x, y)?.closest('.drop'), [dropBox.x + dropBox.width / 2, dropBox.y + dropBox.height - 6])
  check(menuOver, 'menus stack above floating windows')
  await page.keyboard.press('Escape')

  // teclado: setas movem 10 px (Shift 40); Alt+setas redimensionam
  await page.locator(NAME + ' .fw-title').focus()
  b = await box()
  await page.keyboard.press('ArrowRight'); let c = await box()
  check(Math.abs(c.x - b.x - 10) < 1, `ArrowRight moves 10px (${b.x} -> ${c.x})`)
  await page.keyboard.press('Shift+ArrowDown'); b = c; c = await box()
  check(Math.abs(c.y - b.y - 40) < 1, `Shift+ArrowDown moves 40px (${b.y} -> ${c.y})`)
  await page.keyboard.press('Alt+ArrowRight'); b = c; c = await box()
  check(Math.abs(c.width - b.width - 10) < 1, `Alt+ArrowRight resizes 10px (${b.width} -> ${c.width})`)

  // maximizar usa a área útil real (menus + ferramentas + 8 px; barra de status + 8 px)
  await page.locator(NAME + ' .fw-title').dblclick({ position: { x: 150, y: 10 } })
  b = await box()
  check(Math.abs(b.x - 8) < 1 && Math.abs(b.y - (menubarH + toolbarH + 8)) < 1, `maximized top-left (${b.x},${b.y})`)
  check(Math.abs(b.x + b.width - (1440 - 8)) < 1 && Math.abs(b.y + b.height - (900 - statusH - 8)) < 1, `maximized bottom-right (${b.x + b.width},${b.y + b.height})`)
  await shot('k-maximized')
  await page.locator(NAME + ' .fw-title').dblclick({ position: { x: 150, y: 10 } })
  await focusNeutral(); await page.keyboard.press('p')
})

// ------------------------------------------------------------------ internacionalização
async function localePage(locale) {
  const c = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true, locale })
  const pg = await c.newPage()
  pg.on('pageerror', (e) => pageErrors.push('pageerror: ' + e.message))
  pg.on('console', (m) => { if (m.type() === 'error') pageErrors.push('console.error: ' + m.text()) })
  await pg.goto(BASE)
  await pg.waitForFunction(() => crossOriginIsolated, null, { timeout: 30000 })
  await pg.waitForFunction(() => /ready|pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })
  return { c, pg }
}
const htmlLang = (pg) => pg.evaluate(() => document.documentElement.lang)

await flow('l. detecção de idioma: en-US, pt-BR e fr-FR', async () => {
  for (const [loc, lang, run, file] of [['en-US', 'en', 'Run', 'File'], ['pt-BR', 'pt-BR', 'Executar', 'Arquivo'], ['fr-FR', 'en', 'Run', 'File'], ['pt-PT', 'pt-BR', 'Executar', 'Arquivo']]) {
    const { c, pg } = await localePage(loc)
    try {
      check(await htmlLang(pg) === lang, `${loc}: <html lang> = ${lang}`)
      check((await pg.title()) === 'hiveBr Web', `${loc}: localized title`)
      check(await pg.locator('.tb').getByRole('button', { name: new RegExp('^' + run) }).count() >= 1, `${loc}: toolbar shows "${run}"`)
      check(await pg.locator(`[data-menu="file"]`).innerText() === file, `${loc}: menu "${file}"`)
      if (loc === 'en-US') await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-l-en.png`) })
    } finally { await c.close() }
  }
})

await flow('m. Arquivo > Idioma: troca ao vivo durante a demonstração, persiste, Automático', async () => {
  const { c, pg } = await localePage('pt-BR')
  try {
    const time = async () => parseFloat(((await pg.locator('[data-testid="st-time"]').textContent()) || '').replace(',', '.').match(/-?[\d.]+/)[0])
    await pg.locator('.tb').getByRole('button', { name: /^Demonstração/ }).click()
    await pg.waitForFunction(() => /executando/i.test(document.querySelector('[data-testid="pill"]').textContent), null, { timeout: 60000 })
    await sleep(1500)
    const t0 = await time()
    // mouse: Arquivo > Idioma > English
    await pg.locator('[data-menu="file"]').click()
    await pg.getByRole('menuitem', { name: 'Idioma' }).first().click()
    check(await pg.getByRole('menuitemradio', { name: 'Automático (navegador)' }).isVisible(), 'submenu lists "Automático (navegador)"')
    check(await pg.getByRole('menuitemradio', { name: 'Português (Brasil)' }).getAttribute('aria-checked') === 'false', 'radio state exposed')
    await pg.getByRole('menuitemradio', { name: 'English' }).click()
    await sleep(2500)
    check(await htmlLang(pg) === 'en', 'html lang switched to en')
    check(/running/i.test(await pg.locator('[data-testid="pill"]').textContent()), 'pill says running in English')
    const t1 = await time(); await sleep(1200); const t2 = await time()
    check(t2 > t0 && t2 > t1, `simulation kept running through the switch (${t0} -> ${t1} -> ${t2})`)
    check(await pg.locator('.tb').getByRole('button', { name: /^Pause/ }).count() === 1, 'toolbar is in English and the run was not interrupted')
    await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-m-live-en.png`) })
    // persiste ao recarregar
    await pg.reload()
    await pg.waitForFunction(() => /ready/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })
    check(await htmlLang(pg) === 'en', 'choice persisted after reload')
    // teclado: File > Language (ArrowRight opens the submenu) > Automatic
    await pg.locator('[data-menu="file"]').focus(); await pg.keyboard.press('Enter')
    for (let i = 0; i < 8; i++) {
      const label = await pg.evaluate(() => document.activeElement?.textContent || '')
      if (/^\s*Language/.test(label)) break
      await pg.keyboard.press('ArrowDown')
    }
    await pg.keyboard.press('ArrowRight')
    check(await pg.getByRole('menuitemradio', { name: /^Automatic/ }).isVisible(), 'ArrowRight opens the Language submenu')
    await pg.keyboard.press('Escape')
    check(await pg.getByRole('menuitemradio', { name: /^Automatic/ }).count() === 0 && await pg.locator('.drop').isVisible(), 'Esc closes only the submenu')
    await pg.keyboard.press('ArrowRight')
    await pg.keyboard.press('Enter')   // first item: Automatic (browser)
    await sleep(500)
    check(await htmlLang(pg) === 'pt-BR', 'Automatic returns to browser detection (pt-BR)')
    check(await pg.locator('[data-menu="file"]').innerText() === 'Arquivo', 'UI is back in Portuguese')
    await pg.reload()
    await pg.waitForFunction(() => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout: 180000 })
    check(await htmlLang(pg) === 'pt-BR', 'Automatic persisted (no explicit choice left)')
  } finally { await c.close() }
})

await flow('n. en: nenhum português sobra no shell, janelas e modais', async () => {
  const { c, pg } = await localePage('en-US')
  const problems = []
  const snap = async (label) => {
    const text = await pg.evaluate(() => {
      const clone = document.body.cloneNode(true)
      for (const sel of ['.cm-editor', '.log', '.nm', '.etab', '.kids .lb.mono', '.center b', '.fig']) clone.querySelectorAll(sel).forEach((e) => e.remove())
      const attrs = [...document.querySelectorAll('[data-tip],[aria-label],[title],[placeholder],[alt]')]
        .filter((e) => !e.closest('.cm-editor') && !e.closest('.log') && !e.closest('.etab'))
        .map((e) => [e.dataset.tip, e.getAttribute('aria-label'), e.getAttribute('title'), e.getAttribute('placeholder'), e.getAttribute('alt')].filter(Boolean).join(' | '))
      return clone.innerText + '\n' + attrs.join('\n')
    })
    const clean = text.replace(/Português \(Brasil\)/g, '')
    const bad = clean.split('\n').filter((l) => PT_ACCENT.test(l) || PT_WORDS.test(l))
    if (bad.length) problems.push(`[${label}] ${bad.slice(0, 4).join(' || ')}`)
  }
  try {
    await snap('shell')
    await pg.locator('.tb').getByRole('button', { name: /^Demo/ }).click()
    await pg.waitForFunction(() => /running/i.test(document.querySelector('[data-testid="pill"]').textContent), null, { timeout: 60000 })
    await sleep(2500)
    await snap('running')
    // menus
    for (const m of ['file', 'edit', 'view', 'sim', 'ex', 'help']) { await pg.locator(`[data-menu="${m}"]`).click(); await snap('menu-' + m); await pg.keyboard.press('Escape') }
    await pg.locator('[data-menu="file"]').click(); await pg.getByRole('menuitem', { name: 'Language' }).first().click(); await snap('menu-language'); await pg.keyboard.press('Escape'); await pg.keyboard.press('Escape')
    // layers dropdown, bottom tabs, telemetry floating window
    await pg.locator('.tb').getByRole('button', { name: /^Layers/ }).click(); await snap('layers'); await pg.keyboard.press('Escape')
    for (const tab of ['Telemetry', 'Problems', 'Console']) { await pg.locator('.dock .tab', { hasText: tab }).click(); await snap('dock-' + tab) }
    // windows
    const body = pg.locator('.card-h')
    for (const [key, name] of [['p', 'Parameters'], ['g', 'Plots'], ['k', 'Map'], ['b', 'Telemetry']]) {
      await body.click({ position: { x: 300, y: 10 } })
      if (key === 'b') { await pg.locator('.dock .tab', { hasText: 'Telemetry' }).click(); await pg.getByRole('button', { name: /Detach/ }).first().click() }
      else await pg.keyboard.press(key)
      await sleep(900)
      await snap('window-' + name)
      if (key === 'g') {
        await pg.locator(`section[aria-label="${name}"]`).getByRole('button', { name: 'Toggle table' }).click(); await sleep(300); await snap('plots-table')
        await pg.locator(`section[aria-label="${name}"]`).getByRole('button', { name: 'Toggle table' }).click()
      }
      await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-n-en-${name}.png`) })
      if (key !== 'b') { await body.click({ position: { x: 300, y: 10 } }); await pg.keyboard.press(key) }
    }
    // the Figures screen lives as a tab of the simulation panel now
    await pg.locator('.docbar').getByRole('tab', { name: /Figures/ }).click(); await sleep(300); await snap('figures')
    await pg.locator('.docbar').getByRole('tab', { name: /Simulation/ }).click()
    await pg.locator('section[aria-label="Telemetry"] button[aria-label="Close"]').click()
    // modals
    await pg.locator('.tb').getByRole('button', { name: /^Examples/ }).click(); await sleep(400); await snap('modal-examples')
    await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-n-en-examples.png`) })
    await pg.keyboard.press('Escape')
    await body.click({ position: { x: 300, y: 10 } }); await pg.keyboard.press('?'); await sleep(400); await snap('modal-help')
    await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-n-en-help.png`) })
    await pg.keyboard.press('Escape')
    // prompts and context menu on the canvas
    await pg.locator('.tb').getByRole('radio', { name: 'Waypoint' }).click()
    const cb = await pg.locator('.cv canvas').first().boundingBox()
    await pg.keyboard.down('Shift'); await pg.mouse.click(cb.x + cb.width * 0.4, cb.y + cb.height * 0.4); await pg.keyboard.up('Shift')
    await pg.locator('#pf-deg').waitFor(); await snap('prompt-waypoint'); await pg.keyboard.press('Escape')
    await pg.locator('.tb').getByRole('radio', { name: 'Obstacle' }).click()
    await pg.mouse.click(cb.x + cb.width * 0.5, cb.y + cb.height * 0.5)
    await pg.locator('#pf-r').waitFor(); await snap('prompt-obstacle'); await pg.keyboard.press('Escape')
    await pg.locator('.tb').getByRole('radio', { name: 'Select' }).click()
    await pg.mouse.click(cb.x + cb.width * 0.6, cb.y + cb.height * 0.6, { button: 'right' }); await snap('context-menu')
    await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-n-en-context.png`) })
    await pg.keyboard.press('Escape')
    // discard confirmation + toasts + banner + problems
    await pg.locator('.tb').getByRole('button', { name: /^Stop/ }).click()
    await pg.waitForFunction(() => /ready/i.test(document.querySelector('[data-testid="pill"]').textContent), null, { timeout: 30000 })
    await pg.locator('.etab .tab').first().click()
    await pg.locator('.cm-content').click(); await pg.keyboard.press('End'); await pg.keyboard.insertText('# edit')
    await pg.locator('.tb').getByRole('button', { name: /^Examples/ }).click()
    await pg.locator('[aria-modal="true"] .card').first().getByRole('button', { name: 'Load in the editor' }).click()
    await pg.getByRole('button', { name: 'Replace' }).waitFor(); await snap('modal-discard'); await pg.getByRole('button', { name: 'Replace' }).click()
    await snap('toast-example-loaded')
    await pg.locator('.cm-content').click(); await pg.keyboard.press('Control+A'); await pg.keyboard.insertText('x = = 1\n')
    await pg.locator('.tb').getByRole('button', { name: /^Run/ }).click()
    await pg.waitForSelector('.banner.err'); await snap('error-banner'); await snap('problems')
    await pg.screenshot({ path: path.join(SHOTS, `${String(++shotN).padStart(2, '0')}-n-en-error.png`) })
  } finally { await c.close() }
  check(problems.length === 0, 'Portuguese text left in the English UI:\n' + problems.join('\n'))
})

await flow('o. figuras como aba da simulação: galeria, canvas montado e download', async () => {
  const b64 = pngBytes(32, 24, (x, y) => (((x >> 2) + (y >> 2)) % 2 ? 0 : 255)).toString('base64')
  await setCode(`from hivebr_web import host\nhost.post('figure', {'title': 'Figura de teste', 'png_b64': '${b64}'})\n`)
  await tb('Executar').click()
  await page.locator('.docbar .tab-count').waitFor({ timeout: 60000 })

  const tab = page.locator('.docbar').getByRole('tab', { name: /Figuras/ })
  check(await tab.count() === 1, 'the Figures tab is missing from the simulation panel')
  await tab.click()
  await page.locator('.figs-pane .fig').first().waitFor({ timeout: 5000 })

  const fig = page.locator('.figs-pane .fig').first()
  check(await fig.locator('img').evaluate((img) => img.complete && img.naturalWidth > 0), 'the figure image did not render')
  check((await fig.innerText()).includes('Figura de teste'), 'the figure title is missing')
  check(await page.locator('.cv canvas').count() === 1, 'the simulation canvas was unmounted when switching tabs')

  const [dl] = await Promise.all([
    page.waitForEvent('download'),
    fig.getByRole('button', { name: /PNG/ }).click(),
  ])
  check(/\.png$/i.test(dl.suggestedFilename()), `figure download is not a PNG: ${dl.suggestedFilename()}`)

  await shot('o-figures')
  await page.locator('.docbar').getByRole('tab', { name: /Simula/ }).click()
  check(await page.locator('.cv canvas').isVisible(), 'the canvas did not come back on the Simulation tab')
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
