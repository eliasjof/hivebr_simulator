// Focused end-to-end test for the learning trail on the production build.
//
// One activity per level is started from the UI, the active tab is checked
// against the still-unsolved template the student must edit, the solution is
// typed in, the script is executed and the activity must be marked as done.
// After a reload the same progress (XP, activities and emoji badges) must be
// there.
import http from 'node:http'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const WEB = path.resolve(here, '..', '..')
const dist = path.join(WEB, 'dist')
const SHOTS = process.env.E2E_SHOTS || path.join(os.tmpdir(), 'hivebr-e2e-learning')
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
    // Cross-origin isolation enables the SharedArrayBuffer ring used by the
    // interactive runtime (pause/resume and the other live commands).
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
const results = []
async function test(name, fn) {
  try { await fn(); results.push({ name, ok: true }); console.log('  ok', name) }
  catch (e) { results.push({ name, ok: false, err: e.message }); console.log('  FAIL', name, '-', e.message) }
}

const LS_KEY = 'hivebr.web.learning.v1'
const learningModal = page.locator('[role="dialog"][aria-label="Aprender"]')
const progress = () => page.evaluate((key) => JSON.parse(localStorage.getItem(key) || '{}'), LS_KEY)
const waitReady = (timeout = 240000) => page.waitForFunction(
  () => /pronto/i.test(document.querySelector('[data-testid="pill"]')?.textContent || ''), null, { timeout })

async function boot() {
  await page.goto(BASE)
  await waitReady()
}

async function startActivity(id) {
  await page.locator('.tb').getByRole('button', { name: /^Aprender/ }).click()
  await learningModal.waitFor()
  const act = learningModal.locator(`.act[data-activity-id="${id}"]`)
  await act.scrollIntoViewIfNeeded()
  await act.locator('button.btn.primary').click()
  await sleep(150)
  const confirm = page.getByRole('button', { name: 'Substituir' })
  if (await confirm.isVisible().catch(() => false)) await confirm.click()
  await learningModal.waitFor({ state: 'detached', timeout: 20000 })
}

async function setEditor(code) {
  await page.locator('.cm-content').click()
  await page.keyboard.press('Control+A')
  await page.keyboard.insertText(code)
  await sleep(400)
}

function replaceAll(source, from, to, label) {
  if (!source.includes(from)) throw new Error(`${label}: expected block not found in the template`)
  return source.split(from).join(to)
}

function solved(name) {
  const source = fs.readFileSync(path.join(WEB, 'templates', name), 'utf8')
  if (name === 'python_tipos.py') {
    let out = replaceAll(source, '    # TODO: some todos os valores da lista.\n    raise NotImplementedError', '    return sum(distancias)', name)
    out = replaceAll(out, '    # TODO: use distancia_total e a soma dos tempos.\n    raise NotImplementedError', '    return distancia_total(distancias) / sum(tempos)', name)
    return replaceAll(out, '    # TODO: multiplique por 3.6.\n    raise NotImplementedError', '    return velocidade_ms * 3.6', name)
  }
  if (name === 'cinematica_holonomica.py') {
    return replaceAll(
      source,
      '    # TODO: calcule vx = GANHO * dx e vy = GANHO * dy.\n    vx = 0.0\n    vy = 0.0',
      '    vx = GANHO * dx\n    vy = GANHO * dy',
      name,
    )
  }
  if (name === 'ir_para_pose.py') {
    let out = replaceAll(
      source,
      '        # TODO: va em direcao ao ponto (v e omega).\n        v = 0.0\n        omega = 0.0',
      '        v = min(VMAX, KP_DIST * dist)\n        omega = KP_ANG * ang',
      name,
    )
    return replaceAll(
      out,
      '        # TODO: gire no lugar ate o erro angular ficar pequeno.\n        v = 0.0\n        omega = 0.0',
      '        v = 0.0\n        omega = 2.0 * erro',
      name,
    )
  }
  if (name === 'grid_astar.py') {
    let out = replaceAll(
      source,
      '    # TODO: use math.hypot ou |dx| + |dy|.\n    return 0.0',
      '    return math.hypot(a[0] - b[0], a[1] - b[1])',
      name,
    )
    out = replaceAll(
      out,
      `    # TODO: use heapq, custos g e f e um conjunto fechado.
    return None, 0`,
      `    aberto = [(0.0, inicio)]
    pais = {inicio: None}
    g = {inicio: 0.0}
    fechado = set()
    expandidos = 0
    while aberto:
        _, atual = heapq.heappop(aberto)
        if atual in fechado:
            continue
        fechado.add(atual)
        expandidos += 1
        if atual == objetivo:
            return pais, expandidos
        for vizinho in vizinhos(atual, grade):
            if vizinho in fechado:
                continue
            passo = math.hypot(vizinho[0] - atual[0], vizinho[1] - atual[1])
            novo = g[atual] + passo
            if vizinho not in g or novo < g[vizinho]:
                g[vizinho] = novo
                pais[vizinho] = atual
                heapq.heappush(aberto, (novo + heuristica(vizinho, objetivo), vizinho))
    return None, 0`,
      name,
    )
    return replaceAll(
      out,
      '    # TODO: volte do objetivo ao inicio usando o dicionario de pais.\n    return None',
      `    caminho = []
    atual = objetivo
    while atual is not None:
        caminho.append(atual)
        atual = pais.get(atual)
    if not caminho or caminho[-1] != inicio:
        return None
    return caminho[::-1]`,
      name,
    )
  }
  throw new Error(`no solution for ${name}`)
}

