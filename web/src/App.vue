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
import HelpModal from './components/HelpModal.vue'
import PromptModal from './components/PromptModal.vue'
import FatalModal from './components/FatalModal.vue'
import ContextMenu from './components/ContextMenu.vue'
import ToastHost from './components/ToastHost.vue'
import BootOverlay from './components/BootOverlay.vue'
import SimCanvas from './canvas/SimCanvas.vue'
import {
  store, scene, canvasRef, startClient, send, ask, selectRobot, setCursor, runCode, stopCode, toggleSim, stepOnce, resetSim,
  saveNow, toggleTheme, toggleWindow, windows, clampWindow, setNarrow, openPanel, togglePanel, focusEditor, runDemo, pickFile, toast,
} from './state/store.js'

const cv = ref(null)
const D2R = Math.PI / 180

const cardTitle = computed(() => {
  const s = scene.value
  if (!s) return 'Aguardando simulação'
  const w = s.world ? `${s.world.width}×${s.world.height} m` : ''
  const r = s.robots?.[store.selected]
  return [w, r?.type].filter(Boolean).join(' · ')
})

// ---- eventos da cena ----
async function onAddWaypoint({ x, y, shift }) {
  if (shift) {
    const r = await ask({ title: 'Orientação do waypoint', fields: [{ key: 'deg', label: 'Ângulo', type: 'number', value: 0, step: 5, suffix: 'graus', hint: '0° aponta para +x; sentido anti-horário.' }], confirmText: 'Adicionar' })
    if (!r) return
    send({ cmd: 'add_waypoint', robot: store.selected, x, y, theta: r.deg * D2R })
  } else send({ cmd: 'add_waypoint', robot: store.selected, x, y })
}
function onWaypointOrient({ x, y, theta }) { send({ cmd: 'add_waypoint', robot: store.selected, x, y, theta }) }
async function onAddObstacle({ x, y }) {
  const r = await ask({ title: 'Raio do obstáculo', fields: [{ key: 'r', label: 'Raio', type: 'number', value: store.obstacleRadius, min: 0.05, max: 20, step: 0.05, suffix: 'm' }], confirmText: 'Adicionar' })
  if (!r) return
  store.obstacleRadius = r.r
  send({ cmd: 'add_obstacle', x, y, r: r.r })
}
function onContext(c) { store.ctx = c }
function onMove({ index, x, y, theta }) { send({ cmd: 'set_pose', robot: index, x, y, theta }) }
function onCursor(p) { if (p) setCursor(p); else setCursor({ x: null, y: null }) }

