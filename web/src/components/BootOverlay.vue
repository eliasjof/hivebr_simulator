<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import Logo from './Logo.vue'
import { store } from '../state/store.js'
import { t, tOr, fmtInt } from '../i18n/index.js'

const showBoot = computed(() => !store.boot.ready && !store.fatal && !store.boot.dismissed && store.run.state === 'idle')
const showWarn = computed(() => store.boot.ready && !store.interactive && !store.warnDismissed)
const pct = computed(() => Math.round(store.boot.progress * 100))
const stage = computed(() => tOr('boot.stage.' + store.boot.stage, null, t('boot.stage.init')))
</script>
<template>
  <div class="stack">
    <div v-if="showBoot" class="card panel" role="status" aria-live="polite">
      <div class="head"><Logo :size="26" /><div><b>{{ t('boot.title') }}</b><div class="faint small">{{ t('boot.subtitle') }}</div></div>
        <button class="btn ghost icon sm" :aria-label="t('common.hide')" @click="store.boot.dismissed = true"><Icon name="close" :size="13" /></button></div>
      <div class="track" role="progressbar" :aria-valuenow="pct" aria-valuemin="0" aria-valuemax="100" :aria-label="t('boot.title')"><i :style="{ width: pct + '%' }" /></div>
      <div class="line"><span>{{ stage }}<span v-if="store.boot.detail" class="faint mono detail"> · {{ store.boot.detail }}</span></span><span class="mono">{{ fmtInt(pct) }}%</span></div>
    </div>
    <div v-if="showWarn" class="card warn panel" role="alert">
      <div class="head"><Icon name="alert" :size="18" />
        <div><b>{{ t('limited.title') }}</b>
          <div class="small">{{ t('limited.body_before') }}<span class="mono">crossOriginIsolated</span>{{ t('limited.body_after') }}</div></div>
        <button class="btn ghost icon sm" :aria-label="t('common.dismiss')" @click="store.warnDismissed = true"><Icon name="close" :size="13" /></button></div>
    </div>
  </div>
</template>
<style scoped>
.stack { position: fixed; bottom: calc(var(--status-h) + var(--sp-5)); left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: var(--sp-4); width: min(440px, calc(100vw - 2 * var(--sp-5))); z-index: var(--z-banner); pointer-events: none; }
.stack > * { pointer-events: auto; }
.card { padding: var(--sp-5) 14px; box-shadow: var(--shadow); }
.head { display: flex; gap: 10px; align-items: flex-start; }
.head > div { flex: 1; }
.small { font-size: var(--fs-sm); line-height: 1.45; color: var(--text-muted); }
.track { height: 6px; background: var(--surface-3); border-radius: var(--radius-xs); margin: 10px 0 var(--sp-3); overflow: hidden; }
.track i { display: block; height: 100%; background: var(--accent); transition: width var(--dur-slow) var(--ease); }
.line { display: flex; justify-content: space-between; gap: var(--sp-4); font-size: var(--fs-sm); color: var(--text-muted); }
.detail { overflow-wrap: anywhere; }
.warn { border-color: var(--warn); }
.warn svg { color: var(--warn); flex: none; }
</style>
