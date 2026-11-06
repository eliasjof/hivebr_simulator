<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import Logo from './Logo.vue'
import {
  store, scene, CATALOGREF, newFile, pickFile, downloadScript, saveNow, runCode, stopCode, toggleSim, stepOnce, resetSim,
  toggleTheme, togglePanel, openPanel, openWindow, toggleWindow, resetLayout, runDemo, loadExample, canvasRef, consoleBus, toast,
} from '../state/store.js'

const open = ref(null)
const root = ref(null)
const idle = computed(() => store.run.state === 'idle')
const live = computed(() => store.run.state === 'running')
const examples = computed(() => CATALOGREF.filter((e) => e.id !== 'demonstracao').slice(0, 8))

const menus = computed(() => [
  { id: 'file', label: 'Arquivo', items: [
    { label: 'Novo script', key: 'Ctrl+Alt+N', run: newFile },
    { label: 'Abrir .py…', key: 'Ctrl+O', run: pickFile },
    { label: 'Salvar no navegador', key: 'Ctrl+S', run: () => { saveNow(); toast('Salvo no navegador.') } },
    { label: 'Baixar .py', run: downloadScript },
  ] },
  { id: 'edit', label: 'Editar', items: [
    { label: 'Desfazer', key: 'Ctrl+Z', run: () => store.editorApi?.undo(), disabled: !store.editorApi },
    { label: 'Refazer', key: 'Ctrl+Shift+Z', run: () => store.editorApi?.redo(), disabled: !store.editorApi },
    { sep: true },
    { label: 'Limpar console', run: () => consoleBus.clear() },
  ] },
  { id: 'view', label: 'Exibir', items: [
    { label: 'Navegador', check: store.layout.leftOpen, run: () => togglePanel('left') },
    { label: 'Código', key: 'E', check: store.layout.rightOpen, run: () => togglePanel('right') },
    { label: 'Painel inferior', check: store.layout.bottomOpen, run: () => { store.layout.bottomOpen = !store.layout.bottomOpen } },
    { sep: true },
    { label: 'Console', key: 'C', run: () => openPanel('bottom', 'console') },
    { label: 'Telemetria', key: 'B', run: () => openPanel('bottom', 'telemetry') },
    { label: 'Parâmetros', key: 'P', check: store.windows.params.open, run: () => toggleWindow('params') },
    { label: 'Gráficos', key: 'G', check: store.windows.plots.open, run: () => toggleWindow('plots') },
    { label: 'Mapa', key: 'K', check: store.windows.map.open, run: () => toggleWindow('map') },
    { sep: true },
    { label: 'Enquadrar', key: 'F', run: () => canvasRef.value?.fit() },
    { label: store.theme === 'dark' ? 'Tema claro' : 'Tema escuro', key: 'T', run: toggleTheme },
    { label: 'Restaurar layout', run: resetLayout },
  ] },
  { id: 'sim', label: 'Simulação', items: [
    { label: 'Executar código', key: 'Ctrl+Enter', run: runCode, disabled: !idle.value || !store.boot.ready },
    { label: 'Parar', run: stopCode, disabled: !live.value },
    { label: store.stats.running ? 'Pausar simulação' : 'Iniciar simulação', key: 'Espaço', run: toggleSim, disabled: !live.value },
    { label: 'Um passo', key: '.', run: stepOnce, disabled: !live.value },
    { label: 'Reiniciar', key: 'Shift+R', run: resetSim, disabled: !live.value },
    { sep: true },
    { label: 'Demonstração', run: runDemo },
  ] },
  { id: 'ex', label: 'Exemplos', items: [
    { label: 'Galeria de exemplos…', run: () => { store.modals.examples = true } },
    { label: 'Demonstração', run: runDemo },
    { sep: true },
    ...examples.value.map((e) => ({ label: e.title, run: () => loadExample(e) })),
  ] },
  { id: 'help', label: 'Ajuda', items: [
    { label: 'Guia e atalhos', key: '?', run: () => { store.modals.help = true } },
    { label: 'Demonstração', run: runDemo },
    { sep: true },
    { label: 'Sobre…', run: () => { store.modals.about = true } },
  ] },
])

function itemEls() { return [...root.value.querySelectorAll('.drop:not([hidden]) [role^="menuitem"]:not(:disabled)')] }
async function openMenu(id, focusFirst = false) {
  open.value = id
  if (focusFirst) { await nextTick(); itemEls()[0]?.focus() }
}
function closeMenu(refocus = false) {
  const id = open.value
  open.value = null
  if (refocus && id) root.value.querySelector(`[data-menu="${id}"]`)?.focus()
}
function act(it) { closeMenu(); if (!it.disabled) it.run() }
function topKey(e, i) {
  const n = menus.value.length
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    e.preventDefault()
    const j = (i + (e.key === 'ArrowRight' ? 1 : n - 1)) % n
    const id = menus.value[j].id
    root.value.querySelector(`[data-menu="${id}"]`).focus()
    if (open.value) openMenu(id)
  } else if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openMenu(menus.value[i].id, true) }
  else if (e.key === 'Escape') closeMenu(true)
}
function itemKey(e, i) {
  const els = itemEls()
  const k = els.indexOf(document.activeElement)
  if (e.key === 'ArrowDown') { e.preventDefault(); els[(k + 1) % els.length]?.focus() }
  else if (e.key === 'ArrowUp') { e.preventDefault(); els[(k - 1 + els.length) % els.length]?.focus() }
  else if (e.key === 'Home') { e.preventDefault(); els[0]?.focus() }
  else if (e.key === 'End') { e.preventDefault(); els[els.length - 1]?.focus() }
  else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    e.preventDefault()
    const n = menus.value.length
    const cur = menus.value.findIndex((m) => m.id === open.value)
    const j = (cur + (e.key === 'ArrowRight' ? 1 : n - 1)) % n
    openMenu(menus.value[j].id, true)
  } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(true) }
  else if (e.key === 'Tab') closeMenu()
}
function onDoc(e) { if (open.value && !root.value.contains(e.target)) closeMenu() }
onMounted(() => document.addEventListener('pointerdown', onDoc))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDoc))

