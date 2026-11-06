<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import FloatingWindow from './FloatingWindow.vue'
import Icon from './Icon.vue'
import { store, send, canvasRef, bytesToB64, toast, scene } from '../state/store.js'
import mapa1 from '../../../src/hivebr/engine/assets/mapa_1.png?url'
import mapaL from '../../../src/hivebr/engine/assets/mapa_l.png?url'
import mapaU from '../../../src/hivebr/engine/assets/mapa_u.png?url'
import maze2 from '../../../src/hivebr/engine/assets/maze2.png?url'

const bundled = [
  { name: 'mapa_1.png', label: 'Mapa 1', url: mapa1 },
  { name: 'mapa_l.png', label: 'Mapa L', url: mapaL },
  { name: 'mapa_u.png', label: 'Mapa U', url: mapaU },
  { name: 'maze2.png', label: 'Labirinto', url: maze2 },
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
  } catch (err) { toast(`Falha ao carregar ${b.name}.`, 'error') }
}
function apply() {
  const p = picked.value
  if (!p) return
  const r = Number(res.value)
  if (!(r > 0)) { toast('Informe uma resolução maior que zero.', 'warn'); return }
  send({ cmd: 'load_map', name: p.name, b64: bytesToB64(p.bytes), resolution: r, kind: asLine.value ? 'line' : 'occupancy' })
  toast(`Mapa “${p.name}” enviado.`)
}
function clearMap() { send({ cmd: 'clear_map' }) }

function trackApply() {
  const strokes = canvasRef.value?.getStrokes?.() || []
  if (!strokes.length) { toast('Desenhe ao menos um traço na tela.', 'warn'); return }
  send({ cmd: 'track_apply', strokes })
}
function trackClear() { canvasRef.value?.clearStrokes?.(); send({ cmd: 'track_clear' }) }
</script>

<template>
  <FloatingWindow id="map" :min-w="300" :min-h="240">
    <div v-if="!live" class="note"><Icon name="info" :size="14" />Execute um código para aplicar mapas e pistas à simulação.</div>
    <div class="scroll">
      <section>
        <h3>Imagem de mapa</h3>
        <div class="row">
          <button class="btn sm" @click="fileInput.click()"><Icon name="upload" :size="13" />Escolher imagem…</button>
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
        </div>
        <div class="short">
          <span class="label">Mapas incluídos</span>
          <button v-for="b in bundled" :key="b.name" class="btn sm" @click="useBundled(b)">{{ b.label }}</button>
        </div>
        <div v-if="picked" class="prev">
          <img :src="picked.url" :alt="`Pré-visualização de ${picked.name}`" />
          <span class="mono faint">{{ picked.name }}</span>
        </div>
        <div class="field">
          <label for="mres">Resolução (m/px)</label>
          <input id="mres" class="input mono" type="number" min="0.001" step="0.01" v-model.number="res" />
        </div>
        <div class="field">
          <label class="switch"><input type="radio" :value="false" v-model="asLine" /> Mapa de ocupação (obstáculos)</label>
          <label class="switch"><input type="radio" :value="true" v-model="asLine" /> Pista de linha (seguidor de linha)</label>
        </div>
        <div class="row">
          <button class="btn primary sm" :disabled="!live || !picked" @click="apply">Aplicar</button>
          <button class="btn sm" :disabled="!live || !hasMap" @click="clearMap"><Icon name="trash" :size="13" />Remover mapa</button>
        </div>
      </section>
      <section>
        <h3>Desenhar pista</h3>
        <ol class="guide">
          <li>Escolha a ferramenta <b>Desenhar pista</b> (<kbd>D</kbd>).</li>
          <li>Arraste sobre a tela para traçar a linha; cada traço é independente.</li>
          <li>Clique em <b>Aplicar</b> para transformar os traços em uma pista.</li>
        </ol>
        <div class="row">
          <button class="btn sm" :class="{ active: store.tool === 'draw' }" @click="store.tool = 'draw'"><Icon name="pen" :size="13" />Desenhar</button>
          <button class="btn primary sm" :disabled="!live" @click="trackApply">Aplicar</button>
          <button class="btn sm" :disabled="!live" @click="trackClear"><Icon name="eraser" :size="13" />Limpar</button>
          <button class="btn sm" :disabled="!live" @click="send({ cmd: 'track_export' })"><Icon name="download" :size="13" />Exportar PNG</button>
        </div>
      </section>
    </div>
  </FloatingWindow>
</template>

<style scoped>
.note { display: flex; gap: 6px; align-items: center; padding: 6px 12px; font-size: 11.5px; color: var(--text-muted); background: var(--accent-soft); flex: none; }
.scroll { padding: 10px 14px 14px; overflow: auto; display: flex; flex-direction: column; gap: 18px; }
section { display: flex; flex-direction: column; gap: 10px; }
h3 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--text-muted); }
.row, .short { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.prev { display: flex; align-items: center; gap: 10px; }
.prev img { max-width: 120px; max-height: 90px; image-rendering: pixelated; border: 1px solid var(--border-strong); border-radius: 4px; background: #fff; }
.guide { margin: 0; padding-left: 18px; color: var(--text-muted); line-height: 1.6; }
.field .switch { padding: 2px 0; }
</style>
