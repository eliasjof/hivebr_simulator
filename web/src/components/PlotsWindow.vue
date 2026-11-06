<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import PlotChart from './PlotChart.vue'
import { store, scene, logData, send, b64ToBlob, download } from '../state/store.js'
import { t, fmtNum, fmtInt, tn } from '../i18n/index.js'

const tab = ref('signals')
const table = ref(false)
const hidden = ref(new Set())
const live = computed(() => store.run.state === 'running')

const DASHES = ['', '8 4', '2 3', '10 3 2 3', '5 2 1 2', '14 4']
const rgb = (c) => (c ? `rgb(${c[0]},${c[1]},${c[2]})` : '#888')

// Identidade do robô: cor da cena e padrão de traço pela posição na cena (estáveis ao filtrar)
const robots = computed(() => {
  const L = logData.value?.robots || []
  const sc = scene.value?.robots || []
  return L.map((r, i) => {
    let idx = sc.findIndex((s) => s.id === r.id)
    if (idx < 0) idx = i
    return { id: r.id, type: r.type, color: rgb(sc[idx]?.color || r.color), dash: DASHES[idx % DASHES.length], idx, data: r }
  })
})
const visible = computed(() => robots.value.filter((r) => !hidden.value.has(r.id)))
function toggle(id) {
  const s = new Set(hidden.value)
  s.has(id) ? s.delete(id) : s.add(id)
  hidden.value = s
}
const R2D = 180 / Math.PI
const mapArr = (a, f) => (a ? a.map(f) : [])

function mk(r, key, field, kind = 'real', conv = null) {
  const y = r.data[field]
  return { key: `${r.id}-${key}`, robot: r.id, label: String(r.id), color: r.color, dash: r.dash, kind, x: r.data.t || [], y: conv ? mapArr(y, conv) : (y || []) }
}
const charts = computed(() => {
  const v = visible.value
  const end = v.length <= 4
  const withCmd = (field, cmd) => v.flatMap((r) => [mk(r, field, field), ...(r.data[cmd]?.length ? [mk(r, cmd, cmd, 'cmd')] : [])])
  return [
    { id: 'xy', title: t('plots.xy'), unit: 'm', xy: true, series: v.map((r) => ({ key: r.id + '-xy', robot: r.id, label: String(r.id), color: r.color, dash: r.dash, kind: 'real', x: r.data.x || [], y: r.data.y || [], t: r.data.t })), decimals: 2 },
    { id: 'ep', title: t('plots.err_pos'), unit: 'm', series: v.map((r) => mk(r, 'err_pos', 'err_pos')), empty: t('plots.empty_err_pos') },
    { id: 'eo', title: t('plots.err_theta'), unit: '°', series: v.map((r) => mk(r, 'err_theta', 'err_theta', 'real', (z) => z * R2D)), decimals: 2, empty: t('plots.empty_err_theta') },
    { id: 'v', title: t('plots.v'), unit: 'm/s', series: withCmd('v', 'v_cmd') },
    { id: 'w', title: t('plots.w'), unit: 'rad/s', series: withCmd('omega', 'omega_cmd') },
    { id: 'th', title: t('plots.theta'), unit: '°', series: v.map((r) => mk(r, 'theta', 'theta', 'real', (z) => z * R2D)), decimals: 1 },
  ].map((c) => ({ ...c, end }))
})
const hasCmd = computed(() => visible.value.some((r) => r.data.v_cmd?.length || r.data.omega_cmd?.length))
const hasData = computed(() => robots.value.some((r) => (r.data.t?.length || 0) > 0))

// tabela (≤200 linhas)
const COLS = [['t', 't (s)'], ['x', 'x'], ['y', 'y'], ['theta', 'θ (°)'], ['v', 'v'], ['omega', 'ω'], ['v_cmd', 'plots.col_v_cmd'], ['omega_cmd', 'plots.col_w_cmd'], ['err_pos', 'plots.col_e_pos'], ['err_theta', 'plots.col_e_theta']]
const colLabel = (k) => (k.startsWith('plots.') ? t(k) : k)
const rows = computed(() => {
  const v = visible.value
  if (!v.length) return []
  const per = Math.max(1, Math.floor(200 / v.length))
  const out = []
  for (const r of v) {
    const n = r.data.t?.length || 0
    const step = Math.max(1, n / per)
    for (let k = 0; k < Math.min(n, per); k++) {
      const i = Math.min(n - 1, Math.floor(k * step))
      out.push({ r, cells: COLS.map(([f]) => {
        const val = r.data[f]?.[i]
        if (val == null || !Number.isFinite(val)) return '—'
        return fmtNum(f === 'theta' || f === 'err_theta' ? val * R2D : val, f === 't' ? 2 : 3)
      }) })
    }
  }
  return out
})

