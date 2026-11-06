<script setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import Icon from './Icon.vue'
import { t } from '../i18n/index.js'

const props = defineProps({
  title: String,
  width: { type: Number, default: 520 },
  closable: { type: Boolean, default: true },
  labelledby: String,
})
const emit = defineEmits(['close'])
const root = ref(null)
let prev = null
const FOCUSABLE = 'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'

function onKey(e) {
  if (e.key === 'Escape' && props.closable) {
    e.stopPropagation(); e.preventDefault(); emit('close')
    return
  }
  if (e.key !== 'Tab') return
  const items = [...root.value.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null)
  if (!items.length) { e.preventDefault(); return }
  const first = items[0], last = items[items.length - 1]
  if (e.shiftKey && (document.activeElement === first || !root.value.contains(document.activeElement))) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}
onMounted(async () => {
  prev = document.activeElement
  document.addEventListener('keydown', onKey, true)
  await nextTick()
  const auto = root.value.querySelector('[data-autofocus]')
  ;(auto || root.value.querySelector(FOCUSABLE) || root.value).focus()
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey, true)
  if (prev && prev.focus && document.contains(prev)) prev.focus()
})
</script>
<template>
  <div class="backdrop" @pointerdown.self="closable && emit('close')">
    <div ref="root" class="modal panel" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1"
      :style="{ maxWidth: width + 'px' }">
      <header class="m-head">
        <h2>{{ title }}</h2>
        <button v-if="closable" class="btn ghost icon sm" :aria-label="t('common.close')" @click="emit('close')"><Icon name="close" /></button>
      </header>
      <div class="m-body"><slot /></div>
      <footer v-if="$slots.footer" class="m-foot"><slot name="footer" /></footer>
    </div>
  </div>
</template>
<style scoped>
.backdrop {
  position: fixed; inset: 0; z-index: var(--z-modal); display: grid; place-items: center; padding: var(--sp-6);
  background: var(--backdrop); animation: fade var(--dur) var(--ease);
}
.modal { width: 100%; max-height: calc(100vh - 2 * var(--sp-6)); display: flex; flex-direction: column; background: var(--surface); animation: pop var(--dur-pop) var(--ease); outline: none; box-shadow: var(--shadow); }
.m-head { display: flex; align-items: center; justify-content: space-between; padding: var(--sp-5) var(--sp-5) var(--sp-4) var(--sp-6); }
.m-head h2 { font-size: var(--fs-lg); }
.m-body { padding: var(--sp-2) var(--sp-6) var(--sp-6); overflow: auto; min-height: 0; }
.m-foot { display: flex; justify-content: flex-end; gap: var(--sp-4); padding: 10px var(--sp-6); border-top: 1px solid var(--border); }
@keyframes fade { from { opacity: 0 } }
@keyframes pop { from { opacity: 0; transform: translateY(8px) scale(.98) } }
</style>
