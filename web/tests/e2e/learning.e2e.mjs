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

async function openLearning() {
  if (await learningModal.isVisible().catch(() => false)) return
  await page.locator('.tb').getByRole('button', { name: /^Aprender/ }).click()
  await learningModal.waitFor()
}

async function startActivity(id) {
  await openLearning()
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

// ------------------------------------------------------------------ phase 4
const STUDENT_KEY = 'hivebr.web.student.v1'
const ID_RE = /^HB-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/
const studentState = () => page.evaluate((key) => JSON.parse(localStorage.getItem(key) || '{}'), STUDENT_KEY)

async function exportBundle({ password = '' } = {}) {
  await openLearning()
  await learningModal.getByRole('button', { name: 'Exportar progresso' }).click()
  const prompt = page.locator('[role="dialog"][aria-label="Exportar progresso"]')
  await prompt.waitFor()
  if (password) {
    await prompt.locator('#pf-password').fill(password)
    await prompt.locator('#pf-confirm').fill(password)
  }
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    prompt.getByRole('button', { name: 'Exportar', exact: true }).click(),
  ])
  return download
}

let plainFile = null
let protectedFile = null

await test('student profile is local, readable and kept when progress is reset', async () => {
  await openLearning()
  const profile = learningModal.locator('.profile')
  check(await profile.count() === 1, 'student profile section is missing')
  const id = (await profile.locator('.profile-id b').innerText()).trim()
  check(ID_RE.test(id), `unexpected student id: ${id}`)
  check((await studentState()).id === id, 'student id was not stored locally')

  const inputs = profile.locator('.field-inline input')
  await inputs.nth(0).fill('Ana Silva')
  await inputs.nth(1).fill('Turma A')
  await sleep(250)
  const stored = await studentState()
  check(stored.name === 'Ana Silva', `student name not stored: ${stored.name}`)
  check(stored.group === 'Turma A', `student group not stored: ${stored.group}`)
  await page.screenshot({ path: path.join(SHOTS, 'profile.png') })
})

await test('final report fails the rubric, then passes after the student writes it', async () => {
  await openLearning()
  const finals = learningModal.locator('.final')
  check(await finals.count() === 4, `expected one final project per level: ${await finals.count()}/4`)
  const final = learningModal.locator('.final[data-activity-id="relatorio-final"]')
  check(await final.getByRole('button', { name: 'Submeter para avaliação' }).isDisabled(), 'submit must be disabled before the report is written')

  await final.getByRole('button', { name: /Gerar relatório/ }).click()
  await learningModal.waitFor({ state: 'detached' })
  const editor = page.locator('textarea.md-editor')
  await editor.waitFor()
  const skeleton = await editor.inputValue()
  check(skeleton.includes('hivebr:learning-report'), 'generated report is missing its marker')
  check(skeleton.includes('TODO'), 'generated report is missing the TODO prompts')

  const prose = 'Este relatório descreve a atividade, os resultados obtidos e as dificuldades encontradas. '.repeat(40)
  await editor.fill(skeleton.split('TODO: escreva aqui.').join(prose))
  await sleep(300)

  await openLearning()
  const okChecks = learningModal.locator('.final[data-activity-id="relatorio-final"] .rubric li.ok')
  check(await okChecks.count() === 4, `rubric not satisfied after writing: ${await okChecks.count()}/4`)
  const before = await progress()
  await final.getByRole('button', { name: 'Submeter para avaliação' }).click()
  await learningModal.waitFor({ state: 'detached' })
  await sleep(300)
  const after = await progress()
  check(after.activities?.['relatorio-final']?.done === true, 'capstone activity was not completed')
  check(after.badges?.includes('relatorio'), 'report badge was not awarded')
  check(after.xp === before.xp + 180, `capstone XP missing: ${before.xp} -> ${after.xp}`)
  await page.screenshot({ path: path.join(SHOTS, 'final-report.png') })
})

await test('progress export downloads a v2 bundle named after the student', async () => {
  const state = await progress()
  const student = await studentState()
  const download = await exportBundle()
  check(
    download.suggestedFilename() === `hivebr-progress-${student.id}.json`,
    `unexpected export name: ${download.suggestedFilename()}`,
  )
  const file = await download.path()
  plainFile = path.join(SHOTS, 'progress-plain.json')
  fs.copyFileSync(file, plainFile)
  const data = JSON.parse(fs.readFileSync(plainFile, 'utf8'))
  check(data.format === 'hivebr-progress' && data.v === 2, 'export is not a v2 bundle')
  check(data.encrypted === false, 'export without a password must be readable')
  check(data.payload?.student?.id === student.id, 'bundle lost the student identity')
  check(data.payload?.progress?.xp === state.xp, `bundle XP ${data.payload?.progress?.xp} differs from stored ${state.xp}`)
  check(Array.isArray(data.payload?.reports), 'bundle lost the reports')
})

