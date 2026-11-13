<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import Logo from './Logo.vue'
import {
  store, scene, catalog, newFile, pickFile, downloadScript, saveNow, runCode, stopCode, toggleSim, stepOnce, resetSim,
  restartScene, restartPage, clearSiteData,
  toggleTheme, togglePanel, openPanel, toggleWindow, resetLayout, runDemo, loadExample, canvasRef, consoleBus, toast,
  toggleReportTemplateModal, toggleReportsPanel,
} from '../state/store.js'
import { t, choice, setChoice, fmtInt } from '../i18n/index.js'

const open = ref(null)   // id do menu aberto
const sub = ref(null)    // índice do submenu aberto dentro do menu atual
const root = ref(null)
const idle = computed(() => store.run.state === 'idle')
const live = computed(() => store.run.state === 'running')
const examples = computed(() => catalog.value.filter((e) => e.id !== 'demonstracao'))

const menus = computed(() => [
  { id: 'file', label: t('menu.file'), items: [
    { label: t('file.new'), key: 'Ctrl+Alt+N', run: newFile },
    { label: t('file.new_report'), key: 'Ctrl+Shift+R', run: toggleReportTemplateModal },
    { sep: true },
    { label: t('file.open'), key: 'Ctrl+O', run: pickFile },
    { label: t('file.save_browser'), key: 'Ctrl+S', run: () => { saveNow(); toast(t('toast.saved')) } },
    { label: t('file.download'), run: downloadScript },
    { sep: true },
    { label: t('file.clear_cache'), run: clearSiteData },
    { sep: true },
    { label: t('lang.menu'), submenu: [
      { label: t('lang.auto'), radio: choice.value === 'auto', run: () => setChoice('auto') },
      { label: t('lang.pt'), radio: choice.value === 'pt-BR', run: () => setChoice('pt-BR') },
      { label: t('lang.en'), radio: choice.value === 'en', run: () => setChoice('en') },
    ] },
  ] },
  { id: 'edit', label: t('menu.edit'), items: [
    { label: t('edit.undo'), key: 'Ctrl+Z', run: () => store.editorApi?.undo(), disabled: !store.editorApi },
    { label: t('edit.redo'), key: 'Ctrl+Shift+Z', run: () => store.editorApi?.redo(), disabled: !store.editorApi },
    { sep: true },
    { label: t('edit.clear_console'), run: () => consoleBus.clear() },
  ] },
  { id: 'view', label: t('menu.view'), items: [
    { label: t('nav.title'), check: store.layout.leftOpen, run: () => togglePanel('left') },
    { label: t('view.code'), key: 'E', check: store.layout.rightOpen, run: () => togglePanel('right') },
    { label: t('view.reports'), check: store.layout.reportsOpen, run: toggleReportsPanel },
    { label: t('view.bottom'), check: store.layout.bottomOpen, run: () => { store.layout.bottomOpen = !store.layout.bottomOpen } },
    { sep: true },
    { label: t('dock.console'), key: 'C', run: () => openPanel('bottom', 'console') },
    { label: t('dock.telemetry'), key: 'B', run: () => openPanel('bottom', 'telemetry') },
    { label: t('win.params'), key: 'P', check: store.windows.params.open, run: () => toggleWindow('params') },
    { label: t('win.plots'), key: 'G', check: store.windows.plots.open, run: () => toggleWindow('plots') },
    { label: t('win.map'), key: 'K', check: store.windows.map.open, run: () => toggleWindow('map') },
    { sep: true },
    { label: t('view.fit'), key: 'F', run: () => canvasRef.value?.fit() },
    { label: store.theme === 'dark' ? t('view.theme_light') : t('view.theme_dark'), key: 'T', run: toggleTheme },
    { label: t('view.reset_layout'), run: resetLayout },
  ] },
  { id: 'sim', label: t('menu.sim'), items: [
    { label: t('sim.run_code'), key: 'Ctrl+Enter', run: runCode, disabled: !idle.value || !store.boot.ready },
    { label: t('sim.stop'), run: stopCode, disabled: !live.value },
    { label: store.stats.running ? t('sim.pause_sim') : t('sim.start'), key: t('key.space'), run: toggleSim, disabled: !live.value },
    { label: t('sim.step_menu'), key: '.', run: stepOnce, disabled: !live.value },
    { label: t('sim.reset'), key: 'Shift+R', run: resetSim, disabled: !live.value },
    { sep: true },
    { label: t('sim.restart_scene'), run: restartScene, disabled: !store.boot.ready || !idle.value },
    { label: t('sim.restart_page'), run: restartPage },
    { sep: true },
    { label: t('toolbar.demo'), run: runDemo },
  ] },
  { id: 'ex', label: t('menu.examples'), items: [
    { label: t('examples.gallery'), run: () => { store.modals.examples = true } },
    { label: t('toolbar.demo'), run: runDemo },
    { sep: true },
    ...examples.value.map((e) => ({ label: e.title, run: () => loadExample(e) })),
  ] },
  { id: 'help', label: t('menu.help'), items: [
    { label: t('help.guide'), key: '?', run: () => { store.modals.help = true } },
    { label: t('help.about'), run: () => { store.modals.about = true } },
    { label: t('toolbar.demo'), run: runDemo },
    { sep: true },
    { label: t('lang.menu'), submenu: [
      { label: t('lang.auto'), radio: choice.value === 'auto', run: () => setChoice('auto') },
      { label: t('lang.pt'), radio: choice.value === 'pt-BR', run: () => setChoice('pt-BR') },
      { label: t('lang.en'), radio: choice.value === 'en', run: () => setChoice('en') },
    ] },
  ] },
])

