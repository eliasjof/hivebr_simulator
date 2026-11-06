<script setup>
import { reactive, computed, ref, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import {
  store, scene, files, selectRobot, readClientFile, download, toast, toggleWindow, openWindow, focusEditor,
} from '../state/store.js'
import { t, fmtNum, fmtInt } from '../i18n/index.js'

const open = reactive({ script: true, robots: true, scene: true, files: true, tools: true })
const menu = ref(false)
const dd = ref(null)
const robots = computed(() => scene.value?.robots || [])
const rgb = (c) => (c ? `rgb(${c[0]},${c[1]},${c[2]})` : 'var(--text-muted)')
const mapInfo = computed(() => {
  const s = scene.value
  if (s?.map) return t('nav.map_occupancy', { w: fmtNum(s.map.width_m, 1), h: fmtNum(s.map.height_m, 1) })
  if (s?.lineMap) return t('nav.map_line', { w: fmtNum(s.lineMap.width_m, 1), h: fmtNum(s.lineMap.height_m, 1) })
  return t('nav.map_none')
})
const sensorTag = (r) => (r.num_sensors ? t('nav.sensors_short', { n: r.num_sensors }) : null)
const tabName = (tab) => (tab.readonly ? t('tab.demo') : tab.id === store.activeId ? store.fileName : tab.name)
async function getFile(f) {
  try { download(f.path.split('/').pop(), new Blob([await readClientFile(f.path)])) } catch (e) { toast(t('console.read_failed', { path: f.path, error: e.message }), 'error') }
}
function setAll(v) { Object.keys(open).forEach((k) => { open[k] = v }); menu.value = false }
function tool(id) { store.tool = id }
// o menu "…" fecha com clique fora, Esc ou ao escolher um item
function onDoc(e) { if (menu.value && !dd.value?.contains(e.target)) menu.value = false }
function onKey(e) { if (menu.value && e.key === 'Escape') { menu.value = false; e.stopPropagation() } }
onMounted(() => { document.addEventListener('pointerdown', onDoc); document.addEventListener('keydown', onKey, true) })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', onDoc); document.removeEventListener('keydown', onKey, true) })
</script>

<template>
  <aside class="nav" :aria-label="t('nav.title')">
    <header class="ph">
      <Icon name="list" :size="14" /><span class="sec-h">{{ t('nav.title') }}</span><span class="sp" />
      <div ref="dd" class="dd">
        <button class="btn ghost icon sm" :aria-label="t('nav.more')" aria-haspopup="true" :aria-expanded="menu" @click="menu = !menu"><Icon name="dots" :size="14" /></button>
        <div v-if="menu" class="pop panel float" role="menu">
          <button class="mi" role="menuitem" @click="setAll(true)">{{ t('nav.expand_all') }}</button>
          <button class="mi" role="menuitem" @click="setAll(false)">{{ t('nav.collapse_all') }}</button>
          <button class="mi" role="menuitem" @click="store.layout.leftOpen = false; menu = false">{{ t('nav.hide') }}</button>
        </div>
      </div>
    </header>
    <div class="tree">
      <button class="node h" :aria-expanded="open.script" @click="open.script = !open.script"><Icon :name="open.script ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="code" :size="14" /><span class="lb strong">{{ t('nav.script') }}</span></button>
      <div v-if="open.script" class="kids">
        <button v-for="tab in store.tabs" :key="tab.id" class="node" :class="{ sel: tab.id === store.activeId }" @click="focusEditor()">
          <span class="dot" /><span class="lb mono">{{ tabName(tab) }}</span><span v-if="tab.readonly" class="pill gray">{{ t('nav.readonly') }}</span></button>
      </div>

      <button class="node h" :aria-expanded="open.robots" @click="open.robots = !open.robots"><Icon :name="open.robots ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="robot" :size="14" /><span class="lb strong">{{ t('nav.robots') }}</span><span class="count" data-testid="cnt-robots">{{ fmtInt(robots.length) }}</span></button>
      <div v-if="open.robots" class="kids">
        <p v-if="!robots.length" class="empty">{{ t('nav.no_robots') }}</p>
        <button v-for="(r, i) in robots" :key="r.id ?? i" class="node" :class="{ sel: i === store.selected }" @click="selectRobot(i)">
          <span class="swatch" :style="{ background: rgb(r.color) }" /><span class="lb mono">{{ r.id }}</span>
          <span class="pill blue">{{ r.type }}</span><span v-if="sensorTag(r)" class="pill amber">{{ sensorTag(r) }}</span></button>
      </div>

      <button class="node h" :aria-expanded="open.scene" @click="open.scene = !open.scene"><Icon :name="open.scene ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="layers" :size="14" /><span class="lb strong">{{ t('nav.scene') }}</span></button>
      <div v-if="open.scene" class="kids">
        <div class="node"><span class="dot" /><span class="lb">{{ t('nav.obstacles') }}</span><span class="count" data-testid="cnt-obstacles">{{ fmtInt(store.sceneCounts.obstacles) }}</span></div>
        <button class="btn link add" @click="tool('obstacle')">{{ t('nav.add_obstacle') }}</button>
        <div class="node"><span class="dot" /><span class="lb">{{ t('nav.waypoints') }}</span><span class="count" data-testid="cnt-waypoints">{{ fmtInt(store.sceneCounts.waypoints) }}</span></div>
        <button class="btn link add" @click="tool('waypoint')">{{ t('nav.add_waypoint') }}</button>
        <div class="node"><span class="dot" /><span class="lb">{{ t('nav.recharge') }}</span><span class="count" data-testid="cnt-recharge">{{ fmtInt(store.sceneCounts.recharge) }}</span></div>
        <button class="btn link add" @click="tool('recharge')">{{ t('nav.add_recharge') }}</button>
        <div class="node"><span class="dot" /><span class="lb">{{ t('nav.map') }}</span><span class="muted small">{{ mapInfo }}</span></div>
        <button class="btn link add" @click="openWindow('map')">{{ t('nav.load_map') }}</button>
      </div>

      <button class="node h" :aria-expanded="open.files" @click="open.files = !open.files"><Icon :name="open.files ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="download" :size="14" /><span class="lb strong">{{ t('nav.files') }}</span><span class="count">{{ fmtInt(files.length) }}</span></button>
      <div v-if="open.files" class="kids">
        <p v-if="!files.length" class="empty">{{ t('nav.no_files') }}</p>
        <button v-for="f in files" :key="f.path" class="node" :title="t('console.download', { path: f.path })" @click="getFile(f)"><span class="dot" /><span class="lb mono">{{ f.path.split('/').pop() }}</span></button>
      </div>

      <button class="node h" :aria-expanded="open.tools" @click="open.tools = !open.tools"><Icon :name="open.tools ? 'chevronDown' : 'chevron'" :size="12" /><Icon name="sliders" :size="14" /><span class="lb strong">{{ t('nav.tools') }}</span></button>
      <div v-if="open.tools" class="kids">
        <button class="node" @click="toggleWindow('params')"><Icon name="sliders" :size="13" /><span class="lb">{{ t('win.params') }}</span><kbd>P</kbd></button>
        <button class="node" @click="toggleWindow('plots')"><Icon name="chart" :size="13" /><span class="lb">{{ t('win.plots') }}</span><kbd>G</kbd></button>
        <button class="node" @click="toggleWindow('map')"><Icon name="map" :size="13" /><span class="lb">{{ t('win.map') }}</span><kbd>K</kbd></button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.nav { display: flex; flex-direction: column; height: 100%; min-height: 0; background: var(--surface); border-right: 1px solid var(--border); }
.ph { display: flex; align-items: center; gap: var(--sp-4); height: var(--panel-head-h); padding: 0 var(--sp-4) 0 var(--sp-5); flex: none; border-bottom: 1px solid var(--border); color: var(--text-muted); }
.sp { flex: 1; }
.dd { position: relative; }
.pop { position: absolute; right: 0; top: 100%; z-index: var(--z-tip); min-width: 150px; padding: var(--sp-2); display: flex; flex-direction: column; box-shadow: var(--shadow); }
.mi { background: none; border: none; text-align: left; min-height: var(--h-md); padding: 0 var(--sp-4); border-radius: var(--radius-xs); }
.mi:hover { background: var(--accent-soft); }
.tree { flex: 1; overflow: auto; padding: var(--sp-3) 0 var(--sp-5); }
.node { display: flex; align-items: center; gap: var(--sp-4); width: 100%; min-height: var(--h-md); padding: 0 var(--sp-5); background: none; border: none; text-align: left; color: var(--text); }
button.node:hover { background: var(--surface-3); }
.node.h > svg:first-child { color: var(--text-muted); }
.strong { font-weight: 500; }
.node.sel { background: var(--accent-soft); }
.lb { flex: 1 0 auto; min-width: 2.5ch; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kids { margin-left: 18px; border-left: 1px solid var(--border); padding-left: var(--sp-1); }
.kids .node { padding-left: 10px; }
.dot { width: 5px; height: 5px; border-radius: 50%; background: var(--border-strong); flex: none; }
.swatch { width: 10px; height: 10px; flex: none; clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
.count { font-size: var(--fs-xs); color: var(--text-muted); background: var(--surface-3); border-radius: var(--radius-pill); padding: 0 7px; min-width: 22px; text-align: center; font-family: var(--font-mono); }
.pill { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 0 1 auto; font-size: var(--fs-2xs); font-weight: 600; letter-spacing: .02em; padding: 1px var(--sp-3); border-radius: var(--radius-xs); font-family: var(--font-mono); }
.pill.blue { background: var(--accent-soft); color: var(--accent); }
.pill.amber { background: var(--warn-soft); color: var(--warn); flex: none; }
.pill.gray { background: var(--surface-3); color: var(--text-muted); flex: none; }
.add { margin-left: 20px; display: block; min-height: 22px; }
.empty { margin: var(--sp-1) 10px var(--sp-3); font-size: var(--fs-sm); color: var(--text-muted); }
.small { font-size: var(--fs-label); }
</style>
