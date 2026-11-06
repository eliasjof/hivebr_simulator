<script setup>
import { ref } from 'vue'
const props = defineProps({
  axis: { type: String, default: 'x' }, // x: arrasta na horizontal; y: na vertical
  value: Number, min: { type: Number, default: 120 }, max: { type: Number, default: 900 },
  invert: Boolean, // painel à direita/abaixo cresce ao arrastar para a esquerda/cima
  label: String,
})
const emit = defineEmits(['update:value'])
const active = ref(false)
let st = null
function down(e) {
  st = { p: props.axis === 'x' ? e.clientX : e.clientY, v: props.value }
  e.currentTarget.setPointerCapture(e.pointerId)
  active.value = true
}
function move(e) {
  if (!st) return
  const d = (props.axis === 'x' ? e.clientX : e.clientY) - st.p
  emit('update:value', Math.round(Math.max(props.min, Math.min(props.max, st.v + (props.invert ? -d : d)))))
}
function up(e) { st = null; active.value = false; try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* ok */ } }
function key(e) {
  const step = e.shiftKey ? 40 : 10
  const k = props.axis === 'x' ? ['ArrowLeft', 'ArrowRight'] : ['ArrowUp', 'ArrowDown']
  let d = e.key === k[0] ? -step : e.key === k[1] ? step : 0
  if (!d) return
  e.preventDefault()
  emit('update:value', Math.max(props.min, Math.min(props.max, props.value + (props.invert ? -d : d))))
}
</script>
<template>
  <div class="spl" :class="[axis, { active }]" role="separator" :aria-orientation="axis === 'x' ? 'vertical' : 'horizontal'" tabindex="0"
    :aria-label="label" @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up" @keydown="key"><i /></div>
</template>
<style scoped>
.spl { position: relative; flex: none; touch-action: none; z-index: var(--z-raised); }
.spl.x { width: var(--splitter-w); cursor: col-resize; margin: 0 -2px; }
.spl.y { height: var(--splitter-w); cursor: row-resize; margin: -2px 0; }
.spl i { position: absolute; background: transparent; transition: background var(--dur-fast); }
.spl.x i { left: 2px; top: 0; bottom: 0; width: 1px; }
.spl.y i { top: 2px; left: 0; right: 0; height: 1px; }
.spl:hover i, .spl.active i, .spl:focus-visible i { background: var(--accent); }
.spl:focus-visible { outline: none; }
</style>
