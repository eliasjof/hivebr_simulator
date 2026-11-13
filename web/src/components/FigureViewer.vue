<script setup>
// Visualizador/editor de figuras do matplotlib. O PNG original não é editável,
// então o matplotlib também envia o SVG da mesma figura: sobre ele aplicamos
// cores, grade, fundos, espessuras e cores de eixos. Título, legenda e rótulos
// extras continuam compostos em um canvas usado na prévia e nos downloads.
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { addCapture, insertCaptureIntoReport, download, toast } from '../state/store.js'
import { t } from '../i18n/index.js'
import { GRID_DASHES, ensureFigureStyle } from '../utils/figureStyle.js'

const props = defineProps({
  figure: { type: Object, required: true },
  index: { type: Number, default: 0 },
})
const emit = defineEmits(['close'])

const FONTS = ['sans-serif', 'serif', 'monospace', 'Georgia', 'Times New Roman', 'Arial', 'Courier New']
const FONT_MIN = 6
const FONT_MAX = 72
const ZOOM_MIN = 0.05
const ZOOM_MAX = 8
const SVG_NS = 'http://www.w3.org/2000/svg'
const RASTER_SCALE = 2
const IGNORED_COLORS = new Set(['none', 'transparent', '#fff', '#ffffff', '#000', '#000000', '#b0b0b0', '#cccccc'])

const style = ensureFigureStyle(props.figure)
const dashOptions = computed(() => [
  { id: 'solid', label: t('figures.dash_solid') },
  { id: 'dashed', label: t('figures.dash_dashed') },
  { id: 'dotted', label: t('figures.dash_dotted') },
  { id: 'dashdot', label: t('figures.dash_dashdot') },
  { id: 'longdash', label: t('figures.dash_longdash') },
])
const axisOptions = computed(() => [
  { id: 'both', label: t('figures.grid_both') },
  { id: 'x', label: t('figures.grid_x') },
  { id: 'y', label: t('figures.grid_y') },
])

const preview = ref(null)
const scroller = ref(null)
const natural = ref({ w: 0, h: 0 })
const zoom = ref(1)
const pan = ref(null)
const hasSvg = ref(false)
const palette = ref([])
let svgTemplate = null
let pngImg = null
let baseImg = null
let firstFit = false
let renderSeq = 0
let renderTimer = null
let measureCtx = null

const zoomPct = computed(() => Math.round(zoom.value * 100))
const previewStyle = computed(() => ({
  width: Math.max(1, Math.round(natural.value.w * zoom.value)) + 'px',
  height: Math.max(1, Math.round(natural.value.h * zoom.value)) + 'px',
}))

function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)) }
function fontSpec() {
  const family = String(props.figure.font || 'sans-serif')
  return `${clamp(Number(props.figure.fontSize) || 16, FONT_MIN, FONT_MAX)}px ${/\s/.test(family) ? `"${family}"` : family}`
}
function getMeasureCtx() {
  if (!measureCtx) measureCtx = document.createElement('canvas').getContext('2d')
  return measureCtx
}
// Quebra o texto em linhas que cabem na largura da figura (respeita \n).
function wrapLines(ctx, text, maxWidth) {
  const lines = []
  for (const para of String(text).split(/\n/)) {
    const words = para.split(/\s+/).filter(Boolean)
    if (!words.length) { lines.push(''); continue }
    let line = words[0]
    for (let i = 1; i < words.length; i++) {
      const test = `${line} ${words[i]}`
      if (ctx.measureText(test).width <= maxWidth) line = test
      else { lines.push(line); line = words[i] }
    }
    lines.push(line)
  }
  return lines
}

