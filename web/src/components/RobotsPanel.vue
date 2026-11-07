<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { store, scene, telemetry, selectRobot, send, canvasRef } from '../state/store.js'
import { t, fmtNum, fmtInt } from '../i18n/index.js'

const robots = computed(() => scene.value?.robots || [])
const frame = computed(() => telemetry.value)
const sel = computed(() => store.selected)
const rt = computed(() => frame.value?.robots?.[sel.value] || null)
const rcfg = computed(() => robots.value[sel.value] || null)
const rgb = (c) => (c ? `rgb(${c[0]},${c[1]},${c[2]})` : 'var(--text-muted)')
const f = (v, d = 2) => fmtNum(v, d)
const deg = (rad) => (rad == null ? '—' : fmtNum((rad * 180) / Math.PI, 1))

const status = computed(() => {
  const r = rt.value
  if (!r) return null
  if (r.collision) return { label: t('tel.collided'), icon: 'alert', cls: 'bad' }
  if (r.charging) return { label: t('tel.charging'), icon: 'bolt', cls: 'warn' }
  if (r.extra?.line_lost) return { label: t('tel.line_lost'), icon: 'search', cls: 'warn' }
  if (r.extra?.finished) return { label: t('tel.finished'), icon: 'flag', cls: 'ok' }
  return Math.abs(r.v || 0) > 0.01 || Math.abs(r.omega || 0) > 0.01
    ? { label: t('tel.moving'), icon: 'play', cls: '' } : { label: t('tel.stopped'), icon: 'pause', cls: '' }
})
const batt = computed(() => (rt.value?.battery_enabled ? Math.max(0, Math.min(1, rt.value.battery > 1 ? rt.value.battery / 100 : rt.value.battery)) : null))
const sensors = computed(() => rt.value?.extra?.sensors || null)
const goal = computed(() => {
  const g = rt.value?.goal
  return g ? `(${f(g[0])}, ${f(g[1])})` : t('tel.none')
})
const bestLap = computed(() => rt.value?.extra?.best_lap)

function clearWp() { send({ cmd: 'clear_waypoints', robot: sel.value }) }
function clearTrail() { send({ cmd: 'clear_path', robot: sel.value }) }
function center() {
  const cv = canvasRef.value
  const r = rt.value
  if (!cv || !r) return
  cv.centerOn(r.x, r.y)
}
</script>

<template>
  <div class="pane">
    <div v-if="!robots.length" class="empty">
      <p>{{ t('tel.empty_title') }}</p>
      <p class="faint">{{ t('tel.empty_hint') }}</p>
    </div>
    <template v-else>
      <ul class="list" role="listbox" :aria-label="t('tel.robots')">
        <li v-for="(r, i) in robots" :key="r.id ?? i">
          <button class="row" :class="{ sel: i === sel }" role="option" :aria-selected="i === sel" @click="selectRobot(i)">
            <span class="swatch" :style="{ background: rgb(r.color) }" />
            <span class="rid mono">{{ r.id }}</span>
            <span class="rtype faint">{{ r.type }}</span>
            <kbd v-if="i < 9">{{ i + 1 }}</kbd>
          </button>
        </li>
      </ul>
      <div v-if="rt" class="detail">
        <div class="status" :class="status.cls"><Icon :name="status.icon" :size="14" />{{ status.label }}
          <span v-if="rt.wp_total" class="chip mono wpc">WP {{ Math.min(rt.wp_index + 1, rt.wp_total) }}/{{ rt.wp_total }}</span></div>
        <dl class="grid mono">
          <dt>x</dt><dd data-testid="tel-x">{{ f(rt.x) }} m</dd>
          <dt>y</dt><dd data-testid="tel-y">{{ f(rt.y) }} m</dd>
          <dt>θ</dt><dd>{{ deg(rt.theta) }}°</dd>
          <dt>v</dt><dd data-testid="tel-v">{{ f(rt.v) }} m/s</dd>
          <dt>ω</dt><dd>{{ f(rt.omega) }} rad/s</dd>
          <dt>{{ t('tel.goal') }}</dt><dd>{{ goal }}</dd>
          <template v-if="rt.extra?.lap_count != null"><dt>{{ t('tel.laps') }}</dt><dd>{{ fmtInt(rt.extra.lap_count) }}<span v-if="bestLap" class="muted"> · {{ t('tel.best', { v: f(bestLap) }) }}</span></dd></template>
          <template v-if="rt.extra?.line_error != null"><dt>{{ t('tel.line_error') }}</dt><dd>{{ f(rt.extra.line_error, 3) }}</dd></template>
        </dl>
        <div v-if="batt != null" class="batt" :aria-label="t('tel.battery', { pct: Math.round(batt * 100) })">
          <Icon name="battery" :size="14" />
          <div class="bar"><i :style="{ width: batt * 100 + '%' }" :class="{ low: batt < 0.2 }" /></div>
          <span class="mono">{{ fmtInt(Math.round(batt * 100)) }}%</span>
        </div>
        <div v-if="sensors" class="sensors" role="img" :aria-label="t('tel.sensors_aria', { on: sensors.filter((q) => q.on).length, n: sensors.length })">
          <div class="label">{{ t('tel.sensors') }}</div>
          <div class="cells"><i v-for="(sn, k) in sensors" :key="k" :class="{ on: sn.on }" :title="t('tel.sensor_value', { v: f(sn.value, 2) })" /></div>
        </div>
        <div class="acts">
          <button class="btn sm" @click="clearWp"><Icon name="flag" :size="13" />{{ t('tel.clear_waypoints') }}</button>
          <button class="btn sm" @click="clearTrail"><Icon name="eraser" :size="13" />{{ t('tel.clear_trail') }}</button>
          <button class="btn sm" @click="center"><Icon name="target" :size="13" />{{ t('tel.center') }}</button>
        </div>
      </div>
      <p v-else class="faint pad">{{ t('tel.waiting') }}</p>
    </template>
  </div>
