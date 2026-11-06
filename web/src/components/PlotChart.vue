<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

// Gráfico SVG de um único sinal (um eixo y). Séries: { key, robot, color, dash, kind, label, x:[], y:[] }
const props = defineProps({
  title: String,
  unit: { type: String, default: '' },
  series: { type: Array, default: () => [] },
  xy: Boolean,
  endLabels: Boolean,
  height: { type: Number, default: 190 },
  xUnit: { type: String, default: 's' },
  decimals: { type: Number, default: 3 },
  emptyText: { type: String, default: 'Sem dados' },
})

const wrap = ref(null)
const width = ref(320)
let ro = null
onMounted(() => {
  ro = new ResizeObserver((e) => { width.value = Math.max(160, Math.floor(e[0].contentRect.width)) })
  ro.observe(wrap.value)
})
onBeforeUnmount(() => ro?.disconnect())

const M = computed(() => ({ l: 46, r: props.endLabels ? 42 : 10, t: 8, b: 24 }))
const pw = computed(() => Math.max(40, width.value - M.value.l - M.value.r))
const ph = computed(() => props.height - M.value.t - M.value.b)

function niceTicks(lo, hi, n = 4) {
  if (!(hi > lo)) { const c = lo || 0; lo = c - 1; hi = c + 1 }
  const raw = (hi - lo) / n
  const p = Math.pow(10, Math.floor(Math.log10(raw)))
  const f = raw / p
  const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p
  const a = Math.floor(lo / step) * step
  const b = Math.ceil(hi / step) * step
  const out = []
  for (let v = a; v <= b + step * 1e-6; v += step) out.push(+v.toPrecision(12))
  return out
}
const fmt = (v, d = 2) => {
  if (v == null || !Number.isFinite(v)) return '—'
  const a = Math.abs(v)
  return a !== 0 && (a < 0.01 || a >= 10000) ? v.toExponential(1) : (+v.toFixed(d)).toString()
}

const dom = computed(() => {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
  for (const s of props.series) {
    const X = s.x, Y = s.y
    for (let i = 0; i < X.length; i++) {
      const a = X[i], b = Y[i]
      if (!Number.isFinite(a) || !Number.isFinite(b)) continue
      if (a < x0) x0 = a; if (a > x1) x1 = a
      if (b < y0) y0 = b; if (b > y1) y1 = b
    }
  }
  if (!Number.isFinite(x0)) return null
  let xt, yt
  if (props.xy) {
    // proporção igual entre os eixos
    const sx = x1 - x0 || 1, sy = y1 - y0 || 1
    const pad = Math.max(sx, sy) * 0.06
    x0 -= pad; x1 += pad; y0 -= pad; y1 += pad
    const k = Math.max((x1 - x0) / pw.value, (y1 - y0) / ph.value)
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
    x0 = cx - (k * pw.value) / 2; x1 = cx + (k * pw.value) / 2
    y0 = cy - (k * ph.value) / 2; y1 = cy + (k * ph.value) / 2
    xt = niceTicks(x0, x1, Math.max(2, Math.floor(pw.value / 90))).filter((v) => v >= x0 && v <= x1)
    yt = niceTicks(y0, y1, 4).filter((v) => v >= y0 && v <= y1)
  } else {
    if (x1 === x0) x1 = x0 + 1
    const pad = (y1 - y0 || 1) * 0.08
    y0 -= pad; y1 += pad
    xt = niceTicks(x0, x1, Math.max(2, Math.floor(pw.value / 80))).filter((v) => v >= x0 && v <= x1)
    yt = niceTicks(y0, y1, 4).filter((v) => v >= y0 && v <= y1)
  }
  return { x0, x1, y0, y1, xt, yt }
})
const sx = (v) => M.value.l + ((v - dom.value.x0) / (dom.value.x1 - dom.value.x0)) * pw.value
const sy = (v) => M.value.t + (1 - (v - dom.value.y0) / (dom.value.y1 - dom.value.y0)) * ph.value

