<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { store, WINDOW_DEFS, openWindow } from '../state/store.js'
const f = (v, d = 2) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d))
const minimized = computed(() => Object.keys(WINDOW_DEFS).filter((id) => store.windows[id].open && store.windows[id].minimized))
const py = computed(() => {
  if (store.fatal) return 'Python: erro'
  if (store.run.state !== 'idle') return 'Python ' + (store.boot.version || '') + ' · executando'
  if (!store.boot.ready) return `Python: carregando ${Math.round(store.boot.progress * 100)}%`
  return 'Python ' + (store.boot.version || 'pronto')
})
</script>
<template>
  <footer class="status mono" role="status" aria-label="Estado da simulação">
    <span data-testid="st-cursor">x {{ f(store.cursor.x) }} · y {{ f(store.cursor.y) }}</span>
    <span data-testid="st-time">t {{ f(store.stats.t, 1) }} s</span>
    <span data-testid="st-step">passo {{ store.stats.step }}</span>
    <span data-testid="st-rtf">{{ f(store.stats.rtf, 1) }}× tempo real</span>
    <span>{{ store.stats.fps }} fps</span>
    <span class="chips">
      <button v-for="id in minimized" :key="id" class="btn sm chipbtn" @click="openWindow(id)"><Icon :name="WINDOW_DEFS[id].icon" :size="12" />{{ WINDOW_DEFS[id].title }}</button>
    </span>
    <span class="py" :class="{ bad: store.fatal }">{{ py }}</span>
  </footer>
</template>
<style scoped>
.status { height: var(--status-h); display: flex; align-items: center; gap: 18px; padding: 0 12px; background: var(--surface); border-top: 1px solid var(--border); font-size: 11.5px; color: var(--text-muted); overflow: hidden; white-space: nowrap; }
.chips { flex: 1; display: flex; gap: 6px; justify-content: center; }
.chipbtn { min-height: 20px; border-radius: 99px; font-size: 11px; font-family: var(--font-ui); }
.py.bad { color: var(--danger); }
@media (max-width: 700px) { .status span:nth-child(3), .status span:nth-child(4), .status span:nth-child(5) { display: none; } }
</style>
