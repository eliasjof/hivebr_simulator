<script setup>
import { ref, watch } from 'vue'
import Icon from './Icon.vue'
import Modal from './Modal.vue'
import {
  renameReport, deleteReport, openReport, download, toast,
} from '../state/store.js'
import { t, locale } from '../i18n/index.js'
import { translateText } from '../services/translate.js'

const props = defineProps({ report: { type: Object, required: true } })
const emit = defineEmits(['close'])

const draftName = ref(props.report.name)
const confirmDelete = ref(false)
const translating = ref(false)

watch(() => props.report, (report) => {
  draftName.value = report?.name || ''
  confirmDelete.value = false
})

function saveName() {
  const name = draftName.value.trim()
  if (!name || name === props.report.name) { draftName.value = props.report.name; return }
  const updated = renameReport(props.report.id, name)
  if (updated) {
    draftName.value = updated.name
    toast(t('report.renamed', { name: updated.name }))
  }
}

function saveFile() {
  const name = /\.md$/i.test(props.report.name) ? props.report.name : `${props.report.name}.md`
  download(name, new Blob([props.report.content], { type: 'text/markdown' }))
}

function doDelete() {
  const name = props.report.name
  deleteReport(props.report.id)
  emit('close')
  toast(t('report.deleted', { name }))
}

function openIt() {
  openReport(props.report.id)
  emit('close')
}

async function translateReport() {
  if (translating.value) return
  translating.value = true
  try {
    const targetLang = locale.value === 'pt-BR' ? 'en' : 'pt-BR'
    const translated = await translateText(props.report.content, locale.value, targetLang)
    if (translated !== props.report.content) {
      // Update the report's content
      const report = store.reports.find(r => r.id === props.report.id)
      if (report) {
        report.content = translated
        report.modified = Date.now()
      }
      const langLabel = targetLang === 'pt-BR' ? t('lang.pt') : t('lang.en')
      toast(t('toast.translated', { lang: langLabel }))
    } else {
      toast(t('toast.translation_failed'), 'warn')
    }
  } finally {
    translating.value = false
  }
}
</script>

<template>
  <Modal :title="t('report.details')" :width="560" @close="emit('close')">
    <div class="report-view">
      <label class="report-lbl" for="report-name">{{ t('report.name') }}</label>
      <div class="report-edit">
        <input id="report-name" v-model="draftName" class="input mono" data-autofocus @keydown.enter.prevent="saveName" />
        <button class="btn sm" :disabled="!draftName.trim() || draftName.trim() === report.name" @click="saveName"><Icon name="check" :size="12" />{{ t('report.rename') }}</button>
      </div>
      <p v-if="confirmDelete" class="report-warn">{{ t('report.confirm_delete') }}</p>
      <p v-else class="report-meta">{{ report.name }}</p>
    </div>
    <template #footer>
      <button class="btn sm" @click="openIt"><Icon name="open" :size="12" />{{ t('report.open') }}</button>
      <button class="btn sm" @click="saveFile"><Icon name="download" :size="12" />{{ t('report.download') }}</button>
      <button class="btn sm" :disabled="translating" @click="translateReport"><Icon name="translate" :size="12" />{{ translating ? t('report.translating') : t('report.translate') }}</button>
      <span class="foot-sp" />
      <button v-if="!confirmDelete" class="btn sm danger" @click="confirmDelete = true"><Icon name="trash" :size="12" />{{ t('report.delete') }}</button>
      <template v-else>
        <button class="btn sm danger" @click="doDelete"><Icon name="trash" :size="12" />{{ t('report.delete') }}</button>
        <button class="btn sm ghost" @click="confirmDelete = false">{{ t('common.cancel') }}</button>
      </template>
    </template>
  </Modal>
</template>

<style scoped>
.report-view { display: flex; flex-direction: column; gap: var(--sp-4); }
.report-lbl { font-size: var(--fs-sm); color: var(--text-muted); }
.report-edit { display: flex; align-items: center; gap: var(--sp-3); }
.report-edit .input { flex: 1; }
.report-meta { margin: 0; color: var(--text-muted); font-size: var(--fs-sm); }
.report-warn { margin: 0; color: var(--danger); font-size: var(--fs-sm); }
.foot-sp { flex: 1; }
</style>
