<script setup>
import { computed, onMounted, ref, nextTick } from 'vue'
import Modal from './Modal.vue'
import { readClientFile, writeClientConfig, toast } from '../state/store.js'
import { t } from '../i18n/index.js'
import { findMatches, nextMatchIndex, replaceAllMatches } from '../utils/findReplace.js'

const DEFAULT_PATH = '/hivebr/config/default.yaml'
const emit = defineEmits(['close'])
const text = ref('')
const path = ref(DEFAULT_PATH)
const fileInput = ref(null)
const loadedFile = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref('')

// ---- find & replace ----
const area = ref(null)
const findInput = ref(null)
const showFind = ref(false)
const findText = ref('')
const replaceText = ref('')
const matchCase = ref(false)
const findInfo = ref('')

const matches = computed(() => findMatches(text.value, findText.value, matchCase.value))

function toggleFind() {
  showFind.value = !showFind.value
  findInfo.value = ''
  if (showFind.value) nextTick(() => findInput.value?.focus())
}

function selectRange(start, end) {
  const el = area.value
  if (!el) return
  el.focus()
  el.setSelectionRange(start, end)
}

function findNext(dir = 1, fromPos = null) {
  const list = matches.value
  if (!list.length) { findInfo.value = t('config.find_none'); return }
  const el = area.value
  const start = fromPos ?? (el?.selectionStart ?? 0)
  const end = fromPos ?? (el?.selectionEnd ?? 0)
  const pos = nextMatchIndex(list, { start, end, dir })
  selectRange(pos, pos + findText.value.length)
  findInfo.value = t('config.find_count', { i: list.indexOf(pos) + 1, n: list.length })
}

function replaceOne() {
  const list = matches.value
  if (!list.length) { findInfo.value = t('config.find_none'); return }
  const el = area.value
  const start = el?.selectionStart ?? 0
  const end = el?.selectionEnd ?? 0
  const len = findText.value.length
  // Prefer the current selection when it is a match; otherwise use the next one.
  const target = list.find((s) => s === start && s + len === end)
    ?? list.find((s) => s >= end) ?? list[0]
  text.value = text.value.slice(0, target) + replaceText.value + text.value.slice(target + len)
  const nextPos = target + replaceText.value.length
  findInfo.value = t('config.replaced_count', { n: 1 })
  findNext(1, nextPos)
}

function replaceAll() {
  const result = replaceAllMatches(text.value, findText.value, replaceText.value, matchCase.value)
  if (!result.count) { findInfo.value = t('config.find_none'); return }
  text.value = result.text
  findInfo.value = t('config.replaced_count', { n: result.count })
}

function targetPath() {
  let p = String(path.value || '').trim()
  if (!p) p = DEFAULT_PATH
  if (!p.startsWith('/')) p = `/hivebr/config/${p.replace(/^\/+/, '')}`
  return p
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    path.value = targetPath()
    text.value = new TextDecoder().decode(await readClientFile(path.value))
    loadedFile.value = ''
  } catch (e) {
    error.value = String(e?.message || e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  try {
    text.value = await file.text()
    loadedFile.value = file.name
    error.value = ''
  } catch (err) {
    error.value = String(err?.message || err)
  }
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    path.value = targetPath()
    await writeClientConfig(text.value, path.value)
    toast(t('config.saved'))
    emit('close')
  } catch (e) {
    error.value = String(e?.message || e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Modal :title="t('config.editor_title')" :width="860" @close="emit('close')">
      <p class="hint">{{ t('config.editor_hint') }}</p>
      <div class="cfg-row">
        <label class="field cfg-path">
          <span class="label">{{ t('config.path') }}</span>
          <input v-model="path" class="input mono" spellcheck="false" @change="load" />
        </label>
        <button class="btn" type="button" @click="fileInput?.click()">{{ t('config.load_file') }}</button>
        <button class="btn" type="button" @click="toggleFind">{{ t('config.search') }}</button>
        <input ref="fileInput" type="file" class="file" accept=".yaml,.yml,text/yaml,application/x-yaml" @change="onFile" />
      </div>
      <p v-if="loadedFile" class="loaded">{{ t('config.loaded_file', { name: loadedFile }) }}</p>
      <div v-if="showFind && !loading" class="find-row">
        <input ref="findInput" v-model="findText" class="input mono find-input" spellcheck="false"
          :placeholder="t('config.find')" :aria-label="t('config.find')"
          @keydown.enter.prevent="findNext(1)" @keydown.shift.enter.prevent="findNext(-1)" />
        <input v-model="replaceText" class="input mono find-input" spellcheck="false"
          :placeholder="t('config.replace')" :aria-label="t('config.replace')"
          @keydown.enter.prevent="replaceOne" />
        <button class="btn sm" type="button" :title="t('config.find_prev')" :aria-label="t('config.find_prev')"
          :disabled="!matches.length" @click="findNext(-1)">↑</button>
        <button class="btn sm" type="button" :title="t('config.find_next')" :aria-label="t('config.find_next')"
          :disabled="!matches.length" @click="findNext(1)">↓</button>
        <button class="btn sm" type="button" :disabled="!matches.length" @click="replaceOne">{{ t('config.replace_one') }}</button>
        <button class="btn sm" type="button" :disabled="!matches.length" @click="replaceAll">{{ t('config.replace_all') }}</button>
        <label class="find-check">
          <input v-model="matchCase" type="checkbox" />{{ t('config.match_case') }}
        </label>
      </div>
      <p v-if="showFind && !loading && findInfo" class="find-info" aria-live="polite">{{ findInfo }}</p>
      <div v-if="loading" class="faint">{{ t('config.loading') }}</div>
      <textarea v-else ref="area" v-model="text" class="input mono yaml" spellcheck="false" data-autofocus
        :aria-label="t('config.editor_title')"></textarea>
      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <template #footer>
        <button class="btn" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button class="btn primary" :disabled="loading || saving" @click="save">{{ t('config.save') }}</button>
      </template>
    </Modal>
  </Teleport>
</template>

<style scoped>
.hint { margin: 0 0 var(--sp-4); color: var(--text-muted); line-height: 1.5; }
.cfg-row { display: flex; gap: var(--sp-4); align-items: flex-end; margin-bottom: var(--sp-4); }
.cfg-path { flex: 1; min-width: 0; }
.file { display: none; }
.loaded { margin: 0 0 var(--sp-4); color: var(--text-muted); font-size: var(--fs-sm); }
.find-row { display: flex; flex-wrap: wrap; gap: var(--sp-2); align-items: center; margin-bottom: var(--sp-2); }
.find-input { flex: 1 1 180px; min-width: 120px; }
.find-check { display: inline-flex; gap: var(--sp-2); align-items: center; font-size: var(--fs-sm); color: var(--text-muted); white-space: nowrap; }
.find-info { margin: 0 0 var(--sp-2); color: var(--text-muted); font-size: var(--fs-sm); }
.yaml {
  width: 100%; height: min(60vh, 520px); resize: vertical; padding: var(--sp-4);
  font-family: var(--font-mono); font-size: var(--fs-sm); line-height: 1.55;
  white-space: pre; overflow: auto; tab-size: 2;
}
.err { margin: var(--sp-4) 0 0; color: var(--danger); font-size: var(--fs-sm); white-space: pre-wrap; }
</style>
