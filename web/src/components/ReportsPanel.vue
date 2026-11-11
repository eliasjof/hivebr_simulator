<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import Icon from './Icon.vue'
import ReportActionsModal from './ReportActionsModal.vue'
// Inlined at build time so the logo also shows in exported HTML/PDF files,
// which are opened outside the app and cannot resolve app asset paths.
import ifmgLogo from '../assets/ifmg-simples.png?inline'
import { store, toggleReportsPanel, toggleReportsMaximized, toggleReportTemplateModal, addCapture, captures, getCapture, openReport, deleteReport as deleteReportStore, download, toast } from '../state/store.js'
import { t } from '../i18n/index.js'

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
const showReportList = ref(false)
const showReportActions = ref(false)
const actionReport = ref(null)

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

// Abas abertas (fechar só esconde; o relatório continua salvo em store.reports).
const openReports = computed(() => store.reports.filter(r => store.openReportIds.includes(r.id)))

const activeReport = computed(() => {
  if (!store.activeReportId) return null
  return openReports.value.find(r => r.id === store.activeReportId) || null
})

// Initialize marked with highlight.js and custom image renderer for capture:{id} URIs
try {
  const renderer = new marked.Renderer()
  const originalImage = renderer.image.bind(renderer)
  // marked 18.x calls renderer.image(token) with the image token
  // ({ href, title, text, tokens }), not positional (href, title, text).
  // Accept both shapes so capture: URLs are always resolved.
  renderer.image = (tokenOrHref, title, text) => {
    const token = tokenOrHref && typeof tokenOrHref === 'object'
      ? { ...tokenOrHref }
      : { href: tokenOrHref, title, text }
    const href = typeof token.href === 'string' ? token.href : ''
    if (href.startsWith('capture:')) {
      const capture = getCapture(href.slice('capture:'.length))
      if (capture?.dataUrl) token.href = capture.dataUrl
    }
    return originalImage(token)
  }
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: (code, lang) => {
      const safeCode = typeof code === 'string' ? code : ''
      const safeLang = typeof lang === 'string' ? lang : ''
      if (safeLang && hljs.getLanguage(safeLang)) {
        try { return hljs.highlight(safeCode, { language: safeLang }).value } catch { return safeCode }
      }
      return safeCode
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
  },
  ifmg: {
    label: 'Relatório IFMG',
    icon: 'book',
    description: 'Cabeçalho institucional com logo, dados da disciplina e estrutura acadêmica',
    content: (meta) => `${IFMG_HEADER}

<table>
  <tr><td style="width:26%;color:#1e4d2e;font-weight:600;">Data</td><td>${meta.date}</td></tr>
  <tr><td style="color:#1e4d2e;font-weight:600;">Professor(a)</td><td>Escreva aqui o nome do professor</td></tr>
  <tr><td style="color:#1e4d2e;font-weight:600;">Matéria</td><td>Escreva aqui o nome da matéria</td></tr>
  <tr><td style="color:#1e4d2e;font-weight:600;">Turma</td><td>Escreva aqui o nome da turma</td></tr>
  <tr><td style="color:#1e4d2e;font-weight:600;">Estudante(s)</td><td>Escreva aqui o nome do estudante</td></tr>
</table>

# Título principal do relatório

## 1) Introdução

*Descreva o contexto, os objetivos e a motivação do trabalho.*

## 2) Desenvolvimento

*Apresente o referencial teórico, os materiais e métodos, relate a configuração do experimento, ou seja, o que foi feito na atividade.*

## 3) Resultados e Discussão

*Insira as capturas de tela, tabelas e gráficos da simulação e discuta os resultados obtidos ou responda às perguntas solicitadas.*

## 4) Conclusão

*Resuma as principais conclusões e proponha trabalhos futuros ou melhorias.*

## 5) Referências

1. SOBRENOME, Nome. **Título da obra**. Cidade: Editora, ano.
2. SOBRENOME, Nome. *Título do artigo*. Revista, v. 1, n. 1, p. 1-10, ano.
`
  }
}

