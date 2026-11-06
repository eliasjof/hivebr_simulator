<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed, markRaw } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { EditorState, Compartment, StateField, StateEffect } from '@codemirror/state'
import { Decoration } from '@codemirror/view'
import { undo, redo } from '@codemirror/commands'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import Icon from './Icon.vue'
import {
  store, setCode, runCode, stopCode, newFile, pickFile, downloadScript,
  switchTab, closeTab, duplicateDemo, openPanel, WINDOW_DEFS,
} from '../state/store.js'

const host = ref(null)
let view = null
const themeComp = new Compartment()
const roComp = new Compartment()

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

onMounted(() => {
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: store.code,
      extensions: [
        basicSetup, python(), EditorView.lineWrapping, baseTheme, errorField, themeComp.of(themeExt()), roComp.of(roExt()),
        EditorView.contentAttributes.of({ 'aria-label': 'Editor de código Python', spellcheck: 'false' }),
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
})
onBeforeUnmount(() => { view?.destroy(); store.editorApi = null })

watch(() => store.theme, () => view?.dispatch({ effects: themeComp.reconfigure(themeExt()) }))
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

const running = computed(() => store.run.state !== 'idle')
const runDisabled = computed(() => !store.boot.ready && !running.value)
</script>

<template>
  <section class="ed" aria-label="Código">
    <header class="ph">
      <span class="sec-h">Código</span>
      <span class="sp" />
      <button class="btn ghost icon sm" aria-label="Recolher painel de código" data-tip="Recolher" data-tip-pos="end" @click="store.layout.rightOpen = false"><Icon name="panelR" :size="14" /></button>
    </header>
    <div class="tabs" role="tablist" aria-label="Scripts abertos">
      <div v-for="t in store.tabs" :key="t.id" class="etab" :class="{ on: t.id === store.activeId }">
        <button class="tab" role="tab" :aria-selected="t.id === store.activeId" @click="switchTab(t.id)" :title="t.name">
          <Icon :name="t.readonly ? 'demo' : 'file'" :size="13" /><span class="nm">{{ t.id === store.activeId ? store.fileName : t.name }}</span>
          <i v-if="t.id === store.activeId && !t.readonly && store.saveState === 'pending'" class="dirty" aria-label="Alterações pendentes" />
        </button>
        <button class="x" :aria-label="`Fechar ${t.name}`" @click="closeTab(t.id)"><Icon name="close" :size="11" /></button>
      </div>
      <button class="btn ghost icon sm plus" aria-label="Novo script" data-tip="Novo script" @click="newFile"><Icon name="plus" :size="14" /></button>
      <span class="sp" />
      <button class="btn ghost icon sm" aria-label="Abrir arquivo .py" data-tip="Abrir .py (Ctrl+O)" @click="pickFile"><Icon name="open" :size="14" /></button>
      <button class="btn ghost icon sm" aria-label="Baixar arquivo .py" data-tip="Baixar .py" data-tip-pos="end" @click="downloadScript"><Icon name="download" :size="14" /></button>
    </div>
    <div v-if="store.readonly" class="banner ro" role="note">
      <Icon name="info" :size="14" /><span>Exemplo de demonstração, somente leitura</span>
      <button class="btn sm" @click="duplicateDemo">Duplicar para editar</button>
    </div>
    <div v-if="store.error" class="banner err" role="alert">
      <Icon name="alert" :size="14" />
      <div class="errtxt"><b class="mono">{{ store.error.type }}</b>: {{ store.error.message }}<span v-if="store.error.line" class="faint"> (linha {{ store.error.line }})</span></div>
      <button class="btn sm" @click="openPanel('bottom', 'console')">Ver no console</button>
      <button class="btn ghost icon sm" aria-label="Dispensar erro" @click="store.error = null"><Icon name="close" :size="12" /></button>
    </div>
    <div ref="host" class="cm-host" />
    <footer class="efoot">
      <button class="btn sm run" :class="running ? 'stop' : 'go'" :disabled="runDisabled" @click="running ? stopCode() : runCode()">
        <Icon :name="running ? 'stop' : 'play'" :size="12" />{{ running ? 'Parar' : 'Executar' }}</button>
      <label class="switch" data-tip="Inicia a simulação assim que o código criar o simulador" data-tip-pos="up">
        <input type="checkbox" v-model="store.autostart" /> Iniciar automaticamente</label>
      <span class="state mono" :class="{ pending: store.saveState === 'pending' }" data-tip="Ctrl+S salva no navegador" data-tip-pos="end">
        {{ store.readonly ? 'somente leitura' : store.saveState === 'saved' ? 'salvo' : 'alterado' }}</span>
    </footer>
  </section>
</template>

<style scoped>
.ed { display: flex; flex-direction: column; min-height: 0; height: 100%; background: var(--surface); border-left: 1px solid var(--border); }
.ph { display: flex; align-items: center; height: 34px; padding: 0 8px 0 12px; flex: none; border-bottom: 1px solid var(--border); }
.sp { flex: 1; }
.tabs { padding: 0 6px; flex: none; align-items: stretch; overflow-x: auto; overflow-y: hidden; scrollbar-width: none; background: var(--surface-2); }
.etab { display: flex; align-items: center; border-bottom: 2px solid transparent; flex: none; }
.etab.on { border-bottom-color: var(--accent); background: var(--surface); }
.etab .tab { display: flex; align-items: center; gap: 6px; border: none; padding: 6px 4px 6px 10px; max-width: 170px; }
.etab.on .tab { color: var(--text); }
.nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dirty { width: 6px; height: 6px; border-radius: 50%; background: var(--warn); flex: none; }
.x { background: none; border: none; width: 20px; height: 20px; border-radius: 4px; display: grid; place-items: center; color: var(--text-faint); margin-right: 4px; }
.x:hover { background: var(--surface-3); color: var(--text); }
.plus { align-self: center; }
.tabs .btn { align-self: center; }
.banner { display: flex; align-items: center; gap: 8px; padding: 6px 10px; flex: none; font-size: 12px; border-bottom: 1px solid var(--border); }
.banner.ro { background: var(--accent-soft); }
.banner.ro svg { color: var(--accent); }
.banner.ro span { flex: 1; }
.banner.err { background: var(--danger-soft); }
.banner.err > svg { color: var(--danger); flex: none; }
.errtxt { flex: 1; min-width: 0; overflow-wrap: anywhere; max-height: 4.2em; overflow: auto; }
.cm-host { flex: 1; min-height: 0; overflow: hidden; }
.cm-host :deep(.cm-editor) { height: 100%; }
.efoot { display: flex; align-items: center; gap: 12px; flex: none; padding: 6px 10px; border-top: 1px solid var(--border); font-size: 12px; flex-wrap: wrap; }
.run.go { background: var(--ok); border-color: transparent; color: #fff; }
.run.stop { background: var(--danger); border-color: transparent; color: #fff; }
.state { margin-left: auto; color: var(--text-muted); font-size: 11.5px; }
.state.pending { color: var(--warn); }
</style>
