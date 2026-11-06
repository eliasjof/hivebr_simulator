<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import Logo from './Logo.vue'
import { store } from '../state/store.js'

const stages = [
  ['init', 'Iniciar'], ['pyodide', 'Carregar Python'], ['packages', 'Pacotes'], ['hivebr', 'hiveBr'],
]
const showBoot = computed(() => !store.boot.ready && !store.fatal && !store.boot.dismissed && store.run.state === 'idle')
const showWarn = computed(() => store.boot.ready && !store.interactive && !store.warnDismissed)
const pct = computed(() => Math.round(store.boot.progress * 100))
</script>
<template>
  <div class="stack">
    <div v-if="showBoot" class="card panel" role="status" aria-live="polite">
      <div class="head"><Logo :size="26" /><div><b>Preparando o ambiente Python</b><div class="faint small">Você já pode escrever seu código enquanto carrega.</div></div>
        <button class="btn ghost icon sm" aria-label="Ocultar" @click="store.boot.dismissed = true"><Icon name="close" :size="13" /></button></div>
      <div class="track" role="progressbar" :aria-valuenow="pct" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: pct + '%' }" /></div>
      <div class="line"><span>{{ store.boot.text }}</span><span class="mono">{{ pct }}%</span></div>
    </div>
    <div v-if="showWarn" class="card warn panel" role="alert">
      <div class="head"><Icon name="alert" :size="18" />
        <div><b>Modo limitado: comandos ao vivo indisponíveis</b>
          <div class="small">Este navegador não está com isolamento de origem (<span class="mono">crossOriginIsolated</span>) ativo. A simulação roda, mas ferramentas interativas durante a execução (pausar, adicionar waypoints, parâmetros) não funcionam e Parar reinicia o interpretador. Recarregue a página uma vez ou sirva o site com os cabeçalhos COOP/COEP.</div></div>
        <button class="btn ghost icon sm" aria-label="Dispensar aviso" @click="store.warnDismissed = true"><Icon name="close" :size="13" /></button></div>
    </div>
  </div>
</template>
<style scoped>
.stack { position: fixed; bottom: 36px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: 8px; width: min(440px, calc(100vw - 24px)); z-index: 6000; pointer-events: none; }
.stack > * { pointer-events: auto; }
.card { padding: 12px 14px; background: var(--surface-solid); }
.head { display: flex; gap: 10px; align-items: flex-start; }
.head > div { flex: 1; }
.small { font-size: 12px; line-height: 1.45; color: var(--text-muted); }
.track { height: 6px; background: var(--surface-3); border-radius: 3px; margin: 10px 0 6px; overflow: hidden; }
.track i { display: block; height: 100%; background: var(--accent); transition: width .3s var(--ease); }
.line { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); }
.warn { border-color: var(--accent); }
.warn svg { color: var(--accent); flex: none; }
</style>
