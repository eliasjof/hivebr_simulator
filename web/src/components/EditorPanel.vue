<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed, markRaw } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { EditorState, Compartment, StateField, StateEffect } from '@codemirror/state'
import { Decoration, keymap } from '@codemirror/view'
import { undo, redo, indentMore, indentLess } from '@codemirror/commands'
import { indentUnit } from '@codemirror/language'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import Icon from './Icon.vue'
import ScriptActionsModal from './ScriptActionsModal.vue'
import { t, locale } from '../i18n/index.js'
import { CM_PHRASES_PT } from '../i18n/cm-phrases.js'
import {
  store, setCode, runCode, stopCode, newFile, pickFile, downloadScript,
  switchTab, closeTab, openTab, duplicateDemo, openPanel, toggleRightMaximized,
} from '../state/store.js'

const host = ref(null)
let view = null
const scriptList = ref(false)
const scriptAction = ref(null)
const activeTab = computed(() => store.tabs.find((tab) => tab.id === store.activeId) || null)
const openTabs = computed(() => store.tabs.filter((tab) => tab.open !== false))
const closedTabs = computed(() => store.tabs.filter((tab) => tab.open === false))
function reopenTab(id) { openTab(id); scriptList.value = false }
function openScriptActions(tab) { scriptAction.value = tab; scriptList.value = false }
function onDocClick() { scriptList.value = false }
const themeComp = new Compartment()
const roComp = new Compartment()
const phrasesComp = new Compartment()

// Textos do próprio CodeMirror (busca, dobras…): em inglês vale o padrão da biblioteca.
const phrasesExt = () => EditorState.phrases.of(locale.value === 'pt-BR' ? CM_PHRASES_PT : {})

const setErrorLine = StateEffect.define()
const errorField = StateField.define({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes)
    for (const e of tr.effects) {
      if (e.is(setErrorLine)) {
        if (!e.value || e.value < 1 || e.value > tr.state.doc.lines) return Decoration.none
        return Decoration.set([Decoration.line({ class: 'cm-errorLine' }).range(tr.state.doc.line(e.value).from)])
      }
    }
    return deco
  },
  provide: (f) => EditorView.decorations.from(f),
})

const baseTheme = EditorView.theme({
  '&': { height: '100%', fontSize: '13px', backgroundColor: 'var(--surface)', color: 'var(--text)' },
  '.cm-scroller': { fontFamily: 'var(--font-mono)', lineHeight: '1.55' },
  '.cm-gutters': { backgroundColor: 'var(--surface-2)', color: 'var(--text-faint)', border: 'none', borderRight: '1px solid var(--border)' },
  '.cm-activeLineGutter': { backgroundColor: 'var(--accent-soft)' },
  '.cm-activeLine': { backgroundColor: 'var(--accent-soft)' },
  '&.cm-focused': { outline: 'none' },
  '.cm-cursor': { borderLeftColor: 'var(--accent)' },
  '.cm-errorLine': { backgroundColor: 'var(--danger-soft)', boxShadow: 'inset 3px 0 0 var(--danger)' },
})
const darkExt = [oneDark, EditorView.theme({ '&': { backgroundColor: 'var(--surface)' }, '.cm-gutters': { backgroundColor: 'var(--surface-2)' } })]
const themeExt = () => (store.theme === 'dark' ? darkExt : [])
const roExt = () => [EditorState.readOnly.of(store.readonly), EditorView.editable.of(!store.readonly)]

// Python segue a PEP 8: 4 espaços por nível de indentação.
const INDENT = '    '

// Tab indenta o código:
// - cursor dentro da indentação (ou linha vazia): indenta a linha inteira;
// - cursor depois de código: insere espaços no cursor (sem deslocar a linha,
//   o que quebraria a sintaxe do Python);
// - seleção: indenta as linhas selecionadas (Shift-Tab remove um nível).
function tabIndent(view) {
  const { state } = view
  if (state.readOnly) return false
  const range = state.selection.main
  if (!range.empty) return indentMore(view)
  const line = state.doc.lineAt(range.from)
  const before = state.sliceDoc(line.from, range.from)
  if (!/\S/.test(before)) return indentMore(view)
  view.dispatch(state.update({
    changes: { from: range.from, insert: INDENT },
    selection: { anchor: range.from + INDENT.length },
    userEvent: 'input',
  }))
  return true
}