// Reduz para a largura em pixels: mínimo e máximo por coluna (modo temporal).
function buildPoints(s) {
  const d = dom.value
  const X = s.x, Y = s.y, n = X.length
  const pts = []
  if (props.xy) {
    let lx = NaN, ly = NaN
    for (let i = 0; i < n; i++) {
      if (!Number.isFinite(X[i]) || !Number.isFinite(Y[i])) { pts.push(null); continue }
      const px = Math.round(sx(X[i]) * 2) / 2, py = Math.round(sy(Y[i]) * 2) / 2
      if (px === lx && py === ly) continue
      lx = px; ly = py
      pts.push([px, py, i])
    }
    return pts
  }
  const W = Math.max(1, Math.floor(pw.value))
  const span = d.x1 - d.x0
  const lo = new Int32Array(W + 1).fill(-1), hi = new Int32Array(W + 1).fill(-1)
  const nanAt = []
  for (let i = 0; i < n; i++) {
    const y = Y[i]
    if (!Number.isFinite(y) || !Number.isFinite(X[i])) { nanAt.push(i); continue }
    const b = Math.min(W, Math.max(0, Math.floor(((X[i] - d.x0) / span) * W)))
    if (lo[b] < 0) { lo[b] = i; hi[b] = i } else {
      if (y < Y[lo[b]]) lo[b] = i
      if (y > Y[hi[b]]) hi[b] = i
    }
  }
  for (let b = 0; b <= W; b++) {
    if (lo[b] < 0) continue
    const a = Math.min(lo[b], hi[b]), c = Math.max(lo[b], hi[b])
    pts.push([sx(X[a]), sy(Y[a]), a])
    if (c !== a) pts.push([sx(X[c]), sy(Y[c]), c])
  }
  return pts
}
const paths = computed(() => {
  if (!dom.value) return []
  return props.series.map((s) => {
    const pts = buildPoints(s)
    let dStr = '', pen = false
    for (const p of pts) {
      if (p === null) { pen = false; continue }
      dStr += (pen ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)
      pen = true
    }
    return { s, d: dStr, pts }
  })
})

// rótulos diretos no fim da linha (apenas séries "real")
const labels = computed(() => {
  if (!props.endLabels || !dom.value) return []
  const out = []
  for (const p of paths.value) {
    if (p.s.kind === 'cmd' || !p.pts.length) continue
    let last = null
    for (let i = p.pts.length - 1; i >= 0; i--) if (p.pts[i]) { last = p.pts[i]; break }
    if (last) out.push({ text: p.s.label, y: last[1], x: last[0], color: p.s.color, dash: p.s.dash })
  }
  out.sort((a, b) => a.y - b.y)
  for (let i = 1; i < out.length; i++) if (out[i].y - out[i - 1].y < 12) out[i].y = out[i - 1].y + 12
  return out
})

// hover
const hover = ref(null)
function binary(X, t) {
  let a = 0, b = X.length - 1
  while (b - a > 1) { const m = (a + b) >> 1; if (X[m] <= t) a = m; else b = m }
  return Math.abs(X[a] - t) <= Math.abs(X[b] - t) ? a : b
}
function onMove(e) {
  if (!dom.value) return
  const r = e.currentTarget.getBoundingClientRect()
  const px = e.clientX - r.left + M.value.l
  const py = e.clientY - r.top + M.value.t
  const d = dom.value
  const items = []
  let cx = px
  let header = ''
  if (props.xy) {
    let best = null, bd = Infinity
    for (const p of paths.value) for (const q of p.pts) {
      if (!q) continue
      const dd = (q[0] - px) ** 2 + (q[1] - py) ** 2
      if (dd < bd) { bd = dd; best = { p, q } }
    }
    if (!best) return
    const s = best.s || best.p.s
    const i = best.q[2]
    cx = best.q[0]
    items.push({ s, text: `x ${fmt(s.x[i], 2)} · y ${fmt(s.y[i], 2)}`, py: best.q[1], px: best.q[0] })
    header = s.t ? `t = ${fmt(s.t[i], 2)} s` : ''
  } else {
    const t = d.x0 + ((px - M.value.l) / pw.value) * (d.x1 - d.x0)
    header = `t = ${fmt(t, 2)} ${props.xUnit}`
    for (const s of props.series) {
      if (!s.x.length) continue
      const i = binary(s.x, t)
      const y = s.y[i]
      if (!Number.isFinite(y)) continue
      items.push({ s, text: fmt(y, props.decimals) + (props.unit ? ' ' + props.unit : ''), py: sy(y), px: sx(s.x[i]) })
    }
  }
  hover.value = { cx, items, header, left: px > width.value * 0.6 }
}
function onLeave() { hover.value = null }
</script>