await test('progress import accepts a v2 bundle and reports the student', async () => {
  const state = await progress()
  await openLearning()
  await page.locator('input.file-input').setInputFiles(plainFile)
  const confirm = page.locator('[role="dialog"][aria-label="Importar progresso"]')
  await confirm.waitFor()
  const text = await confirm.innerText()
  check(text.includes('Importar o progresso de'), `unexpected import message: ${text}`)
  await confirm.getByRole('button', { name: 'Importar', exact: true }).click()
  await sleep(500)
  const imported = await progress()
  check(imported.xp === state.xp, `imported XP changed: ${state.xp} -> ${imported.xp}`)
  check(imported.activities?.['relatorio-final']?.done === true, 'import lost the capstone activity')
})

await test('protected export encrypts the bundle and protected import restores it', async () => {
  const before = await progress()
  const download = await exportBundle({ password: 'segredo42' })
  const file = await download.path()
  protectedFile = path.join(SHOTS, 'progress-protected.json')
  fs.copyFileSync(file, protectedFile)
  const data = JSON.parse(fs.readFileSync(protectedFile, 'utf8'))
  check(data.encrypted === true, 'protected export must be encrypted')
  check(data.crypto?.kdf === 'PBKDF2-SHA256' && data.crypto?.alg === 'AES-GCM', 'unexpected crypto metadata')
  check(typeof data.payload === 'string' && !data.payload.includes('"xp"'), 'encrypted payload must be opaque')

  // Reset through the UI: the identity must stay, the progress must go.
  await openLearning()
  await learningModal.getByRole('button', { name: 'Zerar progresso' }).click()
  const reset = page.locator('[role="dialog"][aria-label="Zerar progresso"]')
  await reset.waitFor()
  await reset.getByRole('button', { name: 'Zerar', exact: true }).click()
  await sleep(400)
  check(((await progress()).xp || 0) === 0, 'reset did not clear the XP')
  check(!!(await studentState()).id, 'reset must keep the student identity')

  // Wrong password is rejected without touching the progress.
  await page.locator('input.file-input').setInputFiles(protectedFile)
  const password = page.locator('[role="dialog"][aria-label="Importar progresso protegido"]')
  await password.waitFor()
  await password.locator('#pf-password').fill('errada')
  await password.getByRole('button', { name: 'Importar', exact: true }).click()
  await sleep(500)
  check(await page.locator('.toast').filter({ hasText: 'Senha incorreta' }).count() >= 1, 'wrong password did not warn the user')
  check(((await progress()).xp || 0) === 0, 'wrong password changed the progress')

  // Correct password restores the exported state.
  await page.locator('input.file-input').setInputFiles(protectedFile)
  const again = page.locator('[role="dialog"][aria-label="Importar progresso protegido"]')
  await again.waitFor()
  await again.locator('#pf-password').fill('segredo42')
  await again.getByRole('button', { name: 'Importar', exact: true }).click()
  const confirm = page.locator('[role="dialog"][aria-label="Importar progresso"]')
  await confirm.waitFor()
  await confirm.getByRole('button', { name: 'Importar', exact: true }).click()
  await sleep(600)
  const restored = await progress()
  check(restored.xp === before.xp, `protected import lost XP: ${before.xp} -> ${restored.xp}`)
  check(restored.activities?.['relatorio-final']?.done === true, 'protected import lost the capstone activity')
  await page.screenshot({ path: path.join(SHOTS, 'protected-import.png') })
})

await test('malformed progress files are rejected', async () => {
  const state = await progress()
  const bad = path.join(SHOTS, 'progress-bad.json')
  fs.writeFileSync(bad, '{ not json')
  await openLearning()
  await page.locator('input.file-input').setInputFiles(bad)
  await sleep(400)
  check(await page.locator('.toast').filter({ hasText: 'inválido' }).count() >= 1, 'malformed import did not warn the user')
  const still = await progress()
  check(still.xp === state.xp, 'malformed import changed the progress')
})

