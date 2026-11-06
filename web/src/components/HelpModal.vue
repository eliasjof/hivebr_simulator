<script setup>
import Modal from './Modal.vue'
import { store, runDemo } from '../state/store.js'
const keys = [
  ['Ctrl/Cmd + Enter', 'Executar o código'], ['Ctrl/Cmd + S', 'Salvar no navegador'], ['Espaço', 'Iniciar / pausar a simulação'],
  ['.', 'Avançar um passo'], ['Shift + R', 'Reiniciar a simulação'], ['V W O R M D', 'Selecionar, Waypoint, Obstáculo, Recarga, Mover, Desenhar pista'],
  ['1 – 9', 'Selecionar robô'], ['F', 'Enquadrar a cena'], ['+ / −', 'Aproximar / afastar'], ['E', 'Focar o editor'], ['C', 'Console'], ['B', 'Telemetria'],
  ['P / G / K', 'Parâmetros / Gráficos / Mapa'], ['T', 'Alternar tema'], ['Esc', 'Voltar à ferramenta Selecionar / fechar'], ['?', 'Esta ajuda'],
  ['Shift + clique', 'Waypoint com orientação'], ['Botão direito', 'Menu de contexto na cena'], ['Espaço + arrastar / botão do meio', 'Mover a câmera'],
]
</script>
<template>
  <Modal title="Ajuda" :width="760" @close="store.modals.help = false">
    <section>
      <h3>Início rápido</h3>
      <ol>
        <li>Escolha um exemplo em <b>Exemplos</b> ou escreva seu código no painel <b>Código</b>.</li>
        <li>Pressione <kbd>Ctrl</kbd>+<kbd>Enter</kbd> para executar. O Python (Pyodide) roda no seu navegador, sem servidor.</li>
        <li>Use as ferramentas da barra para adicionar waypoints, obstáculos e estações de recarga com o mouse.</li>
        <li>Veja saídas no <b>Console</b>, o estado dos robôs em <b>Telemetria</b> e os sinais em <b>Gráficos</b>.</li>
      </ol>
      <button class="btn sm" @click="store.modals.help = false; runDemo()">Ver demonstração</button>
    </section>
    <section>
      <h3>API em resumo</h3>
      <dl class="api">
        <dt class="mono">HiveBrAgent</dt><dd>Classe base de um robô: implemente <code class="mono">step(obs)</code> para devolver comandos de velocidade.</dd>
        <dt class="mono">SwarmController</dt><dd>Coordena vários agentes de uma vez, com acesso ao estado do enxame.</dd>
        <dt class="mono">SwarmExperiment</dt><dd>Monta cena, robôs e controlador; <code class="mono">exp.run()</code> bloqueia até a simulação parar.</dd>
        <dt class="mono">Simulator</dt><dd>Núcleo da simulação: mundo, robôs, LiDAR, obstáculos e waypoints; <code class="mono">sim.run()</code> bloqueia até parar.</dd>
      </dl>
    </section>
    <section>
      <h3>Atalhos</h3>
      <table class="keys"><tbody><tr v-for="[k, d] in keys" :key="k"><td><kbd>{{ k }}</kbd></td><td>{{ d }}</td></tr></tbody></table>
    </section>
    <section>
      <h3>Diferenças em relação à versão desktop</h3>
      <ul>
        <li>Não há <b>multiprocessing</b> nem threads reais; tudo roda em um único worker.</li>
        <li>Não há janela pygame: a cena é desenhada em canvas e controlada por esta interface.</li>
        <li>Comandos ao vivo (pausar, waypoints, parâmetros) exigem <span class="mono">crossOriginIsolated</span>; sem ele aparece um aviso de modo limitado.</li>
        <li>Arquivos gerados (CSV, PKL, YAML) são baixados pelo navegador; figuras do matplotlib vão para a aba Figuras.</li>
        <li>O Python é carregado de um CDN na primeira visita e precisa de conexão.</li>
      </ul>
    </section>
  </Modal>
</template>
<style scoped>
section { margin-bottom: 18px; } h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-bottom: 8px; }
ol, ul { margin: 0 0 10px; padding-left: 20px; line-height: 1.6; }
.api { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; } .api dd { margin: 0; color: var(--text-muted); }
.keys { border-collapse: collapse; width: 100%; } .keys td { padding: 4px 8px 4px 0; border-bottom: 1px solid var(--border); vertical-align: top; } .keys td:first-child { white-space: nowrap; width: 1%; }
</style>