<template>
  <figure class="pc">
    <figcaption><span class="ttl">{{ title }}</span><span class="faint mono u">{{ unit }}{{ xy ? '' : ' · x: ' + xUnit }}</span></figcaption>
    <div ref="wrap" class="wrap" :style="{ height: height + 'px' }">
      <svg v-if="dom" :width="width" :height="height" role="img" :aria-label="`Gráfico: ${title}`" class="svg">
        <g class="grid">
          <line v-for="v in dom.yt" :key="'gy' + v" :x1="M.l" :x2="M.l + pw" :y1="sy(v)" :y2="sy(v)" />
          <template v-if="xy"><line v-for="v in dom.xt" :key="'gx' + v" :y1="M.t" :y2="M.t + ph" :x1="sx(v)" :x2="sx(v)" /></template>
        </g>
        <g class="axis mono">
          <line :x1="M.l" :x2="M.l + pw" :y1="M.t + ph" :y2="M.t + ph" />
          <text v-for="v in dom.yt" :key="'ty' + v" :x="M.l - 6" :y="sy(v) + 3.5" text-anchor="end">{{ fmt(v, 2) }}</text>
          <text v-for="v in dom.xt" :key="'tx' + v" :x="sx(v)" :y="M.t + ph + 15" text-anchor="middle">{{ fmt(v, 2) }}</text>
        </g>
        <g fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">
          <path v-for="p in paths" :key="p.s.key" :d="p.d" :stroke="p.s.color" :stroke-dasharray="p.s.kind === 'cmd' ? '0.1 5' : p.s.dash || null" />
        </g>
        <g v-for="l in labels" :key="l.text" class="endlbl">
          <line :x1="M.l + pw + 3" :x2="M.l + pw + 11" :y1="l.y" :y2="l.y" :stroke="l.color" stroke-width="2" stroke-linecap="round" />
          <text :x="M.l + pw + 14" :y="l.y + 3.5" class="mono">{{ l.text }}</text>
        </g>
        <g v-if="hover" pointer-events="none">
          <line v-if="!xy" :x1="hover.cx" :x2="hover.cx" :y1="M.t" :y2="M.t + ph" class="cross" />
          <circle v-for="it in hover.items" :key="it.s.key" :cx="it.px" :cy="it.py" r="3.5" :fill="it.s.color" class="dot" />
        </g>
        <rect :x="M.l" :y="M.t" :width="pw" :height="ph" fill="transparent" class="hit" @pointermove="onMove" @pointerdown="onMove" @pointerleave="onLeave" />
      </svg>
      <div v-else class="nodata faint">{{ emptyText }}</div>
      <div v-if="hover" class="tip mono" :style="hover.left ? { right: width - hover.cx + 10 + 'px' } : { left: hover.cx + 12 + 'px' }">
        <div class="th">{{ hover.header }}</div>
        <div v-for="it in hover.items" :key="it.s.key" class="tr">
          <svg width="18" height="8" aria-hidden="true"><line x1="1" x2="17" y1="4" y2="4" :stroke="it.s.color" stroke-width="2" stroke-linecap="round"
            :stroke-dasharray="it.s.kind === 'cmd' ? '0.1 5' : it.s.dash || null" /></svg>
          <span>{{ it.s.label }}{{ it.s.kind === 'cmd' ? ' (cmd)' : '' }}</span><b>{{ it.text }}</b>
        </div>
      </div>
    </div>
  </figure>
</template>

<style scoped>
.pc { margin: 0; padding: 8px 10px 4px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-2); min-width: 0; }
figcaption { display: flex; justify-content: space-between; align-items: baseline; font-size: 12px; font-weight: 600; padding: 0 2px 2px; }
.u { font-weight: 400; font-size: 11px; }
.wrap { position: relative; }
.svg { display: block; overflow: visible; }
.grid line { stroke: var(--grid); stroke-width: 1; }
.axis line { stroke: var(--border-strong); stroke-width: 1; }
.axis text { fill: var(--text-faint); font-size: 10px; }
.endlbl text { fill: var(--text-muted); font-size: 10.5px; }
.cross { stroke: var(--text-muted); stroke-width: 1; stroke-dasharray: 3 3; }
.dot { stroke: var(--surface-solid); stroke-width: 1.5; }
.hit { cursor: crosshair; touch-action: pan-y; }
.nodata { display: grid; place-items: center; height: 100%; text-align: center; padding: 0 16px; line-height: 1.4; font-size: 12px; }
.tip { position: absolute; top: 6px; pointer-events: none; padding: 6px 8px; font-size: 11px; background: var(--surface-solid); border: 1px solid var(--border-strong); border-radius: 6px; box-shadow: var(--shadow); z-index: 5; white-space: nowrap; }
.th { color: var(--text-muted); margin-bottom: 3px; }
.tr { display: flex; align-items: center; gap: 6px; }
.tr b { margin-left: auto; padding-left: 10px; font-weight: 600; }
</style>
