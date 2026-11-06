<script setup>
import Icon from './Icon.vue'
import { store, gotoLine } from '../state/store.js'
</script>
<template>
  <div class="pane">
    <div v-if="!store.error" class="empty faint"><Icon name="check" :size="16" />Nenhum problema. Erros de execução do Python aparecem aqui.</div>
    <div v-else class="prob">
      <button class="head" :disabled="!store.error.line" @click="gotoLine(store.error.line)">
        <Icon name="alert" :size="15" />
        <b class="mono">{{ store.error.type }}</b><span>{{ store.error.message }}</span>
        <span v-if="store.error.line" class="mono link">linha {{ store.error.line }}</span>
      </button>
      <pre v-if="store.error.traceback" class="tb mono">{{ store.error.traceback }}</pre>
    </div>
  </div>
</template>
<style scoped>
.pane { flex: 1; min-height: 0; overflow: auto; }
.empty { display: flex; gap: 8px; align-items: center; padding: 14px; }
.prob { display: flex; flex-direction: column; }
.head { display: flex; gap: 8px; align-items: center; text-align: left; padding: 8px 12px; background: var(--danger-soft); border: none; border-bottom: 1px solid var(--border); }
.head svg { color: var(--danger); flex: none; }
.head:not(:disabled):hover { background: var(--surface-3); }
.link { margin-left: auto; color: var(--accent); }
.tb { margin: 0; padding: 8px 12px; font-size: 12px; white-space: pre-wrap; color: var(--text-muted); user-select: text; }
</style>
