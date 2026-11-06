<script setup>
import Modal from './Modal.vue'
import { store } from '../state/store.js'
import { t } from '../i18n/index.js'
function reload() { window.location.reload() }
</script>
<template>
  <Modal :title="t('fatal.title')" :closable="false" :width="520" @close="() => {}">
    <p class="m">{{ t('fatal.body') }}</p>
    <pre class="mono err">{{ store.fatal }}</pre>
    <template #footer><button class="btn primary" data-autofocus @click="reload">{{ t('fatal.reload') }}</button></template>
  </Modal>
</template>
<style scoped>
.m { margin: 0 0 var(--sp-5); color: var(--text-muted); line-height: 1.5; }
.err { background: var(--danger-soft); padding: 10px; border-radius: var(--radius-sm); max-height: 200px; overflow: auto; white-space: pre-wrap; font-size: var(--fs-sm); margin: 0; }
</style>
