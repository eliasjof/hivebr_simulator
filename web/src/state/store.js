import { reactive, shallowRef, markRaw, ref, watch } from 'vue'
import { SimClient } from '../runtime/client.js'
import { CATALOG, DEFAULT_EXAMPLE_ID, DEMO_EXAMPLE_ID } from '../examples/catalog.js'

const LS = {
  windows: 'hivebr.web.windows.v1',
  prefs: 'hivebr.web.prefs.v1',
  code: 'hivebr.web.code.v1',
  baseline: 'hivebr.web.baseline.v1',
  tabs: 'hivebr.web.tabs.v1',
  reports: 'hivebr.web.reports.v1',
}
function lsGet(key, fallback) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback } catch { return fallback }
}
function lsSet(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* cota cheia */ }
}

export const WINDOW_DEFS = {
  params: { title: 'Parâmetros', shortcut: 'P', icon: 'sliders' },
  plots: { title: 'Gráficos', shortcut: 'G', icon: 'chart' },
  map: { title: 'Mapa', shortcut: 'K', icon: 'map' },
  robots: { title: 'Telemetria', shortcut: 'B', icon: 'robot' },
}

export const TOP = 84
export const BOTTOM = 30

function viewport() {
  return { vw: window.innerWidth, vh: window.innerHeight }
}

export function defaultGeometry(id, order = 0) {
  const { vw, vh } = viewport()
  const avail = Math.max(240, vh - TOP - BOTTOM)
  if (vw < 900) {
    const off = Math.min(order * 14, 60)
    return { x: 8 + off, y: TOP + off, w: vw - 16 - off, h: Math.round(avail * 0.7) }
  }
  switch (id) {
    case 'robots': return { x: vw - 340, y: TOP + 8, w: 320, h: Math.min(avail, 480) }
    case 'params': return { x: vw - 380, y: TOP + 24, w: 340, h: Math.min(avail, 560) }
    case 'plots': return { x: Math.max(260, vw - 880), y: TOP + 16, w: Math.min(820, vw - 280), h: Math.min(avail, 640) }
    case 'map': return { x: vw - 400, y: TOP + 40, w: 360, h: Math.min(avail, 580) }
    default: return { x: 100, y: TOP, w: 420, h: 360 }
  }
}

const savedWin = lsGet(LS.windows, {})
let zCounter = 10
export const windows = reactive({})
Object.keys(WINDOW_DEFS).forEach((id, i) => {
  const s = savedWin[id] || {}
  const g = defaultGeometry(id, i)
    windows[id] = {
    open: s.open ?? false,
    minimized: !!s.minimized,
    maximized: !!s.maximized,
    x: s.x ?? g.x, y: s.y ?? g.y, w: s.w ?? g.w, h: s.h ?? g.h,
    z: ++zCounter,
  }
})
function persistWindows() {
  const out = {}
  for (const [id, w] of Object.entries(windows)) {
    out[id] = { open: w.open, minimized: w.minimized, maximized: w.maximized, x: w.x, y: w.y, w: w.w, h: w.h }
  }
  lsSet(LS.windows, out)
}
let winTimer = null
function schedulePersist() { clearTimeout(winTimer); winTimer = setTimeout(persistWindows, 250) }

const prefs = lsGet(LS.prefs, {})
const initialTheme = prefs.theme || 'light'

const defaultExample = CATALOG.find((e) => e.id === DEFAULT_EXAMPLE_ID) || CATALOG[0]
let tabsInit = lsGet(LS.tabs, null)
if (!tabsInit || !Array.isArray(tabsInit.tabs) || !tabsInit.tabs.length) {
  const legacy = localStorage.getItem(LS.code) != null ? lsGet(LS.code, '') : (defaultExample?.source ?? '')
  const base = localStorage.getItem(LS.baseline) != null ? lsGet(LS.baseline, '') : (defaultExample?.source ?? '')
  tabsInit = { activeId: 't1', tabs: [{ id: 't1', name: defaultExample ? `${defaultExample.id}.py` : 'meu_script.py', code: legacy, baseline: base }] }
}
if (!tabsInit.tabs.some((t) => t.id === tabsInit.activeId)) tabsInit.activeId = tabsInit.tabs[0].id
const activeInit = tabsInit.tabs.find((t) => t.id === tabsInit.activeId)

