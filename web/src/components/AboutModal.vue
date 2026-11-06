<script setup>
import Modal from './Modal.vue'
import { store } from '../state/store.js'
</script>

<template>
  <Modal title="About hiveBr" :width="520" @close="store.modals.about = false">
    <section>
      <h3>hiveBr</h3>
      <p class="muted">Version 0.1.0</p>
      <p>A lightweight 2D simulation framework for single- and multi-robot mobile navigation.</p>
    </section>
    <section>
      <h3>Developers</h3>
      <ul>
        <li><strong>Elias J. R. Freitas</strong>   — IFMG - Campus Ibirité</li>
        <li><strong>Carlos D. S. Júnior</strong> — IFMG - Campus Ibirité</li>  
        <li><a href="https://github.com/eliasjof/hivebr_simulator" target="_blank" rel="noopener">GitHub</a></li>
      </ul>      
    </section>
    <section>
      <h3>Research Group</h3>
      <ul>
        <li><a href="https://epiibots.notion.site" target="_blank" rel="noopener">Robotics and Intelligent Systems - EPIIBOTS</a></li>
      </ul>
    </section>
    <section>
      <h3>Technologies</h3>
      <ul>
        <li>Vue 3 + Vite</li>
        <li>Pyodide</li>
        <li>Canvas 2D</li>
        <li>SharedArrayBuffer</li>
      </ul>
    </section>
    <section>
      <h3>License</h3>
      <p class="muted">MIT — see <code>LICENSE</code> in the project root.</p>
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