// ---- teclado ----
function isTyping(t) {
  return t && (t.closest?.('input, textarea, select, [contenteditable="true"], .cm-editor'))
}
let spaceHeld = false, spaceUsed = false
function onKeyDown(e) {
  const mod = e.ctrlKey || e.metaKey
  if (mod && e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); if (store.run.state === 'idle') runCode(); return }
  if (mod && e.key.toLowerCase() === 's') { e.preventDefault(); e.stopPropagation(); saveNow(); toast('Salvo no navegador.'); return }
  if (mod && e.key.toLowerCase() === 'o') { e.preventDefault(); pickFile(); return }
  if (document.querySelector('[aria-modal="true"]')) return
  if (e.key === 'Escape') {
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
  if (k === 'R' && e.shiftKey) return resetSim()
  if (/^[1-9]$/.test(k)) { const n = Number(k) - 1; if (n < (scene.value?.robots?.length || 0)) selectRobot(n); return }
  const tools = { v: 'select', w: 'waypoint', o: 'obstacle', r: 'recharge', m: 'move', d: 'draw' }
  const lk = k.toLowerCase()
  if (tools[lk] && !e.shiftKey) { store.tool = tools[lk]; return }
  switch (lk) {
    case 'f': cv.value?.fit(); break
    case '+': case '=': cv.value?.zoomIn(); break
    case '-': case '_': cv.value?.zoomOut(); break
    case '.': stepOnce(); break
    case 'e': e.preventDefault(); focusEditor(); break
    case 'c': openPanel('bottom', 'console'); break
    case 'b': openPanel('bottom', 'telemetry'); break
    case 'p': toggleWindow('params'); break
    case 'g': toggleWindow('plots'); break
    case 'k': toggleWindow('map'); break
    case 't': toggleTheme(); break
    case '?': store.modals.help = true; break
  }
}
function onKeyUp(e) {
  if (e.code === 'Space' && spaceHeld) {
    spaceHeld = false
    if (!spaceUsed && !isTyping(e.target) && !document.querySelector('[aria-modal="true"]')) toggleSim()
  }
}
function onPointerDownAny() { if (spaceHeld) spaceUsed = true }
function onResize() {
  store.vw = window.innerWidth
  setNarrow(window.innerWidth < 1100)
  for (const w of Object.values(windows)) if (!w.maximized) clampWindow(w)
}
let zoomTimer = null
onMounted(() => {
  canvasRef.value = cv.value
  window.addEventListener('keydown', onKeyDown, true)
  window.addEventListener('keyup', onKeyUp)
  window.addEventListener('pointerdown', onPointerDownAny, true)
  window.addEventListener('resize', onResize)
  if (window.innerWidth < 1100) { store.narrow = true; store.layout.leftOpen = false; store.layout.rightOpen = false }
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
watch(() => [store.layout.leftOpen, store.layout.rightOpen, store.layout.bottomOpen], () => requestAnimationFrame(() => window.dispatchEvent(new Event('resize'))))

const effLeft = computed(() => Math.min(store.layout.leftW, Math.round(store.vw * 0.22)))
const effRight = computed(() => Math.min(store.layout.rightW, Math.round(store.vw * 0.36)))
const bottomStyle = computed(() => ({ height: (store.layout.bottomOpen ? store.layout.bottomH : 33) + 'px' }))
const maxLeft = computed(() => Math.min(420, window.innerWidth * 0.4))
</script>

<template>
  <div class="shell" :class="{ narrow: store.narrow }">
    <MenuBar />
    <Toolbar />
    <main class="main">
      <!-- painel esquerdo -->
      <aside v-if="store.layout.leftOpen" class="side left" :style="{ width: effLeft + 'px' }"><Navigator /></aside>
      <Splitter v-if="store.layout.leftOpen && !store.narrow" axis="x" v-model:value="store.layout.leftW" :min="180" :max="maxLeft" label="Redimensionar navegador" />
      <button v-if="!store.layout.leftOpen" class="rail left" aria-label="Abrir navegador" data-tip="Navegador" data-tip-pos="start" @click="openPanel('left')"><Icon name="panelL" :size="16" /></button>

      <!-- centro -->
      <section class="center">
        <div class="docbar" role="tablist"><div class="doctab on" role="tab" aria-selected="true"><Icon name="hex" :size="14" />Simulação</div></div>
        <div class="card">
          <header class="card-h">
            <span class="sec-h"><b>Simulação</b> <span class="muted">· {{ cardTitle }}</span></span>
            <span class="sp" />
            <button class="btn ghost icon sm" aria-label="Afastar" data-tip="Afastar (−)" @click="cv?.zoomOut()"><Icon name="zoomOut" :size="14" /></button>
            <span class="zoom mono">{{ store.zoomPct }}%</span>
            <button class="btn ghost icon sm" aria-label="Aproximar" data-tip="Aproximar (+)" @click="cv?.zoomIn()"><Icon name="zoomIn" :size="14" /></button>
            <button class="btn ghost icon sm" aria-label="Enquadrar" data-tip="Enquadrar (F)" data-tip-pos="end" @click="cv?.fit()"><Icon name="fit" :size="14" /></button>
          </header>
          <div class="cv">
            <SimCanvas ref="cv" :scene="scene" :tool="store.tool" :options="store.options" :interactive="store.interactive"
              @add-waypoint="onAddWaypoint" @waypoint-drag-orientation="onWaypointOrient" @add-obstacle="onAddObstacle"
              @add-recharge="(p) => send({ cmd: 'add_recharge', x: p.x, y: p.y })" @context="onContext" @select-robot="(p) => selectRobot(p.index)"
              @move-robot="onMove" @cursor="onCursor" />
            <div v-if="!store.hasRun" class="hint">
              <p>Pressione <b>Executar</b> (<kbd>Ctrl</kbd>+<kbd>Enter</kbd>) para criar a simulação.</p>
              <p class="faint">O código do painel Código controla os robôs; eles aparecem aqui.</p>
              <button class="btn sm" @click="runDemo"><Icon name="demo" :size="14" />Ver demonstração</button>
            </div>
          </div>
        </div>
        <Splitter v-if="store.layout.bottomOpen" axis="y" v-model:value="store.layout.bottomH" invert :min="90" :max="520" label="Redimensionar painel inferior" />
        <div class="bottom" :style="bottomStyle"><BottomDock /></div>
      </section>

      <!-- painel direito -->
      <Splitter v-if="store.layout.rightOpen && !store.narrow" axis="x" v-model:value="store.layout.rightW" invert :min="300" :max="720" label="Redimensionar código" />
      <aside v-if="store.layout.rightOpen" class="side right" :style="{ width: effRight + 'px' }"><EditorPanel /></aside>
      <button v-if="!store.layout.rightOpen" class="rail right" aria-label="Abrir código" data-tip="Código (E)" data-tip-pos="end" @click="openPanel('right')"><Icon name="panelR" :size="16" /></button>
    </main>
    <StatusBar />

    <ParametersWindow v-if="windows.params.open" /><PlotsWindow v-if="windows.plots.open" /><MapWindow v-if="windows.map.open" /><RobotsWindow v-if="windows.robots.open" />
    <BootOverlay />
    <ContextMenu />
    <ToastHost />
    <ExamplesModal v-if="store.modals.examples" />
    <HelpModal v-if="store.modals.help" />
    <PromptModal v-if="store.prompt" />
    <FatalModal v-if="store.fatal" />
  </div>
</template>

<style scoped>
.shell { position: fixed; inset: 0; display: grid; grid-template-rows: var(--menubar-h) var(--toolbar-h) minmax(0, 1fr) var(--status-h); background: var(--bg); }
.main { position: relative; display: flex; min-height: 0; min-width: 0; }
.side { flex: none; min-width: 0; min-height: 0; }
.rail { flex: none; width: 30px; background: var(--surface); border: none; color: var(--text-muted); display: grid; place-items: start center; padding-top: 10px; }
.rail.left { border-right: 1px solid var(--border); } .rail.right { border-left: 1px solid var(--border); }
.rail:hover { color: var(--accent); background: var(--surface-3); }
.narrow .side { position: absolute; top: 0; bottom: 0; z-index: 40; max-width: 92vw; box-shadow: var(--shadow); }
.narrow .side.left { left: 30px; } .narrow .side.right { right: 30px; }
.narrow .rail { z-index: 41; }
.narrow .rail.left { order: -1; } 
.center { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; padding: 0 10px 10px; }
.docbar { height: 38px; display: flex; align-items: flex-end; gap: 4px; padding-top: 6px; flex: none; }
.doctab { display: flex; align-items: center; gap: 6px; padding: 0 14px; height: 32px; background: var(--surface); border: 1px solid var(--border); border-bottom: none; border-radius: 8px 8px 0 0; font-weight: 500; box-shadow: 0 1px 0 var(--surface); position: relative; top: 1px; }
.doctab svg { color: var(--accent); }
.card { flex: 1; min-height: 80px; display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: 0 8px 8px 8px; overflow: hidden; box-shadow: var(--shadow-sm); }
.card-h { display: flex; align-items: center; gap: 4px; height: 34px; padding: 0 8px 0 12px; border-bottom: 1px solid var(--border); flex: none; }
.card-h b { color: var(--text); font-weight: 700; }
.card-h .sec-h { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.sp { flex: 1; }
.zoom { min-width: 44px; text-align: center; font-size: 11.5px; color: var(--text-muted); }
.cv { position: relative; flex: 1; min-height: 0; }
.cv > :deep(*:first-child) { position: absolute; inset: 0; }
.hint { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; gap: 6px; text-align: center; padding: 18px 24px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-sm); max-width: 90%; }
.hint p { margin: 0; color: var(--text-muted); } .hint p.faint { font-size: 12px; margin-bottom: 6px; }
.bottom { flex: none; min-height: 0; margin-top: 9px; }
</style>
