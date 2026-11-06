<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import ConsolePanel from './ConsolePanel.vue'
import RobotsPanel from './RobotsPanel.vue'
import ProblemsPanel from './ProblemsPanel.vue'
import { store, openWindow, closeWindow } from '../state/store.js'
import { t } from '../i18n/index.js'

const tabs = [['console', 'dock.console'], ['telemetry', 'dock.telemetry'], ['problems', 'dock.problems']]
const detached = computed(() => store.windows.robots.open)
function pick(id) { store.layout.bottomTab = id; store.layout.bottomOpen = true }
function detach() { openWindow('robots'); store.layout.bottomTab = 'console' }
</script>
<template>
  <section class="dock" :aria-label="t('dock.aria')">
    <div class="tabs" role="tablist">
      <button v-for="[id, key] in tabs" :key="id" class="tab" role="tab" :aria-selected="store.layout.bottomOpen && store.layout.bottomTab === id" @click="pick(id)">
        {{ t(key) }}<span v-if="id === 'problems' && store.error" class="badge">1</span>
      </button>
      <div class="sp" />
      <button v-if="store.layout.bottomTab === 'telemetry' && !detached" class="btn ghost sm" :data-tip="t('dock.detach_tip')" data-tip-pos="end" @click="detach"><Icon name="max" :size="13" />{{ t('dock.detach') }}</button>
      <button class="btn ghost icon sm" :aria-label="store.layout.bottomOpen ? t('dock.collapse') : t('dock.expand')" :data-tip="store.layout.bottomOpen ? t('dock.collapse') : t('dock.expand')" data-tip-pos="end"
        @click="store.layout.bottomOpen = !store.layout.bottomOpen"><Icon :name="store.layout.bottomOpen ? 'chevronDown' : 'chevron'" :size="14" /></button>
    </div>
    <div v-show="store.layout.bottomOpen" class="body">
      <ConsolePanel v-show="store.layout.bottomTab === 'console'" />
      <template v-if="store.layout.bottomTab === 'telemetry'">
        <div v-if="detached" class="det faint">{{ t('dock.detached') }} <button class="btn link" @click="closeWindow('robots')">{{ t('dock.dock_here') }}</button></div>
        <RobotsPanel v-else />
      </template>
      <ProblemsPanel v-show="store.layout.bottomTab === 'problems'" />
    </div>
  </section>
</template>
<style scoped>
.dock { display: flex; flex-direction: column; min-height: 0; height: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); }
.tabs { flex: none; height: var(--tabs-h); align-items: stretch; padding: 0 var(--sp-3); }
.tabs .btn { align-self: center; }
.tab { position: relative; }
.sp { flex: 1; }
.body { flex: 1; min-height: 0; display: flex; flex-direction: column; container-type: inline-size; }
.badge { margin-left: var(--sp-3); background: var(--danger); color: var(--on-solid); font-size: var(--fs-2xs); border-radius: var(--radius-pill); padding: 0 5px; }
.det { padding: var(--sp-5); }
</style>
