<script setup>
import { reactive, computed, ref } from 'vue'
import Icon from './Icon.vue'
import {
  store, scene, files, selectRobot, readClientFile, download, toast, toggleWindow, openWindow, openPanel, focusEditor,
} from '../state/store.js'

const open = reactive({ script: true, robots: true, scene: true, files: true, tools: true })
const menu = ref(false)
const robots = computed(() => scene.value?.robots || [])
const rgb = (c) => (c ? `rgb(${c[0]},${c[1]},${c[2]})` : 'var(--text-muted)')
const mapInfo = computed(() => {
  const s = scene.value
  if (s?.map) return `Ocupação ${s.map.width_m.toFixed(1)}×${s.map.height_m.toFixed(1)} m`
  if (s?.lineMap) return `Pista ${s.lineMap.width_m.toFixed(1)}×${s.lineMap.height_m.toFixed(1)} m`
  return 'Nenhum'
})
const sensorTag = (r) => (r.num_sensors ? `${r.num_sensors} sens.` : null)
async function getFile(f) {
  try { download(f.path.split('/').pop(), new Blob([await readClientFile(f.path)])) } catch (e) { toast(`Falha ao ler ${f.path}: ${e.message}`, 'error') }
}
function setAll(v) { Object.keys(open).forEach((k) => { open[k] = v }); menu.value = false }
function tool(t) { store.tool = t }
</script>

<template>
  <aside class="nav" aria-label="Navegador">
    <header class="ph">
      <Icon name="list" :size="14" /><span class="sec-h">Navegador</span><span class="sp" />
      <div class="dd">
        <button class="btn ghost icon sm" aria-label="Mais ações" aria-haspopup="true" :aria-expanded="menu" @click="menu = !menu"><Icon name="dots" :size="14" /></button>
        <div v-if="menu" class="pop panel float" role="menu" @mouseleave="menu = false">
          <button class="mi" role="menuitem" @click="setAll(true)">Expandir tudo</button>
          <button class="mi" role="menuitem" @click="setAll(false)">Recolher tudo</button>
          <button class="mi" role="menuitem" @click="store.layout.leftOpen = false">Ocultar painel</button>
        </div>
      </div>
    </header>
    <div class="tree">
      <button class="node h" :aria-expanded="open.script" @click="open.script = !open.script"><Icon :name="open.script ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="code" :size="14" /><span class="lb strong">Script atual</span></button>
      <div v-if="open.script" class="kids">
        <button v-for="t in store.tabs" :key="t.id" class="node" :class="{ sel: t.id === store.activeId }" @click="focusEditor()">
          <span class="dot" /><span class="lb mono">{{ t.id === store.activeId ? store.fileName : t.name }}</span><span v-if="t.readonly" class="pill gray">leitura</span></button>
      </div>

      <button class="node h" :aria-expanded="open.robots" @click="open.robots = !open.robots"><Icon :name="open.robots ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="robot" :size="14" /><span class="lb strong">Robôs</span><span class="count" data-testid="cnt-robots">{{ robots.length }}</span></button>
      <div v-if="open.robots" class="kids">
        <p v-if="!robots.length" class="empty">Nenhum robô. Execute um código.</p>
        <button v-for="(r, i) in robots" :key="r.id ?? i" class="node" :class="{ sel: i === store.selected }" @click="selectRobot(i)">
          <span class="swatch" :style="{ background: rgb(r.color) }" /><span class="lb mono">{{ r.id }}</span>
          <span class="pill blue">{{ r.type }}</span><span v-if="sensorTag(r)" class="pill amber">{{ sensorTag(r) }}</span></button>
      </div>

      <button class="node h" :aria-expanded="open.scene" @click="open.scene = !open.scene"><Icon :name="open.scene ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="layers" :size="14" /><span class="lb strong">Cena</span></button>
      <div v-if="open.scene" class="kids">
        <div class="node"><span class="dot" /><span class="lb">Obstáculos</span><span class="count" data-testid="cnt-obstacles">{{ store.sceneCounts.obstacles }}</span></div>
        <button class="btn link add" @click="tool('obstacle')">+ Adicionar obstáculo</button>
        <div class="node"><span class="dot" /><span class="lb">Waypoints</span><span class="count" data-testid="cnt-waypoints">{{ store.sceneCounts.waypoints }}</span></div>
        <button class="btn link add" @click="tool('waypoint')">+ Adicionar waypoint</button>
        <div class="node"><span class="dot" /><span class="lb">Pontos de recarga</span><span class="count" data-testid="cnt-recharge">{{ store.sceneCounts.recharge }}</span></div>
        <button class="btn link add" @click="tool('recharge')">+ Adicionar recarga</button>
        <div class="node"><span class="dot" /><span class="lb">Mapa</span><span class="muted small">{{ mapInfo }}</span></div>
        <button class="btn link add" @click="openWindow('map')">+ Carregar mapa ou pista</button>
      </div>

      <button class="node h" :aria-expanded="open.files" @click="open.files = !open.files"><Icon :name="open.files ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="download" :size="14" /><span class="lb strong">Arquivos gerados</span><span class="count">{{ files.length }}</span></button>
      <div v-if="open.files" class="kids">
        <p v-if="!files.length" class="empty">Arquivos criados pelo código aparecem aqui.</p>
        <button v-for="f in files" :key="f.path" class="node" @click="getFile(f)" :title="'Baixar ' + f.path"><span class="dot" /><span class="lb mono">{{ f.path.split('/').pop() }}</span></button>
      </div>

      <button class="node h" :aria-expanded="open.tools" @click="open.tools = !open.tools"><Icon :name="open.tools ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="sliders" :size="14" /><span class="lb strong">Ferramentas</span></button>
      <div v-if="open.tools" class="kids">
        <button class="node" @click="toggleWindow('params')"><Icon name="sliders" :size="13" /><span class="lb">Parâmetros</span><kbd>P</kbd></button>
        <button class="node" @click="toggleWindow('plots')"><Icon name="chart" :size="13" /><span class="lb">Gráficos</span><kbd>G</kbd></button>
        <button class="node" @click="toggleWindow('map')"><Icon name="map" :size="13" /><span class="lb">Mapa</span><kbd>K</kbd></button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.nav { display: flex; flex-direction: column; height: 100%; min-height: 0; background: var(--surface); border-right: 1px solid var(--border); }
