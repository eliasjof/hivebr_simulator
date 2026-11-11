<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import PlotChart from './PlotChart.vue'
import { store, scene, logData, send, addCapture, toast } from '../state/store.js'
import { t, fmtNum, fmtInt } from '../i18n/index.js'

const table = ref(false)
const hidden = ref(new Set())
const live = computed(() => store.run.state === 'running')

// ---- seleção de sinais visíveis ----
const SIGNAL_KEY = 'hivebr.web.plots.signals.v1'
const SIGNAL_IDS = ['xy', 'ep', 'eo', 'v', 'w', 'th']
function loadShown() {
  const base = Object.fromEntries(SIGNAL_IDS.map((id) => [id, true]))
  try {
    const saved = JSON.parse(localStorage.getItem(SIGNAL_KEY) || 'null')
    if (saved) for (const id of SIGNAL_IDS) if (id in saved) base[id] = !!saved[id]
  } catch { /* ignora storage inválido */ }
  return base
}
const shown = ref(loadShown())
watch(shown, (v) => { try { localStorage.setItem(SIGNAL_KEY, JSON.stringify(v)) } catch { /* quota */ } }, { deep: true })
const signalMenu = ref(false)
const signalBox = ref(null)
const signalDefs = computed(() => [
  { id: 'xy', label: t('plots.xy') },
  { id: 'ep', label: t('plots.err_pos') },
  { id: 'eo', label: t('plots.err_theta') },
  { id: 'v', label: t('plots.v') },
  { id: 'w', label: t('plots.w') },
  { id: 'th', label: t('plots.theta') },
])
function toggleSignal(id) { shown.value = { ...shown.value, [id]: !shown.value[id] } }
function allSignals(v) { shown.value = Object.fromEntries(SIGNAL_IDS.map((id) => [id, v])) }
const shownCount = computed(() => SIGNAL_IDS.filter((id) => shown.value[id]).length)
function onDocClick(e) { if (signalMenu.value && signalBox.value && !signalBox.value.contains(e.target)) signalMenu.value = false }

// ---- ajuste de eixos por gráfico ----
const axes = ref({})
function setAxis(id, val) { axes.value = { ...axes.value, [id]: val } }

// ---- captura dos gráficos para a galeria de Capturas ----
const chartsEl = ref(null)
const capturing = ref(false)
const SVG_PROPS = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin', 'stroke-opacity', 'opacity', 'font-family', 'font-size', 'font-weight', 'font-style', 'font-variant-numeric', 'text-anchor', 'dominant-baseline', 'paint-order', 'visibility']

function inlineSvg(svg) {
  const clone = svg.cloneNode(true)
  const src = [svg, ...svg.querySelectorAll('*')]
  const dst = [clone, ...clone.querySelectorAll('*')]
  for (let i = 0; i < src.length; i++) {
    const cs = getComputedStyle(src[i])
    for (const p of SVG_PROPS) {
      const v = cs.getPropertyValue(p)
      if (v) dst[i].style.setProperty(p, v)
    }
  }
  return clone
}
function svgToImage(svg) {
  const clone = inlineSvg(svg)
  const xml = new XMLSerializer().serializeToString(clone)
  const url = URL.createObjectURL(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }))
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('svg')) }
    img.src = url
  })
}
async function capturePlots() {
  if (capturing.value) return
  capturing.value = true
  try {
    if (table.value) { table.value = false; await nextTick() }
    const root = chartsEl.value
    const figs = root ? [...root.querySelectorAll('figure.pc')] : []
    const items = []
    for (const fig of figs) {
      const svg = fig.querySelector('svg.svg')
      if (!svg) continue
      const title = fig.querySelector('.ttl')?.textContent?.trim() || ''
      const img = await svgToImage(svg)
      const w = Number(svg.getAttribute('width')) || img.naturalWidth || img.width
      const h = Number(svg.getAttribute('height')) || img.naturalHeight || img.height
      if (w && h) items.push({ title, img, w, h })
    }
    if (!items.length) { toast(t('plots.capture_empty'), 'warn'); return }

    const css = getComputedStyle(document.documentElement)
    const bg = css.getPropertyValue('--surface').trim() || '#ffffff'
    const fg = css.getPropertyValue('--text').trim() || '#111111'
    const cols = items.length === 1 ? 1 : 2
    const pad = 24, gap = 18, titleH = 26, cellW = 520, scale = 2
    const rows = []
    for (let i = 0; i < items.length; i += cols) {
      const row = items.slice(i, i + cols)
      rows.push({ row, h: Math.max(...row.map((it) => it.h * (cellW / it.w))) })
    }
    const width = pad * 2 + cols * cellW + (cols - 1) * gap
    const height = pad * 2 + rows.reduce((s, r) => s + r.h + titleH, 0) + (rows.length - 1) * gap
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(width * scale)
    canvas.height = Math.round(height * scale)
    const ctx = canvas.getContext('2d')
    ctx.scale(scale, scale)
    ctx.fillStyle = bg
    ctx.fillRect(0, 0, width, height)
    ctx.textBaseline = 'top'
    let y = pad
    for (const r of rows) {
      let x = pad
      for (const it of r.row) {
        ctx.fillStyle = fg
        ctx.font = '600 14px system-ui, -apple-system, Segoe UI, sans-serif'
        ctx.fillText(it.title, x, y)
        ctx.drawImage(it.img, x, y + titleH, cellW, it.h * (cellW / it.w))
        x += cellW + gap
      }
      y += r.h + titleH + gap
    }
    const cap = addCapture(canvas.toDataURL('image/png'), `plots_${store.captures.length + 1}.png`)
    toast(t('plots.capture_saved', { name: cap.name }))
  } catch {
    toast(t('plots.capture_fail'), 'error')
  } finally {
    capturing.value = false
  }
}

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
const visibleCharts = computed(() => charts.value.filter((c) => shown.value[c.id]))
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
  timer = setInterval(() => { if (live.value) refresh() }, 2000)
  document.addEventListener('pointerdown', onDocClick)
})
onBeforeUnmount(() => { clearInterval(timer); document.removeEventListener('pointerdown', onDocClick) })
watch(live, (v) => { if (v) setTimeout(refresh, 300) })
</script>