const ITEM = '[role^="menuitem"]:not(:disabled)'
function mainEls() { return [...root.value.querySelectorAll(`.drop > ${ITEM}, .drop > .has-sub > ${ITEM}`)].filter((el) => !el.closest('.sub')) }
function subEls() { return [...root.value.querySelectorAll(`.sub ${ITEM}`)] }
async function openMenu(id, focusFirst = false) {
  open.value = id
  sub.value = null
  if (focusFirst) { await nextTick(); mainEls()[0]?.focus() }
}
function closeMenu(refocus = false) {
  const id = open.value
  open.value = null
  sub.value = null
  if (refocus && id) root.value.querySelector(`[data-menu="${id}"]`)?.focus()
}
async function openSub(i, focusFirst) {
  sub.value = i
  if (focusFirst) { await nextTick(); subEls()[0]?.focus() }
}
function act(it, i) {
  if (it.submenu) { openSub(i, true); return }
  closeMenu()
  if (!it.disabled) it.run()
}
function topKey(e, i) {
  const n = menus.value.length
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    e.preventDefault()
    const j = (i + (e.key === 'ArrowRight' ? 1 : n - 1)) % n
    const id = menus.value[j].id
    root.value.querySelector(`[data-menu="${id}"]`).focus()
    if (open.value) openMenu(id)
  } else if (e.key === 'Home' || e.key === 'End') {
    e.preventDefault()
    const id = menus.value[e.key === 'Home' ? 0 : n - 1].id
    root.value.querySelector(`[data-menu="${id}"]`).focus()
    if (open.value) openMenu(id)
  } else if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openMenu(menus.value[i].id, true) }
  else if (e.key === 'Escape') closeMenu(true)
}
function itemKey(e) {
  const inSub = !!e.target.closest('.sub')
  const els = inSub ? subEls() : mainEls()
  const k = els.indexOf(document.activeElement)
  if (e.key === 'ArrowDown') { e.preventDefault(); els[(k + 1) % els.length]?.focus() }
  else if (e.key === 'ArrowUp') { e.preventDefault(); els[(k - 1 + els.length) % els.length]?.focus() }
  else if (e.key === 'Home') { e.preventDefault(); els[0]?.focus() }
  else if (e.key === 'End') { e.preventDefault(); els[els.length - 1]?.focus() }
  else if (e.key === 'ArrowRight') {
    e.preventDefault()
    const idx = Number(document.activeElement?.dataset?.idx)
    if (!inSub && document.activeElement?.getAttribute('aria-haspopup')) openSub(idx, true)
    else if (!inSub) {
      const n = menus.value.length
      const cur = menus.value.findIndex((m) => m.id === open.value)
      openMenu(menus.value[(cur + 1) % n].id, true)
    }
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    if (inSub) {
      const idx = sub.value
      sub.value = null
      nextTick(() => root.value.querySelector(`.drop [data-idx="${idx}"]`)?.focus())
    } else {
      const n = menus.value.length
      const cur = menus.value.findIndex((m) => m.id === open.value)
      openMenu(menus.value[(cur + n - 1) % n].id, true)
    }
  } else if (e.key === 'Escape') {
    e.preventDefault(); e.stopPropagation()
    if (inSub) { const idx = sub.value; sub.value = null; nextTick(() => root.value.querySelector(`.drop [data-idx="${idx}"]`)?.focus()) }
    else closeMenu(true)
  } else if (e.key === 'Tab') closeMenu()
}
function onDoc(e) { if (open.value && !root.value.contains(e.target)) closeMenu() }
onMounted(() => document.addEventListener('pointerdown', onDoc))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDoc))

