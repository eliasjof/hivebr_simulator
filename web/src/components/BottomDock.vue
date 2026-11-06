<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import ConsolePanel from './ConsolePanel.vue'
import RobotsPanel from './RobotsPanel.vue'
import ProblemsPanel from './ProblemsPanel.vue'
import { store, openWindow, closeWindow } from '../state/store.js'

const tabs = [['console', 'Console'], ['telemetry', 'Telemetria'], ['problems', 'Problemas']]
const detached = computed(() => store.windows.robots.open)
function pick(id) { store.layout.bottomTab = id; store.layout.bottomOpen = true }
function detach() { openWindow('robots'); store.layout.bottomTab = 'console' }
</script>
<template>
  <section class="dock" aria-label="Painel inferior">
    <div class="tabs" role="tablist">
      <button v-for="[id, l] in tabs" :key="id" class="tab" role="tab" :aria-selected="store.layout.bottomOpen && store.layout.bottomTab === id" @click="pick(id)">
        {{ l }}<span v-if="id === 'problems' && store.error" class="badge">1</span>
      </button>
      <div class="sp" />
      <button v-if="store.layout.bottomTab === 'telemetry' && !detached" class="btn ghost sm" data-tip="Destacar em janela" data-tip-pos="end" @click="detach"><Icon name="max" :size="13" />Destacar</button>
      <button class="btn ghost icon sm" :aria-label="store.layout.bottomOpen ? 'Recolher painel' : 'Expandir painel'" :data-tip="store.layout.bottomOpen ? 'Recolher' : 'Expandir'" data-tip-pos="end"
        @click="store.layout.bottomOpen = !store.layout.bottomOpen"><Icon :name="store.layout.bottomOpen ? 'chevronDown' : 'chevron'" :size="14" /></button>
    </div>
    <div v-show="store.layout.bottomOpen" class="body">
      <ConsolePanel v-show="store.layout.bottomTab === 'console'" />
      <template v-if="store.layout.bottomTab === 'telemetry'">
        <div v-if="detached" class="det faint">Telemetria aberta em janela flutuante. <button class="btn link" @click="closeWindow('robots')">Acoplar aqui</button></div>
        <RobotsPanel v-else />
      </template>
      <ProblemsPanel v-show="store.layout.bottomTab === 'problems'" />
    </div>
  </section>
</template>
<style scoped>
.dock { display: flex; flex-direction: column; min-height: 0; height: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); }
.tabs { flex: none; height: 32px; align-items: stretch; padding: 0 6px; }
.tabs .btn { align-self: center; }
.tab { position: relative; }
.sp { flex: 1; }
.body { flex: 1; min-height: 0; display: flex; flex-direction: column; container-type: inline-size; }
.badge { margin-left: 6px; background: var(--danger); color: #fff; font-size: 10px; border-radius: 99px; padding: 0 5px; }
.det { padding: 14px; }
</style>
