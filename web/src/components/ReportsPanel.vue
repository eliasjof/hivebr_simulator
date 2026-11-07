<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import Icon from './Icon.vue'
import { store, toggleReportsPanel, toggleReportsMaximized, toggleReportTemplateModal, addCapture, captures, getCapture } from '../state/store.js'

const localContent = ref('')
const isEditing = ref(true)
const splitRatio = ref(50)
const dragging = ref(false)
const selectedTemplate = ref('experiment')

const showTemplateModal = computed({
  get: () => store.layout.showReportTemplateModal,
  set: (val) => { store.layout.showReportTemplateModal = val }
})

const showCapturesModal = ref(false)

function openCapturesModal() {
  showCapturesModal.value = true
}

function insertCapture(capture) {
  // Use custom URI scheme for short markdown URLs
  const markdown = `![${capture.name}](capture:${capture.id})`
  const cursorPos = localContent.value.length
  localContent.value = localContent.value.slice(0, cursorPos) + markdown + localContent.value.slice(cursorPos)
  showCapturesModal.value = false
}

const activeReport = computed(() => {
  if (!store.activeReportId) return null
  return store.reports.find(r => r.id === store.activeReportId) || null
})

// Initialize marked with highlight.js and custom image renderer for capture:{id} URIs
try {
  const renderer = new marked.Renderer()
  const originalImage = renderer.image.bind(renderer)
  renderer.image = (token) => {
    // marked 18.x passes an object with { href, title, text } properties
    const href = token?.href
    if (typeof href === 'string' && href.startsWith('capture:')) {
      const id = href.slice('capture:'.length)
      const capture = getCapture(id)
      if (capture) {
        return originalImage({ ...token, href: capture.dataUrl })
      }
    }
    return originalImage(token)
  }
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: (code, lang) => {
      if (lang && hljs.getLanguage(lang)) {
        try { return hljs.highlight(code, { language: lang }).value } catch { return code }
      }
      return code
    },
    renderer
  })
} catch (e) {
  console.warn('marked/hljs init failed:', e)
}

