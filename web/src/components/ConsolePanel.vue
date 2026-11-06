<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import { consoleBus, files, readClientFile, download, toast } from '../state/store.js'
import { t, fmtNum, fmtInt, tn } from '../i18n/index.js'

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
  try { await navigator.clipboard.writeText(text); toast(t('console.copied')) } catch { toast(t('console.copy_failed'), 'warn') }
}
async function getFile(f) {
  try {
    const data = await readClientFile(f.path)
    download(f.path.split('/').pop(), new Blob([data]))
  } catch (e) { toast(t('console.read_failed', { path: f.path, error: e.message }), 'error') }
}
const size = (n) => (n > 1048576 ? fmtNum(n / 1048576, 1) + ' MB' : n > 1024 ? fmtNum(n / 1024, 1) + ' kB' : fmtInt(n) + ' B')
</script>

<template>
  <div class="pane">
    <div class="acts">
      <span class="faint mono cnt">{{ tn('console.lines', count) }}</span>
      <button class="btn ghost icon sm" :aria-label="t('console.copy_aria')" :data-tip="t('console.copy')" data-tip-pos="end" @click="copy"><Icon name="copy" /></button>
      <button class="btn ghost icon sm" :aria-label="t('console.clear_aria')" :data-tip="t('console.clear')" data-tip-pos="end" @click="consoleBus.clear()"><Icon name="trash" /></button>
    </div>
    <div ref="box" class="log mono" role="log" aria-live="off" tabindex="0" :aria-label="t('console.aria')" @scroll.passive="onScroll" />
    <button v-if="!stick" class="btn sm jump" @click="toBottom"><Icon name="chevronDown" :size="13" />{{ t('console.jump') }}</button>
    <div v-if="files.length" class="files">
      <div class="label">{{ t('console.files') }}</div>
      <button v-for="f in files" :key="f.path" class="btn sm file" @click="getFile(f)" :data-tip="t('console.download', { path: f.path })" data-tip-pos="up">
        <Icon name="download" :size="12" /><span class="mono">{{ f.path.split('/').pop() }}</span><span class="faint">{{ size(f.size) }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.pane { flex: 1; min-height: 0; display: flex; flex-direction: column; position: relative; }
.acts { position: absolute; right: 10px; top: var(--sp-2); z-index: var(--z-raised); display: flex; align-items: center; gap: var(--sp-1); background: var(--surface); }
.log { flex: 1; min-height: 0; overflow: auto; padding: var(--sp-4) 10px; font-size: var(--fs-sm); line-height: 1.5; user-select: text; }
.log :deep(.ln) { white-space: pre-wrap; overflow-wrap: anywhere; padding-left: var(--sp-4); border-left: 2px solid transparent; }
.log :deep(.ln.err) { color: var(--danger); border-left-color: var(--danger); background: var(--danger-soft); }
.log :deep(.ln.notice) { color: var(--accent); font-style: italic; border-left-color: var(--accent); font-family: var(--font-ui); }
.cnt { font-size: var(--fs-xs); margin-right: var(--sp-2); }
.jump { position: absolute; right: var(--sp-5); bottom: var(--sp-5); box-shadow: var(--shadow); }
.files { flex: none; border-top: 1px solid var(--border); padding: var(--sp-3) 10px var(--sp-4); display: flex; flex-wrap: wrap; gap: var(--sp-3); align-items: center; }
.files .label { width: 100%; }
.file span { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
</style>