onMounted(() => {
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: store.code,
      extensions: [
        basicSetup, python(), indentUnit.of(INDENT),
        keymap.of([{ key: 'Tab', run: tabIndent }, { key: 'Shift-Tab', run: indentLess }]),
        EditorView.lineWrapping, baseTheme, errorField, themeComp.of(themeExt()), roComp.of(roExt()), phrasesComp.of(phrasesExt()),
        EditorView.contentAttributes.of({ 'aria-label': t('editor.aria'), spellcheck: 'false' }),
        EditorView.updateListener.of((u) => { if (u.docChanged) setCode(u.state.doc.toString()) }),
      ],
    }),
  })
  store.editorApi = markRaw({
    undo: () => { if (view) { undo(view); view.focus() } },
    redo: () => { if (view) { redo(view); view.focus() } },
    focus: () => view?.focus(),
  })
  highlightError()
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => {
  view?.destroy(); store.editorApi = null
  document.removeEventListener('click', onDocClick)
})

watch(() => store.theme, () => view?.dispatch({ effects: themeComp.reconfigure(themeExt()) }))
watch(locale, () => view?.dispatch({ effects: phrasesComp.reconfigure(phrasesExt()) }))
watch(() => store.codeRev, () => {
  if (!view) return
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: store.code },
    effects: [setErrorLine.of(0), roComp.reconfigure(roExt())],
  })
})
function highlightError() {
  if (!view) return
  const line = store.error?.line
  view.dispatch({ effects: setErrorLine.of(line || 0) })
  if (line && line >= 1 && line <= view.state.doc.lines) scrollToLine(line)
}
function scrollToLine(line) {
  if (!view || line < 1 || line > view.state.doc.lines) return
  const pos = view.state.doc.line(line).from
  view.dispatch({ selection: { anchor: pos }, effects: EditorView.scrollIntoView(pos, { y: 'center' }) })
  view.focus()
}
watch(() => store.error, highlightError)
watch(() => store.jumpLine, (j) => j && scrollToLine(j.line))

const tabName = (tab) => (tab.readonly ? t('tab.demo') : tab.id === store.activeId ? store.fileName : tab.name)
const running = computed(() => store.run.state !== 'idle')
const runDisabled = computed(() => !store.boot.ready && !running.value)
</script>