// --- Report Templates ---
const templates = {
  experiment: {
    label: 'Relatório de Experimento',
    icon: 'flask',
    description: 'Estrutura completa: configuração, robôs, resultados, análise',
    content: (meta) => `# hiveBr Experiment Report

## ${meta.title || 'Experimento sem título'}

**Data:** ${meta.date}  
**Autor:** ${meta.author || '—'}  
**Simulador:** hiveBr ${meta.version || '0.1.0'}

---

## 1. Robôs

| ID | Tipo | Cinemática | Sensores | Posição Inicial |
|----|------|------------|----------|-----------------|
${meta.robotsTable || '| — | — | — | — | — |'}

## 2. Cenário

- **Mapa:** ${meta.mapInfo || 'Nenhum'}
- **Obstáculos:** ${meta.obstacleCount || 0}
- **Waypoints:** ${meta.waypointCount || 0}
- **Pontos de Recarga:** ${meta.rechargeCount || 0}

## 3. Resultados

### Métricas Principais
- **Tempo de simulação:** ${meta.simTime || 'N/A'} s
- **Colisões totais:** ${meta.collisions || 0}
- **Fator tempo real:** ${meta.rtf || 'N/A'}

### Trajetórias
${meta.trajectories || 'Dados de trajetória não disponíveis.'}

## 4. Análise e Discussão

> Escreva sua análise aqui...

## 5. Conclusões

> Conclusões do experimento...

---

*hiveBr*
`
  },
  swarm: {
    label: 'Análise de Enxame',
    icon: 'robot',
    description: 'Foco em multi-robô: formações, comunicação, métricas coletivas',
    content: (meta) => `# hiveBr Swarm Analysis

## ${meta.title || 'Análise de Enxame'}

**Data:** ${meta.date}  
**Robôs no enxame:** ${meta.robotCount || 0}

---

## 1. Composição do Enxame

| ID | Tipo | Papel | Cinemática |
|----|------|-------|------------|
${meta.swarmTable || '| — | — | — | — |'}

## 2. Topologia de Comunicação

${meta.commTopology || 'Não especificada.'}

## 3. Métricas Coletivas

- **Coesão média:** ${meta.cohesion || 'N/A'}
- **Alinhamento médio:** ${meta.alignment || 'N/A'}
- **Separação média:** ${meta.separation || 'N/A'}
- **Throughput de mensagens:** ${meta.msgThroughput || 'N/A'} msg/s

## 4. Formações e Padrões

${meta.formations || 'Descreva formações observadas...'}

## 5. Análise de Desempenho

${meta.performance || 'Métricas de desempenho...'}

---

*hiveBr*
`
  },
  paper: {
    label: 'Rascunho de Artigo',
    icon: 'file',
    description: 'Estrutura acadêmica: resumo, métodos, resultados, discussão',
    content: (meta) => `# ${meta.title || 'Título do Artigo'}

**Autores:** ${meta.authors || 'Autor'}  
**Instituição:** ${meta.institution || 'Instituição'}  
**Data:** ${meta.date}

---

## Resumo

${meta.abstract || 'Resumo do trabalho...'}

**Palavras-chave:** ${meta.keywords || 'hiveBr, robótica, simulação, enxame'}

---

## 1. Introdução

${meta.intro || 'Introdução...'}

## 2. Fundamentação Teórica

${meta.background || 'Fundamentação...'}

## 3. Metodologia

### 3.1 Robôs e Sensores

${meta.robotsDesc || 'Descrição dos robôs...'}

### 3.2 Algoritmos de Controle

${meta.algorithms || 'Algoritmos utilizados...'}

## 4. Resultados

${meta.results || 'Resultados...'}

## 5. Discussão

${meta.discussion || 'Discussão...'}

## 6. Conclusões e Trabalhos Futuros

${meta.conclusions || 'Conclusões...'}

---

## Referências

${meta.references || '[1] Referências...'}

---

*hiveBr*
`
  },
  quick: {
    label: 'Nota Rápida',
    icon: 'file',
    description: 'Simples, apenas cabeçalho',
    content: (meta) => `# ${meta.title || 'Nota Rápida'}

**Data:** ${meta.date}

---

${meta.content || 'Escreva sua nota aqui...'}

---

*hiveBr*
`
  }
}

function getMeta() {
  const now = new Date()
  const dateStr = now.toLocaleDateString('pt-BR') + ' ' + now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  
  // Try to get simulation metadata
  let config = '# Configuração não disponível'
  let robotsTable = '| — | — | — | — | — |'
  let mapInfo = 'Nenhum'
  let obstacleCount = 0
  let waypointCount = 0
  let rechargeCount = 0
  let robotCount = 0
  let simTime = 'N/A'
  let collisions = 0
  let rtf = 'N/A'
  let version = '0.1.0'
  
  if (store.scene && store.boot.ready) {
    const s = store.scene

    if (s.robots) {
      robotCount = s.robots.length
      robotsTable = s.robots.map(r => 
        `| ${r.id} | ${r.type} | ${r.kinematics || '—'} | ${r.num_sensors || 0} sens. | ${r.pose ? `${r.pose.x.toFixed(2)}, ${r.pose.y.toFixed(2)}` : '—'} |`
      ).join('\n')
    }
    
    mapInfo = s.map ? `${s.map.width_m.toFixed(1)}×${s.map.height_m.toFixed(1)} m` : 
              s.lineMap ? `Pista ${s.lineMap.width_m.toFixed(1)}×${s.lineMap.height_m.toFixed(1)} m` : 'Nenhum'
    obstacleCount = s.obstacles?.length || 0
    waypointCount = s.waypoints?.reduce((a, w) => a + w.length, 0) || 0
    rechargeCount = s.recharge?.length || 0
  }
  
  if (store.stats) {
    simTime = store.stats.t?.toFixed(2) || 'N/A'
    collisions = store.stats.collisions || 0
    rtf = store.stats.rtf?.toFixed(2) || 'N/A'
  }
  
  if (store.boot.version) version = store.boot.version
  
  return {
    date: dateStr,
    author: 'Elias J. R. Freitas',
    version,
    title: 'Experimento hiveBr',
    robotsTable,
    mapInfo,
    obstacleCount,
    waypointCount,
    rechargeCount,
    robotCount,
    simTime,
    collisions,
    rtf,
    swarmTable: robotsTable,
    commTopology: 'Não especificada',
    cohesion: 'N/A',
    alignment: 'N/A',
    separation: 'N/A',
    msgThroughput: 'N/A',
    formations: 'A definir...',
    performance: 'A definir...',
    abstract: 'Este trabalho apresenta...',
    keywords: 'hiveBr, robótica, simulação, enxame',
    intro: 'Introdução...',
    background: 'Fundamentação...',
    robotsDesc: 'Descrição dos robôs...',
    algorithms: 'Algoritmos...',
    results: 'Resultados...',
    discussion: 'Discussão...',
    conclusions: 'Conclusões...',
    references: '[1] Referências...',
    trajectories: 'Dados de trajetória...',
    content: 'Conteúdo da nota...'
  }
}

