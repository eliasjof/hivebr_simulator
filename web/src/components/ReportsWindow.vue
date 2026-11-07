<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import Icon from './Icon.vue'
import { store, focusWindow, closeWindow } from '../state/store.js'

const props = defineProps(['id'])
const reportId = props.id
const localContent = ref('')
const isEditing = ref(true)
const splitRatio = ref(50)
const dragging = ref(false)

const report = computed(() => store.reports.find(r => r.id === reportId))
const title = computed(() => report.value?.name || 'New Report')

// Initialize marked with highlight.js
try {
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: (code, lang) => {
      if (lang && hljs.getLanguage(lang)) {
        try { return hljs.highlight(code, { language: lang }).value } catch { return code }
      }
      return code
    }
  })
} catch (e) {
  console.warn('marked/hljs init failed:', e)
}

function updateContent(val) {
  if (report.value) {
    report.value.content = val
    report.value.modified = Date.now()
  }
}

function exportPDF() {
  if (!report.value) return
  const html = marked.parse(report.value.content)
  const printWindow = window.open('', '_blank')
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${report.value.name}</title>
      <meta charset="utf-8">
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 40px 20px; color: #333; }
        h1, h2, h3 { color: #1a1a2e; margin-top: 1.5em; }
        h1 { border-bottom: 2px solid #3b82f6; padding-bottom: 0.3em; }
        h2 { border-bottom: 1px solid #e5e7eb; padding-bottom: 0.2em; }
        code { background: #f3f4f6; padding: 0.2em 0.4em; border-radius: 4px; font-family: 'Monaco', 'Menlo', monospace; }
        pre { background: #1e1e1e; color: #d4d4d4; padding: 1em; border-radius: 8px; overflow-x: auto; }
        pre code { background: none; padding: 0; color: inherit; }
        blockquote { border-left: 4px solid #3b82f6; margin: 1em 0; padding-left: 1em; color: #6b7280; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #e5e7eb; padding: 0.5em 1em; text-align: left; }
        th { background: #f9fafb; }
        img { max-width: 100%; height: auto; }
        hr { border: none; border-top: 1px solid #e5e7eb; margin: 2em 0; }
        @media print { body { padding: 0; } }
      </style>
    </head>
    <body>${html}</body>
    </html>
  `)
  printWindow.document.close()
  printWindow.onload = () => {
    printWindow.focus()
    printWindow.print()
    setTimeout(() => printWindow.close(), 1000)
  }
}

function exportMD() {
  if (!report.value) return
  const blob = new Blob([report.value.content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = report.value.name.endsWith('.md') ? report.value.name : `${report.value.name}.md`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function deleteReport() {
  if (!report.value || store.reports.length <= 1) return
  if (!confirm(`Delete "${report.value.name}"?`)) return
  const idx = store.reports.findIndex(r => r.id === reportId)
  if (idx >= 0) store.reports.splice(idx, 1)
  closeWindow(reportId)
}

function toggleEdit() {
  isEditing.value = !isEditing.value
}

function onSplitDrag(e) {
  if (!dragging.value) return
  const rect = document.querySelector('.reports-split').getBoundingClientRect()
  const pct = ((e.clientX - rect.left) / rect.width) * 100
  splitRatio.value = Math.max(20, Math.min(80, pct))
}

function startDrag() { dragging.value = true }
function stopDrag() { dragging.value = false }

onMounted(() => {
  if (report.value) localContent.value = report.value.content
  window.addEventListener('mousemove', onSplitDrag)
  window.addEventListener('mouseup', stopDrag)
})
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onSplitDrag)
  window.removeEventListener('mouseup', stopDrag)
})

watch(() => report.value?.content, (v) => { if (v !== undefined) localContent.value = v }, { immediate: true })
watch(localContent, (v) => { if (report.value) updateContent(v) })

const previewHTML = computed(() => marked.parse(localContent.value || ''))

// Window drag
const winStyle = computed(() => {
  const w = store.windows[reportId]
  if (!w) return {}
  return { left: w.x + 'px', top: w.y + 'px', width: w.w + 'px', height: w.h + 'px' }
})
let dragOffset = { x: 0, y: 0 }
function dragStart(e) {
  const w = store.windows[reportId]
  if (!w) return
  dragOffset.x = e.clientX - w.x
  dragOffset.y = e.clientY - w.y
  function onMove(ev) {
    w.x = ev.clientX - dragOffset.x
    w.y = ev.clientY - dragOffset.y
  }
  function onUp() {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}
</script>

<template>
  <div class="reports-window" ref="el" :style="winStyle" @mousedown="focusWindow(reportId)">
    <header class="rpt-hdr" @mousedown.stop="dragStart($event)">
      <span class="title">{{ title }}</span>
      <div class="actions">
        <button class="btn ghost icon sm" @click="toggleEdit" :data-tip="isEditing ? 'Preview' : 'Edit'" :aria-label="isEditing ? 'Switch to preview' : 'Switch to edit'">
          <Icon :name="isEditing ? 'eye' : 'edit'" :size="14" />
        </button>
        <button class="btn ghost icon sm" @click="exportMD" data-tip="Export .md" aria-label="Export as Markdown">
          <Icon name="download" :size="14" />
        </button>
        <button class="btn ghost icon sm" @click="exportPDF" data-tip="Export PDF" aria-label="Export as PDF">
          <Icon name="file" :size="14" />
        </button>
        <button class="btn ghost icon sm" @click="deleteReport" data-tip="Delete" aria-label="Delete Report">
          <Icon name="trash" :size="14" />
        </button>
        <button class="btn ghost icon sm" @click="closeWindow(reportId)" data-tip="Close" aria-label="Close">
          <Icon name="close" :size="14" />
        </button>
      </div>
    </header>
    <div class="reports-split" ref="splitEl">
      <div class="pane editor-pane" :style="{ width: splitRatio + '%' }">
        <textarea
          v-model="localContent"
          class="md-editor"
          :placeholder="isEditing ? 'Write Markdown...' : ''"
          @input="$emit('input', $event.target.value)"
          spellcheck="false"
          aria-label="Markdown editor"
        />
      </div>
      <div class="split-handle" @mousedown="startDrag" :style="{ left: splitRatio + '%' }" aria-label="Resize panes" role="slider" aria-valuemin="20" aria-valuemax="80" :aria-valuenow="Math.round(splitRatio)" tabindex="0">
        <Icon name="dots" :size="16" />
      </div>
      <div class="pane preview-pane" :style="{ width: (100 - splitRatio) + '%' }">
        <div class="md-preview" v-html="previewHTML" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-window {
  position: absolute;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  min-width: 600px;
  min-height: 400px;
  z-index: var(--z-window);
  overflow: hidden;
}
.rpt-hdr {
  display: flex; align-items: center; justify-content: space-between;
  height: 32px; padding: 0 10px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  user-select: none;
  cursor: move;
}
.title { font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }
.actions { display: flex; gap: 2px; }
.reports-split { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.pane { flex: none; display: flex; flex-direction: column; min-width: 120px; overflow: hidden; }
.editor-pane { border-right: 1px solid var(--border); }
.md-editor {
  flex: 1; min-height: 0;
  border: none; outline: none; resize: none;
  background: var(--surface);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 13px; line-height: 1.55;
  padding: 12px;
}
.md-editor::placeholder { color: var(--text-faint); }
.preview-pane { overflow: auto; }
.md-preview { padding: 16px; flex: 1; min-height: 0; overflow: auto; }
.md-preview :deep(h1) { font-size: 1.75em; margin: 0.67em 0; }
.md-preview :deep(h2) { font-size: 1.5em; margin: 0.83em 0; }
.md-preview :deep(h3) { font-size: 1.25em; margin: 1em 0; }
.md-preview :deep(p) { margin: 0.5em 0; }
.md-preview :deep(code) { font-family: var(--font-mono); }
.md-preview :deep(pre) { margin: 1em 0; }
.md-preview :deep(blockquote) { margin: 1em 0; }
.md-preview :deep(table) { font-size: 13px; }
.md-preview :deep(th), .md-preview :deep(td) { font-size: 13px; }
.split-handle {
  width: 8px; background: var(--border);
  display: flex; align-items: center; justify-content: center;
  cursor: col-resize; flex: none; z-index: 1;
  color: var(--text-muted);
}
.split-handle:hover { background: var(--accent); color: var(--accent); }
.split-handle:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
</style>