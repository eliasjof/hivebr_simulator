<script setup>
import Modal from './Modal.vue'
import { store, runDemo } from '../state/store.js'
import { t } from '../i18n/index.js'

// [tecla, chave da descrição]
const keys = [
  ['Ctrl/Cmd + Enter', 'help.k_run'], ['Ctrl/Cmd + S', 'help.k_save'], ['key.space', 'help.k_toggle'], ['.', 'help.k_step'],
  ['Shift + R', 'help.k_reset'], ['V W O R M D', 'help.k_tools'], ['1 – 9', 'help.k_select'], ['F', 'help.k_fit'], ['+ / −', 'help.k_zoom'],
  ['E', 'help.k_editor'], ['C', 'help.k_console'], ['B', 'help.k_telemetry'], ['P / G / K', 'help.k_windows'], ['T', 'help.k_theme'],
  ['Esc', 'help.k_esc'], ['?', 'help.k_help'], ['help.k_shift_click', 'help.k_waypoint_orient'], ['help.k_right_click', 'help.k_context'],
  ['help.k_space_drag', 'help.k_pan'],
]
const keyLabel = (k) => (k.startsWith('key.') || k.startsWith('help.') ? t(k) : k)
</script>
<template>
  <Modal :title="t('help.title')" :width="760" @close="store.modals.help = false">
    <section>
      <h3>{{ t('help.quick') }}</h3>
      <ol>
        <li>{{ t('help.q1_a') }}<b>{{ t('toolbar.examples') }}</b>{{ t('help.q1_b') }}<b>{{ t('view.code') }}</b>{{ t('help.q1_c') }}</li>
        <li>{{ t('help.q2_a') }}<kbd>Ctrl</kbd>+<kbd>Enter</kbd>{{ t('help.q2_b') }}</li>
        <li>{{ t('help.q3') }}</li>
        <li>{{ t('help.q4_a') }}<b>{{ t('dock.console') }}</b>{{ t('help.q4_b') }}<b>{{ t('dock.telemetry') }}</b>{{ t('help.q4_c') }}<b>{{ t('win.plots') }}</b>{{ t('help.q4_d') }}</li>
      </ol>
      <button class="btn sm" @click="store.modals.help = false; runDemo()">{{ t('help.see_demo') }}</button>
    </section>
    <section>
      <h3>{{ t('help.api') }}</h3>
      <dl class="api">
        <dt class="mono">HiveBrAgent</dt><dd>{{ t('help.api_agent_a') }}<code class="mono">step(obs)</code>{{ t('help.api_agent_b') }}</dd>
        <dt class="mono">SwarmController</dt><dd>{{ t('help.api_controller') }}</dd>
        <dt class="mono">SwarmExperiment</dt><dd>{{ t('help.api_experiment_a') }}<code class="mono">exp.run()</code>{{ t('help.api_experiment_b') }}</dd>
        <dt class="mono">Simulator</dt><dd>{{ t('help.api_simulator_a') }}<code class="mono">sim.run()</code>{{ t('help.api_simulator_b') }}</dd>
      </dl>
    </section>
    <section>
      <h3>{{ t('help.shortcuts') }}</h3>
      <table class="keys"><tbody><tr v-for="[k, d] in keys" :key="k"><td><kbd>{{ keyLabel(k) }}</kbd></td><td>{{ t(d) }}</td></tr></tbody></table>
    </section>
    <section>
      <h3>{{ t('help.language') }}</h3>
      <p class="para">{{ t('help.language_body') }}</p>
      <p class="para">{{ t('help.language_limit') }}</p>
    </section>
    <section>
      <h3>{{ t('help.diff') }}</h3>
      <ul>
        <li>{{ t('help.d1_a') }}<b>multiprocessing</b>{{ t('help.d1_b') }}</li>
        <li>{{ t('help.d2') }}</li>
        <li>{{ t('help.d3_a') }}<span class="mono">crossOriginIsolated</span>{{ t('help.d3_b') }}</li>
        <li>{{ t('help.d4') }}</li>
        <li>{{ t('help.d5') }}</li>
      </ul>
    </section>
  </Modal>
</template>
<style scoped>
section { margin-bottom: 18px; } h3 { font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-bottom: var(--sp-4); }
ol, ul { margin: 0 0 10px; padding-left: 20px; line-height: 1.6; }
.para { margin: 0 0 var(--sp-4); line-height: 1.6; color: var(--text-muted); }
.api { display: grid; grid-template-columns: max-content 1fr; gap: var(--sp-3) var(--sp-6); margin: 0; } .api dd { margin: 0; color: var(--text-muted); }
.keys { border-collapse: collapse; width: 100%; } .keys td { padding: var(--sp-2) var(--sp-4) var(--sp-2) 0; border-bottom: 1px solid var(--border); vertical-align: top; } .keys td:first-child { white-space: nowrap; width: 1%; }
</style>
