<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import { store, send, canvasRef, bytesToB64, toast, scene } from '../state/store.js'
import { t } from '../i18n/index.js'
import mapa1 from '../../../src/hivebr/engine/assets/mapa_1.png?url'
import mapaL from '../../../src/hivebr/engine/assets/mapa_l.png?url'
import mapaU from '../../../src/hivebr/engine/assets/mapa_u.png?url'
import maze2 from '../../../src/hivebr/engine/assets/maze2.png?url'

const bundled = [
  { name: 'mapa_1.png', labelKey: 'map.m1', url: mapa1 },
  { name: 'mapa_l.png', labelKey: 'map.ml', url: mapaL },
  { name: 'mapa_u.png', labelKey: 'map.mu', url: mapaU },
  { name: 'maze2.png', labelKey: 'map.maze', url: maze2 },
]
const fileInput = ref(null)
const picked = ref(null) // { name, bytes, url }
const asLine = ref(false)
const live = computed(() => store.run.state === 'running')
const res = computed({ get: () => store.mapResolution, set: (v) => { store.mapResolution = v } })
const hasMap = computed(() => !!(scene.value?.map || scene.value?.lineMap))

function setPicked(name, bytes, mime = 'image/png') {
  if (picked.value) URL.revokeObjectURL(picked.value.url)
  picked.value = { name, bytes, url: URL.createObjectURL(new Blob([bytes], { type: mime })) }
}
onBeforeUnmount(() => picked.value && URL.revokeObjectURL(picked.value.url))
async function onFile(e) {
  const f = e.target.files?.[0]
  if (!f) return
  setPicked(f.name, new Uint8Array(await f.arrayBuffer()), f.type)
}
async function useBundled(b) {
  try {
    const buf = await (await fetch(b.url)).arrayBuffer()
    setPicked(b.name, new Uint8Array(buf))
  } catch (err) { toast(t('map.load_failed', { name: b.name }), 'error') }
}
function apply() {
  const p = picked.value
  if (!p) return
  const r = Number(res.value)
  if (!(r > 0)) { toast(t('map.bad_resolution'), 'warn'); return }
  send({ cmd: 'load_map', name: p.name, b64: bytesToB64(p.bytes), resolution: r, kind: asLine.value ? 'line' : 'occupancy' })
  toast(t('map.sent', { name: p.name }))
}
function clearMap() { send({ cmd: 'clear_map' }) }

function trackApply() {
  const strokes = canvasRef.value?.getStrokes?.() || []
  if (!strokes.length) { toast(t('map.draw_first'), 'warn'); return }
  send({ cmd: 'track_apply', strokes })
}
function trackClear() { canvasRef.value?.clearStrokes?.(); send({ cmd: 'track_clear' }) }
</script>

<template>
  <FloatingWindow id="map">
    <div v-if="!live" class="note"><Icon name="info" :size="14" />{{ t('map.note') }}</div>
    <div class="scroll">
      <section>
        <h3>{{ t('map.image') }}</h3>
        <div class="row">
          <button class="btn sm" @click="fileInput.click()"><Icon name="upload" :size="13" />{{ t('map.choose') }}</button>
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
        </div>
        <div class="short">
          <span class="label">{{ t('map.bundled') }}</span>
          <button v-for="b in bundled" :key="b.name" class="btn sm" @click="useBundled(b)">{{ t(b.labelKey) }}</button>
        </div>
        <div v-if="picked" class="prev">
          <img :src="picked.url" :alt="t('map.preview', { name: picked.name })" />
          <span class="mono faint">{{ picked.name }}</span>
        </div>
        <div class="field">
          <label for="mres">{{ t('map.resolution') }}</label>
          <input id="mres" class="input mono" type="number" min="0.001" step="0.01" v-model.number="res" />
        </div>
        <div class="field">
          <label class="switch"><input type="radio" :value="false" v-model="asLine" /> {{ t('map.kind_occupancy') }}</label>
          <label class="switch"><input type="radio" :value="true" v-model="asLine" /> {{ t('map.kind_line') }}</label>
        </div>
        <div class="row">
          <button class="btn primary sm" :disabled="!live || !picked" @click="apply">{{ t('map.apply') }}</button>
          <button class="btn sm" :disabled="!live || !hasMap" @click="clearMap"><Icon name="trash" :size="13" />{{ t('map.remove') }}</button>
        </div>
      </section>
      <section>
        <h3>{{ t('map.draw_title') }}</h3>
        <ol class="guide">
          <li>{{ t('map.guide1_a') }}<b>{{ t('map.draw_tool') }}</b> (<kbd>D</kbd>){{ t('map.guide1_b') }}</li>
          <li>{{ t('map.guide2') }}</li>
          <li>{{ t('map.guide3_a') }}<b>{{ t('map.apply') }}</b>{{ t('map.guide3_b') }}</li>
        </ol>
        <div class="row">
          <button class="btn sm" :class="{ active: store.tool === 'draw' }" @click="store.tool = 'draw'"><Icon name="pen" :size="13" />{{ t('map.draw') }}</button>
          <button class="btn primary sm" :disabled="!live" @click="trackApply">{{ t('map.apply') }}</button>
          <button class="btn sm" :disabled="!live" @click="trackClear"><Icon name="eraser" :size="13" />{{ t('map.clear') }}</button>
          <button class="btn sm" :disabled="!live" @click="send({ cmd: 'track_export' })"><Icon name="download" :size="13" />{{ t('map.export_png') }}</button>
        </div>
      </section>
    </div>
  </FloatingWindow>
</template>

<style scoped>
.note { display: flex; gap: var(--sp-3); align-items: center; padding: var(--sp-3) var(--sp-5); font-size: var(--fs-label); color: var(--text-muted); background: var(--accent-soft); flex: none; }
.scroll { padding: 10px 14px 14px; overflow: auto; display: flex; flex-direction: column; gap: 18px; }
section { display: flex; flex-direction: column; gap: 10px; }
h3 { font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); }
.row, .short { display: flex; flex-wrap: wrap; gap: var(--sp-3); align-items: center; }
.prev { display: flex; align-items: center; gap: 10px; }
.prev img { max-width: 120px; max-height: 90px; image-rendering: pixelated; border: 1px solid var(--border-strong); border-radius: var(--radius-xs); background: var(--surface); }
.guide { margin: 0; padding-left: 18px; color: var(--text-muted); line-height: 1.6; }
.field .switch { padding: var(--sp-1) 0; }
</style>