// ------------------------------------------------------------------ phase 6
const TEACHER_KEY = 'hivebr.web.teacher.v1'
const teacherState = () => page.evaluate((key) => JSON.parse(localStorage.getItem(key) || '{}'), TEACHER_KEY)

async function closeLearning() {
  if (await learningModal.isVisible().catch(() => false)) {
    await page.keyboard.press('Escape')
    await learningModal.waitFor({ state: 'detached' })
  }
}

async function openMenu(label) {
  // Hovering another top item opens it, so a click on a menu that is already
  // open only closes it. Start from a clean state.
  await page.keyboard.press('Escape')
  await page.locator('.mb .menus').getByRole('menuitem', { name: label, exact: true }).click()
}

async function openClassMenu(label) {
  await openMenu('Turma')
  await page.locator('.mb .drop').getByRole('menuitem', { name: label, exact: true }).click()
}

async function openTeacher() {
  await openClassMenu('Modo professor')
  const modal = page.locator('[role="dialog"][aria-label="Modo professor"]')
  await modal.waitFor()
  return modal
}

await test('student chip shows the name and class and opens the profile', async () => {
  await closeLearning()
  const chip = page.locator('.mb .chip')
  check(await chip.isVisible(), 'student chip is not visible in the menu bar')
  const text = (await chip.innerText()).replace(/\s+/g, ' ').trim()
  check(text.includes('Ana Silva') && text.includes('Turma A'), `chip is missing name/class: ${text}`)

  await chip.click()
  const modal = page.locator('[role="dialog"][aria-label="Meu perfil"]')
  await modal.waitFor()
  check((await modal.locator('#sp-name').inputValue()) === 'Ana Silva', 'profile modal did not load the name')
  check((await modal.locator('#sp-group').inputValue()) === 'Turma A', 'profile modal did not load the class')

  await modal.locator('#sp-group').fill('Turma B')
  await modal.getByRole('button', { name: 'Salvar perfil' }).click()
  await modal.waitFor({ state: 'detached' })
  check((await studentState()).group === 'Turma B', 'class was not saved from the profile modal')
  const updated = (await page.locator('.mb .chip').innerText()).replace(/\s+/g, ' ')
  check(updated.includes('Turma B'), `chip did not follow the new class: ${updated}`)
  await page.screenshot({ path: path.join(SHOTS, 'student-chip.png') })
})

await test('changing the class updates the report identification in place', async () => {
  // The import tests replace the reports and close their tabs, so reopen the
  // saved learning report before checking the identification block.
  const panel = page.locator('aside.side.right.reports')
  if (!(await panel.count())) {
    await openMenu('Exibir')
    await page.locator('.mb .drop').getByRole('menuitemcheckbox', { name: /Relatórios/ }).click()
    await panel.waitFor()
  }
  const editor = page.locator('textarea.md-editor')
  if (!(await editor.isVisible().catch(() => false))) {
    const saved = panel.locator('.saved-row').filter({ hasText: 'relatorio_nivel_4' })
    await saved.locator('button').first().click()
  }
  await editor.waitFor()
  const content = await editor.inputValue()
  check(content.includes('| Turma | Turma B |'), 'report identification did not follow the profile')
  check(content.includes('| Aluno(a) | Ana Silva |'), 'report lost the student name')
  check(content.includes('Este relatório descreve'), 'report prose was overwritten by the identification sync')
  await page.screenshot({ path: path.join(SHOTS, 'report-identity.png') })
})

