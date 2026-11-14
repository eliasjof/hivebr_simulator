<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import {
  store, toggleRun, toggleSim, stepOnce, resetSim, restartScene, setSpeed, newFile, pickFile, downloadScript, runDemo,
} from '../state/store.js'
import { t } from '../i18n/index.js'

const runLabel = computed(() => {
  if (!store.boot.ready && store.run.state === 'idle') return t('run.loading')
  return t({ idle: 'run.run', starting: 'run.running', running: 'run.running', stopping: 'run.stopping' }[store.run.state])
})
const idle = computed(() => store.run.state === 'idle')
const runDisabled = computed(() => !idle.value || !store.boot.ready)
const live = computed(() => store.run.state === 'running')
const stoppable = computed(() => store.run.state === 'running' || store.run.state === 'starting')

const tools = [
  { id: 'select', key: 'V', icon: 'cursor' },
  { id: 'waypoint', key: 'W', icon: 'waypoint' },
  { id: 'obstacle', key: 'O', icon: 'obstacle' },
  { id: 'recharge', key: 'R', icon: 'bolt' },
  { id: 'move', key: 'M', icon: 'move' },
  { id: 'draw', key: 'D', icon: 'pen' },
]
const speeds = [0.25, 0.5, 1, 2, 4, Infinity]
const speedLabel = (s) => (s === Infinity ? t('speed.max') : `${s}×`)
const layers = ['showGrid', 'showPaths', 'showLidar', 'showWaypoints', 'showLabels', 'showLinks']

// dropdown de camadas: a barra rola na horizontal (overflow), então ancoramos com coordenadas do botão
const menu = ref(false)
const menuPos = ref({ left: 0, top: 0 })
const root = ref(null)
const layersBtn = ref(null)
function toggleMenu() {
  menu.value = !menu.value
  if (menu.value) {
    const r = layersBtn.value.getBoundingClientRect()
    menuPos.value = { left: Math.max(8, Math.min(r.left, window.innerWidth - 228)), top: r.bottom + 4 }
  }
}
function onDoc(e) { if (menu.value && !root.value.contains(e.target)) menu.value = false }
function onKey(e) { if (e.key === 'Escape') menu.value = false }
onMounted(() => { document.addEventListener('pointerdown', onDoc); document.addEventListener('keydown', onKey) })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', onDoc); document.removeEventListener('keydown', onKey) })
const ed = () => store.editorApi
</script>