const speedLabel = computed(() => (store.speed === Infinity ? 'Máx' : `${store.speed}×`))
const pill = computed(() => {
  if (store.fatal) return { t: 'Erro', c: 'bad' }
  if (store.run.state === 'stopping') return { t: 'Parando', c: 'warn' }
  if (store.run.state === 'starting') return { t: 'Iniciando', c: 'warn' }
  if (store.run.state === 'running') {
    if (!scene.value) return { t: 'Executando · script', c: 'run' }
    return store.stats.running ? { t: `Executando · ${speedLabel.value}`, c: 'run' } : { t: 'Pausado', c: 'warn' }
  }
  if (!store.boot.ready) return { t: `Carregando ${Math.round(store.boot.progress * 100)}%`, c: 'warn' }
  if (store.run.state === 'idle') return { t: 'Python pronto · parado', c: 'ok' }
  return store.stats.running ? { t: `Executando · ${speedLabel.value}`, c: 'run' } : { t: 'Pausado', c: 'warn' }
})
const summary = computed(() => {
  const n = scene.value?.robots?.length || 0
  return n ? `${n} ${n === 1 ? 'robô' : 'robôs'}` : 'sem simulação'
})
</script>

<template>
  <header ref="root" class="mb">
    <div class="brand"><Logo :size="22" /><b>hiveBr</b><span>Web Studio</span></div>
    <nav class="menus" role="menubar" aria-label="Menu principal">
      <div v-for="(m, i) in menus" :key="m.id" class="m">
        <button class="top" role="menuitem" aria-haspopup="true" :aria-expanded="open === m.id" :data-menu="m.id" :class="{ on: open === m.id }"
          @click="open === m.id ? closeMenu() : openMenu(m.id)" @pointerenter="open && openMenu(m.id)" @keydown="topKey($event, i)">{{ m.label }}</button>
        <div v-if="open === m.id" class="drop menu-surface" role="menu" :aria-label="m.label" @keydown="itemKey($event)">
          <template v-for="(it, k) in m.items" :key="k">
            <hr v-if="it.sep" role="separator" />
            <button v-else class="it" :role="it.check != null ? 'menuitemcheckbox' : 'menuitem'" :aria-checked="it.check" :disabled="it.disabled" @click="act(it)">
              <span class="ck">{{ it.check ? '✓' : '' }}</span><span class="lb">{{ it.label }}</span><kbd v-if="it.key">{{ it.key }}</kbd>
            </button>
          </template>
        </div>
      </div>
    </nav>
    <div class="center" aria-live="polite"><b>{{ store.fileName }}</b><span>·</span><span>{{ summary }}</span></div>
    <div class="pill" data-testid="pill" :class="pill.c" role="status"><i />{{ pill.t }}</div>
  </header>
</template>

<style scoped>
.mb { height: var(--menubar-h); background: var(--topbar); color: var(--topbar-text); display: flex; align-items: center; gap: 16px; padding: 0 12px; position: relative; z-index: var(--z-menu); }
.brand { display: flex; align-items: center; gap: 6px; flex: none; font-size: 13px; }
.brand b { font-weight: 600; } .brand span { color: var(--topbar-muted); }
.menus { display: flex; gap: 2px; }
.m { position: relative; }
.top { background: none; border: none; color: var(--topbar-text); padding: 0 10px; height: 28px; border-radius: 6px; font-size: 13px; }
.top:hover, .top.on { background: rgba(255, 255, 255, .10); }
.top:focus-visible { outline-color: #93c5fd; outline-offset: -2px; }
.drop { position: absolute; top: calc(100% + 4px); left: 0; min-width: 250px; padding: 4px; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius); display: flex; flex-direction: column; }
.it { display: flex; align-items: center; gap: 6px; min-height: 28px; padding: 0 8px; background: none; border: none; border-radius: 4px; text-align: left; color: var(--text); font-size: 13px; }
.it:hover:not(:disabled), .it:focus-visible { background: var(--accent-soft); outline: none; }
.it:disabled { color: var(--text-faint); cursor: default; }
.ck { width: 14px; color: var(--accent); font-size: 12px; }
.lb { flex: 1; }
.it kbd { background: none; border: none; color: var(--text-muted); padding: 0; font-size: 11px; }
hr { border: none; border-top: 1px solid var(--border); margin: 4px 0; width: 100%; }
.center { flex: 1; min-width: 0; display: flex; justify-content: center; gap: 8px; font-size: 13px; color: var(--topbar-muted); pointer-events: none; white-space: nowrap; overflow: hidden; }
.center b { color: var(--topbar-text); font-weight: 600; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.center span { flex: none; }
.pill { margin-left: auto; display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 99px; background: rgba(255, 255, 255, .08); font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; white-space: nowrap; }
.pill i { width: 7px; height: 7px; border-radius: 50%; background: var(--topbar-muted); }
.pill.ok i { background: #4ade80; } .pill.run i { background: #4ade80; animation: pulse 1.4s infinite; }
.pill.warn i { background: #fbbf24; } .pill.bad i { background: #f87171; }
@keyframes pulse { 50% { opacity: .35; } }
@media (max-width: 1100px) { .center, .brand span { display: none; } }
@media (max-width: 760px) { .brand b { display: none; } .mb { gap: 8px; padding: 0 6px; } .top { padding: 0 6px; } }
</style>
