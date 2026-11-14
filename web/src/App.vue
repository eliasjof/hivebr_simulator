<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import MenuBar from './components/MenuBar.vue'
import Toolbar from './components/Toolbar.vue'
import Navigator from './components/Navigator.vue'
import EditorPanel from './components/EditorPanel.vue'
import BottomDock from './components/BottomDock.vue'
import StatusBar from './components/StatusBar.vue'
import Splitter from './components/Splitter.vue'
import Icon from './components/Icon.vue'
import ParametersWindow from './components/ParametersWindow.vue'
import PlotsWindow from './components/PlotsWindow.vue'
import MapWindow from './components/MapWindow.vue'
import RobotsWindow from './components/RobotsWindow.vue'
import ExamplesModal from './components/ExamplesModal.vue'
import LearningModal from './components/LearningModal.vue'
import HelpModal from './components/HelpModal.vue'
import AboutModal from './components/AboutModal.vue'
import PromptModal from './components/PromptModal.vue'
import FatalModal from './components/FatalModal.vue'
import ContextMenu from './components/ContextMenu.vue'
import ToastHost from './components/ToastHost.vue'
import BootOverlay from './components/BootOverlay.vue'
import SimCanvas from './canvas/SimCanvas.vue'
import ReportsPanel from './components/ReportsPanel.vue'
import FigureViewer from './components/FigureViewer.vue'
import {
  store, scene, canvasRef, startClient, send, ask, selectRobot, setCursor, runCode, stopCode, toggleSim, stepOnce, resetSim,
  saveNow, toggleTheme, toggleWindow, windows, clampWindow, setNarrow, openPanel, togglePanel, focusEditor, runDemo, pickFile, toast,
  toggleRightMaximized, toggleReportsPanel, toggleReportsMaximized, editable,
  addCapture, b64ToBlob, download,
} from './state/store.js'
import { t, fmtNum, fmtInt } from './i18n/index.js'

const cv = ref(null)
const D2R = Math.PI / 180

const cardTitle = computed(() => {
  const s = scene.value
  if (!s) return t('card.waiting')
  const w = s.world ? `${fmtNum(s.world.width, 0)}×${fmtNum(s.world.height, 0)} m` : ''
  const r = s.robots?.[store.selected]
  return [w, r?.type].filter(Boolean).join(' · ')
})

// ---- eventos da cena ----
async function onAddWaypoint({ x, y, shift }) {
  if (shift) {
    const r = await ask({ title: t('prompt.wp_title'), fields: [{ key: 'deg', label: t('prompt.wp_angle'), type: 'number', value: 0, step: 5, suffix: t('prompt.degrees'), hint: t('prompt.wp_hint') }], confirmText: t('common.add') })
    if (!r) return
    send({ cmd: 'add_waypoint', robot: store.selected, x, y, theta: r.deg * D2R })
  } else send({ cmd: 'add_waypoint', robot: store.selected, x, y })
}
function onWaypointOrient({ x, y, theta }) { send({ cmd: 'add_waypoint', robot: store.selected, x, y, theta }) }
async function onAddObstacle({ x, y }) {
  const r = await ask({ title: t('prompt.obs_title'), fields: [{ key: 'r', label: t('prompt.obs_radius'), type: 'number', value: store.obstacleRadius, min: 0.05, max: 20, step: 0.05, suffix: 'm' }], confirmText: t('common.add') })
  if (!r) return
  store.obstacleRadius = r.r
  send({ cmd: 'add_obstacle', x, y, r: r.r })
}
function onContext(c) { store.ctx = c }
function onMove({ index, x, y, theta }) { send({ cmd: 'set_pose', robot: index, x, y, theta }) }
function onCursor(p) { if (p) setCursor(p); else setCursor({ x: null, y: null }) }

function captureSimulation() {
  if (!cv.value?.canvas) return
  const canvas = cv.value.canvas
  const dataUrl = canvas.toDataURL('image/png')
  const capture = addCapture(dataUrl)
  toast(t('toast.capture_saved', { name: capture.name }))
}