.ph { display: flex; align-items: center; gap: 8px; height: 34px; padding: 0 8px 0 12px; flex: none; border-bottom: 1px solid var(--border); color: var(--text-muted); }
.sp { flex: 1; }
.dd { position: relative; }
.pop { position: absolute; right: 0; top: 100%; z-index: 20; min-width: 150px; padding: 4px; display: flex; flex-direction: column; }
.mi { background: none; border: none; text-align: left; padding: 5px 8px; border-radius: 4px; }
.mi:hover { background: var(--accent-soft); }
.tree { flex: 1; overflow: auto; padding: 6px 0 12px; }
.node { display: flex; align-items: center; gap: 8px; width: 100%; min-height: 28px; padding: 0 12px; background: none; border: none; text-align: left; color: var(--text); }
button.node:hover { background: var(--surface-3); }
.node.h { color: var(--text); }
.node.h > svg:first-child { color: var(--text-faint); }
.strong { font-weight: 500; }
.node.sel { background: var(--accent-soft); }
.lb { flex: 1 0 auto; min-width: 2.5ch; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kids { margin-left: 18px; border-left: 1px solid var(--border); padding-left: 2px; }
.kids .node { padding-left: 10px; }
.dot { width: 5px; height: 5px; border-radius: 50%; background: var(--border-strong); flex: none; }
.swatch { width: 10px; height: 10px; flex: none; clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
.count { font-size: 11px; color: var(--text-muted); background: var(--surface-3); border-radius: 99px; padding: 0 7px; min-width: 22px; text-align: center; font-family: var(--font-mono); }
.pill { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 0 1 auto; font-size: 10px; font-weight: 600; letter-spacing: .02em; padding: 1px 6px; border-radius: 4px; font-family: var(--font-mono); }
.pill.blue { background: rgba(37, 99, 235, .12); color: var(--accent); }
.pill.amber { background: var(--warn-soft); color: var(--warn); }
.pill.amber { flex: none; }
.pill.gray { background: var(--surface-3); color: var(--text-muted); }
.add { margin-left: 20px; display: block; min-height: 22px; }
.empty { margin: 2px 10px 6px; font-size: 12px; color: var(--text-faint); }
.small { font-size: 11.5px; }
kbd { font-size: 10.5px; }
</style>
