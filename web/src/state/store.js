import { reactive, shallowRef, markRaw, ref, watch, computed } from 'vue'
import { SimClient } from '../runtime/client.js'
import { getCatalog, DEFAULT_EXAMPLE_ID, DEMO_EXAMPLE_ID } from '../examples/catalog.js'
import { t, tOr, locale, fmtNum } from '../i18n/index.js'

const LS = {
  windows: 'hivebr.web.windows.v1',
  prefs: 'hivebr.web.prefs.v1',
  code: 'hivebr.web.code.v1',
  baseline: 'hivebr.web.baseline.v1',
  tabs: 'hivebr.web.tabs.v1',
  reports: 'hivebr.web.reports.v1',
  clientConfig: 'hivebr.web.client_config.v1',
}
function lsGet(key, fallback) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback } catch { return fallback }
}
function lsSet(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* cota cheia */ }
}

export const WINDOW_DEFS = {
  params: { titleKey: 'win.params', shortcut: 'P', icon: 'sliders', minW: 280, minH: 200, w: 340, h: 560 },
  plots: { titleKey: 'win.plots', shortcut: 'G', icon: 'chart', minW: 360, minH: 260, w: 780, h: 640 },
  map: { titleKey: 'win.map', shortcut: 'K', icon: 'map', minW: 300, minH: 240, w: 360, h: 580 },
  robots: { titleKey: 'win.robots', shortcut: 'B', icon: 'robot', minW: 260, minH: 200, w: 320, h: 480 },
}

// Alturas reais das barras vêm dos tokens CSS (nada de constantes mágicas).
function cssPx(name, fallback) {
  const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name))
  return Number.isFinite(v) ? v : fallback
}
export const menubarH = () => cssPx('--menubar-h', 38)
export const chromeTop = () => menubarH() + cssPx('--toolbar-h', 40)
export const chromeBottom = () => cssPx('--status-h', 24)
const zBase = () => cssPx('--z-float', 100)
const zCeil = () => cssPx('--z-banner', 6000) - 1
const VISIBLE_SIDE = 160 // px da janela que sempre ficam visíveis nas laterais
const KEEP_BELOW = 40    // px da barra de título que sempre ficam acima da borda inferior

function viewport() {
  return { vw: window.innerWidth, vh: window.innerHeight }
}

/** Posição inicial: ancorada à direita, abaixo das barras, em cascata de 16 px (k = ordem mod 5). */
export function defaultGeometry(id, order = 0) {
  const { vw, vh } = viewport()
  const def = WINDOW_DEFS[id] || { w: 420, h: 360 }
  const top = chromeTop()
  const avail = Math.max(240, vh - top - chromeBottom())
  if (vw < 900) {
    const off = Math.min(order * 14, 60)
    return { x: 8 + off, y: top + off, w: vw - 16 - off, h: Math.round(avail * 0.7) }
  }
  const k = order % 5
  const w = Math.min(def.w, vw - 40)
  return { x: Math.max(8, vw - w - 20 - 16 * k), y: top + 6 + 16 * k, w, h: Math.min(def.h, avail) }
}

const savedWin = lsGet(LS.windows, {})
let zCounter = zBase()
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
window.addEventListener('pagehide', persistWindows)

const prefs = lsGet(LS.prefs, {})
const initialTheme = prefs.theme || 'light'

const defaultExample = getCatalog(locale.value).find((e) => e.id === DEFAULT_EXAMPLE_ID)
let tabsInit = lsGet(LS.tabs, null)
if (!tabsInit || !Array.isArray(tabsInit.tabs) || !tabsInit.tabs.length) {
  const legacy = localStorage.getItem(LS.code) != null ? lsGet(LS.code, '') : (defaultExample?.source ?? '')
  const base = localStorage.getItem(LS.baseline) != null ? lsGet(LS.baseline, '') : (defaultExample?.source ?? '')
  tabsInit = { activeId: 't1', tabs: [{ id: 't1', name: defaultExample ? `${defaultExample.id}.py` : t('script.default_name'), code: legacy, baseline: base }] }
}
if (!tabsInit.tabs.some((t) => t.id === tabsInit.activeId)) tabsInit.activeId = tabsInit.tabs[0].id
const activeInit = tabsInit.tabs.find((t) => t.id === tabsInit.activeId)

const LAYOUT_DEFAULTS = { leftOpen: true, rightOpen: true, bottomOpen: true, leftW: 240, rightW: 460, bottomH: 220, bottomTab: 'console', rightMaximized: false, reportsOpen: false, reportsW: 460, reportsMaximized: false, activeReportId: null, showReportTemplateModal: false }
const client = new SimClient({ clientConfig: lsGet(LS.clientConfig, null) })

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
// capturas antigas de boas-vindas não fazem mais parte da galeria
const savedCaptures = lsGet('hivebr.web.captures.v1', []).filter((c) => c.id !== 'cap_welcome')
export const captures = reactive(savedCaptures)

function persistCaptures() {
  lsSet('hivebr.web.captures.v1', captures.map(c => ({ ...c })))
}
watch(captures, persistCaptures, { deep: true })
persistCaptures()