function refresh() { if (!live.value) return; send({ cmd: 'get_log', open: false }) }
function exportLog(fmt) { send({ cmd: 'export_log', format: fmt }) }
function resetLog() { send({ cmd: 'reset_logger' }); setTimeout(refresh, 100) }

let timer = null
onMounted(() => {
  refresh()
  timer = setInterval(() => { if (live.value && tab.value === 'signals') refresh() }, 2000)
})
onBeforeUnmount(() => clearInterval(timer))
watch(live, (v) => { if (v) setTimeout(refresh, 300) })

function dlFig(f, i) { download(`${(f.title || 'figure' + i).replace(/[^\w-]+/g, '_')}.png`, b64ToBlob(f.png_b64, 'image/png')) }
</script>

<template>
  <FloatingWindow id="plots">
    <template #actions>
      <button v-if="tab === 'signals'" class="btn ghost icon sm" :disabled="!live" :aria-label="t('plots.refresh')" :data-tip="t('plots.refresh_tip')" @click="refresh"><Icon name="refresh" /></button>
      <button v-if="tab === 'signals'" class="btn ghost icon sm" :class="{ active: table }" :aria-label="t('plots.toggle_table')" :aria-pressed="table" :data-tip="t('plots.table')" @click="table = !table"><Icon name="table" /></button>
    </template>
    <div class="tabs" role="tablist">
      <button class="tab" role="tab" :aria-selected="tab === 'signals'" @click="tab = 'signals'">{{ t('plots.signals') }}</button>
      <button class="tab" role="tab" :aria-selected="tab === 'figs'" @click="tab = 'figs'">{{ t('plots.figures') }}<span v-if="store.figures.length" class="chip n">{{ fmtInt(store.figures.length) }}</span></button>
    </div>

    <template v-if="tab === 'signals'">
      <div class="bar">
        <div v-if="robots.length" class="filters" role="group" :aria-label="t('plots.filter')">
          <label v-for="r in robots" :key="r.id" class="flt" :class="{ off: hidden.has(r.id) }">
            <input type="checkbox" :checked="!hidden.has(r.id)" @change="toggle(r.id)" />
            <svg width="26" height="8" aria-hidden="true"><line x1="1" x2="25" y1="4" y2="4" :stroke="r.color" stroke-width="2" stroke-linecap="round" :stroke-dasharray="r.dash || null" /></svg>
            <span class="mono">{{ r.id }}</span>
          </label>
        </div>
        <div v-if="hasCmd" class="styles faint">
          <svg width="26" height="8" aria-hidden="true"><line x1="1" x2="25" y1="4" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>{{ t('plots.actual') }}
          <svg width="26" height="8" aria-hidden="true"><line x1="1" x2="25" y1="4" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="0.1 5" /></svg>{{ t('plots.command') }}
        </div>
        <div class="exp">
          <button class="btn sm" :disabled="!live" @click="exportLog('csv')"><Icon name="download" :size="12" />CSV</button>
          <button class="btn sm" :disabled="!live" @click="exportLog('pkl')"><Icon name="download" :size="12" />PKL</button>
          <button class="btn sm danger" :disabled="!live" @click="resetLog"><Icon name="trash" :size="12" />{{ t('plots.reset_log') }}</button>
        </div>
      </div>
      <div class="scroll">
        <div v-if="!hasData" class="empty">
          <Icon name="chart" :size="28" />
          <h3>{{ t('plots.empty_title') }}</h3>
          <p>{{ t('plots.empty_a') }}<code class="mono">logger.plot()</code>{{ t('plots.empty_b') }}</p>
        </div>
        <template v-else-if="!visible.length"><p class="muted pad">{{ t('plots.all_hidden') }}</p></template>
        <div v-else-if="!table" class="charts">
          <PlotChart v-for="c in charts" :key="c.id" :title="c.title" :unit="c.unit" :series="c.series" :xy="c.xy" :end-labels="c.end" :decimals="c.decimals ?? 3" :empty-text="c.empty" />
        </div>
        <div v-else class="tbl-wrap">
          <table class="tbl mono">
            <thead><tr><th>{{ t('plots.col_robot') }}</th><th v-for="c in COLS" :key="c[0]">{{ colLabel(c[1]) }}</th></tr></thead>
            <tbody><tr v-for="(row, k) in rows" :key="k">
              <td><svg width="18" height="8" aria-hidden="true"><line x1="1" x2="17" y1="4" y2="4" :stroke="row.r.color" stroke-width="2" stroke-linecap="round" :stroke-dasharray="row.r.dash || null" /></svg> {{ row.r.id }}</td>
              <td v-for="(cell, j) in row.cells" :key="j">{{ cell }}</td></tr></tbody>
          </table>
          <p class="muted pad">{{ t('plots.table_note') }}</p>
        </div>
        <section v-if="logData?.collisions?.length" class="coll">
          <h3>{{ t('plots.collisions', { n: fmtInt(logData.collisions.length) }) }}</h3>
          <ul class="mono"><li v-for="(c, i) in logData.collisions" :key="i">{{ c }}</li></ul>
        </section>
      </div>
    </template>

    <div v-else class="scroll">
      <div v-if="!store.figures.length" class="empty">
        <Icon name="image" :size="28" />
        <h3>{{ t('plots.no_figs') }}</h3>
        <p>{{ t('plots.no_figs_a') }}<code class="mono">plt.show()</code>{{ t('plots.no_figs_b') }}</p>
      </div>
      <div class="figs">
        <figure v-for="(f, i) in store.figures" :key="i" class="fig">
          <img :src="'data:image/png;base64,' + f.png_b64" :alt="f.title || t('plots.fig_n', { n: i + 1 })" />
          <figcaption><span>{{ f.title || t('plots.fig_n', { n: i + 1 }) }}</span>
            <button class="btn sm" @click="dlFig(f, i)"><Icon name="download" :size="12" />{{ t('plots.download_png') }}</button></figcaption>
        </figure>
      </div>
    </div>
  </FloatingWindow>