function downloadFigure(f, i) {
  download(`${(f.name || 'figure' + i).replace(/[^\w-]+/g, '_')}.png`, b64ToBlob(f.png_b64, 'image/png'))
}

// ---- visualizador de figuras ----
const openFigIndex = ref(null)
const activeFigure = computed(() => {
  const i = openFigIndex.value
  return i == null ? null : (store.figures[i] || null)
})
function openFigure(i) { openFigIndex.value = i }
function closeFigure() { openFigIndex.value = null }
watch(() => store.figures.length, (n) => {
  if (openFigIndex.value != null && openFigIndex.value >= n) openFigIndex.value = null
})

// ---- teclado ----
function isTyping(el) {
  return el && (el.closest?.('input, textarea, select, [contenteditable="true"], .cm-editor'))
}
let spaceHeld = false, spaceUsed = false
function onKeyDown(e) {
  const mod = e.ctrlKey || e.metaKey
  if (mod && e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); if (store.run.state === 'idle') runCode(); return }
  if (mod && e.key.toLowerCase() === 's') { e.preventDefault(); e.stopPropagation(); saveNow(); toast(t('toast.saved')); return }
  if (mod && e.key.toLowerCase() === 'o') { e.preventDefault(); pickFile(); return }
  if (document.querySelector('[aria-modal="true"]')) return
  if (e.key === 'Escape') {
    if (store.layout.reportsMaximized) { toggleReportsMaximized(); return }
    if (store.layout.rightMaximized) { toggleRightMaximized(); return }
    if (store.ctx) { store.ctx = null; return }
    store.tool = 'select'
    return
  }
  if (isTyping(e.target) || mod || e.altKey) return
  if (e.code === 'Space') {
    if (e.target.closest?.('button, [role="menuitem"]')) return
    e.preventDefault(); if (!spaceHeld) { spaceHeld = true; spaceUsed = false }
    return
  }
  const k = e.key
  if (k === 'R' && e.shiftKey) { if (store.run.state !== 'idle') resetSim(); return }
  if (/^[1-9]$/.test(k)) { const n = Number(k) - 1; if (n < (scene.value?.robots?.length || 0)) selectRobot(n); return }
  const tools = { v: 'select', w: 'waypoint', o: 'obstacle', r: 'recharge', m: 'move', d: 'draw' }
  const lk = k.toLowerCase()
  if (tools[lk] && !e.shiftKey) { store.tool = tools[lk]; return }
  switch (lk) {
    case 'f': cv.value?.fit(); break
    case '+': case '=': cv.value?.zoomIn(); break
    case '-': case '_': cv.value?.zoomOut(); break
    case '.': if (store.run.state !== 'idle') stepOnce(); break
    case 'e': e.preventDefault(); focusEditor(); break
    case 'c': openPanel('bottom', 'console'); break
    case 'b': openPanel('bottom', 'telemetry'); break
    case 'p': toggleWindow('params'); break
    case 'g': toggleWindow('plots'); break
    case 'k': toggleWindow('map'); break
    case 't': toggleTheme(); break
    case '?': store.modals.help = true; break
    case 's': if (e.shiftKey) { e.preventDefault(); captureSimulation() } break
  }
}
function onKeyUp(e) {
  if (e.code === 'Space' && spaceHeld) {
    spaceHeld = false
    if (!spaceUsed && store.run.state !== 'idle' && !isTyping(e.target) && !document.querySelector('[aria-modal="true"]')) toggleSim()
  }
}
function onPointerDownAny() { if (spaceHeld) spaceUsed = true }
function onResize() {
  store.vw = window.innerWidth
  setNarrow(window.innerWidth < 1100)
  for (const [id, w] of Object.entries(windows)) if (!w.maximized) clampWindow(w, id)
}
let zoomTimer = null
onMounted(() => {
  canvasRef.value = cv.value
  window.addEventListener('keydown', onKeyDown, true)
  window.addEventListener('keyup', onKeyUp)
  window.addEventListener('pointerdown', onPointerDownAny, true)
  window.addEventListener('resize', onResize)
  onResize()
  zoomTimer = setInterval(() => {
    const cam = cv.value?.getCamera?.()
    if (cam) store.zoomPct = Math.round((cam.scale / 50) * 100)
  }, 250)
  startClient()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown, true)
  window.removeEventListener('keyup', onKeyUp)
  window.removeEventListener('pointerdown', onPointerDownAny, true)
  window.removeEventListener('resize', onResize)
  clearInterval(zoomTimer)
})
// recoloca o canvas após mudanças de layout
watch(() => [store.layout.leftOpen, store.layout.rightOpen, store.layout.reportsOpen, store.layout.bottomOpen], () => requestAnimationFrame(() => window.dispatchEvent(new Event('resize'))))

