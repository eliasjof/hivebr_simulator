<script setup>
import { onMounted, ref } from 'vue'
import Modal from './Modal.vue'
import { readClientFile, writeClientConfig, toast } from '../state/store.js'
import { t } from '../i18n/index.js'

const DEFAULT_PATH = '/hivebr/config/default.yaml'
const emit = defineEmits(['close'])
const text = ref('')
const path = ref(DEFAULT_PATH)
const fileInput = ref(null)
const loadedFile = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref('')

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
        <input ref="fileInput" type="file" class="file" accept=".yaml,.yml,text/yaml,application/x-yaml" @change="onFile" />
      </div>
      <p v-if="loadedFile" class="loaded">{{ t('config.loaded_file', { name: loadedFile }) }}</p>
      <div v-if="loading" class="faint">{{ t('config.loading') }}</div>
      <textarea v-else v-model="text" class="input mono yaml" spellcheck="false" data-autofocus
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
.yaml {
  width: 100%; height: min(60vh, 520px); resize: vertical; padding: var(--sp-4);
  font-family: var(--font-mono); font-size: var(--fs-sm); line-height: 1.55;
  white-space: pre; overflow: auto; tab-size: 2;
}
.err { margin: var(--sp-4) 0 0; color: var(--danger); font-size: var(--fs-sm); white-space: pre-wrap; }
</style>