function updateContent(val) {
  if (activeReport.value) {
    activeReport.value.content = val
    activeReport.value.modified = Date.now()
  }
}

function resolveCaptureUrls(html) {
  return html.replace(/src="capture:([^"]+)"/g, (match, id) => {
    const capture = getCapture(id)
    return capture ? `src="${capture.dataUrl}"` : match
  })
}

function exportPDF() {
  if (!activeReport.value) return
  const html = marked.parse(activeReport.value.content)
  const resolvedHtml = resolveCaptureUrls(html)
  const printWindow = window.open('', '_blank')
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${activeReport.value.name}</title>
      <meta charset="utf-8">
      <style>
        @page { margin: 2cm; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.7; max-width: 800px; margin: 0 auto; padding: 40px 20px; color: #1e293b; }
        h1, h2, h3, h4 { color: #312e81; margin-top: 1.8em; page-break-after: avoid; }
        h1 { border-bottom: 3px solid #4f46e5; padding-bottom: 0.4em; font-size: 2.2em; }
        h2 { border-bottom: 1px solid #c7d2fe; padding-bottom: 0.2em; font-size: 1.7em; }
        h3 { font-size: 1.4em; }
        h4 { font-size: 1.2em; color: #4338ca; }
        code { background: #eef2ff; padding: 0.2em 0.5em; border-radius: 4px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; }
        pre { background: #0f172a; color: #e2e8f0; padding: 1.2em; border-radius: 8px; overflow-x: auto; page-break-inside: avoid; }
        pre code { background: none; padding: 0; color: inherit; }
        blockquote { border-left: 4px solid #4f46e5; margin: 1.2em 0; padding-left: 1.2em; color: #64748b; font-style: italic; }
        table { border-collapse: collapse; width: 100%; margin: 1.2em 0; font-size: 0.95em; page-break-inside: avoid; }
        th, td { border: 1px solid #c7d2fe; padding: 0.6em 1em; text-align: left; }
        th { background: #eef2ff; color: #312e81; font-weight: 600; }
        tr:nth-child(even) td { background: #f8fafc; }
        img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
        hr { border: none; border-top: 2px solid #c7d2fe; margin: 2.5em 0; }
        a { color: #4f46e5; text-decoration: none; }
        a:hover { text-decoration: underline; }

        /* hiveBr branding */
        img[src="/hivebr-bar.png"] { display: block; margin: 0 auto 0.5em; opacity: 0.85; max-width: 160px; }
        h1:first-of-type { border-top: 3px solid #4f46e5; padding-top: 0.8em; margin-top: 0.5em; }
        h1:first-of-type::before { content: "hiveBr"; display: block; font-size: 0.55em; font-weight: 700; color: #4f46e5; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.3em; }
        hr:last-of-type { margin-top: 3em; border-top: 2px solid #c7d2fe; }
        hr:last-of-type + p { text-align: center; color: #94a3b8; font-size: 0.85em; font-style: italic; }

        @media print { 
          body { padding: 0; }
          .no-print { display: none; }
        }
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

function exportHTML() {
  if (!activeReport.value) return
  const html = marked.parse(activeReport.value.content)
  const resolvedHtml = resolveCaptureUrls(html)
  const fullHTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>${activeReport.value.name}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.7; max-width: 900px; margin: 0 auto; padding: 40px 20px; color: #1e293b; background: #f8fafc; }
    .container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
    h1, h2, h3, h4 { color: #312e81; margin-top: 1.8em; }
    h1 { border-bottom: 3px solid #4f46e5; padding-bottom: 0.4em; font-size: 2.2em; }
    h2 { border-bottom: 1px solid #c7d2fe; padding-bottom: 0.2em; font-size: 1.7em; }
    h3 { font-size: 1.4em; }
    code { background: #eef2ff; padding: 0.2em 0.5em; border-radius: 4px; font-family: 'Monaco', 'Menlo', monospace; }
    pre { background: #0f172a; color: #e2e8f0; padding: 1.2em; border-radius: 8px; overflow-x: auto; }
    pre code { background: none; padding: 0; color: inherit; }
    blockquote { border-left: 4px solid #4f46e5; margin: 1.2em 0; padding-left: 1.2em; color: #64748b; }
    table { border-collapse: collapse; width: 100%; margin: 1.2em 0; }
    th, td { border: 1px solid #c7d2fe; padding: 0.6em 1em; text-align: left; }
    th { background: #eef2ff; color: #312e81; }
    img { max-width: 100%; height: auto; }
    hr { border: none; border-top: 2px solid #c7d2fe; margin: 2.5em 0; }
    .header-logo { text-align: center; margin-bottom: 1.5em; }
    .header-logo img { max-width: 200px; }
    .meta-bar { display: flex; gap: 24px; margin: 1em 0; padding: 1em; background: #f1f5f9; border-radius: 8px; font-size: 0.9em; color: #475569; }
    .footer { margin-top: 3em; padding-top: 1.5em; border-top: 1px solid #e2e8f0; text-align: center; color: #94a3b8; font-size: 0.85em; }

    /* hiveBr branding */
    img[src="/hivebr-bar.png"] { display: block; margin: 0 auto 0.5em; opacity: 0.85; max-width: 160px; }
    h1:first-of-type { border-top: 3px solid #4f46e5; padding-top: 0.8em; margin-top: 0.5em; }
    h1:first-of-type::before { content: "hiveBr"; display: block; font-size: 0.55em; font-weight: 700; color: #4f46e5; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.3em; }
    hr:last-of-type { margin-top: 3em; border-top: 2px solid #c7d2fe; }
    hr:last-of-type + p { text-align: center; color: #94a3b8; font-size: 0.85em; font-style: italic; }
    .footer { margin-top: 3em; padding-top: 1.5em; border-top: 1px solid #e2e8f0; text-align: center; color: #94a3b8; font-size: 0.85em; }
  </style>
</head>
<body>
  <div class="container">
    ${html}
    <div class="footer">
      Gerado no hiveBr Web · ${new Date().toLocaleDateString('pt-BR')}
    </div>
  </div>
</body>
</html>`
  const blob = new Blob([fullHTML], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = activeReport.value.name.replace('.md', '.html')
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function exportMD() {
  if (!activeReport.value) return
  const blob = new Blob([activeReport.value.content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = activeReport.value.name.endsWith('.md') ? activeReport.value.name : `${activeReport.value.name}.md`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function closeReportTab(id) {
  if (store.activeReportId === id) {
    // Switch to another report or clear selection
    const idx = store.reports.findIndex(r => r.id === id)
    if (idx > 0) {
      store.activeReportId = store.reports[idx - 1].id
    } else if (store.reports.length > 1) {
      store.activeReportId = store.reports[1].id
    } else {
      store.activeReportId = null
    }
  }
}

function deleteReport(id) {
  const idx = store.reports.findIndex(r => r.id === id)
  if (idx < 0) return
  if (!confirm(`Excluir "${store.reports[idx].name}"?`)) return
  store.reports.splice(idx, 1)
  if (store.activeReportId === id) {
    // Select another report
    if (idx > 0) {
      store.activeReportId = store.reports[idx - 1].id
    } else if (store.reports.length > 0) {
      store.activeReportId = store.reports[0].id
    } else {
      store.activeReportId = null
    }
  }
}

function newReport() {
  showTemplateModal.value = true
}

function createReportFromTemplate() {
  const id = 'rpt_' + Date.now()
  const meta = getMeta()
  const template = templates[selectedTemplate.value]
  const content = template.content(meta)
  const name = `${template.label.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}.md`
  const r = { id, name, content, created: Date.now(), modified: Date.now() }
  store.reports.push(r)
  store.activeReportId = id
  store.layout.reportsOpen = true
  store.layout.rightOpen = false
  showTemplateModal.value = false
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
  if (activeReport.value) localContent.value = activeReport.value.content
  window.addEventListener('mousemove', onSplitDrag)
  window.addEventListener('mouseup', stopDrag)
})
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onSplitDrag)
  window.removeEventListener('mouseup', stopDrag)
})

watch(() => activeReport.value?.content, (v) => { if (v !== undefined) localContent.value = v }, { immediate: true })
watch(() => store.activeReportId, () => { if (activeReport.value) localContent.value = activeReport.value.content })
watch(localContent, (v) => { if (activeReport.value) updateContent(v) })

const previewHTML = computed(() => marked.parse(localContent.value || ''))
</script>

<template>
  <section class="reports-panel" aria-label="Relatórios">
    <header class="ph">
      <span class="sec-h">Relatórios</span>
      <span class="sp" />
      <button class="btn ghost icon sm" @click="newReport" data-tip="Novo relatório" aria-label="Novo relatório"><Icon name="plus" :size="14" /></button>
      <button class="btn ghost icon sm" :aria-label="store.layout.reportsMaximized ? 'Restaurar painel' : 'Maximizar painel'" :data-tip="store.layout.reportsMaximized ? 'Restaurar' : 'Maximizar'" @click="toggleReportsMaximized"><Icon :name="store.layout.reportsMaximized ? 'restore' : 'max'" :size="14" /></button>
      <button class="btn ghost icon sm" @click="toggleReportsPanel" data-tip="Fechar painel" aria-label="Fechar painel"><Icon name="panelR" :size="14" /></button>
    </header>

    <div v-if="!activeReport" class="empty-state">
      <div class="empty-content">
        <img src="/hivebr-logo.png" alt="hiveBr" class="empty-logo" />
        <p>Nenhum relatório aberto</p>
        <button class="btn" @click="newReport"><Icon name="plus" :size="12" />Criar relatório</button>
      </div>
    </div>

    <div v-if="activeReport" class="reports-content">
      <div class="report-tabs" role="tablist">
        <div v-for="r in store.reports" :key="r.id" class="tab" :class="{ active: r.id === store.activeReportId }" @click="store.activeReportId = r.id" role="tab" :aria-selected="r.id === store.activeReportId" tabindex="0" @keydown.enter="store.activeReportId = r.id">
          <Icon name="file" :size="13" /><span>{{ r.name }}</span>
          <span class="close-tab" @click.stop="closeReportTab(r.id)" aria-label="Fechar aba" title="Fechar aba" tabindex="0" @keydown.enter.stop="closeReportTab(r.id)"><Icon name="close" :size="10" /></span>
        </div>
      </div>

      <div v-if="activeReport" class="reports-split">
        <div class="pane editor-pane" :style="{ width: splitRatio + '%' }">
          <div class="toolbar">
            <button class="btn ghost icon sm" @click="toggleEdit" :data-tip="isEditing ? 'Preview' : 'Edit'" :aria-label="isEditing ? 'Switch to preview' : 'Switch to edit'">
              <Icon :name="isEditing ? 'eye' : 'edit'" :size="14" />
            </button>
            <button class="btn ghost icon sm" @click="exportMD" data-tip="Export .md"><Icon name="download" :size="14" /></button>
            <button class="btn ghost icon sm" @click="exportHTML" data-tip="Export HTML"><Icon name="code" :size="14" /></button>
            <button class="btn ghost icon sm" @click="exportPDF" data-tip="Export PDF"><Icon name="file" :size="14" /></button>
            <button class="btn ghost icon sm" @click="openCapturesModal" data-tip="Inserir captura" aria-label="Inserir captura de tela"><Icon name="image" :size="14" /></button>
            <button class="btn ghost icon sm danger" @click="deleteReport(activeReport.id)" data-tip="Excluir relatório" aria-label="Excluir relatório"><Icon name="trash" :size="14" /></button>
            <span class="sp" />
            <span class="muted mono">{{ activeReport.name }}</span>
          </div>
          <textarea
            v-model="localContent"
            class="md-editor"
            :placeholder="isEditing ? 'Write Markdown...' : ''"
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

    <!-- Template Selection Modal -->
    <div v-if="showTemplateModal" class="modal-overlay" @click.self="showTemplateModal = false">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="template-title">
        <header class="modal-header">
          <h2 id="template-title">Novo Relatório</h2>
          <button class="btn ghost icon" @click="showTemplateModal = false" aria-label="Fechar"><Icon name="close" :size="16" /></button>
        </header>
        <div class="modal-body">
          <p class="modal-desc">Escolha um modelo para começar:</p>
          <div class="template-grid">
            <div v-for="(t, key) in templates" :key="key" class="template-card" :class="{ selected: selectedTemplate === key }" @click="selectedTemplate = key">
              <div class="template-icon"><Icon :name="t.icon" :size="28" /></div>
              <h3>{{ t.label }}</h3>
              <p>{{ t.description }}</p>
            </div>
          </div>
        </div>
        <footer class="modal-footer">
          <button class="btn ghost" @click="showTemplateModal = false">Cancelar</button>
          <button class="btn" @click="createReportFromTemplate">Criar</button>
        </footer>
      </div>
    </div>

    <!-- Captures Modal -->
    <div v-if="showCapturesModal" class="modal-overlay" @click.self="showCapturesModal = false">
      <div class="modal modal-wide" role="dialog" aria-modal="true" aria-labelledby="captures-title">
        <header class="modal-header">
          <h2 id="captures-title">Inserir Captura de Tela</h2>
          <button class="btn ghost icon" @click="showCapturesModal = false" aria-label="Fechar"><Icon name="close" :size="16" /></button>
        </header>
        <div class="modal-body captures-grid">
          <p v-if="!store.captures.length" class="empty-captures">Nenhuma captura disponível. Use o botão 📷 na simulação (Shift+S) para capturar.</p>
          <div v-else class="captures-list">
            <div v-for="c in store.captures" :key="c.id" class="capture-item" @click="insertCapture(c)">
              <img :src="c.dataUrl" :alt="c.name" class="capture-thumb" />
              <div class="capture-info">
                <span class="capture-name">{{ c.name }}</span>
                <span class="capture-date">{{ new Date(c.created).toLocaleString('pt-BR') }}</span>
              </div>
            </div>
          </div>
        </div>
        <footer class="modal-footer">
          <button class="btn ghost" @click="showCapturesModal = false">Cancelar</button>
        </footer>
      </div>
    </div>
  </section>
</template>

<style scoped>
.reports-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--surface);
  border-left: 1px solid var(--border);
}
.ph {
  display: flex; align-items: center; height: 34px; padding: 0 8px 0 12px;
  flex: none; border-bottom: 1px solid var(--border);
}
.sp { flex: 1; }
.report-tabs {
  display: flex; flex-wrap: wrap; gap: 2px; padding: 4px 6px;
  background: var(--surface-2); border-bottom: 1px solid var(--border);
}
.tab {
  display: flex; align-items: center; gap: 6px; padding: 4px 8px 4px 10px;
  background: var(--surface-3); border: none; border-radius: 4px 4px 0 0;
  font-size: 12px; color: var(--text-muted); cursor: pointer;
  max-width: 180px; min-width: 80px;
}
.tab:hover { background: var(--surface); color: var(--text); }
.tab.active { background: var(--surface); color: var(--text); border-bottom: 2px solid var(--accent); }
.close-tab {
  background: none; border: none; padding: 0; margin-left: 4px;
  color: var(--text-faint); cursor: pointer; border-radius: 2px;
  display: flex; align-items: center; justify-content: center; width: 16px; height: 16px;
}
.close-tab:hover { background: var(--danger-soft); color: var(--danger); }
.empty-state {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 20px; text-align: center;
}
.empty-content {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  color: var(--text-muted);
}
.empty-logo { width: 80px; height: auto; opacity: 0.6; }
.reports-content { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.reports-split { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.pane { flex: none; display: flex; flex-direction: column; min-width: 120px; overflow: hidden; }
.editor-pane { border-right: 1px solid var(--border); }
.toolbar {
  display: flex; align-items: center; gap: 4px; padding: 4px 8px;
  background: var(--surface-2); border-bottom: 1px solid var(--border); flex: none;
}
.btn.danger { color: var(--danger); }
.btn.danger:hover { background: var(--danger-soft); color: var(--danger); }
.btn.ghost.danger:hover { background: var(--danger-soft); color: var(--danger); }
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

/* hiveBr branding in preview */
.md-preview :deep(img[src="/hivebr-bar.png"]) {
  display: block;
  margin: 0 auto 0.5em;
  opacity: 0.85;
}
.md-preview :deep(h1:first-of-type) {
  border-top: 3px solid var(--accent);
  padding-top: 0.8em;
  margin-top: 0.5em;
}
.md-preview :deep(h1:first-of-type)::before {
  content: "hiveBr";
  display: block;
  font-size: 0.55em;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 0.3em;
}
.md-preview :deep(hr:last-of-type) {
  margin-top: 3em;
  border-top: 2px solid var(--border);
}
.md-preview :deep(hr:last-of-type) + p {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85em;
  font-style: italic;
}
.md-preview :deep(p:has(+ hr:last-of-type)) {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85em;
  font-style: italic;
}
.split-handle {
  width: 8px; background: var(--border);
  display: flex; align-items: center; justify-content: center;
  cursor: col-resize; flex: none; z-index: 1;
  color: var(--text-muted);
}
.split-handle:hover { background: var(--accent); color: var(--accent); }
.split-handle:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 20px;
}
.modal {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
  width: 100%; max-width: 640px; max-height: 90vh;
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.modal-header h2 { margin: 0; font-size: 1.1em; }
.modal-body { padding: 20px; overflow-y: auto; }
.modal-desc { margin: 0 0 16px; color: var(--text-muted); font-size: 0.9em; }
.template-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;
}
.template-card {
  padding: 20px; border: 2px solid var(--border); border-radius: 10px;
  cursor: pointer; transition: all 0.2s; text-align: center;
  background: var(--surface);
}
.template-card:hover { border-color: var(--accent); background: var(--accent-soft); }
.template-card.selected { border-color: var(--accent); background: var(--accent-soft); box-shadow: 0 0 0 2px var(--accent); }
.template-icon { color: var(--accent); margin-bottom: 10px; }
.template-card h3 { margin: 0 0 8px; font-size: 1em; color: var(--text); }
.template-card p { margin: 0; font-size: 0.85em; color: var(--text-muted); }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 16px 20px; border-top: 1px solid var(--border);
}
.modal-wide { max-width: 800px; }
.captures-grid { padding: 20px; max-height: 60vh; overflow-y: auto; }
.empty-captures { text-align: center; color: var(--text-muted); padding: 40px 20px; }
.captures-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.capture-item {
  border: 2px solid var(--border); border-radius: 8px; overflow: hidden;
  cursor: pointer; transition: all 0.2s; background: var(--surface);
}
.capture-item:hover { border-color: var(--accent); box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
.capture-thumb { width: 100%; height: 120px; object-fit: cover; display: block; }
.capture-info { padding: 8px; display: flex; flex-direction: column; gap: 2px; }
.capture-name { font-size: 0.85em; font-weight: 500; color: var(--text); }
.capture-date { font-size: 0.75em; color: var(--text-muted); }
</style>