<template>
  <FloatingWindow id="plots">
    <template #actions>
      <button class="btn ghost icon sm" :disabled="!live" :aria-label="t('plots.refresh')" :data-tip="t('plots.refresh_tip')" @click="refresh"><Icon name="refresh" /></button>
      <button class="btn ghost icon sm" :disabled="!hasData || !shownCount || capturing" :aria-label="t('plots.capture')" :data-tip="t('plots.capture_tip')" @click="capturePlots"><Icon name="camera" /></button>
      <button class="btn ghost icon sm" :class="{ active: table }" :aria-label="t('plots.toggle_table')" :aria-pressed="table" :data-tip="t('plots.table')" @click="table = !table"><Icon name="table" /></button>
    </template>

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
        <div ref="signalBox" class="sig-menu">
          <button class="btn sm" aria-haspopup="true" :aria-expanded="signalMenu" @click="signalMenu = !signalMenu">
            <Icon name="sliders" :size="12" />{{ t('plots.choose_signals') }}<span class="faint mono sig-count">{{ shownCount }}/{{ SIGNAL_IDS.length }}</span>
          </button>
          <div v-if="signalMenu" class="menu" role="menu">
            <label v-for="s in signalDefs" :key="s.id" class="mi" role="menuitemcheckbox" :aria-checked="!!shown[s.id]">
              <input type="checkbox" :checked="!!shown[s.id]" @change="toggleSignal(s.id)" />
              <span>{{ s.label }}</span>
            </label>
            <div class="mi-actions">
              <button class="btn ghost sm" @click="allSignals(true)">{{ t('plots.show_all') }}</button>
              <button class="btn ghost sm" @click="allSignals(false)">{{ t('plots.hide_all') }}</button>
            </div>
          </div>
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
        <div v-else-if="!shownCount" class="empty">
          <Icon name="chart" :size="24" />
          <p>{{ t('plots.all_signals_hidden') }}</p>
          <button class="btn sm" @click="allSignals(true)">{{ t('plots.show_all') }}</button>
        </div>
        <div v-else-if="!table" ref="chartsEl" class="charts">
          <PlotChart v-for="c in visibleCharts" :key="c.id" :title="c.title" :unit="c.unit" :series="c.series" :xy="c.xy" :end-labels="c.end" :decimals="c.decimals ?? 3" :empty-text="c.empty" :axis="axes[c.id]" @update:axis="setAxis(c.id, $event)" />
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
  </FloatingWindow>
</template>

<style scoped>
.bar { display: flex; flex-wrap: wrap; gap: var(--sp-4) var(--sp-6); align-items: center; padding: var(--sp-4) var(--sp-5); border-bottom: 1px solid var(--border); flex: none; }
.filters { display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-5); }
.flt { display: inline-flex; align-items: center; gap: var(--sp-3); cursor: pointer; }
.flt.off svg { opacity: .3; }
.styles { display: inline-flex; align-items: center; gap: var(--sp-3); font-size: var(--fs-label); color: var(--text-muted); }
.exp { display: flex; gap: var(--sp-3); margin-left: auto; }
.sig-menu { position: relative; }
.sig-count { font-weight: 400; font-size: var(--fs-xs); }
.menu { position: absolute; top: calc(100% + 4px); left: 0; z-index: 30; min-width: 210px; padding: var(--sp-2); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow, 0 8px 24px rgba(0,0,0,.18)); display: flex; flex-direction: column; gap: 2px; }
.mi { display: flex; align-items: center; gap: var(--sp-3); padding: var(--sp-2) var(--sp-3); border-radius: var(--radius-xs); cursor: pointer; font-size: var(--fs-label); }
.mi:hover { background: var(--surface-2); }
.mi input { margin: 0; }
.mi-actions { display: flex; gap: var(--sp-2); padding: var(--sp-2) var(--sp-2) 0; border-top: 1px solid var(--border); margin-top: var(--sp-2); }
.mi-actions .btn { flex: 1; justify-content: center; }
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
</style>
