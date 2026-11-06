<script setup>
import Icon from './Icon.vue'
import { store, dismissToast } from '../state/store.js'
</script>
<template>
  <div class="toasts" aria-live="polite" role="status">
    <div v-for="t in store.toasts" :key="t.id" class="toast panel" :class="t.level">
      <Icon :name="t.level === 'error' ? 'alert' : t.level === 'warn' ? 'alert' : 'info'" :size="15" />
      <span>{{ t.text }}</span>
      <button class="btn ghost icon sm" aria-label="Dispensar" @click="dismissToast(t.id)"><Icon name="close" :size="12" /></button>
    </div>
  </div>
</template>
<style scoped>
.toasts { position: fixed; z-index: var(--z-toast); left: 12px; bottom: 36px; display: flex; flex-direction: column-reverse; gap: 8px; width: min(360px, calc(100vw - 24px)); pointer-events: none; }
.toast { display: flex; align-items: flex-start; gap: 8px; padding: 8px 8px 8px 12px; pointer-events: auto; background: var(--surface-solid); border-left: 3px solid var(--text-faint); animation: in .2s var(--ease); overflow-wrap: anywhere; }
.toast > span { flex: 1; }
.toast.warn { border-left-color: var(--accent); } .toast.error { border-left-color: var(--danger); }
.toast svg { margin-top: 2px; flex: none; }
@keyframes in { from { opacity: 0; transform: translateY(8px); } }
</style>