export const store = reactive({
  client: markRaw(client),
  // boot
  boot: { stage: 'init', progress: 0, detail: '', ready: false, dismissed: false, version: '' },
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
export function clampWindow(w, id) {
  const { vw, vh } = viewport()
  const def = WINDOW_DEFS[id] || {}
  const minW = Math.min(def.minW ?? 280, vw), minH = Math.min(def.minH ?? 160, vh)
  w.w = Math.max(minW, Math.min(w.w, vw))
  w.h = Math.max(minH, Math.min(w.h, vh - 8))
  w.x = Math.max(-w.w + VISIBLE_SIDE, Math.min(w.x, vw - VISIBLE_SIDE))
  w.y = Math.max(menubarH(), Math.min(w.y, vh - KEEP_BELOW))
}
export function focusWindow(id) {
  if (zCounter >= zCeil()) {  // nunca alcança a camada dos banners: renormaliza a ordem
    Object.entries(windows).sort((a, b) => a[1].z - b[1].z).forEach(([k, w], i) => { w.z = zBase() + i })
    zCounter = zBase() + Object.keys(windows).length
  }
  windows[id].z = ++zCounter
}
export function openWindow(id) {
  const w = windows[id]
  w.open = true
  w.minimized = false
  clampWindow(w, id)
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
Object.entries(windows).forEach(([id, w]) => clampWindow(w, id)) // o monitor pode ter mudado
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
  if (!store.tabs.length) addTab(t('script.default_name'), t('script.new_template'))
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
  if (store.readonly) { addTab(fileName || t('script.default_name'), text); store.error = null; return }
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
    title: t('discard.title'),
    message: t('discard.message', { what }),
    confirmText: t('discard.confirm'),
    danger: true,
  })
  return !!r
}
export async function loadExample(ex) {
  if (!(await confirmDiscard(t('discard.what_example', { title: ex.title })))) return false
  replaceCode(ex.source, { fileName: `${ex.id}.py` })
  store.modals.examples = false
  openPanel('right')
  toast(t('toast.example_loaded', { title: ex.title }))
  return true
}
export function newFile() {
  addTab(`script_${tabSeq + 1}.py`, t('script.new_template'))
  openPanel('right')
}

// ---- demonstração (aba somente leitura, não altera o script do usuário) ----
export async function runDemo() {
  const ex = catalog.value.find((e) => e.id === DEMO_EXAMPLE_ID)
  if (!ex) { toast(t('toast.demo_unavailable'), 'warn'); return }
  const existing = store.tabs.find((x) => x.readonly)
  if (existing) { syncActive(); existing.code = ex.source; loadTab(existing) } else addTab(t('tab.demo'), ex.source, { readonly: true })
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
  if (!store.boot.ready) { toast(t('toast.wait_python'), 'warn'); return }
  runCode()
}
export function duplicateDemo() {
  const tab = activeTab()
  if (!tab?.readonly) return
  addTab(t('script.demo_copy_name'), tab.code)
  toast(t('toast.demo_duplicated'))
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
export function addCapture(dataUrl, name = null) {
  const id = 'cap_' + Date.now()
  const capture = { id, name: name || `sim_${captures.length + 1}.png`, dataUrl, created: Date.now() }
  captures.unshift(capture) // newest first
  if (captures.length > 50) captures.pop() // limit to 50
  return capture
}
export function deleteCapture(id) {
  const i = captures.findIndex(c => c.id === id)
  if (i >= 0) captures.splice(i, 1)
}
export function renameCapture(id, name) {
  const c = captures.find(c => c.id === id)
  const clean = String(name ?? '').trim()
  if (!c || !clean) return null
  c.name = clean
  return c
}
export function getCaptureDataUrl(id) {
  const c = captures.find(c => c.id === id)
  return c?.dataUrl
}
export function getCapture(id) {
  return captures.find(c => c.id === id)
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
    toast(t(store.interactive ? 'toast.run_first' : 'toast.limited_mode'), 'warn')
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
    toast(t('toast.run_failed', { error: String(e?.message || e) }), 'error')
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
    store.boot.stage = p.stage; store.boot.progress = p.progress ?? 0; store.boot.detail = p.text || ''
    store.boot.ready = false
    store.boot.dismissed = false
  })
  on('restart', () => { store.boot.ready = false; store.boot.progress = 0; store.boot.stage = 'restart'; store.boot.detail = ''; store.boot.dismissed = false })
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
    toast(t('toast.file_downloaded', { name: p.name }))
  })
  on('figure', (p) => {
    store.figures.push(markRaw(p))
    toast(t('toast.figure_captured', { title: p.title || t('plots.untitled') }))
  })
  on('notice', (p) => {
    // `code` + `params` (Python/worker) são traduzidos aqui; sem tradução, vale o texto em inglês.
    const text = p.code ? tOr('notice.' + p.code, p.params, p.text) : p.text
    toast(text, p.level === 'warn' ? 'warn' : p.level === 'error' ? 'error' : 'info', p.level === 'error' ? 9000 : 5000)
    consoleBus.push('notice', text)
  })
  on('client_config', (p) => {
    // Persiste o YAML atualizado para reaplicá-lo no próximo boot; "reset" volta ao padrão do build.
    if (p?.reset) {
      try { localStorage.removeItem(LS.clientConfig) } catch { /* storage indisponível */ }
    } else if (p?.b64) {
      lsSet(LS.clientConfig, { path: p.path, b64: p.b64 })
    }
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
      consoleBus.push('notice', t('console.stopped'))
    } else {
      consoleBus.push('notice', t('console.finished'))
    }
  })
  on('fatal', (p) => { store.fatal = typeof p === 'string' ? p : (p?.message || p?.text || 'Fatal error while starting Python.') })
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
    toast(t('toast.file_opened', { name: f.name }))
  }
  i.click()
}
export function downloadScript() {
  const name = /\.py$/.test(store.fileName) ? store.fileName : store.fileName + '.py'
  download(name, new Blob([store.code], { type: 'text/x-python' }))
  saveNow()
}
/** Catálogo no idioma atual (reativo). */
export const catalog = computed(() => getCatalog(locale.value))