const effLeft = computed(() => Math.min(store.layout.leftW, Math.round(store.vw * 0.22)))
// The side panels can grow much wider now, but always leave room for the canvas.
const maxSide = computed(() => {
  const left = store.layout.leftOpen && !store.narrow ? effLeft.value : 0
  return Math.max(320, Math.min(Math.round(store.vw * 0.72), store.vw - left - 240))
})
const effRight = computed(() => Math.min(store.layout.rightW, maxSide.value))
const effReports = computed(() => Math.min(store.layout.reportsW, maxSide.value))
// recolhido = altura das abas + as duas bordas do dock
const bottomStyle = computed(() => ({ height: store.layout.bottomOpen ? store.layout.bottomH + 'px' : 'calc(var(--tabs-h) + 2px)' }))
const maxLeft = computed(() => Math.min(420, Math.round(store.vw * 0.4)))

// Tooltips montados fora do template para evitar concatenação em atributos.
const zoomOutTip = computed(() => `${t('zoom.out')} (−)`)
const zoomInTip = computed(() => `${t('zoom.in')} (+)`)
const viewFitTip = computed(() => `${t('view.fit')} (F)`)
</script>

<template>
  <div class="shell" :class="{ narrow: store.narrow, rightMaximized: store.layout.rightMaximized, reportsMaximized: store.layout.reportsMaximized }">
    <MenuBar />
    <Toolbar />
    <main class="main">
      <!-- painel esquerdo -->
      <aside v-if="store.layout.leftOpen && !store.layout.rightMaximized && !store.layout.reportsMaximized" class="side left" :style="{ width: effLeft + 'px' }"><Navigator /></aside>
      <Splitter v-if="store.layout.leftOpen && !store.narrow && !store.layout.rightMaximized && !store.layout.reportsMaximized" axis="x" v-model:value="store.layout.leftW" :min="180" :max="maxLeft" :label="t('split.nav')" />
      <button v-if="!store.layout.leftOpen" class="rail left" :aria-label="t('rail.open_nav')" :data-tip="t('nav.title')" data-tip-pos="start" @click="openPanel('left')"><Icon name="panelL" :size="16" /></button>

      <!-- centro -->
      <section v-if="!store.layout.rightMaximized && !store.layout.reportsMaximized" class="center">
        <div class="docbar" role="tablist" :aria-label="t('card.docs')">
          <button class="doctab" :class="{ on: store.layout.centerTab === 'sim' }" role="tab" :aria-selected="store.layout.centerTab === 'sim'" @click="store.layout.centerTab = 'sim'"><Icon name="hex" :size="14" />{{ t('card.sim') }}</button>
          <button class="doctab" :class="{ on: store.layout.centerTab === 'figs' }" role="tab" :aria-selected="store.layout.centerTab === 'figs'" @click="store.layout.centerTab = 'figs'"><Icon name="image" :size="14" />{{ t('plots.figures') }}<span v-if="store.figures.length" class="tab-count">{{ fmtInt(store.figures.length) }}</span></button>
        </div>
        <div class="card">
          <header class="card-h">
            <span v-if="store.layout.centerTab === 'sim'" class="sec-h"><b>{{ t('card.sim') }}</b> <span class="muted">· {{ cardTitle }}</span></span>
            <span v-else class="sec-h"><b>{{ t('plots.figures') }}</b> <span class="muted">· {{ fmtInt(store.figures.length) }}</span></span>
            <span class="sp" />
            <template v-if="store.layout.centerTab === 'sim'">
              <button class="btn ghost icon sm" :aria-label="t('capture.aria')" :data-tip="t('capture.tip')" @click="captureSimulation"><Icon name="camera" :size="14" /></button>
              <button class="btn ghost icon sm" :aria-label="t('zoom.out')" :data-tip="zoomOutTip" @click="cv?.zoomOut()"><Icon name="zoomOut" :size="14" /></button>
              <span class="zoom mono">{{ fmtInt(store.zoomPct) }}%</span>
              <button class="btn ghost icon sm" :aria-label="t('zoom.in')" :data-tip="zoomInTip" @click="cv?.zoomIn()"><Icon name="zoomIn" :size="14" /></button>
              <button class="btn ghost icon sm" :aria-label="t('view.fit')" :data-tip="viewFitTip" data-tip-pos="end" @click="cv?.fit()"><Icon name="fit" :size="14" /></button>
            </template>
          </header>
          <div v-show="store.layout.centerTab === 'sim'" class="cv">
            <SimCanvas ref="cv" :scene="scene" :tool="store.tool" :options="store.options" :interactive="editable" :lineWidth="store.lineWidth"
              @add-waypoint="onAddWaypoint" @waypoint-drag-orientation="onWaypointOrient" @add-obstacle="onAddObstacle"
              @add-recharge="(p) => send({ cmd: 'add_recharge', x: p.x, y: p.y })" @context="onContext" @select-robot="(p) => selectRobot(p.index)"
              @move-robot="onMove" @cursor="onCursor" />
            <div v-if="!store.hasRun && store.tool === 'select'" class="hint">
              <p>{{ t('hint.press') }}<b>{{ t('run.run') }}</b> (<kbd>Ctrl</kbd>+<kbd>Enter</kbd>){{ t('hint.to_create') }}</p>
              <p class="muted small">{{ t('hint.sub') }}</p>
              <button class="btn sm" @click="runDemo"><Icon name="demo" :size="14" />{{ t('hint.see_demo') }}</button>
            </div>
          </div>
          <div v-if="store.layout.centerTab === 'figs'" class="figs-pane">
            <div v-if="!store.figures.length" class="fig-empty">
              <Icon name="image" :size="28" />
              <h3>{{ t('plots.no_figs') }}</h3>
              <p>{{ t('plots.no_figs_a') }}<code class="mono">plt.show()</code>{{ t('plots.no_figs_b') }}</p>
            </div>
            <div v-else class="figs">
              <figure v-for="(f, i) in store.figures" :key="i" class="fig">
                <button class="fig-thumb" type="button" :aria-label="t('figures.open') + ': ' + (f.name || t('plots.fig_n', { n: i + 1 }))" :data-tip="t('figures.open')" @click="openFigure(i)">
                  <img :src="'data:image/png;base64,' + f.png_b64" :alt="f.name || t('plots.fig_n', { n: i + 1 })" />
                  <span class="fig-open"><Icon name="max" :size="16" /></span>
                </button>
                <figcaption>
                  <span class="fig-name">{{ f.name || t('plots.fig_n', { n: i + 1 }) }}</span>
                  <span class="fig-actions">
                    <button class="btn ghost icon sm" type="button" :aria-label="t('figures.open')" :data-tip="t('figures.open')" @click="openFigure(i)"><Icon name="max" :size="13" /></button>
                    <button class="btn sm" type="button" @click.stop="downloadFigure(f, i)"><Icon name="download" :size="12" />{{ t('plots.download_png') }}</button>
                  </span>
                </figcaption>
              </figure>
            </div>
          </div>
        </div>
        <Splitter v-if="store.layout.bottomOpen" axis="y" v-model:value="store.layout.bottomH" invert :min="90" :max="520" :label="t('split.bottom')" />
        <div class="bottom" :style="bottomStyle"><BottomDock /></div>
      </section>

      <!-- painel direito - código -->
      <Splitter v-if="store.layout.rightOpen && !store.narrow && !store.layout.rightMaximized && !store.layout.reportsMaximized" axis="x" v-model:value="store.layout.rightW" invert :min="300" :max="maxSide" :label="t('split.code')" />
      <aside v-if="store.layout.rightOpen" class="side right code" :style="{ width: store.layout.rightMaximized ? 'auto' : effRight + 'px' }"><EditorPanel /></aside>
      <button v-if="!store.layout.rightOpen && !store.layout.rightMaximized" class="rail right" :aria-label="t('rail.open_code')" :data-tip="t('view.code') + ' (E)'" data-tip-pos="end" @click="openPanel('right')"><Icon name="panelR" :size="16" /></button>

      <!-- painel direito - relatórios -->
      <Splitter v-if="store.layout.reportsOpen && !store.narrow && !store.layout.reportsMaximized && !store.layout.rightMaximized" axis="x" v-model:value="store.layout.reportsW" invert :min="300" :max="maxSide" :label="t('split.reports')" />
      <aside v-if="store.layout.reportsOpen" class="side right reports" :style="{ width: store.layout.reportsMaximized ? 'auto' : effReports + 'px' }"><ReportsPanel /></aside>
      <button v-if="!store.layout.reportsOpen && !store.layout.reportsMaximized" class="rail right" :aria-label="t('report.section')" :data-tip="t('report.section')" data-tip-pos="end" @click="toggleReportsPanel"><Icon name="file" :size="16" /></button>
    </main>
    <StatusBar />

    <ParametersWindow v-if="windows.params.open" /><PlotsWindow v-if="windows.plots.open" /><MapWindow v-if="windows.map.open" /><RobotsWindow v-if="windows.robots.open" />
    <BootOverlay />
    <ContextMenu />
    <ToastHost />
    <ExamplesModal v-if="store.modals.examples" />
    <LearningModal v-if="store.modals.learning" />
    <HelpModal v-if="store.modals.help" />
    <AboutModal v-if="store.modals.about" />
    <PromptModal v-if="store.prompt" />
    <FatalModal v-if="store.fatal" />
    <FigureViewer v-if="activeFigure" :figure="activeFigure" :index="openFigIndex" @close="closeFigure" />
  </div>