const speedLabel = computed(() => (store.speed === Infinity ? t('speed.max') : `${store.speed}×`))
const pill = computed(() => {
  if (store.fatal) return { t: t('pill.error'), c: 'bad' }
  if (store.run.state === 'stopping') return { t: t('pill.stopping'), c: 'warn' }
  if (store.run.state === 'starting') return { t: t('pill.starting'), c: 'warn' }
  if (store.run.state === 'running') {
    if (!scene.value) return { t: t('pill.running_script'), c: 'run' }
    return store.stats.running ? { t: t('pill.running', { speed: speedLabel.value }), c: 'run' } : { t: t('pill.paused'), c: 'warn' }
  }
  if (!store.boot.ready) return { t: t('pill.loading', { pct: fmtInt(Math.round(store.boot.progress * 100)) }), c: 'warn' }
  return { t: t('pill.ready'), c: 'ok' }
})
const title = computed(() => (store.readonly ? t('tab.demo') : store.fileName))
const summary = computed(() => {
  const n = scene.value?.robots?.length || 0
  return n ? t(n === 1 ? 'menubar.robot_one' : 'menubar.robot_other', { n: fmtInt(n) }) : t('menubar.no_sim')
})
</script>

<template>
  <header ref="root" class="mb">
    <div class="brand"><Logo :size="22" /><b>hiveBr</b><span>Web Studio</span></div>
    <nav class="menus" role="menubar" :aria-label="t('menu.aria')">
      <div v-for="(m, i) in menus" :key="m.id" class="m">
        <button class="top" role="menuitem" aria-haspopup="true" :aria-expanded="open === m.id" :data-menu="m.id" :class="{ on: open === m.id }"
          @click="open === m.id ? closeMenu() : openMenu(m.id)" @pointerenter="open && openMenu(m.id)" @keydown="topKey($event, i)">{{ m.label }}</button>
        <div v-if="open === m.id" class="drop menu-surface" role="menu" :aria-label="m.label" @keydown="itemKey($event)">
          <template v-for="(it, k) in m.items" :key="k">
            <hr v-if="it.sep" role="separator" />
            <div v-else-if="it.submenu" class="has-sub">
              <button class="it" role="menuitem" aria-haspopup="true" :aria-expanded="sub === k" :data-idx="k" @click="act(it, k)" @pointerenter="openSub(k, false)">
                <span class="ck" /><span class="lb">{{ it.label }}</span><span class="arrow" aria-hidden="true">›</span>
              </button>
              <div v-if="sub === k" class="sub menu-surface" role="menu" :aria-label="it.label">
                <button v-for="(si, j) in it.submenu" :key="j" class="it" role="menuitemradio" :aria-checked="si.radio" @click="closeMenu(); si.run()">
                  <span class="ck">{{ si.radio ? '●' : '' }}</span><span class="lb">{{ si.label }}</span>
                </button>
              </div>
            </div>
            <button v-else class="it" :role="it.check != null ? 'menuitemcheckbox' : 'menuitem'" :aria-checked="it.check" :disabled="it.disabled" :data-idx="k" @click="act(it, k)" @pointerenter="sub = null">
              <span class="ck">{{ it.check ? '✓' : '' }}</span><span class="lb">{{ it.label }}</span><kbd v-if="it.key">{{ it.key }}</kbd>
            </button>
          </template>
        </div>
      </div>
    </nav>
    <div class="center" aria-live="polite"><b>{{ title }}</b><span>·</span><span>{{ summary }}</span></div>
    <div class="pill" data-testid="pill" :class="pill.c" role="status"><i />{{ pill.t }}</div>
  </header>
