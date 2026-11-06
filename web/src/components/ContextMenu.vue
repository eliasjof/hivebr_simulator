<script setup>
import { computed, onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import Icon from './Icon.vue'
import { store, send, latestFrame } from '../state/store.js'
import { t, fmtNum } from '../i18n/index.js'

const c = computed(() => store.ctx)
const el = ref(null)
const pos = ref({ left: 0, top: 0 })
const sel = computed(() => store.selected)

function close() { store.ctx = null }
const items = computed(() => {
  const m = c.value
  if (!m) return []
  const list = [
    { icon: 'waypoint', label: t('ctx.waypoint', { n: sel.value + 1 }), run: () => send({ cmd: 'add_waypoint', robot: sel.value, x: m.x, y: m.y }) },
    { icon: 'obstacle', label: t('ctx.obstacle'), run: () => send({ cmd: 'add_obstacle', x: m.x, y: m.y, r: store.obstacleRadius }) },
    { icon: 'bolt', label: t('ctx.recharge'), run: () => send({ cmd: 'add_recharge', x: m.x, y: m.y }) },
    { icon: 'move', label: t('ctx.move', { n: sel.value + 1 }), run: () => {
      const th = latestFrame()?.robots?.[sel.value]?.theta ?? 0
      send({ cmd: 'set_pose', robot: sel.value, x: m.x, y: m.y, theta: th })
    } },
  ]
  const h = m.hit
  if (h?.type === 'obstacle') list.push({ icon: 'trash', danger: true, label: t('ctx.remove_obstacle'), run: () => send({ cmd: 'remove_obstacle', index: h.index }) })
  if (h?.type === 'waypoint') list.push({ icon: 'trash', danger: true, label: t('ctx.remove_waypoint'), run: () => send({ cmd: 'remove_waypoint', robot: h.robot, index: h.index }) })
  if (h?.type === 'recharge') list.push({ icon: 'trash', danger: true, label: t('ctx.remove_recharge'), run: () => send({ cmd: 'remove_recharge', index: h.index }) })
  return list
})
function pick(it) { it.run(); close() }
function onDoc(e) { if (c.value && !el.value?.contains(e.target)) close() }
function onKey(e) { if (e.key === 'Escape' && c.value) { close(); e.stopPropagation() } }
onMounted(() => { document.addEventListener('pointerdown', onDoc, true); document.addEventListener('keydown', onKey, true); window.addEventListener('blur', close) })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', onDoc, true); document.removeEventListener('keydown', onKey, true); window.removeEventListener('blur', close) })
import { watch } from 'vue'
watch(c, async (m) => {
  if (!m) return
  pos.value = { left: m.screenX, top: m.screenY }
  await nextTick()
  const r = el.value?.getBoundingClientRect()
  if (!r) return
  pos.value = {
    left: Math.max(4, Math.min(m.screenX, window.innerWidth - r.width - 4)),
    top: Math.max(4, Math.min(m.screenY, window.innerHeight - r.height - 4)),
  }
  el.value.querySelector('button')?.focus()
})
</script>
<template>
  <div v-if="c" ref="el" class="ctx panel" role="menu" :aria-label="t('ctx.aria')" :style="{ left: pos.left + 'px', top: pos.top + 'px' }" @contextmenu.prevent>
    <div class="coord mono faint">x {{ fmtNum(c.x) }} · y {{ fmtNum(c.y) }}</div>
    <button v-for="it in items" :key="it.label" class="btn ghost it" :class="{ danger: it.danger }" role="menuitem" @click="pick(it)">
      <Icon :name="it.icon" :size="14" />{{ it.label }}</button>
  </div>
</template>
<style scoped>
.ctx { position: fixed; z-index: var(--z-ctx); min-width: 240px; padding: var(--sp-2); display: flex; flex-direction: column; box-shadow: var(--shadow); }
.coord { font-size: var(--fs-xs); padding: var(--sp-2) var(--sp-4) var(--sp-3); border-bottom: 1px solid var(--border); margin-bottom: var(--sp-2); }
.it { justify-content: flex-start; text-align: left; min-height: var(--h-md); border-radius: var(--radius-sm); }
</style>