const LAYOUT_DEFAULTS = { leftOpen: true, rightOpen: true, bottomOpen: true, leftW: 240, rightW: 460, bottomH: 220, bottomTab: 'console', rightMaximized: false, reportsOpen: false, reportsW: 460, reportsMaximized: false, activeReportId: null, showReportTemplateModal: false }
const client = new SimClient()

// ---- reports ----
const savedReports = lsGet(LS.reports, [])
const initialReports = savedReports.length ? savedReports : [{
  id: 'rpt_welcome',
  name: 'welcome.md',
  content: '# Welcome\n\nStart writing reports here...',
  created: Date.now(),
  modified: Date.now()
}]
export const reports = reactive(initialReports)

function persistReports() {
  lsSet(LS.reports, reports.map(r => ({ ...r })))
}
watch(reports, persistReports, { deep: true })

// ---- captures (localStorage) ----
const savedCaptures = lsGet('hivebr.web.captures.v1', [])
export const captures = reactive(savedCaptures.length ? savedCaptures : [{
  id: 'cap_welcome',
  name: 'welcome.png',
  dataUrl: '',
  created: Date.now()
}])

function persistCaptures() {
  lsSet('hivebr.web.captures.v1', captures.map(c => ({ ...c })))
}
watch(captures, persistCaptures, { deep: true })

export const store = reactive({
  client: markRaw(client),
  // boot
  boot: { stage: 'init', progress: 0, text: 'Iniciando…', ready: false, dismissed: false, version: '' },
  interactive: true,
  warnDismissed: false,
  fatal: null,
  // execução
  run: { state: 'idle' }, // idle | starting | running | stopping
  hasRun: false,
  autostart: prefs.autostart ?? true,
  speed: prefs.speed ?? 1,
  selected: 0,
  // editor
  tabs: tabsInit.tabs,
  activeId: tabsInit.activeId,
  code: activeInit.code,
  codeRev: 0,
  baseline: activeInit.baseline ?? activeInit.code,
  readonly: false,
  saveState: 'saved', // saved | pending
  fileName: activeInit.name,
  editorApi: null,
  jumpLine: null,
  layout: { ...LAYOUT_DEFAULTS, ...(prefs.layout || {}) },
  narrow: window.innerWidth < 1100,
  vw: window.innerWidth,
  sceneCounts: { obstacles: 0, recharge: 0, waypoints: 0 },
  zoomPct: 100,
  error: null,
  // cena
  tool: 'select',
  options: {
    showGrid: prefs.options?.showGrid ?? true,
    showPaths: prefs.options?.showPaths ?? true,
    showLidar: prefs.options?.showLidar ?? true,
    showWaypoints: prefs.options?.showWaypoints ?? true,
    showLabels: prefs.options?.showLabels ?? true,
    showLinks: prefs.options?.showLinks ?? true,
    themeOverride: initialTheme,
  },
  theme: initialTheme,
  obstacleRadius: prefs.obstacleRadius ?? 0.4,
  mapResolution: prefs.mapResolution ?? 0.05,
  // estatísticas (≤4 Hz)
  stats: { t: 0, rtf: 0, fps: 0, running: false, step: 0, collisions: 0 },
  cursor: { x: null, y: null },
  // janelas
  windows,
  // reports
  reports,
  activeReportId: null,
  // captures
  captures,
  // UI
  toasts: [],
  ctx: null,
  modals: { examples: false, help: false, about: false },
  prompt: null,
  figures: [],
  consoleUnread: 0,
})

// ---- refs não reativos profundamente ----
export const scene = shallowRef(null)
export const telemetry = shallowRef(null)
export const logData = shallowRef(null)
export const files = shallowRef([])
export const canvasRef = shallowRef(null)

// ---- console ----
export const consoleBus = {
  lines: [],
  subs: new Set(),
  push(kind, text) {
    const l = { kind, text: String(text), t: Date.now() }
    this.lines.push(l)
    if (this.lines.length > 5000) this.lines.splice(0, this.lines.length - 5000)
    this.subs.forEach((fn) => fn(l))
  },
  clear() {
    this.lines.length = 0
    this.subs.forEach((fn) => fn(null))
  },
}

// ---- toasts ----
let toastId = 0
export function toast(text, level = 'info', ms = 5000) {
  const id = ++toastId
  store.toasts.push({ id, text, level })
  if (store.toasts.length > 5) store.toasts.shift()
  setTimeout(() => dismissToast(id), ms)
}
export function dismissToast(id) {
  const i = store.toasts.findIndex((t) => t.id === id)
  if (i >= 0) store.toasts.splice(i, 1)
}

