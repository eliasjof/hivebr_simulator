<script setup>
import { ref, watch } from 'vue'
import Icon from './Icon.vue'
import Modal from './Modal.vue'
import {
  store, renameScript, deleteScript, downloadScript, openTab, toast,
} from '../state/store.js'
import { t } from '../i18n/index.js'

const props = defineProps({ tab: { type: Object, required: true } })
const emit = defineEmits(['close'])

const draftName = ref(props.tab.name)
const confirmDelete = ref(false)

watch(() => props.tab, (tab) => {
  draftName.value = tab?.name || ''
  confirmDelete.value = false
})

function saveName() {
  const name = draftName.value.trim()
  if (!name || name === props.tab.name) { draftName.value = props.tab.name; return }
  const updated = renameScript(props.tab.id, name)
  if (updated) {
    draftName.value = updated.name
    toast(t('script.renamed', { name: updated.name }))
  }
}

function saveFile() {
  downloadScript(props.tab.id === store.activeId ? null : props.tab)
}

function doDelete() {
  const name = props.tab.name
  deleteScript(props.tab.id)
  emit('close')
  toast(t('script.deleted', { name }))
}

function openIt() {
  openTab(props.tab.id)
  emit('close')
}
</script>

<template>
  <Modal :title="t('script.details')" :width="560" @close="emit('close')">
    <div class="script-view">
      <label class="script-lbl" for="script-name">{{ t('script.name') }}</label>
      <div class="script-edit">
        <input id="script-name" v-model="draftName" class="input mono" data-autofocus @keydown.enter.prevent="saveName" />
        <button class="btn sm" :disabled="!draftName.trim() || draftName.trim() === tab.name" @click="saveName"><Icon name="check" :size="12" />{{ t('script.rename') }}</button>
      </div>
      <p v-if="confirmDelete" class="script-warn">{{ t('script.confirm_delete') }}</p>
      <p v-else class="script-meta">{{ tab.name }}<span v-if="tab.open === false"> · {{ t('editor.closed_tag') }}</span></p>
    </div>
    <template #footer>
      <button class="btn sm" @click="openIt"><Icon name="open" :size="12" />{{ t('script.open') }}</button>
      <button class="btn sm" @click="saveFile"><Icon name="download" :size="12" />{{ t('script.download') }}</button>
      <span class="foot-sp" />
      <button v-if="!confirmDelete" class="btn sm danger" @click="confirmDelete = true"><Icon name="trash" :size="12" />{{ t('script.delete') }}</button>
      <template v-else>
        <button class="btn sm danger" @click="doDelete"><Icon name="trash" :size="12" />{{ t('script.delete') }}</button>
        <button class="btn sm ghost" @click="confirmDelete = false">{{ t('common.cancel') }}</button>
      </template>
    </template>
  </Modal>
</template>

<style scoped>
.script-view { display: flex; flex-direction: column; gap: var(--sp-4); }
.script-lbl { font-size: var(--fs-sm); color: var(--text-muted); }
.script-edit { display: flex; align-items: center; gap: var(--sp-3); }
.script-edit .input { flex: 1; }
.script-meta { margin: 0; color: var(--text-muted); font-size: var(--fs-sm); }
.script-warn { margin: 0; color: var(--danger); font-size: var(--fs-sm); }
.foot-sp { flex: 1; }
</style>