async function runUntilDone(id) {
  await page.locator('.tb').getByRole('button', { name: /^Executar/ }).click()
  await page.waitForFunction(({ key, activity }) => {
    try {
      const p = JSON.parse(localStorage.getItem(key) || '{}')
      return !!p.activities?.[activity]?.done
    } catch {
      return false
    }
  }, { key: LS_KEY, activity: id }, { timeout: 180000 })
  await waitReady(60000)
}

const CASES = [
  { id: 'python-tipos', level: 1, template: 'python_tipos.py', badge: 'pythonista', xp: 40 },
  { id: 'holonomico-vxvy', level: 2, template: 'cinematica_holonomica.py', badge: 'holonomico', xp: 60 },
  { id: 'chegar-alvo-orientacao', level: 3, template: 'ir_para_pose.py', badge: 'orientacao', xp: 80 },
  { id: 'grid-astar', level: 4, template: 'grid_astar.py', badge: 'astar', xp: 110 },
]
await boot()
await page.locator('select.speed').selectOption('4')

for (const item of CASES) {
  await test(`level ${item.level}: ${item.id} is editable, runs and completes`, async () => {
    await startActivity(item.id)
    // The activity must load the right, still-unsolved template. CodeMirror
    // virtualizes long files, so check the active tab name and the file on disk
    // instead of scraping only the visible lines.
    const tabName = (await page.locator('.etab.on .nm').innerText()).trim()
    check(tabName === item.template, `wrong example loaded: ${tabName}`)
    const template = fs.readFileSync(path.join(WEB, 'templates', item.template), 'utf8')
    check(/# TODO/.test(template), 'the template must still contain a TODO for the student')

    const beforeXp = (await progress()).xp || 0
    await setEditor(solved(item.template))
    await runUntilDone(item.id)

    const state = await progress()
    check(state.activities?.[item.id]?.done === true, 'activity was not persisted as done')
    check(state.badges?.includes(item.badge), `badge ${item.badge} was not awarded`)
    check((state.xp || 0) === beforeXp + item.xp, `XP was not awarded: ${beforeXp} -> ${state.xp}`)
    await page.screenshot({ path: path.join(SHOTS, `${item.level}-${item.id}.png`) })
  })
}

await test('progress and emoji badges survive a reload', async () => {
  const before = await progress()
  await page.reload()
  await waitReady()
  const after = await progress()
  check(after.xp === before.xp, `XP changed after reload: ${before.xp} -> ${after.xp}`)
  for (const item of CASES) {
    check(after.activities?.[item.id]?.done === true, `${item.id} was lost after reload`)
  }

  await page.locator('.tb').getByRole('button', { name: /^Aprender/ }).click()
  await learningModal.waitFor()
  for (const item of CASES) {
    const act = learningModal.locator(`.act[data-activity-id="${item.id}"]`)
    check(await act.locator('.pill.done').count() === 1, `${item.id} is not shown as done`)
  }
  const badgeText = (await learningModal.locator('.badge-list').first().innerText()).trim()
  check(/🐍/.test(badgeText), `python badge without emoji: ${badgeText}`)
  check(/🛞/.test(badgeText), `holonomic badge without emoji: ${badgeText}`)
  check(/🧭/.test(badgeText), `orientation badge without emoji: ${badgeText}`)
  check(/⭐/.test(badgeText), `A* badge without emoji: ${badgeText}`)
  check(await learningModal.locator('.badges h3').last().isVisible(), 'achievements section is present')
  await page.screenshot({ path: path.join(SHOTS, 'reload-learning.png') })
})

// ------------------------------------------------------------------ summary
const failed = results.filter((r) => !r.ok)
if (pageErrors.length) console.log('\nPage errors:\n' + pageErrors.join('\n'))
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed` + (pageErrors.length ? `, ${pageErrors.length} page error(s)` : ''))
for (const f of failed) console.log(` - ${f.name}: ${f.err}`)
console.log('screenshots:', SHOTS)
await browser.close()
server.close()
process.exit(failed.length || pageErrors.length ? 1 : 0)