// ---- prompts ----
export function ask(cfg) {
  return new Promise((resolve) => {
    store.prompt = { cfg, resolve }
  })
}
export function resolvePrompt(value) {
  const p = store.prompt
  store.prompt = null
  p?.resolve(value)
}

// ---- janelas ----
export function clampWindow(w) {
  const { vw, vh } = viewport()
  w.w = Math.max(240, Math.min(w.w, vw))
  w.h = Math.max(120, Math.min(w.h, vh - 8))
  w.x = Math.max(-w.w + 80, Math.min(w.x, vw - 80))
  w.x = Math.max(Math.min(0, w.x), Math.min(w.x, vw - Math.min(w.w, 120)))
  w.y = Math.max(0, Math.min(w.y, vh - 40))
}
export function focusWindow(id) { windows[id].z = ++zCounter }
export function openWindow(id) {
  const w = windows[id]
  w.open = true
  w.minimized = false
  clampWindow(w)
  focusWindow(id)
}
export function closeWindow(id) { windows[id].open = false; windows[id].minimized = false }
export function toggleWindow(id) {
  const w = windows[id]
  if (w.open && !w.minimized) closeWindow(id)
  else openWindow(id)
}
export function resetLayout() {
  Object.keys(WINDOW_DEFS).forEach((id, i) => {
    Object.assign(windows[id], defaultGeometry(id, i), { maximized: false, minimized: false })
  })
  Object.assign(store.layout, LAYOUT_DEFAULTS)
}
watch(windows, schedulePersist, { deep: true })

// ---- preferências ----
function persistPrefs() {
  lsSet(LS.prefs, {
    theme: store.theme, autostart: store.autostart, speed: store.speed, options: { ...store.options },
    obstacleRadius: store.obstacleRadius, mapResolution: store.mapResolution, layout: { ...store.layout },
  })
}
watch(() => [store.theme, store.autostart, store.speed, store.obstacleRadius, store.mapResolution, { ...store.layout }, { ...store.options }], persistPrefs, { deep: true })

export function applyTheme(theme) {
  store.theme = theme
  store.options.themeOverride = theme
  document.documentElement.dataset.theme = theme
}
export function toggleTheme() { applyTheme(store.theme === 'dark' ? 'light' : 'dark') }
applyTheme(initialTheme)

// ---- código (abas) ----
let saveTimer = null
let tabSeq = 1
store.tabs.forEach((t) => { const n = parseInt(String(t.id).slice(1), 10); if (n > tabSeq) tabSeq = n })
const activeTab = () => store.tabs.find((t) => t.id === store.activeId)
function syncActive() {
  const t = activeTab()
  if (!t || t.readonly) return
  t.code = store.code; t.baseline = store.baseline; t.name = store.fileName
}
function loadTab(t) {
  store.activeId = t.id
  store.code = t.code
  store.baseline = t.baseline ?? t.code
  store.fileName = t.name
  store.readonly = !!t.readonly
  store.codeRev++
}
export function switchTab(id) {
  if (id === store.activeId) return
  syncActive()
  const t = store.tabs.find((x) => x.id === id)
  if (t) { loadTab(t); store.error = null; saveNow() }
}
export function addTab(name, code, { readonly = false, activate = true } = {}) {
  syncActive()
  const t = { id: 't' + ++tabSeq, name, code, baseline: code, readonly }
  store.tabs.push(t)
  if (activate) loadTab(t)
  saveNow()
  return t
}
export function closeTab(id) {
  const i = store.tabs.findIndex((t) => t.id === id)
  if (i < 0) return
  const wasActive = id === store.activeId
  if (wasActive) syncActive()
  store.tabs.splice(i, 1)
  if (!store.tabs.length) addTab('meu_script.py', '')
  else if (wasActive) loadTab(store.tabs[Math.min(i, store.tabs.length - 1)])
  saveNow()
}
export function setCode(text) {
  if (store.readonly) return
  store.code = text
  store.saveState = 'pending'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(saveNow, 800)
}
export function saveNow() {
  clearTimeout(saveTimer)
  syncActive()
  lsSet(LS.tabs, {
    activeId: store.activeId === 'demo' || store.readonly ? (store.tabs.find((t) => !t.readonly)?.id) : store.activeId,
    tabs: store.tabs.filter((t) => !t.readonly).map((t) => ({ id: t.id, name: t.name, code: t.code, baseline: t.baseline })),
  })
  store.saveState = 'saved'
}
export function replaceCode(text, { baseline = true, fileName } = {}) {
  if (store.readonly) { addTab(fileName || 'meu_script.py', text); store.error = null; return }
  store.code = text
  if (baseline) store.baseline = text
  if (fileName) store.fileName = fileName
  store.codeRev++
  store.error = null
  saveNow()
}
export function hasUserEdits() { return !store.readonly && store.code !== store.baseline && store.code.trim() !== '' }