<template>
  <div ref="root" class="tb" role="toolbar" :aria-label="t('toolbar.aria')" @scroll.passive="menu = false">
    <div class="grp">
      <button class="btn ghost icon" :aria-label="t('file.new')" :data-tip="t('file.new')" data-tip-pos="start" @click="newFile"><Icon name="file" /></button>
      <button class="btn ghost icon" :aria-label="t('file.open_short')" :data-tip="t('file.open_tip')" @click="pickFile"><Icon name="open" /></button>
      <button class="btn ghost icon" :aria-label="t('file.download')" :data-tip="t('file.download')" @click="downloadScript"><Icon name="save" /></button>
    </div>
    <span class="sep" />
    <div class="grp">
      <button class="btn ghost icon" :disabled="!ed()" :aria-label="t('edit.undo')" :data-tip="t('edit.undo_tip')" @click="ed()?.undo()"><Icon name="undo" /></button>
      <button class="btn ghost icon" :disabled="!ed()" :aria-label="t('edit.redo')" :data-tip="t('edit.redo_tip')" @click="ed()?.redo()"><Icon name="redo" /></button>
    </div>
    <span class="sep" />
    <div class="grp">
      <button class="btn ghost" @click="store.modals.learning = true"><Icon name="graduation" />{{ t('toolbar.learn') }}</button>
      <button class="btn ghost" @click="store.modals.examples = true"><Icon name="book" />{{ t('toolbar.examples') }}</button>
      <button class="btn ghost" :data-tip="t('toolbar.demo_tip')" @click="runDemo"><Icon name="demo" />{{ t('toolbar.demo') }}</button>
    </div>
    <span class="sep" />
    <div class="grp">
      <button class="btn ghost act go" :disabled="runDisabled" :data-tip="t('toolbar.run_tip')" @click="toggleRun"><Icon name="play" :size="14" />{{ runLabel }}</button>
      <button class="btn ghost act pause" :disabled="!live" :aria-label="store.stats.running ? t('sim.pause') : t('sim.start')" :data-tip="(store.stats.running ? t('sim.pause') : t('sim.start')) + ' (' + t('key.space') + ')'" @click="toggleSim">
        <Icon :name="store.stats.running ? 'pause' : 'play'" :size="14" /><span class="lbl">{{ store.stats.running ? t('sim.pause') : t('sim.start_short') }}</span></button>
      <button class="btn ghost act stop" :disabled="!stoppable" :aria-label="t('sim.stop')" :data-tip="t('sim.stop_tip')" @click="toggleRun"><Icon name="stop" :size="14" /><span class="lbl">{{ t('sim.stop') }}</span></button>
      <button class="btn ghost icon" :disabled="!live" :aria-label="t('sim.reset')" :data-tip="t('sim.reset_tip')" @click="resetSim"><Icon name="reset" /></button>
      <button class="btn ghost icon" :disabled="!store.boot.ready || !idle" :aria-label="t('sim.restart_scene')" :data-tip="t('sim.restart_scene_tip')" @click="restartScene"><Icon name="refresh" /></button>
      <button class="btn ghost icon" :disabled="!live" :aria-label="t('sim.step')" :data-tip="t('sim.step_tip')" @click="stepOnce"><Icon name="step" /></button>
      <select class="input mono speed" :value="store.speed" :aria-label="t('speed.aria')" @change="setSpeed(Number($event.target.value))">
        <option v-for="s in speeds" :key="s" :value="s">{{ speedLabel(s) }}</option>
      </select>
    </div>
    <span class="sep" />
    <div class="seg" role="radiogroup" :aria-label="t('tool.aria')">
      <button v-for="tl in tools" :key="tl.id" class="btn icon" :class="{ active: store.tool === tl.id }" role="radio" :aria-checked="store.tool === tl.id"
        :aria-label="t('tool.' + tl.id)" :data-tip="`${t('tool.' + tl.id)} (${tl.key})`" @click="store.tool = tl.id"><Icon :name="tl.icon" /></button>
    </div>
    <span class="sep" />
    <div class="dd">
      <button ref="layersBtn" class="btn ghost" :class="{ active: menu }" aria-haspopup="true" :aria-expanded="menu" @click="toggleMenu"><Icon name="layers" />{{ t('layers.title') }}<Icon name="chevronDown" :size="12" /></button>
      <div v-if="menu" class="menu panel float" role="menu" :aria-label="t('layers.title')" :style="{ left: menuPos.left + 'px', top: menuPos.top + 'px' }">
        <label v-for="k in layers" :key="k" class="mi"><input v-model="store.options[k]" type="checkbox" /> {{ t('layers.' + k) }}</label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tb { height: var(--toolbar-h); background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: var(--sp-4); padding: 0 var(--sp-5); overflow-x: auto; overflow-y: visible; scrollbar-width: none; position: relative; z-index: var(--z-bar); }
.grp { display: flex; align-items: center; gap: var(--sp-1); flex: none; }
.sep { width: 1px; height: 20px; background: var(--border); flex: none; }
.btn { flex: none; }
.act.go { color: var(--ok); font-weight: 500; }
.act.pause { color: var(--warn); }
.act.stop { color: var(--danger); }
.act.go:hover:not(:disabled) { background: var(--ok-soft); } .act.pause:hover:not(:disabled) { background: var(--warn-soft); } .act.stop:hover:not(:disabled) { background: var(--danger-soft); }
.speed { width: 64px; margin-left: var(--sp-2); }
.seg { display: flex; border: 1px solid var(--border-strong); border-radius: var(--radius-sm); overflow: hidden; flex: none; }
.seg .btn { border: none; border-radius: 0; background: var(--surface); }
.seg .btn + .btn { border-left: 1px solid var(--border); }
.seg .btn.active { background: var(--accent-soft); color: var(--accent); }
.dd { flex: none; }
.menu { position: fixed; min-width: 220px; padding: var(--sp-2); display: flex; flex-direction: column; z-index: var(--z-menu); box-shadow: var(--shadow); }
.mi { display: flex; align-items: center; gap: var(--sp-4); min-height: var(--h-md); padding: 0 var(--sp-4); border-radius: var(--radius-xs); cursor: pointer; }
.mi:hover { background: var(--accent-soft); }
@media (min-width: 900px) { .tb { overflow: visible; } } /* tooltips ficam visíveis; abaixo disso a barra rola */
@media (max-width: 1280px) { .lbl { display: none; } }
@media (max-width: 899px) { .btn.icon { width: var(--h-touch); min-height: var(--h-touch); } }
</style>
