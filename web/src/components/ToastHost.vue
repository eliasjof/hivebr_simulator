<script setup>
import Icon from './Icon.vue'
import { store, dismissToast } from '../state/store.js'
import { t } from '../i18n/index.js'
</script>
<template>
  <div class="toasts" aria-live="polite" role="status">
    <div v-for="item in store.toasts" :key="item.id" class="toast panel float" :class="item.level">
      <Icon :name="item.level === 'info' ? 'info' : 'alert'" :size="15" />
      <span>{{ item.text }}</span>
      <button class="btn ghost icon sm" :aria-label="t('common.dismiss')" @click="dismissToast(item.id)"><Icon name="close" :size="12" /></button>
    </div>
  </div>
</template>
<style scoped>
.toasts { position: fixed; z-index: var(--z-toast); left: var(--sp-5); bottom: calc(var(--status-h) + var(--sp-5)); display: flex; flex-direction: column-reverse; gap: var(--sp-4); width: min(360px, calc(100vw - 2 * var(--sp-5))); pointer-events: none; }
.toast { display: flex; align-items: flex-start; gap: var(--sp-4); padding: var(--sp-4) var(--sp-4) var(--sp-4) var(--sp-5); pointer-events: auto; border-left: 3px solid var(--text-faint); animation: in var(--dur-toast) var(--ease); overflow-wrap: anywhere; }
.toast > span { flex: 1; }
.toast.warn { border-left-color: var(--warn); } .toast.error { border-left-color: var(--danger); }
.toast svg { margin-top: var(--sp-1); flex: none; }
@keyframes in { from { opacity: 0; transform: translateY(8px); } }
</style>