export async function confirmDiscard(what) {
  if (!hasUserEdits()) return true
  const r = await ask({
    title: 'Descartar alterações?',
    message: `O script ativo tem alterações que ainda não foram salvas em arquivo. ${what} substituirá o conteúdo atual.`,
    confirmText: 'Substituir',
    danger: true,
  })
  return !!r
}
export async function loadExample(ex) {
  if (!(await confirmDiscard(`Carregar “${ex.title}”`))) return false
  replaceCode(ex.source, { fileName: `${ex.id}.py` })
  store.modals.examples = false
  openPanel('right')
  toast(`Exemplo “${ex.title}” carregado.`)
  return true
}
export function newFile() {
  addTab(`script_${tabSeq + 1}.py`, '')
  openPanel('right')
}

// ---- demonstração (aba somente leitura, não altera o script do usuário) ----
export async function runDemo() {
  const ex = CATALOG.find((e) => e.id === DEMO_EXAMPLE_ID)
  if (!ex) { toast('Demonstração indisponível.', 'warn'); return }
  let t = store.tabs.find((x) => x.readonly)
  if (t) { syncActive(); t.code = ex.source; loadTab(t) } else addTab('Demonstração', ex.source, { readonly: true })
  store.error = null
  openPanel('right')
  if (store.run.state !== 'idle') {
    await new Promise((resolve) => {
      let off = null
      const done = () => { off?.(); resolve() }
      off = client.on('finished', done)
      setTimeout(done, 6000)
      stopCode()
    })
  }
  if (!store.boot.ready) { toast('Aguarde o Python terminar de carregar para executar a demonstração.', 'warn'); return }
  runCode()
}
export function duplicateDemo() {
  const t = activeTab()
  if (!t?.readonly) return
  addTab('minha_demonstracao.py', t.code)
  toast('Demonstração duplicada para edição.')
}

// ---- painéis ----
export function openPanel(which, tab) {
  if (which === 'left') store.layout.leftOpen = true
  if (which === 'right') store.layout.rightOpen = true
  if (which === 'bottom') { store.layout.bottomOpen = true; if (tab) store.layout.bottomTab = tab }
  if (store.narrow && which !== 'bottom') { if (which === 'left') store.layout.rightOpen = false; else store.layout.leftOpen = false }
}
export function togglePanel(which) {
  const k = which + 'Open'
  if (store.layout[k]) store.layout[k] = false
  else openPanel(which)
}
export function toggleRightMaximized() {
  store.layout.rightMaximized = !store.layout.rightMaximized
  if (store.layout.rightMaximized) {
    store.layout._prevLeft = store.layout.leftOpen
    store.layout._prevBottom = store.layout.bottomOpen
    store.layout.leftOpen = false
    store.layout.bottomOpen = false
    store.layout.rightOpen = true
  } else {
    store.layout.leftOpen = store.layout._prevLeft ?? true
    store.layout.bottomOpen = store.layout._prevBottom ?? true
  }
}
export function toggleReportsMaximized() {
  store.layout.reportsMaximized = !store.layout.reportsMaximized
  if (store.layout.reportsMaximized) {
    store.layout._prevLeft = store.layout.leftOpen
    store.layout._prevBottom = store.layout.bottomOpen
    store.layout.leftOpen = false
    store.layout.bottomOpen = false
    store.layout.reportsOpen = true
  } else {
    store.layout.leftOpen = store.layout._prevLeft ?? true
    store.layout.bottomOpen = store.layout._prevBottom ?? true
  }
}
export function toggleReportsPanel() {
  store.layout.reportsOpen = !store.layout.reportsOpen
  if (store.layout.reportsOpen) {
    store.layout.rightOpen = false // close code panel when opening reports
  }
}
export function toggleReportTemplateModal() {
  store.layout.showReportTemplateModal = !store.layout.showReportTemplateModal
  if (store.layout.showReportTemplateModal) {
    store.layout.reportsOpen = true
    store.layout.rightOpen = false
  }
}
export function openReport(id) {
  store.activeReportId = id
  store.layout.reportsOpen = true
  store.layout.rightOpen = false
}
export function closeReportsPanel() {
  store.layout.reportsOpen = false
  store.activeReportId = null
}
// ---- reports ----
export function createReport() {
  const id = 'rpt_' + Date.now()
  const r = { id, name: `report_${reports.length + 1}.md`, content: '# New Report\n\n', created: Date.now(), modified: Date.now() }
  reports.push(r)
  openReport(id)
  return r
}
export function deleteReport(id) {
  const i = reports.findIndex(r => r.id === id)
  if (i >= 0) reports.splice(i, 1)
  if (store.activeReportId === id) store.activeReportId = null
}
// ---- captures ----
export function addCapture(dataUrl) {
  const id = 'cap_' + Date.now()
  const name = `sim_${captures.length + 1}.png`
  const capture = { id, name, dataUrl, created: Date.now() }
  captures.unshift(capture) // newest first
  if (captures.length > 50) captures.pop() // limit to 50
  return capture
}
export function deleteCapture(id) {
  const i = captures.findIndex(c => c.id === id)
  if (i >= 0) captures.splice(i, 1)
}
export function getCaptureDataUrl(id) {
  const c = captures.find(c => c.id === id)
  return c?.dataUrl
}
export function focusEditor() { openPanel('right'); setTimeout(() => store.editorApi?.focus(), 30) }
export function gotoLine(n) { openPanel('right'); store.jumpLine = { line: n, n: Date.now() } }

