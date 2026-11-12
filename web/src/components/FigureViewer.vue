<script setup>
// Visualizador/editor de figuras do matplotlib. O PNG original não é editável,
// então título, legenda e rótulos dos eixos são compostos em um canvas branco
// (sem moldura) usado tanto na prévia quanto nos downloads.
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { addCapture, insertCaptureIntoReport, download, toast } from '../state/store.js'
import { t } from '../i18n/index.js'

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

const preview = ref(null)
const scroller = ref(null)
const natural = ref({ w: 0, h: 0 })
const zoom = ref(1)
const pan = ref(null)
let baseImg = null
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
function composeTo(target) {
  if (!baseImg || !target) return false
  const iw = baseImg.naturalWidth || baseImg.width
  const ih = baseImg.naturalHeight || baseImg.height
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
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, W, H)
  ctx.drawImage(baseImg, left, top, iw, ih)
  ctx.fillStyle = '#111111'
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

function render() {
  if (!preview.value) return
  if (!composeTo(preview.value)) return
  natural.value = { w: preview.value.width, h: preview.value.height }
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

function captureCanvas() {
  const canvas = document.createElement('canvas')
  return composeTo(canvas) ? canvas : null
}
function safeName(ext) {
  const base = String(props.figure.name || '').trim()
    .replace(/[\\/:*?"<>|]+/g, '_')
    .replace(/\s+/g, '_')
  return `${base || 'figure'}.${ext}`
}

function addToCaptures() {
  try {
    const canvas = captureCanvas()
    if (!canvas) return
    const capture = addCapture(canvas.toDataURL('image/png'), props.figure.name)
    toast(t('figures.capture_saved', { name: capture.name }))
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

async function exportPNG() {
  try {
    const canvas = captureCanvas()
    if (!canvas) return
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (blob) download(safeName('png'), blob)
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

function exportPDF() {
  try {
    const canvas = captureCanvas()
    if (!canvas) return
    download(safeName('pdf'), pdfBlob(canvas))
  } catch (err) {
    toast(t('figures.export_failed', { error: String(err?.message || err) }), 'error')
  }
}

function saveToReport() {
  try {
    const canvas = captureCanvas()
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

onMounted(() => {
  if (!props.figure.png_b64) return
  const img = new Image()
  img.onload = () => {
    baseImg = img
    render()
    nextTick(fit)
    setTimeout(fit, 80)
  }
  img.src = `data:image/png;base64,${props.figure.png_b64}`
})

watch(
  () => [props.figure.title, props.figure.caption, props.figure.xLabel, props.figure.yLabel, props.figure.font, props.figure.fontSize],
  () => render(),
)
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
.fv { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: var(--sp-5); align-items: start; }
.fv-preview-pane { display: flex; flex-direction: column; gap: var(--sp-3); min-width: 0; }
.fv-toolbar { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.fv-zoom { min-width: 52px; text-align: center; font-size: var(--fs-label); color: var(--text-muted); }
.fv-scroll { height: min(62vh, 620px); overflow: auto; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); cursor: grab; }
.fv-scroll.panning { cursor: grabbing; }
.fv-stage { display: flex; align-items: center; justify-content: center; width: max-content; min-width: 100%; min-height: 100%; padding: 14px; box-sizing: border-box; }
.fv-canvas { display: block; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, .12); max-width: none; }
.fv-fields { display: flex; flex-direction: column; gap: var(--sp-4); min-width: 0; }
.fv-fields textarea { min-height: 64px; resize: vertical; }
.fv-row { display: flex; gap: var(--sp-3); }
.fv-row .field { flex: 1 1 0; min-width: 0; }
.fv-size { max-width: 96px; }
.fv-hint { max-width: 520px; line-height: 1.4; }
.sp { flex: 1; }
@media (max-width: 900px) {
  .fv { grid-template-columns: 1fr; }
  .fv-scroll { height: 40vh; }
  .fv-hint { display: none; }
}
</style>
