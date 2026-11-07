<script setup>
import Modal from './Modal.vue'
import { store } from '../state/store.js'
import { t } from '../i18n/index.js'
</script>

<template>
  <Modal :title="t('about.title')" :width="520" @close="store.modals.about = false">
    <section>
      <h3>hiveBr</h3>
      <p class="muted">{{ t('about.version') }}</p>
      <p>{{ t('about.desc') }}</p>
    </section>
    <section>
      <h3>{{ t('about.developers') }}</h3>
      <ul>
        <li><strong>{{ t('about.dev1') }}</strong></li>
        <li><strong>{{ t('about.dev2') }}</strong></li>
        <li><a href="https://github.com/eliasjof/hivebr_simulator" target="_blank" rel="noopener">GitHub</a></li>
      </ul>
    </section>
    <section>
      <h3>{{ t('about.research') }}</h3>
      <ul>
        <li><a href="https://epiibots.notion.site" target="_blank" rel="noopener">{{ t('about.research_name') }}</a></li>
      </ul>
    </section>
    <section>
      <h3>{{ t('about.tech') }}</h3>
      <ul>
        <li>Vue 3 + Vite</li>
        <li>Pyodide</li>
        <li>Canvas 2D</li>
        <li>SharedArrayBuffer</li>
      </ul>
    </section>
    <section>
      <h3>{{ t('about.license') }}</h3>
      <p class="muted">{{ t('about.license_text') }}</p>
    </section>
  </Modal>
</template>

<style scoped>
section { margin-bottom: 14px; }
h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-bottom: 6px; }
ul { margin: 0; padding-left: 20px; line-height: 1.7; }
.muted { color: var(--text-muted); font-size: 13px; }
a { color: var(--accent); }
</style>