</template>

<style scoped>
.shell { position: fixed; inset: 0; display: grid; grid-template-rows: var(--menubar-h) var(--toolbar-h) minmax(0, 1fr) var(--status-h); background: var(--bg); }
.main { position: relative; display: flex; min-height: 0; min-width: 0; }
.side { flex: none; min-width: 0; min-height: 0; }
.rail { flex: none; width: var(--rail-w); background: var(--surface); border: none; color: var(--text-muted); display: grid; place-items: start center; padding-top: 10px; }
.rail.left { border-right: 1px solid var(--border); } .rail.right { border-left: 1px solid var(--border); }
.rail:hover { color: var(--accent); background: var(--surface-3); }
.narrow .side { position: absolute; top: 0; bottom: 0; z-index: var(--z-panel); max-width: 92vw; box-shadow: var(--shadow); }
.narrow .side.left { left: var(--rail-w); } .narrow .side.right { right: var(--rail-w); }
.narrow .rail { z-index: var(--z-panel); }
.narrow .rail.left { order: -1; }
.rail.right { order: 1; }
.rail.right:last-of-type { order: 2; }
.center { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; padding: 0 10px 10px; }
.rightMaximized .center { display: none; }
.rightMaximized .side.left { display: none; }
.rightMaximized .side.right.code { flex: 1 1 auto; width: auto !important; }
.rightMaximized .rail.right { display: none; }
.reportsMaximized .center { display: none; }
.reportsMaximized .side.left { display: none; }
.reportsMaximized .side.right.reports { flex: 1 1 auto; width: auto !important; }
.reportsMaximized .rail.right { display: none; }
.docbar { height: var(--docbar-h); display: flex; align-items: flex-end; gap: var(--sp-2); padding-top: var(--sp-3); flex: none; }
.doctab { display: flex; align-items: center; gap: var(--sp-3); padding: 0 14px; height: var(--tabs-h); background: var(--surface); border: 1px solid var(--border); border-bottom: none; border-radius: var(--radius) var(--radius) 0 0; font-weight: 500; box-shadow: 0 1px 0 var(--surface); position: relative; top: 1px; color: var(--text-muted); }
.doctab svg { color: var(--accent); }
.doctab:hover { color: var(--text); }
.doctab.on { color: var(--text); border-color: var(--border); box-shadow: 0 2px 0 var(--surface); }
.doctab.on::after { content: ''; position: absolute; left: 10px; right: 10px; bottom: -1px; height: 2px; background: var(--accent); border-radius: 2px; }
.doctab .tab-count { margin-left: var(--sp-2); padding: 0 6px; border-radius: 999px; background: var(--surface-2); color: var(--text-muted); font-size: var(--fs-xs); font-variant-numeric: tabular-nums; }
.card { flex: 1; min-height: 80px; display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: 0 var(--radius) var(--radius) var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); }
.card-h { display: flex; align-items: center; gap: var(--sp-2); height: var(--panel-head-h); padding: 0 var(--sp-4) 0 var(--sp-5); border-bottom: 1px solid var(--border); flex: none; }
.card-h b { color: var(--text); font-weight: 700; }
.card-h .sec-h { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.sp { flex: 1; }
.zoom { min-width: 44px; text-align: center; font-size: var(--fs-label); color: var(--text-muted); }
.cv { position: relative; flex: 1; min-height: 0; }
.cv > :deep(*:first-child) { position: absolute; inset: 0; }
.hint { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; gap: var(--sp-3); text-align: center; padding: 18px var(--sp-7); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-sm); max-width: 90%; pointer-events: none; }
.hint .btn { pointer-events: auto; }
.hint p { margin: 0; color: var(--text-muted); } .hint p.small { font-size: var(--fs-sm); margin-bottom: var(--sp-3); }
.figs-pane { flex: 1; min-height: 0; overflow: auto; padding: 14px var(--sp-5); }
.fig-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--sp-3); height: 100%; text-align: center; color: var(--text-muted); }
.fig-empty svg { color: var(--accent); }
.fig-empty h3 { margin: 0; font-size: var(--fs-md); color: var(--text); }
.fig-empty p { max-width: 420px; margin: 0; line-height: 1.5; }
.figs { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--sp-5); }
.fig { margin: 0; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--surface); }
.fig-thumb { position: relative; display: block; width: 100%; padding: 0; border: none; background: var(--surface-2); cursor: zoom-in; }
.fig-thumb img { width: 100%; display: block; }
.fig-thumb:hover img, .fig-thumb:focus-visible img { opacity: .92; }
.fig-open { position: absolute; right: 8px; bottom: 8px; display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: rgba(0, 0, 0, .55); color: #fff; opacity: 0; transition: opacity var(--dur) var(--ease); pointer-events: none; }
.fig-thumb:hover .fig-open, .fig-thumb:focus-visible .fig-open { opacity: 1; }
.fig figcaption { display: flex; justify-content: space-between; align-items: center; gap: var(--sp-3); padding: var(--sp-3) var(--sp-4); background: var(--surface-2); color: var(--text); }
.fig-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fig-actions { display: flex; align-items: center; gap: var(--sp-2); flex: none; }
.bottom { flex: none; min-height: 0; margin-top: 9px; }
</style>