<template>
  <section class="ed" :aria-label="t('view.code')">
    <header class="ph">
      <span class="sec-h">{{ t('view.code') }}</span>
      <span class="sp" />
      <div v-if="closedTabs.length" class="script-list-wrap" @click.stop>
        <button class="btn ghost icon sm" :aria-label="t('editor.closed_scripts')" :data-tip="t('editor.closed_scripts')" :aria-expanded="scriptList" @click="scriptList = !scriptList"><Icon name="list" :size="14" /></button>
        <div v-if="scriptList" class="script-menu" role="menu">
          <button v-for="tab in closedTabs" :key="tab.id" class="script-menu-item" role="menuitem" :title="tabName(tab)" @click="reopenTab(tab.id)">
            <Icon name="file" :size="13" /><span class="script-menu-name">{{ tabName(tab) }}</span>
          </button>
        </div>
      </div>
      <button class="btn ghost icon sm" :aria-label="store.layout.rightMaximized ? t('win.restore') : t('win.maximize')" :data-tip="store.layout.rightMaximized ? t('win.restore') : t('win.maximize')" @click="toggleRightMaximized"><Icon :name="store.layout.rightMaximized ? 'restore' : 'max'" :size="14" /></button>
      <button class="btn ghost icon sm" :aria-label="t('editor.collapse')" :data-tip="t('dock.collapse')" data-tip-pos="end" @click="store.layout.rightOpen = false"><Icon name="panelR" :size="14" /></button>
    </header>
    <div class="tabs" role="tablist" :aria-label="t('editor.tabs')">
      <div v-for="tab in openTabs" :key="tab.id" class="etab" :class="{ on: tab.id === store.activeId }">
        <button class="tab" role="tab" :aria-selected="tab.id === store.activeId" :title="tabName(tab)" @click="switchTab(tab.id)">
          <Icon :name="tab.readonly ? 'demo' : 'file'" :size="13" /><span class="nm">{{ tabName(tab) }}</span>
          <i v-if="tab.id === store.activeId && !tab.readonly && store.saveState === 'pending'" class="dirty" :aria-label="t('editor.pending')" />
        </button>
        <button class="more" :aria-label="t('script.actions')" :data-tip="t('script.actions')" @click.stop="openScriptActions(tab)"><Icon name="dots" :size="11" /></button>
        <button class="x" :aria-label="t('editor.close_tab', { name: tabName(tab) })" @click="closeTab(tab.id)"><Icon name="close" :size="11" /></button>
      </div>
      <button class="btn ghost icon sm plus" :aria-label="t('file.new')" :data-tip="t('file.new')" @click="newFile"><Icon name="plus" :size="14" /></button>
      <span class="sp" />
      <button class="btn ghost icon sm" :aria-label="t('file.open_short')" :data-tip="t('file.open_tip')" @click="pickFile"><Icon name="open" :size="14" /></button>
      <button class="btn ghost icon sm" :aria-label="t('file.download')" :data-tip="t('file.download')" data-tip-pos="end" :disabled="!activeTab" @click="downloadScript()"><Icon name="download" :size="14" /></button>
    </div>
    <div v-if="store.readonly" class="banner ro" role="note">
      <Icon name="info" :size="14" /><span>{{ t('editor.demo_banner') }}</span>
      <button class="btn sm" @click="duplicateDemo">{{ t('editor.duplicate') }}</button>
    </div>
    <div v-if="store.error" class="banner err" role="alert">
      <Icon name="alert" :size="14" />
      <div class="errtxt"><b class="mono">{{ store.error.type }}</b>: {{ store.error.message }}<span v-if="store.error.line" class="muted"> ({{ t('problems.line', { n: store.error.line }) }})</span></div>
      <button class="btn sm" @click="openPanel('bottom', 'console')">{{ t('editor.see_console') }}</button>
      <button class="btn ghost icon sm" :aria-label="t('common.dismiss')" @click="store.error = null"><Icon name="close" :size="12" /></button>
    </div>
    <div v-if="!activeTab" class="ed-empty">
      <div class="ed-empty-inner">
        <p class="ed-empty-title">{{ t('editor.no_open_scripts') }}</p>
        <div v-if="store.tabs.length" class="ed-empty-list">
          <p class="ed-empty-sub">{{ t('editor.saved_scripts') }}</p>
          <div v-for="tab in store.tabs" :key="tab.id" class="ed-empty-row">
            <button class="btn sm" :title="tabName(tab)" @click="openTab(tab.id)">
              <Icon name="file" :size="12" /><span class="ed-empty-name">{{ tabName(tab) }}</span>
            </button>
            <button class="btn ghost icon sm" :aria-label="t('script.actions')" :data-tip="t('script.actions')" @click.stop="openScriptActions(tab)"><Icon name="dots" :size="13" /></button>
          </div>
        </div>
        <button class="btn" @click="newFile"><Icon name="plus" :size="12" />{{ t('file.new') }}</button>
      </div>
    </div>
    <div v-show="activeTab" ref="host" class="cm-host" />
    <footer v-if="activeTab" class="efoot">
      <button class="btn sm" :class="running ? 'run-stop' : 'run-go'" :disabled="runDisabled" @click="running ? stopCode() : runCode()">
        <Icon :name="running ? 'stop' : 'play'" :size="12" />{{ running ? t('sim.stop') : t('run.run') }}</button>
      <label class="switch" :data-tip="t('editor.autostart_tip')" data-tip-pos="up">
        <input v-model="store.autostart" type="checkbox" /> {{ t('editor.autostart') }}</label>
      <span class="state mono" :class="{ pending: store.saveState === 'pending' }" :data-tip="t('editor.save_tip')" data-tip-pos="end">
        {{ store.readonly ? t('editor.readonly') : store.saveState === 'saved' ? t('editor.saved') : t('editor.modified') }}</span>
    </footer>
    <Teleport to="body">
      <ScriptActionsModal v-if="scriptAction" :tab="scriptAction" @close="scriptAction = null" />
    </Teleport>
  </section>
</template>