// Desenha a composição final em `target` e devolve false se a imagem ainda não carregou.
function composeTo(target, img = baseImg) {
  if (!img || !target) return false
  const iw = img.naturalWidth || img.width
  const ih = img.naturalHeight || img.height
  if (!iw || !ih) return false

  const f = props.figure
  const title = String(f.title || '').trim()
  const caption = String(f.caption || '').trim()
  const xLabel = String(f.xLabel || '').trim()
  const yLabel = String(f.yLabel || '').trim()

  const spec = fontSpec()
  const fontSize = clamp(Number(f.fontSize) || 16, FONT_MIN, FONT_MAX)
  const lineH = Math.round(fontSize * 1.35)
  const gap = Math.max(6, Math.round(fontSize * 0.5))
  // Sem textos extras a imagem sai exatamente como o matplotlib gerou (sem
  // margens); com textos, abre espaço para desenhá-los fora da área do gráfico.
  const hasOverlay = !!(title || caption || xLabel || yLabel)
  const pad = hasOverlay ? Math.max(12, Math.round(Math.min(iw, ih) * 0.035)) : 0

  const measurer = getMeasureCtx()
  measurer.font = spec
  const titleLines = title ? wrapLines(measurer, title, iw) : []
  const captionLines = caption ? wrapLines(measurer, caption, iw) : []

  const left = pad + (yLabel ? lineH + gap : 0)
  const top = pad + (titleLines.length ? titleLines.length * lineH + gap : 0)
  let bottom = pad
  if (xLabel) bottom += gap + lineH
  if (captionLines.length) bottom += (xLabel ? Math.round(gap / 2) : gap) + captionLines.length * lineH

  const W = Math.max(1, Math.round(left + iw + pad))
  const H = Math.max(1, Math.round(top + ih + bottom))

  target.width = W
  target.height = H
  const ctx = target.getContext('2d')
  ctx.fillStyle = style.figureBg || '#ffffff'
  ctx.fillRect(0, 0, W, H)
  ctx.drawImage(img, left, top, iw, ih)
  ctx.fillStyle = style.textColor || '#111111'
  ctx.font = spec
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  titleLines.forEach((line, i) => {
    ctx.fillText(line, left + iw / 2, pad + i * lineH + lineH / 2)
  })

  if (yLabel) {
    ctx.save()
    ctx.translate(pad + lineH / 2, top + ih / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText(yLabel, 0, 0)
    ctx.restore()
    // O rótulo rotacionado pode ser mais alto que a figura; centraliza mesmo assim.
    ctx.textAlign = 'center'
  }

  let y = top + ih
  if (xLabel) {
    y += gap
    ctx.fillText(xLabel, left + iw / 2, y + lineH / 2)
    y += lineH
  }
  if (captionLines.length) {
    y += xLabel ? Math.round(gap / 2) : gap
    captionLines.forEach((line, i) => {
      ctx.fillText(line, left + iw / 2, y + i * lineH + lineH / 2)
    })
  }
  return true
}

// ---- SVG do matplotlib: detecção e transformações ----

function decodeSvg(b64) {
  try {
    const bin = atob(b64)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
    const doc = new DOMParser().parseFromString(new TextDecoder('utf-8').decode(bytes), 'image/svg+xml')
    return doc.querySelector('parsererror') ? null : doc
  } catch { return null }
}

function parseStyle(styleText) {
  const out = {}
  for (const part of String(styleText || '').split(';')) {
    const i = part.indexOf(':')
    if (i > 0) out[part.slice(0, i).trim()] = part.slice(i + 1).trim()
  }
  return out
}
function withStyle(styleText, prop, value) {
  const parts = String(styleText || '').split(';').map((p) => p.trim()).filter(Boolean)
  let found = false
  const out = parts.map((p) => {
    const i = p.indexOf(':')
    if (i > 0 && p.slice(0, i).trim() === prop) { found = true; return `${prop}: ${value}` }
    return p
  })
  if (!found) out.push(`${prop}: ${value}`)
  return out.join('; ')
}
function colorFromStyle(styleText, prop) {
  const c = parseStyle(styleText)[prop]
  if (!c) return ''
  const v = c.trim().toLowerCase()
  return v.startsWith('#') ? v.slice(0, 7) : v
}
function pathBox(d) {
  const nums = String(d || '').match(/-?\d*\.?\d+(?:e[-+]?\d+)?/gi)
  if (!nums || nums.length < 4) return null
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
  for (let i = 0; i + 1 < nums.length; i += 2) {
    const x = Number(nums[i]), y = Number(nums[i + 1])
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue
    x0 = Math.min(x0, x); x1 = Math.max(x1, x)
    y0 = Math.min(y0, y); y1 = Math.max(y1, y)
  }
  return Number.isFinite(x0) ? { x0, y0, x1, y1 } : null
}

function collectPalette(doc) {
  const seen = new Map()
  for (const ax of doc.querySelectorAll('g[id^="axes_"]')) {
    for (const el of ax.querySelectorAll('[style]')) {
      if (el.tagName === 'g') continue
      if (el.closest('g[id^="matplotlib.axis"]') || el.closest('g[id^="text_"]')) continue
      const st = el.getAttribute('style') || ''
      for (const prop of ['fill', 'stroke']) {
        const c = colorFromStyle(st, prop)
        if (!c.startsWith('#') || IGNORED_COLORS.has(c)) continue
        seen.set(c, (seen.get(c) || 0) + 1)
      }
    }
  }
  return [...seen.entries()].map(([color, count]) => ({ color, count }))
}

function hasOriginalGrid(doc) {
  return !!doc.querySelector('g[id^="matplotlib.axis"] path[style*="#b0b0b0"]')
}

function hideOriginalGrid(doc) {
  for (const p of doc.querySelectorAll('g[id^="matplotlib.axis"] path[style]')) {
    const st = parseStyle(p.getAttribute('style'))
    if (st.fill === 'none' && String(st.stroke || '').toLowerCase() === '#b0b0b0') {
      const g = p.closest('g')
      if (g) g.style.display = 'none'
    }
  }
}

function axesBackground(ax) {
  for (const g of ax.children) {
    if (g.tagName !== 'g' || !/^patch_/.test(g.id || '')) continue
    const p = g.querySelector('path')
    if (!p) continue
    const st = parseStyle(p.getAttribute('style'))
    if (st.fill && st.fill !== 'none' && /z\s*$/.test(p.getAttribute('d') || '')) return p
  }
  return null
}

function axesBox(doc, ax) {
  const clipped = ax.querySelector('[clip-path]')
  if (clipped) {
    const m = /url\(#([^)]+)\)/.exec(clipped.getAttribute('clip-path') || '')
    const rect = m && doc.getElementById(m[1])?.querySelector('rect')
    if (rect) {
      const x = Number(rect.getAttribute('x')) || 0
      const y = Number(rect.getAttribute('y')) || 0
      return { x0: x, y0: y, x1: x + (Number(rect.getAttribute('width')) || 0), y1: y + (Number(rect.getAttribute('height')) || 0) }
    }
  }
  const bg = axesBackground(ax)
  return bg ? pathBox(bg.getAttribute('d')) : null
}

function tickPositions(ax, kind) {
  const values = []
  const groups = ax.querySelectorAll(kind === 'x' ? 'g[id^="xtick_"]' : 'g[id^="ytick_"]')
  for (const tick of groups) {
    let v = NaN
    const use = tick.querySelector('use[x]')
    if (use) v = Number(kind === 'x' ? use.getAttribute('x') : use.getAttribute('y'))
    if (!Number.isFinite(v)) {
      const box = pathBox(tick.querySelector('path[d]')?.getAttribute('d'))
      if (box) v = kind === 'x' ? box.x0 : box.y0
    }
    if (Number.isFinite(v)) values.push(Math.round(v * 1000) / 1000)
  }
  return [...new Set(values)]
}

function addGrid(doc, axes) {
  const cfg = style.grid
  const dash = GRID_DASHES[cfg.dash] || ''
  const width = Math.max(0.1, Number(cfg.width) || 0.8)
  const alpha = clamp(Number(cfg.alpha) || 1, 0.05, 1)
  for (const ax of axes) {
    const box = axesBox(doc, ax)
    if (!box) continue
    const g = doc.createElementNS(SVG_NS, 'g')
    g.setAttribute('data-hv-grid', '1')
    const line = (x1, y1, x2, y2) => {
      const el = doc.createElementNS(SVG_NS, 'line')
      el.setAttribute('x1', x1)
      el.setAttribute('y1', y1)
      el.setAttribute('x2', x2)
      el.setAttribute('y2', y2)
      el.setAttribute('stroke', cfg.color)
      el.setAttribute('stroke-width', width)
      if (dash) el.setAttribute('stroke-dasharray', dash)
      if (alpha < 1) el.setAttribute('opacity', alpha)
      g.appendChild(el)
    }
    if (cfg.axis !== 'y') for (const x of tickPositions(ax, 'x')) line(x, box.y0, x, box.y1)
    if (cfg.axis !== 'x') for (const y of tickPositions(ax, 'y')) line(box.x0, y, box.x1, y)
    if (!g.childNodes.length) continue
    ax.insertBefore(g, ax.children[0]?.nextSibling || null)
  }
}

function applyStyleToDoc(doc) {
  // 1) cores dos traços/marcadores (inclui a amostra da legenda)
  const map = Object.keys(style.colors)
  if (map.length) {
    for (const el of doc.querySelectorAll('[style]')) {
      let st = el.getAttribute('style')
      let changed = false
      for (const from of map) {
        const to = style.colors[from]
        if (!to) continue
        const re = /((?:fill|stroke)\s*:\s*)(#[0-9a-fA-F]{3,8})/g
        const next = st.replace(re, (m, prop, color) => (color.toLowerCase().slice(0, 7) === from ? prop + to : m))
        if (next !== st) { st = next; changed = true }
      }
      if (changed) el.setAttribute('style', st)
    }
  }

  // 2) espessura dos traços (somente linhas de dados e suas amostras na legenda)
  const lw = Number(style.lineWidth)
  if (Number.isFinite(lw) && lw > 0) {
    for (const p of doc.querySelectorAll('path[style]')) {
      const st = p.getAttribute('style')
      const props = parseStyle(st)
      if (props.fill !== 'none' || !props.stroke) continue
      if (/^#(000000|b0b0b0)$/i.test(props.stroke)) continue
      if (p.closest('g[id^="matplotlib.axis"]')) continue
      p.setAttribute('style', withStyle(st, 'stroke-width', String(lw)))
    }
  }

  const axes = [...doc.querySelectorAll('g[id^="axes_"]')]

  // 3) fundos da figura e da área do gráfico
  if (style.figureBg) {
    const fig = doc.querySelector('g[id^="figure_"]')
    const patch = fig ? [...fig.children].find((g) => g.tagName === 'g' && /^patch_/.test(g.id || '')) : null
    const p = patch?.querySelector('path')
    if (p) p.setAttribute('style', withStyle(p.getAttribute('style'), 'fill', style.figureBg))
  }
  if (style.axesBg) {
    for (const ax of axes) {
      const p = axesBackground(ax)
      if (p) p.setAttribute('style', withStyle(p.getAttribute('style'), 'fill', style.axesBg))
    }
  }

  // 4) cor do texto (títulos, rótulos e ticks seriam paths; o grupo herda o fill)
  if (style.textColor) {
    for (const g of doc.querySelectorAll('g[id^="text_"]')) g.setAttribute('fill', style.textColor)
  }

  // 5) bordas (spines) e marcas dos eixos
  const spineW = Number(style.spineWidth)
  if (style.spineColor || (Number.isFinite(spineW) && spineW > 0)) {
    for (const ax of axes) {
      for (const g of ax.children) {
        if (g.tagName !== 'g' || !/^patch_/.test(g.id || '')) continue
        const p = g.querySelector('path')
        if (!p) continue
        const props = parseStyle(p.getAttribute('style'))
        if (props.fill !== 'none' || !props.stroke) continue
        let st = p.getAttribute('style')
        if (style.spineColor) st = withStyle(st, 'stroke', style.spineColor)
        if (Number.isFinite(spineW) && spineW > 0) st = withStyle(st, 'stroke-width', String(spineW))
        p.setAttribute('style', st)
      }
    }
    if (style.spineColor) {
      for (const u of doc.querySelectorAll('g[id^="matplotlib.axis"] use[style]')) {
        const st = u.getAttribute('style')
        if (parseStyle(st).stroke) u.setAttribute('style', withStyle(st, 'stroke', style.spineColor))
      }
    }
  }

  // 6) grade: esconde a original e desenha a configurada nas posições dos ticks
  hideOriginalGrid(doc)
  if (style.grid.show) addGrid(doc, axes)

  return doc
}

function rasterize(doc) {
  const root = doc.documentElement
  const vb = String(root.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number)
  const w = (vb.length === 4 && vb[2]) || parseFloat(root.getAttribute('width')) || 640
  const h = (vb.length === 4 && vb[3]) || parseFloat(root.getAttribute('height')) || 480
  root.setAttribute('width', String(Math.round(w * RASTER_SCALE)))
  root.setAttribute('height', String(Math.round(h * RASTER_SCALE)))
  const xml = new XMLSerializer().serializeToString(root)
  const url = URL.createObjectURL(new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }))
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('svg')) }
    img.src = url
  })
}

