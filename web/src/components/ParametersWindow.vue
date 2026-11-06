<script setup>
import { computed, reactive, watch } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import { store, scene, send, ask } from '../state/store.js'

const DEFS = [
  { key: 'max_speed', label: 'Velocidade máx. (m/s)', min: 0.2, max: 8, step: 0.05 },
  { key: 'max_omega', label: 'Vel. angular máx. (rad/s)', min: 0.1, max: 6, step: 0.05 },
  { key: 'max_steer', label: 'Esterçamento máx. (rad)', min: 0.1, max: 1.2, step: 0.01 },
  { key: 'grid_size', label: 'Tamanho da grade (m)', min: 0.1, max: 5, step: 0.1 },
  { key: 'noise_sigma', label: 'Ruído σ', min: 0, max: 1, step: 0.01 },
  { key: 'servo_max_speed', label: 'Vel. máx. do servo (rad/s)', min: 0.5, max: 30, step: 0.1 },
  { key: 'goal_tolerance', label: 'Tolerância da meta (m)', min: 0.02, max: 2, step: 0.01 },
]
const vals = reactive({})
watch(scene, (s) => {
  if (!s) return
  const p = { ...(s.params || {}), goal_tolerance: s.waypoints_cfg?.goal_tolerance }
  for (const d of DEFS) vals[d.key] = p[d.key] ?? null
}, { immediate: true })

const shown = computed(() => DEFS.filter((d) => vals[d.key] != null))
function set(d, raw) {
  let v = Number(raw)
  if (!Number.isFinite(v)) return
  v = Math.min(d.max, Math.max(d.min, v))
  vals[d.key] = v
  send({ cmd: 'set_param', name: d.key, value: v })
}
const lidarOn = computed(() => !!scene.value?.lidar?.enabled)
const noiseOn = computed(() => !!scene.value?.noise?.enabled)
const live = computed(() => store.run.state === 'running')
function toggleLidar() { send({ cmd: 'toggle_lidar' }); setTimeout(() => send({ cmd: 'refresh' }), 50) }
function toggleNoise() { send({ cmd: 'toggle_noise' }); setTimeout(() => send({ cmd: 'refresh' }), 50) }
async function clearObs() {
  if (await ask({ title: 'Limpar obstáculos', message: 'Remover todos os obstáculos da cena?', confirmText: 'Remover', danger: true })) send({ cmd: 'clear_obstacles' })
}
</script>

<template>
  <FloatingWindow id="params" :min-w="280" :min-h="200">
    <div v-if="!live" class="note"><Icon name="info" :size="14" />Os comandos agem apenas enquanto um código está em execução.</div>
    <div class="scroll">
      <div v-for="d in shown" :key="d.key" class="prm">
        <label :for="'p-' + d.key">{{ d.label }}</label>
        <div class="ctl">
          <input type="range" :min="d.min" :max="d.max" :step="d.step" :value="vals[d.key]" :disabled="!live" :aria-label="d.label" @input="set(d, $event.target.value)" />
          <input :id="'p-' + d.key" class="input mono num" type="number" :min="d.min" :max="d.max" :step="d.step" :value="Number(vals[d.key]).toFixed(2)"
            :disabled="!live" @change="set(d, $event.target.value)" />
        </div>
      </div>
      <p v-if="!shown.length" class="faint">Os parâmetros aparecem quando a cena é criada.</p>
      <div class="sw">
        <label class="switch"><input type="checkbox" :checked="lidarOn" :disabled="!live" @change="toggleLidar" /> LiDAR</label>
        <label class="switch"><input type="checkbox" :checked="noiseOn" :disabled="!live" @change="toggleNoise" /> Ruído</label>
      </div>
      <div class="acts">
        <button class="btn sm" :disabled="!live" @click="send({ cmd: 'clear_waypoints' })"><Icon name="flag" :size="13" />Limpar waypoints</button>
        <button class="btn sm" :disabled="!live" @click="clearObs"><Icon name="obstacle" :size="13" />Limpar obstáculos</button>
        <button class="btn sm" :disabled="!live" @click="send({ cmd: 'clear_path' })"><Icon name="eraser" :size="13" />Limpar rastros</button>
        <button class="btn sm primary" :disabled="!live" @click="send({ cmd: 'save_config' })"><Icon name="download" :size="13" />Salvar config (YAML)</button>
      </div>
    </div>
  </FloatingWindow>
</template>

<style scoped>
.scroll { padding: 10px 14px 14px; overflow: auto; display: flex; flex-direction: column; gap: 10px; }
.note { display: flex; gap: 6px; align-items: center; padding: 6px 12px; font-size: 11.5px; color: var(--text-muted); background: var(--accent-soft); flex: none; }
.prm label { font-size: 12px; color: var(--text-muted); }
.ctl { display: flex; align-items: center; gap: 10px; }
.num { width: 76px; flex: none; text-align: right; }
.sw { display: flex; gap: 18px; padding: 4px 0; }
.acts { display: flex; flex-wrap: wrap; gap: 6px; }
</style>