</template>

<style scoped>
.pane { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: auto; }
@container (min-width: 560px) {
  .pane { flex-direction: row; overflow: hidden; }
  .list { max-height: none; width: 230px; border-bottom: none; border-right: 1px solid var(--border); }
  .detail { flex: 1; overflow: auto; display: grid; grid-template-columns: 1fr 1fr; align-content: start; gap: 10px 24px; }
  .detail .acts, .detail .status { grid-column: 1 / -1; }
}
.empty { padding: var(--sp-6); text-align: center; color: var(--text-muted); }
.list { list-style: none; margin: 0; padding: var(--sp-3); display: flex; flex-direction: column; gap: var(--sp-1); overflow: auto; max-height: 38%; flex: none; border-bottom: 1px solid var(--border); }
.row { width: 100%; display: flex; align-items: center; gap: var(--sp-4); min-height: var(--h-md); padding: 0 var(--sp-4); border-radius: var(--radius-sm); border: 1px solid transparent; background: transparent; text-align: left; }
.row:hover { background: var(--surface-3); }
.row.sel { background: var(--accent-soft); border-color: var(--accent); }
.swatch { width: 12px; height: 12px; flex: none; clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
.rid { flex: 1; }
.rtype { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.detail { padding: 10px var(--sp-5); overflow: auto; display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.status { display: flex; align-items: center; gap: var(--sp-3); font-weight: 600; }
.status.bad { color: var(--danger); } .status.warn { color: var(--warn); } .status.ok { color: var(--ok); }
.wpc { margin-left: auto; font-weight: 400; color: var(--text); }
.grid { display: grid; grid-template-columns: auto 1fr; gap: 3px 14px; margin: 0; font-size: var(--fs-sm); }
dt { color: var(--text-muted); } dd { margin: 0; }
.batt { display: flex; align-items: center; gap: var(--sp-4); }
.bar { flex: 1; height: 8px; border-radius: var(--radius-xs); background: var(--surface-3); overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--ok); transition: width var(--dur); }
.bar i.low { background: var(--danger); }
.cells { display: flex; gap: 3px; margin-top: var(--sp-2); }
.cells i { flex: 1; height: 14px; max-width: 28px; border-radius: var(--radius-xs); background: var(--surface-3); border: 1px solid var(--border-strong); }
.cells i.on { background: var(--accent); border-color: var(--accent); }
.acts { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
.pad { padding: var(--sp-5); }
</style>
