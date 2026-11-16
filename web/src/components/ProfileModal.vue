<script setup>
import { computed, ref } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { store, toast, syncLearningReportIdentity } from '../state/store.js'
import { t, locale } from '../i18n/index.js'
import { student, ensureStudent, setStudentName, setStudentGroup, resetStudent } from '../learning/identity.js'

ensureStudent()

const name = ref(student.name)
const group = ref(student.group)
const dirty = computed(() => name.value.trim() !== student.name || group.value.trim() !== student.group)

const created = computed(() => {
  if (!student.createdAt) return ''
  try {
    return new Date(student.createdAt).toLocaleDateString(locale.value)
  } catch {
    return ''
  }
})

function close() {
  store.modals.profile = false
}

function save() {
  setStudentName(name.value)
  setStudentGroup(group.value)
  syncLearningReportIdentity()
  toast(t('student.profile_saved'))
  close()
}

async function copyId() {
  try {
    await navigator.clipboard.writeText(student.id)
    toast(t('learn.profile_copied'))
  } catch {
    toast(t('learn.profile_copy_failed'), 'warn')
  }
}

function newIdentity() {
  resetStudent()
  ensureStudent()
  name.value = ''
  group.value = ''
  toast(t('learn.profile_removed'))
}
</script>
<template>
  <Modal :title="t('student.profile_title')" :width="520" @close="close">
    <p class="hint">{{ t('student.profile_hint') }}</p>
    <div class="id-row">
      <span class="muted small">{{ t('learn.profile_id') }}</span>
      <b class="mono">{{ student.id }}</b>
      <button class="btn ghost sm" @click="copyId"><Icon name="copy" :size="12" />{{ t('learn.profile_copy') }}</button>
      <span v-if="created" class="muted small">· {{ t('student.profile_created', { date: created }) }}</span>
    </div>
    <label class="field">
      <span>{{ t('learn.profile_name') }}</span>
      <input id="sp-name" v-model="name" class="input" maxlength="60" :placeholder="t('student.profile_name_placeholder')" data-autofocus />
    </label>
    <label class="field">
      <span>{{ t('learn.profile_group') }}</span>
      <input id="sp-group" v-model="group" class="input" maxlength="60" :placeholder="t('student.profile_group_placeholder')" />
    </label>
    <p class="note">{{ t('student.profile_report_hint') }}</p>
    <template #footer>
      <button class="btn ghost" @click="newIdentity"><Icon name="refresh" :size="13" />{{ t('student.profile_new_id') }}</button>
      <span class="spacer" />
      <button class="btn" @click="close">{{ t('common.cancel') }}</button>
      <button class="btn primary" :disabled="!dirty" @click="save">{{ t('student.profile_save') }}</button>
    </template>
  </Modal>
</template>
<style scoped>
.hint { margin: 0 0 var(--sp-4); color: var(--text-muted); font-size: var(--fs-sm); line-height: 1.5; }
.id-row { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; margin-bottom: var(--sp-5); padding: var(--sp-3) var(--sp-4); border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); }
.id-row b { letter-spacing: 0.06em; }
.field { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--sp-4); }
.field span { font-size: var(--fs-sm); color: var(--text-muted); }
.note { margin: 0; color: var(--text-muted); font-size: var(--fs-xs); line-height: 1.5; }
.spacer { flex: 1; }
</style>
