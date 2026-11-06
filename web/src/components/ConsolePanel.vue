<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import { consoleBus, files, readClientFile, download, toast, store } from '../state/store.js'

const box = ref(null)
const stick = ref(true)
const count = ref(consoleBus.lines.length)
let pending = []
let raf = 0
const MAX = 5000

function make(l) {
  const d = document.createElement('div')
  d.className = 'ln ' + l.kind
  d.textContent = l.text === '' ? ' ' : l.text
  return d
}
function flush() {
  raf = 0
  const el = box.value
  if (!el) return
  const frag = document.createDocumentFragment()
  for (const l of pending) frag.appendChild(make(l))
  pending = []
  el.appendChild(frag)
  while (el.childElementCount > MAX) el.removeChild(el.firstElementChild)
  count.value = el.childElementCount
  if (stick.value) el.scrollTop = el.scrollHeight
}
function onLine(l) {
  if (l === null) { pending = []; if (box.value) box.value.textContent = ''; count.value = 0; return }
  pending.push(l)
  if (!raf) raf = requestAnimationFrame(flush)
}
function onScroll() {
  const el = box.value
  stick.value = el.scrollHeight - el.scrollTop - el.clientHeight < 24
}
onMounted(() => {
  const frag = document.createDocumentFragment()
  for (const l of consoleBus.lines) frag.appendChild(make(l))
  box.value.appendChild(frag)
  box.value.scrollTop = box.value.scrollHeight
  consoleBus.subs.add(onLine)
})
onBeforeUnmount(() => { consoleBus.subs.delete(onLine); cancelAnimationFrame(raf) })

function toBottom() { stick.value = true; box.value.scrollTop = box.value.scrollHeight }
async function copy() {
  const text = consoleBus.lines.map((l) => l.text).join('\n')
  try { await navigator.clipboard.writeText(text); toast('Console copiado.') } catch { toast('Não foi possível copiar.', 'warn') }
}
async function getFile(f) {
  try {
    const data = await readClientFile(f.path)
    download(f.path.split('/').pop(), new Blob([data]))
  } catch (e) { toast(`Falha ao ler ${f.path}: ${e.message}`, 'error') }
}
const size = (n) => (n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n > 1024 ? (n / 1024).toFixed(1) + ' kB' : n + ' B')
</script>

<template>
  <div class="pane">
    <div class="acts">
      <span class="faint mono cnt">{{ count }} linhas</span>
      <button class="btn ghost icon sm" aria-label="Copiar saída" data-tip="Copiar" data-tip-pos="end" @click="copy"><Icon name="copy" /></button>
      <button class="btn ghost icon sm" aria-label="Limpar console" data-tip="Limpar" data-tip-pos="end" @click="consoleBus.clear()"><Icon name="trash" /></button>
    </div>
    <div ref="box" class="log mono" role="log" aria-live="off" tabindex="0" aria-label="Saída do console" @scroll.passive="onScroll" />
    <button v-if="!stick" class="btn sm jump" @click="toBottom"><Icon name="chevronDown" :size="13" />Ir para o fim</button>
    <div v-if="files.length" class="files">
      <div class="label">Arquivos gerados</div>
      <button v-for="f in files" :key="f.path" class="btn sm file" @click="getFile(f)" :data-tip="'Baixar ' + f.path" data-tip-pos="up">
        <Icon name="download" :size="12" /><span class="mono">{{ f.path.split('/').pop() }}</span><span class="faint">{{ size(f.size) }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.pane { flex: 1; min-height: 0; display: flex; flex-direction: column; position: relative; }
.acts { position: absolute; right: 10px; top: 4px; z-index: 2; display: flex; align-items: center; gap: 2px; background: var(--surface); }
.log { flex: 1; min-height: 0; overflow: auto; padding: 8px 10px; font-size: 12px; line-height: 1.5; user-select: text; }
.log :deep(.ln) { white-space: pre-wrap; overflow-wrap: anywhere; padding-left: 8px; border-left: 2px solid transparent; }
.log :deep(.ln.err) { color: var(--danger); border-left-color: var(--danger); background: var(--danger-soft); }
.log :deep(.ln.notice) { color: var(--accent); font-style: italic; border-left-color: var(--accent); font-family: var(--font-ui); }
.cnt { font-size: 11px; margin-right: 4px; }
.jump { position: absolute; right: 12px; bottom: 12px; box-shadow: var(--shadow); }
.files { flex: none; border-top: 1px solid var(--border); padding: 6px 10px 8px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.files .label { width: 100%; }
.file span { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
</style>