export function download(name, blob) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
export function b64ToBlob(b64, mime = 'application/octet-stream') {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type: mime })
}
export function bytesToB64(buf) {
  const bytes = new Uint8Array(buf)
  let s = ''
  const chunk = 0x8000
  for (let i = 0; i < bytes.length; i += chunk) s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk))
  return btoa(s)
}

// ---- comandos ----
let lastWarn = 0
export function send(cmd) {
  let ok = false
  try { ok = client.send(cmd) } catch (e) { console.warn('send falhou', e) }
  if (!ok && Date.now() - lastWarn > 4000) {
    lastWarn = Date.now()
    toast(store.interactive ? 'Execute um código para interagir com a simulação.' : 'Comandos ao vivo indisponíveis neste navegador (modo limitado).', 'warn')
  }
  return ok
}
export function runCode() {
  if (!store.boot.ready || store.run.state !== 'idle') return
  consoleBus.clear()
  store.error = null
  store.run.state = 'starting'
  store.hasRun = true
  scene.value = null
  telemetry.value = null
  store.stats.running = false
  Object.assign(store.sceneCounts, { obstacles: 0, recharge: 0, waypoints: 0 })
  files.value = []
  store.figures = []
  saveNow()
  client.run(store.code, { autostart: store.autostart }).catch((e) => {
    store.run.state = 'idle'
    toast(String(e?.message || e), 'error')
  })
}
export function stopCode() {
  if (store.run.state === 'idle' || store.run.state === 'stopping') return
  store.run.state = 'stopping'
  client.stop()
}
export function toggleRun() { store.run.state === 'idle' ? runCode() : stopCode() }
export function toggleSim() { send({ cmd: 'toggle' }) }
export function stepOnce() { send({ cmd: 'step_once' }) }
export function resetSim() { send({ cmd: 'reset' }) }
export function setSpeed(f) { store.speed = f; send({ cmd: 'set_speed', factor: f === Infinity ? 0 : f }) }
export function selectRobot(i) { store.selected = i; send({ cmd: 'select_robot', index: i }) }
export function robotCount() { return scene.value?.robots?.length ?? 0 }

// ---- frames ----
let latest = null
let fpsCount = 0
let lastTele = 0
let seq = 0
let teleSeq = 0
export function latestFrame() { return latest }

function onFrame(f) {
  latest = f
  seq++
  fpsCount++
  canvasRef.value?.pushFrame(f)
  if (f.obstacles) { store.sceneCounts.obstacles = f.obstacles.length; store.sceneCounts.recharge = f.recharge?.length || 0 }
  if (f.waypoints) store.sceneCounts.waypoints = f.waypoints.reduce((a, l) => a + l.length, 0)
}
setInterval(() => {
  const now = performance.now()
  const dt = now - lastTele
  lastTele = now
  const fps = Math.round((fpsCount * 1000) / Math.max(dt, 1))
  fpsCount = 0
  if (seq !== teleSeq && latest) {
    teleSeq = seq
    telemetry.value = latest
    const s = store.stats
    s.t = latest.t; s.rtf = latest.realtime_factor ?? 0; s.running = !!latest.running
    s.step = latest.step ?? 0; s.collisions = latest.collisions_total ?? 0
    if (typeof latest.selected === 'number') store.selected = latest.selected
    if (latest.speed != null && latest.speed !== store.speed && !(latest.speed === 0 && store.speed === Infinity)) {
      store.speed = latest.speed === 0 ? Infinity : latest.speed
    }
  }
  store.stats.fps = fps
}, 200)