async function styledImage() {
  if (!svgTemplate) return pngImg
  return rasterize(applyStyleToDoc(svgTemplate.cloneNode(true)))
}

function scheduleRender() {
  clearTimeout(renderTimer)
  renderTimer = setTimeout(render, 90)
}

async function render() {
  if (!preview.value) return
  const seq = ++renderSeq
  let img = pngImg
  if (svgTemplate) {
    try { img = await styledImage() } catch { img = pngImg }
  }
  if (seq !== renderSeq || !img) return
  baseImg = img
  if (!composeTo(preview.value, img)) return
  natural.value = { w: preview.value.width, h: preview.value.height }
  if (!firstFit) { firstFit = true; nextTick(fit) }
}

function fit() {
  const el = scroller.value
  if (!el || !natural.value.w) return
  const availW = Math.max(40, el.clientWidth - 28)
  const availH = Math.max(40, el.clientHeight - 28)
  zoom.value = clamp(Math.min(1, availW / natural.value.w, availH / natural.value.h), ZOOM_MIN, ZOOM_MAX)
}
function zoomBy(factor) {
  zoom.value = clamp(zoom.value * factor, ZOOM_MIN, ZOOM_MAX)
}
function zoomIn() { zoomBy(1.2) }
function zoomOut() { zoomBy(1 / 1.2) }