</template>

<style scoped>
.mb { height: var(--menubar-h); background: var(--topbar); color: var(--topbar-text); display: flex; align-items: center; gap: var(--sp-6); padding: 0 var(--sp-5); position: relative; z-index: var(--z-menu); }
.brand { display: flex; align-items: center; gap: var(--sp-3); flex: none; font-size: var(--fs-md); }
.brand b { font-weight: 600; } .brand span { color: var(--topbar-muted); }
.menus { display: flex; gap: var(--sp-1); flex: none; }
.m { position: relative; }
.top { background: none; border: none; color: var(--topbar-text); padding: 0 10px; height: var(--h-md); border-radius: var(--radius-sm); font-size: var(--fs-md); }
.top:hover, .top.on { background: var(--topbar-hover); }
.top:focus-visible { outline-color: var(--topbar-focus); outline-offset: -2px; }
.drop { position: absolute; top: calc(100% + var(--sp-2)); left: 0; min-width: 250px; padding: var(--sp-2); background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius); display: flex; flex-direction: column; }
.has-sub { position: relative; display: flex; flex-direction: column; }
.sub { position: absolute; left: calc(100% - var(--sp-2)); top: calc(-1 * var(--sp-2)); min-width: 210px; padding: var(--sp-2); background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius); display: flex; flex-direction: column; }
.it { display: flex; align-items: center; gap: var(--sp-3); min-height: var(--h-md); padding: 0 var(--sp-4); background: none; border: none; border-radius: var(--radius-xs); text-align: left; color: var(--text); font-size: var(--fs-md); white-space: nowrap; }
.it:hover:not(:disabled), .it:focus-visible { background: var(--accent-soft); outline: none; }
.it:disabled { color: var(--text-faint); cursor: default; }
.ck { width: 14px; color: var(--accent); font-size: var(--fs-sm); flex: none; }
.lb { flex: 1; }
.arrow { color: var(--text-muted); }
.it kbd { background: none; border: none; color: var(--text-muted); padding: 0 0 0 var(--sp-5); font-size: var(--fs-xs); }
hr { border: none; border-top: 1px solid var(--border); margin: var(--sp-2) 0; width: 100%; }
.center { flex: 1; min-width: 0; display: flex; justify-content: center; gap: var(--sp-4); font-size: var(--fs-md); color: var(--topbar-muted); pointer-events: none; white-space: nowrap; overflow: hidden; }
.center b { color: var(--topbar-text); font-weight: 600; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.center span { flex: none; }
.pill { margin-left: auto; display: inline-flex; align-items: center; gap: var(--sp-3); padding: 3px 10px; border-radius: var(--radius-pill); background: var(--topbar-pill); font-size: var(--fs-xs); font-weight: 600; letter-spacing: .06em; text-transform: uppercase; white-space: nowrap; }
.pill i { width: 7px; height: 7px; border-radius: 50%; background: var(--topbar-muted); }
.pill.ok i { background: var(--topbar-ok); } .pill.run i { background: var(--topbar-ok); animation: pulse 1.4s infinite; }
.pill.warn i { background: var(--topbar-warn); } .pill.bad i { background: var(--topbar-danger); }
@keyframes pulse { 50% { opacity: .35; } }
@media (max-width: 1100px) { .center, .brand span { display: none; } }
@media (max-width: 760px) { .brand b { display: none; } .mb { gap: var(--sp-4); padding: 0 var(--sp-3); } .top { padding: 0 var(--sp-3); } }
</style>