// ---- cursor (rAF) ----
let curRaf = 0
export function setCursor(p) {
  if (curRaf) return
  curRaf = requestAnimationFrame(() => { curRaf = 0; store.cursor.x = p.x; store.cursor.y = p.y })
}

// ---- eventos do cliente ----
function wire() {
  const on = (t, fn) => client.on(t, fn)
  on('boot', (p) => {
    // Pacotes carregados sob demanda durante uma execução não bloqueiam a interface.
    // Depois de pronto, mensagens de carregamento (scipy, imports) não reabrem o estado de boot.
    if (store.boot.ready || client.state === 'running' || client.state === 'stopping' || store.run.state !== 'idle') return
    store.boot.stage = p.stage; store.boot.progress = p.progress ?? 0; store.boot.text = p.text || ''
    store.boot.ready = false
    store.boot.dismissed = false
  })
  on('restart', () => { store.boot.ready = false; store.boot.progress = 0; store.boot.text = 'Reiniciando o interpretador…'; store.boot.dismissed = false })
  on('ready', (p) => {
    store.boot.ready = true
    store.boot.progress = 1
    store.boot.version = p?.pyodide_version || ''
    store.interactive = p?.interactive !== false
    if (store.run.state !== 'idle') store.run.state = 'idle'
  })
  on('stdout', (p) => consoleBus.push('out', p.text))
  on('stderr', (p) => consoleBus.push('err', p.text))
  on('run_started', () => { store.run.state = 'running'; store.hasRun = true })
  on('scene', (p) => {
    scene.value = markRaw(p)
    
  })
  on('frame', onFrame)
  on('log_data', (p) => {
    logData.value = markRaw(p)
    if (p.open) openWindow('plots')
  })
  on('file', (p) => {
    download(p.name, b64ToBlob(p.b64, p.mime))
    toast(`Arquivo “${p.name}” baixado.`)
  })
  on('figure', (p) => {
    store.figures.push(markRaw(p))
    toast(`Figura “${p.title || 'sem título'}” capturada (aba Figuras em Gráficos).`)
  })
  on('notice', (p) => {
    toast(p.text, p.level === 'warn' ? 'warn' : p.level === 'error' ? 'error' : 'info', p.level === 'error' ? 9000 : 5000)
    consoleBus.push('notice', p.text)
  })
  on('finished', (p) => {
    store.run.state = 'idle'
    store.stats.running = false
    files.value = p.files || []
    if (p.error) {
      store.error = p.error
      openPanel('right')
      openPanel('bottom', 'problems')
    } else if (p.stopped) {
      consoleBus.push('notice', 'Execução interrompida.')
    } else {
      consoleBus.push('notice', 'Execução concluída.')
    }
  })
  on('fatal', (p) => { store.fatal = typeof p === 'string' ? p : (p?.message || p?.text || 'Erro fatal ao inicializar o Python.') })
}
wire()

export function startClient() {
  const r = client.init()
  if (r?.catch) r.catch((e) => { store.fatal = String(e?.message || e) })
}

export async function readClientFile(path) {
  return client.readFile(path)
}
export const params = ref(null)

export function setNarrow(v) {
  if (v === store.narrow) return
  store.narrow = v
  if (v) { store.layout.leftOpen = false; store.layout.rightOpen = false }
}

// ---- arquivos ----
export function pickFile() {
  const i = document.createElement('input')
  i.type = 'file'
  i.accept = '.py,text/x-python,text/plain'
  i.onchange = async () => {
    const f = i.files?.[0]
    if (!f) return
    addTab(f.name, await f.text())
    openPanel('right')
    toast(`Arquivo “${f.name}” aberto.`)
  }
  i.click()
}
export function downloadScript() {
  const name = /\.py$/.test(store.fileName) ? store.fileName : store.fileName + '.py'
  download(name, new Blob([store.code], { type: 'text/x-python' }))
  saveNow()
}
export const CATALOGREF = CATALOG
