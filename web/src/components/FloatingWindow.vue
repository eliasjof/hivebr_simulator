<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'
import { t } from '../i18n/index.js'
import { store, WINDOW_DEFS, focusWindow, closeWindow, clampWindow, menubarH } from '../state/store.js'

const props = defineProps({
  id: { type: String, required: true },
  minW: { type: Number, default: null },
  minH: { type: Number, default: null },
})
const w = computed(() => store.windows[props.id])
const def = computed(() => WINDOW_DEFS[props.id])
const minW = computed(() => props.minW ?? def.value.minW ?? 280)
const minH = computed(() => props.minH ?? def.value.minH ?? 160)
const title = computed(() => t(def.value.titleKey))
const interacting = ref(false)

const style = computed(() => {
  const s = w.value
  if (s.maximized) {
    // área útil real: abaixo de menus + ferramentas e acima da barra de status (+8 px de respiro)
    return {
      left: 'var(--sp-4)', right: 'var(--sp-4)',
      top: 'calc(var(--menubar-h) + var(--toolbar-h) + var(--sp-4))',
      bottom: 'calc(var(--status-h) + var(--sp-4))', zIndex: s.z,
    }
  }
  return { left: s.x + 'px', top: s.y + 'px', width: s.w + 'px', height: s.h + 'px', zIndex: s.z }
})

let drag = null
function startDrag(e) {
  focusWindow(props.id)
  if (e.target.closest('button, input, select, a, [data-nodrag]')) return
  if (w.value.maximized || e.button > 0) return
  drag = { px: e.clientX, py: e.clientY, x: w.value.x, y: w.value.y }
  e.currentTarget.setPointerCapture(e.pointerId)
  interacting.value = true
}
function moveDrag(e) {
  if (!drag) return
  w.value.x = drag.x + e.clientX - drag.px
  w.value.y = drag.y + e.clientY - drag.py
  clampWindow(w.value, props.id)
}
function endDrag(e) {
  if (!drag) return
  drag = null
  interacting.value = false
  try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* já liberado */ }
}

let rs = null
function startResize(dir, e) {
  if (w.value.maximized) return
  focusWindow(props.id)
  rs = { dir, px: e.clientX, py: e.clientY, x: w.value.x, y: w.value.y, w: w.value.w, h: w.value.h }
  e.currentTarget.setPointerCapture(e.pointerId)
  interacting.value = true
  e.preventDefault()
}
function moveResize(e) {
  if (!rs) return
  const dx = e.clientX - rs.px
  const dy = e.clientY - rs.py
  const s = w.value
  const vw = window.innerWidth, vh = window.innerHeight
  const top = menubarH()
  let { x, y, w: ww, h: hh } = rs
  if (rs.dir.includes('e')) ww = Math.min(rs.w + dx, vw - rs.x)
  if (rs.dir.includes('s')) hh = Math.min(rs.h + dy, vh - rs.y)
  if (rs.dir.includes('w')) {
    // a borda oeste para em x = 0
    const nx = Math.max(0, Math.min(rs.x + dx, rs.x + rs.w - minW.value))
    x = nx; ww = rs.x + rs.w - nx
  }
  if (rs.dir.includes('n')) {
    // a borda norte para sob a barra de menus
    const ny = Math.max(top, Math.min(rs.y + dy, rs.y + rs.h - minH.value))
    y = ny; hh = rs.y + rs.h - ny
  }
  s.x = x; s.y = y; s.w = Math.max(minW.value, ww); s.h = Math.max(minH.value, hh)
}
function endResize(e) {
  if (!rs) return
  rs = null
  interacting.value = false
  try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* já liberado */ }
}

// teclado: setas movem 10 px (Shift 40); Alt+setas redimensionam
function onTitleKey(e) {
  if (e.target !== e.currentTarget || w.value.maximized) return
  const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key]
  if (!d) return
  e.preventDefault()
  const step = e.shiftKey ? 40 : 10
  const s = w.value
  if (e.altKey) {
    s.w = Math.max(minW.value, s.w + d[0] * step)
    s.h = Math.max(minH.value, s.h + d[1] * step)
  } else {
    s.x += d[0] * step; s.y += d[1] * step
  }
  clampWindow(s, props.id)
}
function toggleMax() { w.value.maximized = !w.value.maximized; focusWindow(props.id) }
function minimize() { w.value.minimized = true }
const dirs = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw']
</script>