function onWheel(e) {
  // Rolagem do mouse amplia/reduz, como em uma janela interativa de plot.
  e.preventDefault()
  zoom.value = clamp(zoom.value * (e.deltaY < 0 ? 1.12 : 1 / 1.12), ZOOM_MIN, ZOOM_MAX)
}
function onPanDown(e) {
  if (e.button !== 0 || !scroller.value) return
  pan.value = { x: e.clientX, y: e.clientY, left: scroller.value.scrollLeft, top: scroller.value.scrollTop }
  scroller.value.setPointerCapture?.(e.pointerId)
}
function onPanMove(e) {
  if (!pan.value || !scroller.value) return
  scroller.value.scrollLeft = pan.value.left - (e.clientX - pan.value.x)
  scroller.value.scrollTop = pan.value.top - (e.clientY - pan.value.y)
}
function onPanUp(e) {
  if (scroller.value?.hasPointerCapture?.(e.pointerId)) scroller.value.releasePointerCapture(e.pointerId)
  pan.value = null
}

// ---- estilo ----
function setColor(from, to) {
  style.colors = { ...style.colors, [from]: to }
}
function clearColor(from) {
  const next = { ...style.colors }
  delete next[from]
  style.colors = next
}
function shownColor(from) {
  return style.colors[from] || from
}
function clearField(key) { style[key] = '' }
function resetStyle() {
  const grid = { ...style.grid, show: style.grid.show, color: '#b0b0b0', width: 0.8, alpha: 1, dash: 'solid', axis: 'both' }
  style.colors = {}
  style.lineWidth = ''
  style.textColor = ''
  style.spineColor = ''
  style.spineWidth = ''
  style.figureBg = ''
  style.axesBg = ''
  style.grid = grid
}