</template>

<style scoped>
.n { margin-left: var(--sp-3); padding: 0 var(--sp-3); }
.bar { display: flex; flex-wrap: wrap; gap: var(--sp-4) var(--sp-6); align-items: center; padding: var(--sp-4) var(--sp-5); border-bottom: 1px solid var(--border); flex: none; }
.filters { display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-5); }
.flt { display: inline-flex; align-items: center; gap: var(--sp-3); cursor: pointer; }
.flt.off svg { opacity: .3; }
.styles { display: inline-flex; align-items: center; gap: var(--sp-3); font-size: var(--fs-label); color: var(--text-muted); }
.exp { display: flex; gap: var(--sp-3); margin-left: auto; }
.scroll { flex: 1; min-height: 0; overflow: auto; padding: 10px var(--sp-5) 14px; }
.charts { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; }
.empty { text-align: center; color: var(--text-muted); padding: 28px var(--sp-6); display: flex; flex-direction: column; align-items: center; gap: var(--sp-3); }
.empty svg { color: var(--accent); }
.empty p { max-width: 420px; margin: 0; line-height: 1.5; }
.pad { padding: var(--sp-4) var(--sp-1); }
.tbl-wrap { overflow: auto; }
.tbl { border-collapse: collapse; width: 100%; font-size: var(--fs-label); }
.tbl th, .tbl td { padding: 3px var(--sp-4); text-align: right; white-space: nowrap; border-bottom: 1px solid var(--border); }
.tbl th { position: sticky; top: 0; background: var(--surface); color: var(--text-muted); font-weight: 500; }
.tbl td:first-child, .tbl th:first-child { text-align: left; }
.coll { margin-top: 14px; }
.coll h3 { font-size: var(--fs-sm); margin-bottom: var(--sp-2); }
.coll ul { margin: 0; padding-left: var(--sp-6); max-height: 120px; overflow: auto; font-size: var(--fs-label); color: var(--text-muted); }
.figs { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--sp-5); }
.fig { margin: 0; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: var(--surface); }
.fig img { width: 100%; display: block; }
.fig figcaption { display: flex; justify-content: space-between; align-items: center; padding: var(--sp-3) var(--sp-4); background: var(--surface-2); color: var(--text); }
</style>