await test('teacher mode sets a keyword, imports a bundle and exports the class sheet', async () => {
  const modal = await openTeacher()
  await modal.locator('#tf-name').fill('Prof. Souza')
  await modal.locator('#tf-school').fill('Escola Modelo')
  await modal.locator('#tf-keyword').fill('turma2026')
  await modal.locator('#tf-keyword-confirm').fill('turma2026')
  await modal.getByRole('button', { name: 'Ativar modo professor' }).click()
  await sleep(400)

  const stored = await teacherState()
  check(stored.configured === true, 'teacher mode was not stored')
  check(!JSON.stringify(stored).includes('turma2026'), 'the plain keyword must never be stored')
  check((await modal.locator('.roster').count()) === 0, 'the roster should start empty')

  const beforeXp = (await progress()).xp
  await modal.locator('input.teacher-file').setInputFiles(plainFile)
  const rows = modal.locator('.roster tr[data-student-id]')
  await rows.first().waitFor()
  check((await rows.count()) === 1, 'the student bundle was not imported into the roster')
  const rowText = (await rows.first().innerText()).replace(/\s+/g, ' ')
  check(rowText.includes('Ana Silva') && rowText.includes('Turma A'), `roster row is wrong: ${rowText}`)
  check(rowText.includes('Incompleto') && rowText.includes('1/4'), `roster row should show the partial report count: ${rowText}`)
  // The import must not touch the local student progress.
  check((await progress()).xp === beforeXp, 'teacher import changed the local progress')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    modal.getByRole('button', { name: 'Exportar planilha' }).click(),
  ])
  const csvFile = path.join(SHOTS, 'turma.csv')
  await download.saveAs(csvFile)
  const csv = fs.readFileSync(csvFile, 'utf8')
  check(csv.startsWith('\ufeff'), 'the class sheet must start with a UTF-8 BOM')
  check(csv.includes('Identificador;Aluno;Turma;XP'), `CSV header is not localized: ${csv.slice(0, 120)}`)
  check(csv.includes('Ana Silva') && csv.includes('HB-'), 'CSV lost the student row')
  check(csv.includes(';1/4;'), 'CSV should count the completed level reports')
  await page.screenshot({ path: path.join(SHOTS, 'teacher.png') })
})

await test('teacher panel locks on exit and only unlocks with the keyword', async () => {
  const modal = page.locator('[role="dialog"][aria-label="Modo professor"]')
  await modal.getByRole('button', { name: 'Sair', exact: true }).click()
  await modal.getByRole('button', { name: 'Fechar' }).click()
  await modal.waitFor({ state: 'detached' })

  const locked = await openTeacher()
  check((await locked.locator('#tf-unlock').count()) === 1, 'locked panel should ask for the keyword')
  await locked.locator('#tf-unlock').fill('errada')
  await locked.getByRole('button', { name: 'Entrar', exact: true }).click()
  await sleep(400)
  check(
    (await page.locator('.toast').filter({ hasText: 'Palavra-chave incorreta' }).count()) >= 1,
    'a wrong keyword did not warn the user',
  )

  await locked.locator('#tf-unlock').fill('turma2026')
  await locked.getByRole('button', { name: 'Entrar', exact: true }).click()
  await locked.locator('.roster').waitFor()
  check((await locked.locator('.roster tr[data-student-id]').count()) === 1, 'the roster was lost after unlocking')
  await page.screenshot({ path: path.join(SHOTS, 'teacher-unlocked.png') })
  await locked.getByRole('button', { name: 'Fechar' }).click()
  await locked.waitFor({ state: 'detached' })
})

await test('each level submits its own report without overwriting the previous one', async () => {
  await openLearning()
  const final1 = learningModal.locator('.final[data-activity-id="projeto-final-1"]')
  check(await final1.count() === 1, 'level 1 final project section is missing')
  check(await final1.getByRole('button', { name: 'Submeter para avaliação' }).isDisabled(), 'level 1 submit must start disabled')

  await final1.getByRole('button', { name: /Gerar relatório/ }).click()
  await learningModal.waitFor({ state: 'detached' })
  const editor = page.locator('textarea.md-editor')
  await editor.waitFor()
  const skeleton = await editor.inputValue()
  check(skeleton.includes('Relatório final — Nível 1'), `level 1 report title is wrong: ${skeleton.slice(0, 80)}`)
  const prose = 'Este projeto descreve a atividade do nível um e os resultados obtidos. '.repeat(25)
  await editor.fill(skeleton.split('TODO: escreva aqui.').join(prose))
  await sleep(300)

  await openLearning()
  const okChecks = learningModal.locator('.final[data-activity-id="projeto-final-1"] .rubric li.ok')
  check(await okChecks.count() === 4, `level 1 rubric not satisfied: ${await okChecks.count()}/4`)
  const before = await progress()
  await learningModal.locator('.final[data-activity-id="projeto-final-1"]')
    .getByRole('button', { name: 'Submeter para avaliação' }).click()
  await learningModal.waitFor({ state: 'detached' })
  await sleep(300)
  const after = await progress()
  check(after.activities?.['projeto-final-1']?.done === true, 'level 1 final project was not completed')
  check(after.badges?.includes('projeto1'), 'level 1 project badge was not awarded')
  check(after.xp === before.xp + 120, `level 1 project XP missing: ${before.xp} -> ${after.xp}`)
  check(after.activities?.['relatorio-final']?.done === true, 'the level 4 report was overwritten')
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