<style scoped>
.ed { display: flex; flex-direction: column; min-height: 0; height: 100%; background: var(--surface); border-left: 1px solid var(--border); }
.ph { display: flex; align-items: center; height: var(--panel-head-h); padding: 0 var(--sp-4) 0 var(--sp-5); flex: none; border-bottom: 1px solid var(--border); }
.sp { flex: 1; }
.script-list-wrap { position: relative; display: flex; }
.script-menu {
  position: absolute; top: calc(100% + 4px); right: 0; z-index: var(--z-tip);
  min-width: 180px; max-width: 300px; max-height: 280px; overflow: auto;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); box-shadow: var(--shadow); padding: 4px;
}
.script-menu-item {
  display: flex; align-items: center; gap: 6px; width: 100%; padding: 5px 8px;
  border: none; background: none; color: var(--text); font-size: 12px;
  cursor: pointer; border-radius: 3px; text-align: left;
}
.script-menu-item:hover { background: var(--surface-3); }
.script-menu-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tabs { padding: 0 var(--sp-3); flex: none; align-items: stretch; overflow-x: auto; overflow-y: hidden; scrollbar-width: none; background: var(--surface-2); }
.etab { display: flex; align-items: center; border-bottom: 2px solid transparent; flex: none; }
.etab.on { border-bottom-color: var(--accent); background: var(--surface); }
.etab .tab { display: flex; align-items: center; gap: var(--sp-3); border: none; padding: var(--sp-3) var(--sp-2) var(--sp-3) 10px; max-width: 170px; }
.etab.on .tab { color: var(--text); }
.nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dirty { width: 6px; height: 6px; border-radius: 50%; background: var(--warn); flex: none; }
.x { background: none; border: none; width: var(--h-xs); height: var(--h-xs); border-radius: var(--radius-xs); display: grid; place-items: center; color: var(--text-muted); margin-right: var(--sp-2); }
.x:hover { background: var(--surface-3); color: var(--text); }
.more { background: none; border: none; width: var(--h-xs); height: var(--h-xs); border-radius: var(--radius-xs); display: grid; place-items: center; color: var(--text-muted); opacity: 0; flex: none; }
.etab:hover .more, .etab.on .more, .more:focus-visible { opacity: 1; }
.more:hover { background: var(--surface-3); color: var(--text); }
.plus { align-self: center; }
.tabs .btn { align-self: center; }
.banner { display: flex; align-items: center; gap: var(--sp-4); padding: var(--sp-3) 10px; flex: none; font-size: var(--fs-sm); border-bottom: 1px solid var(--border); }
.banner.ro { background: var(--accent-soft); }
.banner.ro svg { color: var(--accent); }
.banner.ro span { flex: 1; }
.banner.err { background: var(--danger-soft); }
.banner.err > svg { color: var(--danger); flex: none; }
.errtxt { flex: 1; min-width: 0; overflow-wrap: anywhere; max-height: 4.2em; overflow: auto; }
.cm-host { flex: 1; min-height: 0; overflow: hidden; }
.ed-empty { flex: 1; min-height: 0; overflow: auto; display: flex; align-items: center; justify-content: center; padding: 20px; text-align: center; }
.ed-empty-inner { display: flex; flex-direction: column; align-items: center; gap: 14px; color: var(--text-muted); max-width: 100%; }
.ed-empty-title { margin: 0; }
.ed-empty-sub { margin: 0; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--text-faint); }
.ed-empty-list { display: flex; flex-direction: column; gap: 4px; width: 100%; max-width: 260px; }
.ed-empty-row { display: flex; align-items: center; gap: 2px; }
.ed-empty-row .btn.sm { flex: 1; min-width: 0; justify-content: flex-start; max-width: 100%; }
.ed-empty-row .btn.ghost { flex: none; opacity: .5; }
.ed-empty-row:hover .btn.ghost, .ed-empty-row .btn.ghost:focus-visible { opacity: 1; }
.ed-empty-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cm-host :deep(.cm-editor) { height: 100%; }
.efoot { display: flex; align-items: center; gap: var(--sp-5); flex: none; padding: var(--sp-3) 10px; border-top: 1px solid var(--border); font-size: var(--fs-sm); flex-wrap: wrap; }
.state { margin-left: auto; color: var(--text-muted); font-size: var(--fs-label); }
.state.pending { color: var(--warn); }
</style>
