<script setup>
import Logo from './Logo.vue'
import { store } from '../state/store.js'
</script>
<template>
  <div v-if="!store.hasRun" class="hint" aria-hidden="false">
    <Logo :size="44" />
    <p>Pressione <b>Executar</b> (<kbd>Ctrl</kbd>+<kbd>Enter</kbd>) para criar a simulação.</p>
    <p class="faint">O código do editor controla os robôs; eles aparecem aqui.</p>
  </div>
</template>
<style scoped>
.hint { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; pointer-events: none; text-align: center; padding: 20px; }
.hint svg { opacity: .5; margin-bottom: 8px; }
.hint p { margin: 0; color: var(--text-muted); font-size: 14px; }
.hint p.faint { font-size: 12.5px; color: var(--text-faint); }
</style>
