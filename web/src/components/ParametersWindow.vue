<script setup>
import { computed, reactive, ref, watch } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import ConfigEditor from './ConfigEditor.vue'
import { store, scene, send, ask } from '../state/store.js'
import { t } from '../i18n/index.js'

const DEFS = [
  { key: 'max_speed', labelKey: 'params.max_speed', min: 0.2, max: 8, step: 0.05 },
  { key: 'max_omega', labelKey: 'params.max_omega', min: 0.1, max: 6, step: 0.05 },
  { key: 'max_steer', labelKey: 'params.max_steer', min: 0.1, max: 1.2, step: 0.01 },
  { key: 'grid_size', labelKey: 'params.grid_size', min: 0.1, max: 5, step: 0.1 },
  { key: 'noise_sigma', labelKey: 'params.noise_sigma', min: 0, max: 1, step: 0.01 },
  { key: 'servo_max_speed', labelKey: 'params.servo_max_speed', min: 0.5, max: 30, step: 0.1 },
  { key: 'goal_tolerance', labelKey: 'params.goal_tolerance', min: 0.02, max: 2, step: 0.01 },
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
const editorOpen = ref(false)
function toggleLidar() { send({ cmd: 'toggle_lidar' }); setTimeout(() => send({ cmd: 'refresh' }), 50) }
function toggleNoise() { send({ cmd: 'toggle_noise' }); setTimeout(() => send({ cmd: 'refresh' }), 50) }
async function clearObs() {
  if (await ask({ title: t('params.clear_obstacles_title'), message: t('params.clear_obstacles_msg'), confirmText: t('common.remove'), danger: true })) send({ cmd: 'clear_obstacles' })
}
async function resetConfig() {
  if (await ask({ title: t('params.reset_config_title'), message: t('params.reset_config_msg'), confirmText: t('params.reset_config'), danger: true })) send({ cmd: 'reset_config' })
}
</script>

<template>
  <FloatingWindow id="params">
    <div v-if="!live" class="note"><Icon name="info" :size="14" />{{ t('params.note') }}</div>
    <div class="scroll">
      <div v-for="d in shown" :key="d.key" class="prm">
        <label :for="'p-' + d.key">{{ t(d.labelKey) }}</label>
        <div class="ctl">
          <input type="range" :min="d.min" :max="d.max" :step="d.step" :value="vals[d.key]" :disabled="!live" :aria-label="t(d.labelKey)" @input="set(d, $event.target.value)" />
          <input :id="'p-' + d.key" class="input mono num" type="number" :min="d.min" :max="d.max" :step="d.step" :value="Number(vals[d.key]).toFixed(2)"
            :disabled="!live" @change="set(d, $event.target.value)" />
        </div>
      </div>
      <p v-if="!shown.length" class="faint">{{ t('params.empty') }}</p>
      <div class="sw">
        <label class="switch"><input type="checkbox" :checked="lidarOn" :disabled="!live" @change="toggleLidar" /> {{ t('params.lidar') }}</label>
        <label class="switch"><input type="checkbox" :checked="noiseOn" :disabled="!live" @change="toggleNoise" /> {{ t('params.noise') }}</label>
      </div>
      <div class="acts">
        <button class="btn sm" :disabled="!live" @click="send({ cmd: 'clear_waypoints' })"><Icon name="flag" :size="13" />{{ t('params.clear_waypoints') }}</button>
        <button class="btn sm" :disabled="!live" @click="clearObs"><Icon name="obstacle" :size="13" />{{ t('params.clear_obstacles') }}</button>
        <button class="btn sm" :disabled="!live" @click="send({ cmd: 'clear_path' })"><Icon name="eraser" :size="13" />{{ t('params.clear_trails') }}</button>
        <button class="btn sm" :disabled="!store.boot.ready || live" :data-tip="t('params.edit_config_tip')" @click="editorOpen = true"><Icon name="file" :size="13" />{{ t('params.edit_config') }}</button>
        <button class="btn sm" :disabled="!live" :data-tip="t('params.reset_config_tip')" @click="resetConfig"><Icon name="reset" :size="13" />{{ t('params.reset_config') }}</button>
        <button class="btn sm primary" :disabled="!live" :data-tip="t('params.update_config_tip')" @click="send({ cmd: 'update_config' })"><Icon name="check" :size="13" />{{ t('params.update_config') }}</button>
        <button class="btn sm" :disabled="!live" @click="send({ cmd: 'save_config' })"><Icon name="download" :size="13" />{{ t('params.save_config') }}</button>
      </div>
    </div>
    <ConfigEditor v-if="editorOpen" @close="editorOpen = false" />
  </FloatingWindow>
</template>

<style scoped>
.scroll { padding: 10px 14px 14px; overflow: auto; display: flex; flex-direction: column; gap: 10px; }
.note { display: flex; gap: var(--sp-3); align-items: center; padding: var(--sp-3) var(--sp-5); font-size: var(--fs-label); color: var(--text-muted); background: var(--accent-soft); flex: none; }
.prm label { font-size: var(--fs-sm); color: var(--text-muted); }
.ctl { display: flex; align-items: center; gap: 10px; }
.num { width: 76px; flex: none; text-align: right; }
.sw { display: flex; gap: 18px; padding: var(--sp-2) 0; }
.acts { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
</style>
