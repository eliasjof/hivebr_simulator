<script setup>
import Modal from './Modal.vue'
import { store } from '../state/store.js'
</script>
<template>
  <Modal title="Não foi possível iniciar o Python" :closable="false" :width="520" @close="() => {}">
    <p class="m">O ambiente de simulação falhou ao carregar. Verifique sua conexão com a internet (o Python é baixado de um CDN) e tente novamente.</p>
    <pre class="mono err">{{ store.fatal }}</pre>
    <template #footer><button class="btn primary" data-autofocus @click="location.reload()">Recarregar a página</button></template>
  </Modal>
</template>
<script>
export default { computed: {}, data: () => ({ location: window.location }) }
</script>
<style scoped>
.m { margin: 0 0 10px; color: var(--text-muted); line-height: 1.5; }
.err { background: var(--danger-soft); padding: 10px; border-radius: 6px; max-height: 200px; overflow: auto; white-space: pre-wrap; font-size: 12px; margin: 0; }
</style>