<template>
  <section v-if="w.open" v-show="!w.minimized" class="fw panel float"
    :class="{ maximized: w.maximized, interacting }" :style="style"
    role="dialog" :aria-label="title" @pointerdown.capture="focusWindow(id)">
    <header class="fw-title" tabindex="0" :aria-label="t('win.title_hint', { title })" @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="endDrag"
      @pointercancel="endDrag" @keydown="onTitleKey" @dblclick="(e) => { if (!e.target.closest('button, input, select')) toggleMax() }">
      <span class="fw-icon"><Icon :name="def.icon" :size="15" /></span>
      <h2 class="fw-name">{{ title }}</h2>
      <div class="fw-actions" data-nodrag><slot name="actions" /></div>
      <div class="fw-ctrl" data-nodrag>
        <button class="btn ghost icon sm" :data-tip="t('win.minimize')" :aria-label="t('win.minimize')" @click="minimize"><Icon name="min" :size="14" /></button>
        <button class="btn ghost icon sm" :data-tip="w.maximized ? t('win.restore') : t('win.maximize')" :aria-label="w.maximized ? t('win.restore') : t('win.maximize')" @click="toggleMax"><Icon :name="w.maximized ? 'restore' : 'max'" :size="13" /></button>
        <button class="btn ghost icon sm" :data-tip="t('win.close', { key: def.shortcut })" :aria-label="t('win.close_aria')" data-tip-pos="end" @click="closeWindow(id)"><Icon name="close" :size="14" /></button>
      </div>
    </header>
    <div class="fw-body"><slot /></div>
    <template v-if="!w.maximized">
      <div v-for="d in dirs" :key="d" class="fw-h" :class="'h-' + d" @pointerdown="startResize(d, $event)"
        @pointermove="moveResize" @pointerup="endResize" @pointercancel="endResize" />
      <svg class="fw-grip" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
        <path d="M10 2l-1 1.7h-2L6 2l1-1.7h2zM10 8l-1 1.7h-2L6 8l1-1.7h2zM4 8L3 9.7H1L0 8l1-1.7h2z" fill="currentColor" />
      </svg>
    </template>
  </section>
</template>

<style scoped>
/* overflow visível: as alças ficam 3 px fora da borda; os cantos são aparados nos filhos */
.fw { position: fixed; display: flex; flex-direction: column; min-width: 0; }
.fw.interacting { user-select: none; }
.fw.interacting .fw-body { pointer-events: none; }
.fw-title {
  display: flex; align-items: center; gap: var(--sp-4); height: var(--fw-title-h); padding: 0 var(--sp-3) 0 10px; flex: none;
  border-bottom: 1px solid var(--border); cursor: grab; touch-action: none; user-select: none;
  background: var(--surface-2); border-radius: calc(var(--radius) - 1px) calc(var(--radius) - 1px) 0 0;
}
.fw-title:active { cursor: grabbing; }
.fw.maximized .fw-title { cursor: default; }
.fw-title:focus-visible { outline-offset: -2px; }
.fw-icon { color: var(--text-muted); display: grid; }
.fw-name { font-size: var(--fs-xs); font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--text-muted); flex: none; }
.fw-actions { display: flex; align-items: center; gap: var(--sp-2); margin-left: auto; min-width: 0; }
.fw-ctrl { display: flex; }
.fw-body {
  flex: 1; min-height: 0; display: flex; flex-direction: column; position: relative; container-type: inline-size; overflow: hidden;
  border-radius: 0 0 calc(var(--radius) - 1px) calc(var(--radius) - 1px);
}
.fw-h { position: absolute; z-index: 3; touch-action: none; }
.h-n { top: -3px; left: 10px; right: 10px; height: 8px; cursor: ns-resize; }
.h-s { bottom: -3px; left: 10px; right: 10px; height: 8px; cursor: ns-resize; }
.h-e { right: -3px; top: 10px; bottom: 10px; width: 8px; cursor: ew-resize; }
.h-w { left: -3px; top: 10px; bottom: 10px; width: 8px; cursor: ew-resize; }
.h-ne { top: -3px; right: -3px; width: 14px; height: 14px; cursor: nesw-resize; }
.h-nw { top: -3px; left: -3px; width: 14px; height: 14px; cursor: nwse-resize; }
.h-se { bottom: -3px; right: -3px; width: 18px; height: 18px; cursor: nwse-resize; }
.h-sw { bottom: -3px; left: -3px; width: 14px; height: 14px; cursor: nesw-resize; }
.fw-grip { position: absolute; right: 3px; bottom: 3px; color: var(--text-faint); pointer-events: none; z-index: 2; opacity: .7; }
@media (pointer: coarse) {
  .h-n, .h-s { height: 14px; } .h-e, .h-w { width: 14px; }
  .h-se { width: 28px; height: 28px; }
}
</style>