async function captureCanvas() {
  const img = await styledImage()
  const canvas = document.createElement('canvas')
  return composeTo(canvas, img) ? canvas : null
}
function safeName(ext) {
  const base = String(props.figure.name || '').trim()
    .replace(/[\\/:*?"<>|]+/g, '_')
    .replace(/\s+/g, '_')
  return `${base || 'figure'}.${ext}`
}

async function addToCaptures() {
  try {
    const canvas = await captureCanvas()
    if (!canvas) return
    const capture = addCapture(canvas.toDataURL('image/png'), props.figure.name)
    toast(t('figures.capture_saved', { name: capture.name }))
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

async function exportPNG() {
  try {
    const canvas = await captureCanvas()
    if (!canvas) return
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (blob) download(safeName('png'), blob)
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

function exportSVG() {
  try {
    if (!svgTemplate) return
    const doc = applyStyleToDoc(svgTemplate.cloneNode(true))
    const xml = new XMLSerializer().serializeToString(doc.documentElement)
    download(safeName('svg'), new Blob([xml], { type: 'image/svg+xml;charset=utf-8' }))
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

// PDF mínimo com uma única imagem JPEG ocupando a página inteira, sem margens.
function pdfBlob(canvas) {
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
  const bin = atob(dataUrl.slice(dataUrl.indexOf(',') + 1))
  const jpeg = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) jpeg[i] = bin.charCodeAt(i)

  const W = canvas.width
  const H = canvas.height
  const encoder = new TextEncoder()
  const chunks = []
  const offsets = []
  let length = 0
  const push = (data) => {
    const bytes = typeof data === 'string' ? encoder.encode(data) : data
    chunks.push(bytes)
    length += bytes.length
  }
  const begin = (n, dict) => { offsets[n] = length; push(`${n} 0 obj\n${dict}\n`) }
  const end = () => push('endobj\n')

  push('%PDF-1.4\n')
  begin(1, '<< /Type /Catalog /Pages 2 0 R >>'); end()
  begin(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>'); end()
  begin(3, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${W} ${H}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>`); end()

  offsets[4] = length
  push(`4 0 obj\n<< /Type /XObject /Subtype /Image /Width ${W} /Height ${H} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`)
  push(jpeg)
  push('\nendstream\nendobj\n')

  const content = `q\n${W} 0 0 ${H} 0 0 cm\n/Im0 Do\nQ\n`
  begin(5, `<< /Length ${content.length} >>\nstream\n${content}endstream`); end()

  const xref = length
  push('xref\n0 6\n0000000000 65535 f \n')
  for (let n = 1; n <= 5; n++) push(`${String(offsets[n]).padStart(10, '0')} 00000 n \n`)
  push(`trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`)

  const out = new Uint8Array(length)
  let at = 0
  for (const chunk of chunks) { out.set(chunk, at); at += chunk.length }
  return new Blob([out], { type: 'application/pdf' })
}

async function exportPDF() {
  try {
    const canvas = await captureCanvas()
    if (!canvas) return
    download(safeName('pdf'), pdfBlob(canvas))
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

async function saveToReport() {
  try {
    const canvas = await captureCanvas()
    if (!canvas) return
    const capture = addCapture(canvas.toDataURL('image/png'), props.figure.name)
    const alt = String(props.figure.caption || props.figure.title || props.figure.name || '').trim()
    insertCaptureIntoReport(capture, alt)
    toast(t('figures.report_saved', { name: capture.name }))
    emit('close')
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

function loadPng(onDone) {
  if (!props.figure.png_b64) { onDone(); return }
  const img = new Image()
  img.onload = () => { pngImg = img; onDone() }
  img.onerror = () => { onDone() }
  img.src = `data:image/png;base64,${props.figure.png_b64}`
}

onMounted(() => {
  if (props.figure.svg_b64) {
    const doc = decodeSvg(props.figure.svg_b64)
    if (doc) {
      svgTemplate = doc
      hasSvg.value = true
      palette.value = collectPalette(doc)
      if (!style.gridTouched && hasOriginalGrid(doc)) {
        style.grid.show = true
        style.gridTouched = true
      }
    }
  }
  loadPng(() => render())
})

watch(
  () => [props.figure.title, props.figure.caption, props.figure.xLabel, props.figure.yLabel, props.figure.font, props.figure.fontSize],
  () => render(),
)
watch(style, () => scheduleRender(), { deep: true })
</script>

<template>
  <Modal :title="t('figures.window_title', { n: index + 1 }) + (figure.name ? ' · ' + figure.name : '')" :width="1180" @close="emit('close')">
    <div class="fv">
      <section class="fv-preview-pane">
        <div class="fv-toolbar">
          <button class="btn ghost icon sm" type="button" :aria-label="t('figures.zoom_out')" :data-tip="t('figures.zoom_out')" @click="zoomOut"><Icon name="zoomOut" :size="14" /></button>
          <span class="fv-zoom mono">{{ zoomPct }}%</span>
          <button class="btn ghost icon sm" type="button" :aria-label="t('figures.zoom_in')" :data-tip="t('figures.zoom_in')" @click="zoomIn"><Icon name="zoomIn" :size="14" /></button>
          <button class="btn ghost icon sm" type="button" :aria-label="t('figures.fit')" :data-tip="t('figures.fit')" @click="fit"><Icon name="fit" :size="14" /></button>
          <span class="sp" />
          <button class="btn ghost sm" type="button" @click="addToCaptures"><Icon name="camera" :size="13" />{{ t('figures.add_capture') }}</button>
          <button class="btn ghost sm" type="button" @click="exportPNG"><Icon name="download" :size="13" />{{ t('figures.download_png') }}</button>
          <button class="btn ghost sm" type="button" :disabled="!hasSvg" @click="exportSVG"><Icon name="file" :size="13" />{{ t('figures.download_svg') }}</button>
          <button class="btn ghost sm" type="button" @click="exportPDF"><Icon name="file" :size="13" />{{ t('figures.download_pdf') }}</button>
        </div>
        <div ref="scroller" class="fv-scroll" :class="{ panning: !!pan }" @pointerdown="onPanDown" @pointermove="onPanMove" @pointerup="onPanUp" @pointercancel="onPanUp" @wheel="onWheel" @dblclick="fit">
          <div class="fv-stage">
            <canvas ref="preview" class="fv-canvas" :style="previewStyle" role="img" :aria-label="figure.name || t('plots.fig_n', { n: index + 1 })" />
          </div>
        </div>
      </section>

      <aside class="fv-fields">
        <label class="field">
          <span class="label">{{ t('figures.name') }}</span>
          <input v-model="figure.name" class="input" type="text" spellcheck="false" />
        </label>
        <label class="field">
          <span class="label">{{ t('figures.title') }}</span>
          <input v-model="figure.title" class="input" type="text" :placeholder="t('figures.title_ph')" />
        </label>
        <label class="field">
          <span class="label">{{ t('figures.caption') }}</span>
          <textarea v-model="figure.caption" class="input" rows="3" :placeholder="t('figures.caption_ph')" />
        </label>
        <div class="fv-row">
          <label class="field">
            <span class="label">{{ t('figures.x_label') }}</span>
            <input v-model="figure.xLabel" class="input" type="text" :placeholder="t('figures.x_label_ph')" />
          </label>
          <label class="field">
            <span class="label">{{ t('figures.y_label') }}</span>
            <input v-model="figure.yLabel" class="input" type="text" :placeholder="t('figures.y_label_ph')" />
          </label>
        </div>
        <div class="fv-row">
          <label class="field">
            <span class="label">{{ t('figures.font') }}</span>
            <select v-model="figure.font" class="input">
              <option v-for="f in FONTS" :key="f" :value="f">{{ f }}</option>
            </select>
          </label>
          <label class="field fv-size">
            <span class="label">{{ t('figures.font_size') }}</span>
            <input v-model.number="figure.fontSize" class="input mono" type="number" :min="FONT_MIN" :max="FONT_MAX" step="1" />
          </label>
        </div>

        <template v-if="hasSvg">
          <div class="fv-sep" />
          <div class="fv-style-head">
            <b>{{ t('figures.style') }}</b>
            <button class="btn ghost sm" type="button" @click="resetStyle"><Icon name="refresh" :size="12" />{{ t('figures.reset_style') }}</button>
          </div>

          <details class="fv-sec" open>
            <summary>{{ t('figures.series_colors') }}</summary>
            <div v-if="palette.length" class="fv-colors">
              <label v-for="p in palette" :key="p.color" class="fv-color">
                <input class="fv-color-input" type="color" :value="shownColor(p.color)" :aria-label="t('figures.series_color', { color: p.color })" @input="setColor(p.color, $event.target.value)" />
                <span class="fv-old mono">{{ p.color }}</span>
                <button v-if="style.colors[p.color]" class="btn ghost icon sm" type="button" :aria-label="t('figures.reset_color')" :data-tip="t('figures.reset_color')" @click="clearColor(p.color)"><Icon name="close" :size="11" /></button>
              </label>
            </div>
            <p v-else class="fv-note muted small">{{ t('figures.no_series') }}</p>
          </details>

          <details class="fv-sec" open>
            <summary>{{ t('figures.grid') }}</summary>
            <label class="fv-check">
              <input v-model="style.grid.show" type="checkbox" @change="style.gridTouched = true" />
              <span>{{ t('figures.show_grid') }}</span>
            </label>
            <div class="fv-row">
              <label class="field">
                <span class="label">{{ t('figures.grid_axis') }}</span>
                <select v-model="style.grid.axis" class="input">
                  <option v-for="a in axisOptions" :key="a.id" :value="a.id">{{ a.label }}</option>
                </select>
              </label>
              <label class="field">
                <span class="label">{{ t('figures.grid_style') }}</span>
                <select v-model="style.grid.dash" class="input">
                  <option v-for="d in dashOptions" :key="d.id" :value="d.id">{{ d.label }}</option>
                </select>
              </label>
            </div>
            <div class="fv-row">
              <label class="field">
                <span class="label">{{ t('figures.grid_color') }}</span>
                <input v-model="style.grid.color" class="input fv-color-input" type="color" />
              </label>
              <label class="field fv-size">
                <span class="label">{{ t('figures.grid_width') }}</span>
                <input v-model.number="style.grid.width" class="input mono" type="number" min="0.1" max="8" step="0.1" />
              </label>
            </div>
            <label class="field">
              <span class="label">{{ t('figures.grid_alpha') }} · {{ Math.round(style.grid.alpha * 100) }}%</span>
              <input v-model.number="style.grid.alpha" class="fv-range" type="range" min="0.1" max="1" step="0.05" />
            </label>
          </details>

          <details class="fv-sec">
            <summary>{{ t('figures.lines_axes') }}</summary>
            <div class="fv-row">
              <label class="field">
                <span class="label">{{ t('figures.line_width') }}</span>
                <input v-model.number="style.lineWidth" class="input mono" type="number" min="0.1" max="12" step="0.1" :placeholder="t('figures.auto')" />
              </label>
              <label class="field">
                <span class="label">{{ t('figures.spine_width') }}</span>
                <input v-model.number="style.spineWidth" class="input mono" type="number" min="0.1" max="12" step="0.1" :placeholder="t('figures.auto')" />
              </label>
            </div>
            <div class="fv-row">
              <label class="field">
                <span class="label">{{ t('figures.text_color') }}</span>
                <span class="fv-color-field">
                  <input class="input fv-color-input" type="color" :value="style.textColor || '#111111'" @input="style.textColor = $event.target.value" />
                  <button v-if="style.textColor" class="btn ghost icon sm" type="button" :aria-label="t('figures.reset_color')" @click="clearField('textColor')"><Icon name="close" :size="11" /></button>
                </span>
              </label>
              <label class="field">
                <span class="label">{{ t('figures.spine_color') }}</span>
                <span class="fv-color-field">
                  <input class="input fv-color-input" type="color" :value="style.spineColor || '#000000'" @input="style.spineColor = $event.target.value" />
                  <button v-if="style.spineColor" class="btn ghost icon sm" type="button" :aria-label="t('figures.reset_color')" @click="clearField('spineColor')"><Icon name="close" :size="11" /></button>
                </span>
              </label>
            </div>
          </details>

          <details class="fv-sec">
            <summary>{{ t('figures.background') }}</summary>
            <div class="fv-row">
              <label class="field">
                <span class="label">{{ t('figures.figure_bg') }}</span>
                <span class="fv-color-field">
                  <input class="input fv-color-input" type="color" :value="style.figureBg || '#ffffff'" @input="style.figureBg = $event.target.value" />
                  <button v-if="style.figureBg" class="btn ghost icon sm" type="button" :aria-label="t('figures.reset_color')" @click="clearField('figureBg')"><Icon name="close" :size="11" /></button>
                </span>
              </label>
              <label class="field">
                <span class="label">{{ t('figures.axes_bg') }}</span>
                <span class="fv-color-field">
                  <input class="input fv-color-input" type="color" :value="style.axesBg || '#ffffff'" @input="style.axesBg = $event.target.value" />
                  <button v-if="style.axesBg" class="btn ghost icon sm" type="button" :aria-label="t('figures.reset_color')" @click="clearField('axesBg')"><Icon name="close" :size="11" /></button>
                </span>
              </label>
            </div>
          </details>
        </template>
      </aside>
    </div>

    <template #footer>
      <span class="fv-hint muted small">{{ t('figures.hint') }}</span>
      <span class="sp" />
      <button class="btn ghost" type="button" @click="emit('close')">{{ t('common.close') }}</button>
      <button class="btn primary" type="button" @click="saveToReport"><Icon name="file" :size="14" />{{ t('figures.save_report') }}</button>
    </template>
  </Modal>
</template>

<style scoped>
.fv { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: var(--sp-5); align-items: start; }
.fv-preview-pane { display: flex; flex-direction: column; gap: var(--sp-3); min-width: 0; }
.fv-toolbar { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.fv-zoom { min-width: 52px; text-align: center; font-size: var(--fs-label); color: var(--text-muted); }
.fv-scroll { height: min(62vh, 620px); overflow: auto; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); cursor: grab; }
.fv-scroll.panning { cursor: grabbing; }
.fv-stage { display: flex; align-items: center; justify-content: center; width: max-content; min-width: 100%; min-height: 100%; padding: 14px; box-sizing: border-box; }
.fv-canvas { display: block; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, .12); max-width: none; }
.fv-fields { display: flex; flex-direction: column; gap: var(--sp-3); min-width: 0; }
.fv-fields textarea { min-height: 64px; resize: vertical; }
.fv-row { display: flex; gap: var(--sp-3); }
.fv-row .field { flex: 1 1 0; min-width: 0; }
.fv-size { max-width: 96px; }
.fv-sep { height: 1px; background: var(--border); margin: var(--sp-2) 0; }
.fv-style-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); }
.fv-style-head b { font-size: var(--fs-label); }
.fv-sec { border: 1px solid var(--border); border-radius: var(--radius); padding: var(--sp-2) var(--sp-3) var(--sp-3); background: var(--surface-2); }
.fv-sec > summary { cursor: pointer; font-size: var(--fs-label); font-weight: 600; padding: var(--sp-2) 0; user-select: none; }
.fv-sec > *:not(summary) { margin-top: var(--sp-2); }
.fv-sec .fv-row { margin-top: var(--sp-3); }
.fv-sec .field { gap: 3px; }
.fv-sec .label { font-size: var(--fs-xs); }
.fv-check { display: flex; align-items: center; gap: var(--sp-3); cursor: pointer; font-size: var(--fs-label); }
.fv-check input { margin: 0; }
.fv-colors { display: flex; flex-direction: column; gap: 4px; max-height: 190px; overflow: auto; }
.fv-color { display: flex; align-items: center; gap: var(--sp-3); padding: 1px 0; }
.fv-color-input { width: 34px; height: 24px; padding: 1px; border: 1px solid var(--border); border-radius: var(--radius-xs); background: var(--surface); cursor: pointer; flex: none; }
.fv-old { font-size: var(--fs-2xs); color: var(--text-muted); flex: 1; }
.fv-color-field { display: flex; align-items: center; gap: var(--sp-2); }
.fv-color-field .fv-color-input { flex: 1; width: auto; }
.fv-range { width: 100%; accent-color: var(--accent); }
.fv-note { margin: 0; line-height: 1.4; }
.fv-hint { max-width: 420px; line-height: 1.4; }
.sp { flex: 1; }
@media (max-width: 980px) {
  .fv { grid-template-columns: 1fr; }
  .fv-scroll { height: 40vh; }
  .fv-hint { display: none; }
}
</style>
