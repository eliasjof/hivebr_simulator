<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import PlotChart from './PlotChart.vue'
import { store, scene, logData, send, b64ToBlob, download } from '../state/store.js'

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
    { id: 'xy', title: 'Trajetória XY', unit: 'm', xy: true, series: v.map((r) => ({ key: r.id + '-xy', robot: r.id, label: String(r.id), color: r.color, dash: r.dash, kind: 'real', x: r.data.x || [], y: r.data.y || [], t: r.data.t })), decimals: 2 },
    { id: 'ep', title: 'Erro de posição', unit: 'm', series: v.map((r) => mk(r, 'err_pos', 'err_pos')), empty: 'Sem dados: o erro de posição só existe enquanto o robô tem um waypoint ativo.' },
    { id: 'eo', title: 'Erro de orientação', unit: '°', series: v.map((r) => mk(r, 'err_theta', 'err_theta', 'real', (z) => z * R2D)), decimals: 2, empty: 'Sem dados: o erro de orientação só existe para waypoints com orientação (shift+clique ou rota com ângulos).' },
    { id: 'v', title: 'Velocidade linear v: real e comando', unit: 'm/s', series: withCmd('v', 'v_cmd') },
    { id: 'w', title: 'Velocidade angular ω: real e comando', unit: 'rad/s', series: withCmd('omega', 'omega_cmd') },
    { id: 'th', title: 'Orientação θ', unit: '°', series: v.map((r) => mk(r, 'theta', 'theta', 'real', (z) => z * R2D)), decimals: 1 },
  ].map((c) => ({ ...c, end }))
})
const hasCmd = computed(() => visible.value.some((r) => r.data.v_cmd?.length || r.data.omega_cmd?.length))
const hasData = computed(() => robots.value.some((r) => (r.data.t?.length || 0) > 0))

// tabela (≤200 linhas)
const COLS = [['t', 't (s)'], ['x', 'x'], ['y', 'y'], ['theta', 'θ (°)'], ['v', 'v'], ['omega', 'ω'], ['v_cmd', 'v cmd'], ['omega_cmd', 'ω cmd'], ['err_pos', 'e pos'], ['err_theta', 'e θ (°)']]
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
        return (f === 'theta' || f === 'err_theta' ? val * R2D : val).toFixed(f === 't' ? 2 : 3)
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

function dlFig(f, i) { download(`${(f.title || 'figura' + i).replace(/[^\w-]+/g, '_')}.png`, b64ToBlob(f.png_b64, 'image/png')) }
</script>

