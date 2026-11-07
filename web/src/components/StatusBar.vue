<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { store, WINDOW_DEFS, openWindow } from '../state/store.js'
import { t, fmtNum, fmtInt } from '../i18n/index.js'
const minimized = computed(() => Object.keys(WINDOW_DEFS).filter((id) => store.windows[id].open && store.windows[id].minimized))
const py = computed(() => {
  const v = store.boot.version
  if (store.fatal) return t('status.py_error')
  if (store.run.state !== 'idle') return t('status.py_running', { v })
  if (!store.boot.ready) return t('status.py_loading', { pct: fmtInt(Math.round(store.boot.progress * 100)) })
  return t('status.py_ready', { v })
})
</script>
<template>
  <footer class="status mono" role="status" :aria-label="t('status.aria')">
    <span data-testid="st-cursor">x {{ fmtNum(store.cursor.x) }} · y {{ fmtNum(store.cursor.y) }}</span>
    <span data-testid="st-time">t {{ fmtNum(store.stats.t, 1) }} s</span>
    <span data-testid="st-step">{{ t('status.step') }} {{ fmtInt(store.stats.step) }}</span>
    <span data-testid="st-rtf">{{ t('status.rtf', { v: fmtNum(store.stats.rtf, 1) }) }}</span>
    <span>{{ fmtInt(store.stats.fps) }} fps</span>
    <span class="chips">
      <button v-for="id in minimized" :key="id" class="btn sm chipbtn" @click="openWindow(id)"><Icon :name="WINDOW_DEFS[id].icon" :size="12" />{{ t(WINDOW_DEFS[id].titleKey) }}</button>
    </span>
    <span class="py" :class="{ bad: store.fatal }">{{ py }}</span>
  </footer>
</template>
<style scoped>
.status { height: var(--status-h); display: flex; align-items: center; gap: 18px; padding: 0 var(--sp-5); background: var(--surface); border-top: 1px solid var(--border); font-size: var(--fs-label); color: var(--text-muted); overflow: hidden; white-space: nowrap; }
.chips { flex: 1; display: flex; gap: var(--sp-3); justify-content: center; min-width: 0; }
.chipbtn { min-height: var(--h-xs); border-radius: var(--radius-pill); font-size: var(--fs-xs); font-family: var(--font-ui); }
.py.bad { color: var(--danger); }
@media (max-width: 700px) { .status span:nth-child(3), .status span:nth-child(4), .status span:nth-child(5) { display: none; } }
</style>