// IFMG template: the decorative banner lives behind this marker, so the
// Markdown source stays readable and does not store the logo data URI.
// It is expanded only for the preview and for HTML/PDF exports.
const IFMG_HEADER = '<!-- ifmg-header -->'

function ifmgHeaderHtml() {
  return `<div style="display:flex;align-items:center;gap:20px;padding:18px 22px;border-radius:10px;background:linear-gradient(135deg,#14351f,#1f4d2e 60%,#3f6b3a);border-bottom:6px solid #7d9b3a;color:#fff;">
  <div style="flex:none;background:#fff;border-radius:8px;padding:8px 12px;line-height:0;">
    <img src="${ifmgLogo}" alt="Logo do IFMG" style="display:block;margin:0;height:54px;width:auto;" />
  </div>
  <div style="min-width:0;line-height:1.35;">
    <div style="font-size:11px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:#cfe0c3;">INSTITUTO FEDERAL DE MINAS GERAIS</div>
    <div style="font-size:19px;font-weight:700;margin-top:3px;">Relatório de Atividade Acadêmica</div>
  </div>
</div>`
}

/** Replaces short template markers by their rendered HTML before Markdown parsing. */
function expandTemplateMarkers(md) {
  if (typeof md !== 'string' || !md.includes(IFMG_HEADER)) return md
  return md.split(IFMG_HEADER).join(ifmgHeaderHtml())
}