<template>
  <FloatingWindow id="plots" :min-w="360" :min-h="260">
    <template #actions>
      <button v-if="tab === 'signals'" class="btn ghost icon sm" :disabled="!live" aria-label="Atualizar" data-tip="Atualizar dados" @click="refresh"><Icon name="refresh" /></button>
      <button v-if="tab === 'signals'" class="btn ghost icon sm" :class="{ active: table }" aria-label="Alternar tabela" :aria-pressed="table" data-tip="Tabela" @click="table = !table"><Icon name="table" /></button>
    </template>
    <div class="tabs" role="tablist">
      <button class="tab" role="tab" :aria-selected="tab === 'signals'" @click="tab = 'signals'">Sinais</button>
      <button class="tab" role="tab" :aria-selected="tab === 'figs'" @click="tab = 'figs'">Figuras<span v-if="store.figures.length" class="chip n">{{ store.figures.length }}</span></button>
    </div>

    <template v-if="tab === 'signals'">
      <div class="bar">
        <div v-if="robots.length" class="filters" role="group" aria-label="Filtrar robôs">
          <label v-for="r in robots" :key="r.id" class="flt" :class="{ off: hidden.has(r.id) }">
            <input type="checkbox" :checked="!hidden.has(r.id)" @change="toggle(r.id)" />
            <svg width="26" height="8" aria-hidden="true"><line x1="1" x2="25" y1="4" y2="4" :stroke="r.color" stroke-width="2" stroke-linecap="round" :stroke-dasharray="r.dash || null" /></svg>
            <span class="mono">{{ r.id }}</span>
          </label>
        </div>
        <div v-if="hasCmd" class="styles faint">
          <svg width="26" height="8" aria-hidden="true"><line x1="1" x2="25" y1="4" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>real
          <svg width="26" height="8" aria-hidden="true"><line x1="1" x2="25" y1="4" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="0.1 5" /></svg>comando
        </div>
        <div class="exp">
          <button class="btn sm" :disabled="!live" @click="exportLog('csv')"><Icon name="download" :size="12" />CSV</button>
          <button class="btn sm" :disabled="!live" @click="exportLog('pkl')"><Icon name="download" :size="12" />PKL</button>
          <button class="btn sm danger" :disabled="!live" @click="resetLog"><Icon name="trash" :size="12" />Reiniciar log</button>
        </div>
      </div>
      <div class="scroll">
        <div v-if="!hasData" class="empty">
          <Icon name="chart" :size="28" />
          <h3>Sem dados de log</h3>
          <p>Execute uma simulação com ao menos um robô. Os sinais (trajetória, erros, velocidades e orientação) são registrados durante a execução e atualizados a cada 2 s. Você também pode chamar <code class="mono">logger.plot()</code> no seu código.</p>
        </div>
        <template v-else-if="!visible.length"><p class="faint pad">Todos os robôs estão ocultos. Marque ao menos um acima.</p></template>
        <div v-else-if="!table" class="charts">
          <PlotChart v-for="c in charts" :key="c.id" :title="c.title" :unit="c.unit" :series="c.series" :xy="c.xy" :end-labels="c.end" :decimals="c.decimals ?? 3" :empty-text="c.empty" />
        </div>
        <div v-else class="tbl-wrap">
          <table class="tbl mono">
            <thead><tr><th>robô</th><th v-for="c in COLS" :key="c[0]">{{ c[1] }}</th></tr></thead>
            <tbody><tr v-for="(row, k) in rows" :key="k">
              <td><svg width="18" height="8" aria-hidden="true"><line x1="1" x2="17" y1="4" y2="4" :stroke="row.r.color" stroke-width="2" stroke-linecap="round" :stroke-dasharray="row.r.dash || null" /></svg> {{ row.r.id }}</td>
              <td v-for="(cell, j) in row.cells" :key="j">{{ cell }}</td></tr></tbody>
          </table>
          <p class="faint pad">Mostrando até 200 linhas amostradas uniformemente.</p>
        </div>
        <section v-if="logData?.collisions?.length" class="coll">
          <h3>Colisões ({{ logData.collisions.length }})</h3>
          <ul class="mono"><li v-for="(c, i) in logData.collisions" :key="i">{{ c }}</li></ul>
        </section>
      </div>
    </template>

    <div v-else class="scroll">
      <div v-if="!store.figures.length" class="empty">
        <Icon name="image" :size="28" />
        <h3>Nenhuma figura</h3>
        <p>Figuras do matplotlib exibidas com <code class="mono">plt.show()</code> aparecem aqui.</p>
      </div>
      <div class="figs">
        <figure v-for="(f, i) in store.figures" :key="i" class="fig">
          <img :src="'data:image/png;base64,' + f.png_b64" :alt="f.title || 'Figura ' + (i + 1)" />
          <figcaption><span>{{ f.title || 'Figura ' + (i + 1) }}</span>
            <button class="btn sm" @click="dlFig(f, i)"><Icon name="download" :size="12" />Baixar PNG</button></figcaption>
        </figure>
      </div>
    </div>
  </FloatingWindow>
</template>

<style scoped>
.n { margin-left: 6px; padding: 0 6px; }
.bar { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border); flex: none; }
.filters { display: flex; flex-wrap: wrap; gap: 4px 12px; }
.flt { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
.flt.off svg { opacity: .3; }
.styles { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; }
.exp { display: flex; gap: 6px; margin-left: auto; }
.scroll { flex: 1; min-height: 0; overflow: auto; padding: 10px 12px 14px; }
.charts { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; }
.empty { text-align: center; color: var(--text-muted); padding: 28px 16px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.empty svg { color: var(--accent); }
.empty p { max-width: 420px; margin: 0; line-height: 1.5; }
.pad { padding: 8px 2px; }
.tbl-wrap { overflow: auto; }
.tbl { border-collapse: collapse; width: 100%; font-size: 11.5px; }
.tbl th, .tbl td { padding: 3px 8px; text-align: right; white-space: nowrap; border-bottom: 1px solid var(--border); }
.tbl th { position: sticky; top: 0; background: var(--surface-solid); color: var(--text-muted); font-weight: 500; }
.tbl td:first-child, .tbl th:first-child { text-align: left; }
.coll { margin-top: 14px; }
.coll h3 { font-size: 12px; margin-bottom: 4px; }
.coll ul { margin: 0; padding-left: 16px; max-height: 120px; overflow: auto; font-size: 11.5px; color: var(--text-muted); }
.figs { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.fig { margin: 0; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff; }
.fig img { width: 100%; display: block; }
.fig figcaption { display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--surface-2); color: var(--text); }
</style>
