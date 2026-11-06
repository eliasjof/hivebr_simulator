<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import {
  store, canvasRef, toggleRun, toggleSim, stepOnce, resetSim, setSpeed, newFile, pickFile, downloadScript, runDemo,
} from '../state/store.js'

const runLabel = computed(() => {
  if (!store.boot.ready && store.run.state === 'idle') return 'Carregando'
  return { idle: 'Executar', starting: 'Executando', running: 'Executando', stopping: 'Parando' }[store.run.state]
})
const idle = computed(() => store.run.state === 'idle')
const runDisabled = computed(() => !idle.value || !store.boot.ready)
const live = computed(() => store.run.state === 'running')
const stoppable = computed(() => store.run.state === 'running' || store.run.state === 'starting')

const tools = [
  { id: 'select', label: 'Selecionar', key: 'V', icon: 'cursor' },
  { id: 'waypoint', label: 'Waypoint', key: 'W', icon: 'waypoint' },
  { id: 'obstacle', label: 'Obstáculo', key: 'O', icon: 'obstacle' },
  { id: 'recharge', label: 'Recarga', key: 'R', icon: 'bolt' },
  { id: 'move', label: 'Mover robô', key: 'M', icon: 'move' },
  { id: 'draw', label: 'Desenhar pista', key: 'D', icon: 'pen' },
]
const speeds = [0.25, 0.5, 1, 2, 4, Infinity]
const speedLabel = (s) => (s === Infinity ? 'Máx' : `${s}×`)
const layers = [
  ['showGrid', 'Grade'], ['showPaths', 'Rastros'], ['showLidar', 'LiDAR'],
  ['showWaypoints', 'Waypoints'], ['showLabels', 'Rótulos'], ['showLinks', 'Ligações entre robôs'],
]
const menu = ref(false)
const root = ref(null)
function onDoc(e) { if (menu.value && !root.value.contains(e.target)) menu.value = false }
function onKey(e) { if (e.key === 'Escape') menu.value = false }
onMounted(() => { document.addEventListener('pointerdown', onDoc); document.addEventListener('keydown', onKey) })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', onDoc); document.removeEventListener('keydown', onKey) })
const ed = () => store.editorApi
</script>

<template>
  <div ref="root" class="tb" role="toolbar" aria-label="Barra de ferramentas">
    <div class="grp">
      <button class="btn ghost icon" aria-label="Novo script" data-tip="Novo script" data-tip-pos="start" @click="newFile"><Icon name="file" /></button>
      <button class="btn ghost icon" aria-label="Abrir .py" data-tip="Abrir .py (Ctrl+O)" @click="pickFile"><Icon name="open" /></button>
      <button class="btn ghost icon" aria-label="Baixar .py" data-tip="Baixar .py" @click="downloadScript"><Icon name="save" /></button>
    </div>
    <span class="sep" />
    <div class="grp">
      <button class="btn ghost icon" :disabled="!ed()" aria-label="Desfazer" data-tip="Desfazer (Ctrl+Z)" @click="ed()?.undo()"><Icon name="undo" /></button>
      <button class="btn ghost icon" :disabled="!ed()" aria-label="Refazer" data-tip="Refazer (Ctrl+Shift+Z)" @click="ed()?.redo()"><Icon name="redo" /></button>
    </div>
    <span class="sep" />
    <div class="grp">
      <button class="btn ghost" @click="store.modals.examples = true"><Icon name="book" />Exemplos</button>
      <button class="btn ghost" data-tip="Abre e executa um exemplo somente leitura" @click="runDemo"><Icon name="demo" />Demonstração</button>
    </div>
    <span class="sep" />
    <div class="grp">
      <button class="btn ghost act go" :disabled="runDisabled" data-tip="Executar o código (Ctrl+Enter)" @click="toggleRun"><Icon name="play" :size="14" />{{ runLabel }}</button>
      <button class="btn ghost act pause" :disabled="!live" :aria-label="store.stats.running ? 'Pausar' : 'Iniciar simulação'" :data-tip="(store.stats.running ? 'Pausar' : 'Iniciar simulação') + ' (Espaço)'" @click="toggleSim">
        <Icon :name="store.stats.running ? 'pause' : 'play'" :size="14" /><span class="lbl">{{ store.stats.running ? 'Pausar' : 'Iniciar' }}</span></button>
      <button class="btn ghost act stop" :disabled="!stoppable" aria-label="Parar" data-tip="Parar a execução" @click="toggleRun"><Icon name="stop" :size="14" /><span class="lbl">Parar</span></button>
      <button class="btn ghost icon" :disabled="!live" aria-label="Reiniciar simulação" data-tip="Reiniciar (Shift+R)" @click="resetSim"><Icon name="reset" /></button>
      <button class="btn ghost icon" :disabled="!live" aria-label="Passo" data-tip="Um passo (.)" @click="stepOnce"><Icon name="step" /></button>
      <select class="input mono speed" :value="store.speed" aria-label="Velocidade da simulação" @change="setSpeed(Number($event.target.value))">
        <option v-for="s in speeds" :key="s" :value="s">{{ speedLabel(s) }}</option>
      </select>
    </div>
    <span class="sep" />
    <div class="seg" role="radiogroup" aria-label="Ferramenta">
      <button v-for="t in tools" :key="t.id" class="btn icon" :class="{ active: store.tool === t.id }" role="radio" :aria-checked="store.tool === t.id"
        :aria-label="t.label" :data-tip="`${t.label} (${t.key})`" @click="store.tool = t.id"><Icon :name="t.icon" /></button>
    </div>
    <span class="sep" />
    <div class="dd">
      <button class="btn ghost" :class="{ active: menu }" aria-haspopup="true" :aria-expanded="menu" @click="menu = !menu"><Icon name="layers" />Camadas<Icon name="chevronDown" :size="12" /></button>
      <div v-if="menu" class="menu panel float" role="menu">
        <label v-for="[k, l] in layers" :key="k" class="mi"><input type="checkbox" v-model="store.options[k]" /> {{ l }}</label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tb { height: var(--toolbar-h); background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; padding: 0 12px; overflow-x: auto; overflow-y: visible; scrollbar-width: none; position: relative; z-index: 60; }
.grp { display: flex; align-items: center; gap: 2px; flex: none; }
.sep { width: 1px; height: 20px; background: var(--border); flex: none; }
.btn { flex: none; }
.btn:disabled { opacity: .4; }
.act.go { color: var(--ok); font-weight: 500; }
.act.pause { color: var(--warn); }
.act.stop { color: var(--danger); }
.act.go:hover:not(:disabled) { background: var(--ok-soft); } .act.pause:hover:not(:disabled) { background: var(--warn-soft); } .act.stop:hover:not(:disabled) { background: var(--danger-soft); }
.speed { width: 64px; margin-left: 4px; }
.seg { display: flex; border: 1px solid var(--border-strong); border-radius: var(--radius-sm); overflow: hidden; flex: none; }
.seg .btn { border: none; border-radius: 0; background: var(--surface); }
.seg .btn + .btn { border-left: 1px solid var(--border); }
.seg .btn.active { background: var(--accent-soft); color: var(--accent); }
.dd { position: relative; flex: none; }
.menu { position: fixed; margin-top: 4px; min-width: 200px; padding: 4px; display: flex; flex-direction: column; z-index: var(--z-menu); }
.mi { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 4px; cursor: pointer; }
.mi:hover { background: var(--accent-soft); }
@media (max-width: 1280px) { .lbl { display: none; } }
@media (max-width: 899px) { .btn.icon { width: 34px; min-height: 34px; } }
</style>