function renderMarkdown(md) {
  return marked.parse(expandTemplateMarkers(md))
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

// IFMG template: moss-green institutional accents while the body stays black.
// Appended after the default CSS so it wins without !important.
const IFMG_DOC_CSS = `
  body { color: #111; }
  h1, h2, h3, h4 { color: #111; }
  h1 { border-bottom-color: #2f6b3f; }
  h2 { border-bottom-color: #b9cfae; }
  h4 { color: #1e4d2e; }
  code { background: #eef4ea; }
  blockquote { border-left-color: #2f6b3f; color: #333; }
  th, td { border-color: #cfdcc6; }
  th { background: #eef4ea; color: #1e4d2e; }
  a { color: #2f6b3f; }
  hr { border-top-color: #cfdcc6; }
  h1:first-of-type { border-top: none; padding-top: 0; margin-top: 1.2em; }
  h1:first-of-type::before { content: none; }
`

function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

/** Prints `html` from an off-screen iframe (no popup blocker, no onload race). */
function printHtml(html, onError) {
  // Remove leftovers from a previous print that never fired `afterprint`.
  document.querySelectorAll('iframe[data-hivebr-print]').forEach((el) => el.remove())
  const frame = document.createElement('iframe')
  frame.setAttribute('aria-hidden', 'true')
  frame.setAttribute('data-hivebr-print', '')
  // Off-screen but with a real viewport: a 1px iframe can produce a blank or
  // clipped print layout in some browsers.
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:1024px;height:768px;border:0;pointer-events:none;'
  document.body.appendChild(frame)

  const win = frame.contentWindow
  if (!win) {
    frame.remove()
    if (onError) onError(new Error('iframe contentWindow unavailable'))
    return
  }
  const doc = win.document
  let removed = false
  const cleanup = () => {
    if (removed) return
    removed = true
    if (frame.parentNode) frame.remove()
  }
  const fail = (err) => {
    cleanup()
    if (onError) onError(err)
  }

  doc.open()
  doc.write(html)
  doc.close()
  win.addEventListener('afterprint', cleanup, { once: true })

  // Two animation frames + a short delay guarantee the document is laid out
  // before the print dialog snapshots it.
  const nextFrame = () => new Promise((resolve) => {
    let done = false
    const finish = () => { if (!done) { done = true; setTimeout(resolve, 80) } }
    const raf = win.requestAnimationFrame ? win.requestAnimationFrame.bind(win) : (cb) => setTimeout(cb, 16)
    raf(() => raf(finish))
    // rAF can be throttled; never block the print on it.
    setTimeout(finish, 250)
  })
  const fontsReady = () => {
    try { return doc.fonts?.ready ? doc.fonts.ready.catch(() => {}) : Promise.resolve() } catch { return Promise.resolve() }
  }
  const imagesReady = () => new Promise((resolve) => {
    let pending
    try { pending = [...doc.images].filter((img) => !img.complete) } catch { resolve(); return }
    if (!pending.length) { resolve(); return }
    let left = pending.length
    const done = () => { if (--left <= 0) resolve() }
    pending.forEach((img) => {
      img.addEventListener('load', done, { once: true })
      img.addEventListener('error', done, { once: true })
    })
    // Never block the print dialog on a broken image.
    setTimeout(resolve, 3000)
  })

  fontsReady()
    .then(nextFrame)
    .then(imagesReady)
    .then(() => new Promise((resolve) => setTimeout(resolve, 60)))
    .then(() => {
      try {
        win.focus()
        win.print()
      } catch (err) {
        fail(err)
        return
      }
      // Some browsers return from print() before the dialog closes.
      setTimeout(cleanup, 60000)
    })
    .catch(fail)
}

function buildPrintDocument(report, bodyHtml) {
  const baseName = typeof report?.name === 'string' && report.name.length > 0 ? report.name : 'relatorio'
  const ifmg = report?.template === 'ifmg'
  return `<!DOCTYPE html>
    <html>
    <head>
      <title>${escapeHtml(baseName)}</title>
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
        ${ifmg ? IFMG_DOC_CSS : ''}
      </style>
    </head>
    <body>${bodyHtml}</body>
    </html>`
}

function exportPDF(report = activeReport.value) {
  if (report instanceof Event) report = activeReport.value
  if (!report) return
  const fail = (err) => toast(t('report.export_failed', { error: String(err?.message || err) }), 'error')
  try {
    const content = typeof report.content === 'string' ? report.content : ''
    const html = renderMarkdown(content)
    printHtml(buildPrintDocument(report, resolveCaptureUrls(html)), fail)
  } catch (err) {
    fail(err)
  }
}

function exportHTML(report = activeReport.value) {
  if (report instanceof Event) report = activeReport.value
  if (!report) return
  const content = typeof report.content === 'string' ? report.content : ''
  const baseName = typeof report.name === 'string' && report.name.length > 0 ? report.name : 'relatorio'
  const html = renderMarkdown(content)
  const resolvedHtml = resolveCaptureUrls(html)
  const ifmg = report?.template === 'ifmg'
  const fullHTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>${baseName}</title>
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
    ${ifmg ? IFMG_DOC_CSS : ''}
  </style>
</head>
<body>
  <div class="container">
    ${resolvedHtml}
    <div class="footer">
      Gerado no hiveBr Web · ${new Date().toLocaleDateString('pt-BR')}
    </div>
  </div>
</body>
</html>`
  const blob = new Blob([fullHTML], { type: 'text/html' })
  const fileName = /\.html?$/i.test(baseName) ? baseName : `${baseName.replace(/\.md$/i, '')}.html`
  download(fileName, blob)
}

function exportMD(report = activeReport.value) {
  if (report instanceof Event) report = activeReport.value
  if (!report) return
  const content = typeof report.content === 'string' ? report.content : ''
  const baseName = typeof report.name === 'string' && report.name.length > 0 ? report.name : 'relatorio'
  const blob = new Blob([content], { type: 'text/markdown' })
  download(baseName.endsWith('.md') ? baseName : `${baseName}.md`, blob)
}

function neighbourOf(id, ids) {
  const idx = ids.indexOf(id)
  const remaining = ids.filter(x => x !== id)
  // Prefer the tab on the left, then the same position (shifted), then the first.
  return remaining[idx - 1] ?? remaining[idx] ?? remaining[0] ?? null
}

// Fechar uma aba apenas a esconde: o relatório continua em store.reports e pode
// ser reaberto pelo menu "Relatórios" (ícone de lista) ou pelo navegador.
function closeReportTab(id) {
  const ids = openReports.value.map(r => r.id)
  if (!ids.includes(id)) return
  const wasActive = store.activeReportId === id
  const next = wasActive ? neighbourOf(id, ids) : null
  const oi = store.openReportIds.indexOf(id)
  if (oi >= 0) store.openReportIds.splice(oi, 1)
  if (wasActive) store.activeReportId = next
}

function deleteReport(id) {
  const r = store.reports.find(x => x.id === id)
  if (!r) return
  if (!confirm(t('report.confirm_delete'))) return
  deleteReportStore(id)
  toast(t('report.deleted', { name: r.name }))
}

// ---- ações do relatório (renomear / salvar arquivo / excluir) ----
function openReportActions(r) {
  actionReport.value = r
  showReportActions.value = true
  showReportList.value = false
}

function closeReportActions() {
  showReportActions.value = false
  actionReport.value = null
}

function openReportTab(r) {
  openReport(r.id)
  showReportList.value = false
  closeReportActions()
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
  const r = { id, name, content, template: selectedTemplate.value, created: Date.now(), modified: Date.now() }
  store.reports.push(r)
  openReport(id)
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

function onDocClick() { showReportList.value = false }

// One-time cleanup for IFMG reports created by the first version, which kept
// the whole banner (and the logo data URI) inside the Markdown source.
function normalizeIfmgReports() {
  for (const r of store.reports) {
    if (r.template !== 'ifmg' || typeof r.content !== 'string') continue
    if (r.content.includes(IFMG_HEADER)) continue
    if (!r.content.startsWith('<div style="display:flex;align-items:center;gap:20px;')) continue
    const tableAt = r.content.indexOf('<table>')
    if (tableAt < 0) continue
    r.content = IFMG_HEADER + '\n\n' + r.content.slice(tableAt)
    r.modified = Date.now()
  }
}

onMounted(() => {
  normalizeIfmgReports()
  if (activeReport.value) localContent.value = activeReport.value.content
  window.addEventListener('mousemove', onSplitDrag)
  window.addEventListener('mouseup', stopDrag)
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onSplitDrag)
  window.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('click', onDocClick)
})

watch(() => activeReport.value?.content, (v) => { if (v !== undefined) localContent.value = v }, { immediate: true })
watch(() => store.activeReportId, () => { if (activeReport.value) localContent.value = activeReport.value.content })
watch(localContent, (v) => { if (activeReport.value) updateContent(v) })

const previewHTML = computed(() => renderMarkdown(localContent.value || ''))
</script>

<template>
  <section class="reports-panel" aria-label="Relatórios">
    <header class="ph">
      <span class="sec-h">Relatórios</span>
      <span class="sp" />
      <div class="report-list-wrap">
        <button class="btn ghost icon sm" @click.stop="showReportList = !showReportList" data-tip="Abrir relatório" aria-label="Abrir relatório" :aria-expanded="showReportList"><Icon name="list" :size="14" /></button>
        <div v-if="showReportList" class="report-menu" role="menu" @click.stop>
          <p v-if="!store.reports.length" class="report-menu-empty">Nenhum relatório salvo</p>
          <div v-for="r in store.reports" :key="r.id" class="report-menu-row">
            <button class="report-menu-item" :class="{ active: r.id === store.activeReportId }" role="menuitem" :title="r.name" @click="openReportTab(r)">
              <Icon name="file" :size="13" />
              <span class="report-menu-name">{{ r.name }}</span>
              <span v-if="store.openReportIds.includes(r.id)" class="report-menu-tag">aberta</span>
            </button>
            <button class="btn ghost icon sm report-menu-action" :aria-label="t('report.actions')" :data-tip="t('report.actions')" @click.stop="openReportActions(r)"><Icon name="dots" :size="13" /></button>
          </div>
        </div>
      </div>
      <button class="btn ghost icon sm" @click="newReport" data-tip="Novo relatório" aria-label="Novo relatório"><Icon name="plus" :size="14" /></button>
      <button class="btn ghost icon sm" :aria-label="store.layout.reportsMaximized ? 'Restaurar painel' : 'Maximizar painel'" :data-tip="store.layout.reportsMaximized ? 'Restaurar' : 'Maximizar'" @click="toggleReportsMaximized"><Icon :name="store.layout.reportsMaximized ? 'restore' : 'max'" :size="14" /></button>
      <button class="btn ghost icon sm" @click="toggleReportsPanel" data-tip="Fechar painel" aria-label="Fechar painel"><Icon name="panelR" :size="14" /></button>
    </header>

    <div v-if="!activeReport" class="empty-state">
      <div class="empty-content">
        <img src="/hivebr-logo.png" alt="hiveBr" class="empty-logo" />
        <p>Nenhum relatório aberto</p>
        <div v-if="store.reports.length" class="saved-reports">
          <p class="saved-title">Relatórios salvos</p>
          <div v-for="r in store.reports" :key="r.id" class="saved-row">
            <button class="btn sm" :title="r.name" @click="openReportTab(r)">
              <Icon name="file" :size="12" /><span class="saved-name">{{ r.name }}</span>
            </button>
            <button class="btn ghost icon sm" :aria-label="t('report.actions')" :data-tip="t('report.actions')" @click.stop="openReportActions(r)"><Icon name="dots" :size="13" /></button>
          </div>
        </div>
        <button class="btn" @click="newReport"><Icon name="plus" :size="12" />Criar relatório</button>
      </div>
    </div>

    <div v-if="activeReport" class="reports-content">
      <div class="report-tabs" role="tablist">
        <div v-for="r in openReports" :key="r.id" class="tab" :class="{ active: r.id === store.activeReportId }" @click="store.activeReportId = r.id" role="tab" :aria-selected="r.id === store.activeReportId" tabindex="0" @keydown.enter="store.activeReportId = r.id">
          <Icon name="file" :size="13" /><span class="tab-name">{{ r.name }}</span>
          <button class="tab-actions" :aria-label="t('report.actions')" :data-tip="t('report.actions')" @click.stop="openReportActions(r)"><Icon name="dots" :size="10" /></button>
          <span class="close-tab" @click.stop="closeReportTab(r.id)" aria-label="Fechar aba" title="Fechar aba" tabindex="0" @keydown.enter.stop="closeReportTab(r.id)"><Icon name="close" :size="10" /></span>
        </div>
      </div>

      <div v-if="activeReport" class="reports-split">
        <div class="pane editor-pane" :style="{ width: splitRatio + '%' }">
          <div class="toolbar">
            <button class="btn ghost icon sm" @click="toggleEdit" :data-tip="isEditing ? 'Preview' : 'Edit'" :aria-label="isEditing ? 'Switch to preview' : 'Switch to edit'">
              <Icon :name="isEditing ? 'eye' : 'edit'" :size="14" />
            </button>
            <button class="btn ghost icon sm" @click="exportMD()" data-tip="Export .md"><Icon name="download" :size="14" /></button>
            <button class="btn ghost icon sm" @click="exportHTML()" data-tip="Export HTML"><Icon name="code" :size="14" /></button>
            <button class="btn ghost icon sm" @click="exportPDF()" data-tip="Export PDF"><Icon name="file" :size="14" /></button>
            <button class="btn ghost icon sm" @click="openReportActions(activeReport)" :data-tip="t('report.actions')" :aria-label="t('report.actions')"><Icon name="dots" :size="14" /></button>
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
          <div class="md-preview" :class="activeReport?.template ? `tpl-${activeReport.template}` : null" v-html="previewHTML" />
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

    <!-- Report Actions Modal -->
    <Teleport to="body">
      <ReportActionsModal v-if="showReportActions && actionReport" :report="actionReport" @close="closeReportActions" />
    </Teleport>

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
.report-list-wrap { position: relative; display: flex; }
.report-menu {
  position: absolute; top: calc(100% + 4px); right: 0; z-index: 20;
  min-width: 200px; max-width: 320px; max-height: 320px; overflow: auto;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); box-shadow: var(--shadow); padding: 4px;
}
.report-menu-item {
  display: flex; align-items: center; gap: 6px; width: 100%; padding: 5px 8px;
  border: none; background: none; color: var(--text); font-size: 12px;
  cursor: pointer; border-radius: 3px; text-align: left;
}
.report-menu-row { display: flex; align-items: center; gap: 2px; }
.report-menu-row .report-menu-item { flex: 1; min-width: 0; }
.report-menu-action { flex: none; opacity: .5; }
.report-menu-row:hover .report-menu-action, .report-menu-action:focus-visible { opacity: 1; }
.report-menu-item:hover { background: var(--surface-3); }
.report-menu-item.active { color: var(--accent); }
.report-menu-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.report-menu-tag { margin-left: auto; font-size: 10px; color: var(--text-faint); }
.report-menu-empty { margin: 0; padding: 8px; color: var(--text-muted); font-size: 12px; }
.saved-reports { display: flex; flex-direction: column; gap: 4px; max-width: 100%; }
.saved-title { margin: 0; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--text-faint); }
.saved-row { display: flex; align-items: center; gap: 2px; }
.saved-row .btn.sm { flex: 1; min-width: 0; justify-content: flex-start; max-width: 100%; }
.saved-row .btn.ghost { flex: none; opacity: .5; }
.saved-row:hover .btn.ghost, .saved-row .btn.ghost:focus-visible { opacity: 1; }
.saved-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.report-tabs {
  display: flex; flex-wrap: wrap; gap: 2px; padding: 4px 6px;
  background: var(--surface-2); border-bottom: 1px solid var(--border);
}
.tab {
  display: flex; align-items: center; gap: 6px; padding: 4px 8px 4px 10px;
  background: var(--surface-3); border: none; border-radius: 4px 4px 0 0;
  font-size: 12px; color: var(--text-muted); cursor: pointer;
  max-width: 180px; min-width: 80px; overflow: hidden;
}
.tab:hover { background: var(--surface); color: var(--text); }
.tab.active { background: var(--surface); color: var(--text); border-bottom: 2px solid var(--accent); }
.tab-name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.close-tab {
  background: none; border: none; padding: 0; margin-left: 4px; flex: none;
  color: var(--text-faint); cursor: pointer; border-radius: 2px;
  display: flex; align-items: center; justify-content: center; width: 16px; height: 16px;
}
.tab-actions {
  background: none; border: none; padding: 0; margin-left: 4px; flex: none;
  color: var(--text-faint); cursor: pointer; border-radius: 2px;
  display: flex; align-items: center; justify-content: center; width: 16px; height: 16px;
  opacity: 0;
}
.tab:hover .tab-actions, .tab.active .tab-actions, .tab-actions:focus-visible { opacity: 1; }
.tab-actions:hover { background: var(--surface-3); color: var(--text); }
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

/* IFMG template: the green header is inline; the body uses black headings and
   moss-green rules instead of the hiveBr accent. */
.md-preview.tpl-ifmg :deep(h1:first-of-type) {
  border-top: none;
  padding-top: 0;
  margin-top: 1.2em;
}
.md-preview.tpl-ifmg :deep(h1:first-of-type)::before { content: none; }
.md-preview.tpl-ifmg :deep(h1) { border-bottom: 2px solid #2f6b3f; padding-bottom: 0.2em; }
.md-preview.tpl-ifmg :deep(h2) { border-bottom: 1px solid #b9cfae; padding-bottom: 0.15em; }
.md-preview.tpl-ifmg :deep(table) { border-collapse: collapse; width: 100%; }
.md-preview.tpl-ifmg :deep(th), .md-preview.tpl-ifmg :deep(td) { border: 1px solid #cfdcc6; padding: 6px 10px; }
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