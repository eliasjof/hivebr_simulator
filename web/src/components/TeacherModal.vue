<script setup>
import { computed, ref } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { store, ask, download, toast } from '../state/store.js'
import { t, fmtInt } from '../i18n/index.js'
import { decodeBundle, inspectBundle } from '../learning/bundle.js'
import {
  teacher, MIN_KEYWORD, ROSTER_FIELDS,
  setTeacherProfile, setTeacherKey, checkTeacherKey, unlockTeacher,
  isSessionUnlocked, lockSession, clearTeacherKey, resetTeacher,
  upsertStudent, removeStudent, clearRoster, rosterSummary,
  rosterEntryFromBundle, rosterCsv, rosterPayload, applyRosterPayload, isRosterPayload,
} from '../learning/teacher.js'

const phase = ref(teacher.configured ? (isSessionUnlocked() ? 'open' : 'locked') : 'setup')

const teacherName = ref(teacher.name)
const school = ref(teacher.school)
const keyword = ref('')
const keywordConfirm = ref('')
const unlockKey = ref('')
const busy = ref(false)
const fileInput = ref(null)

const summary = computed(() => rosterSummary(teacher.students))

const COLUMN_KEYS = {
  id: 'teacher.column.id',
  name: 'teacher.column.name',
  group: 'teacher.column.group',
  xp: 'teacher.column.xp',
  level: 'teacher.column.level',
  activities: 'teacher.column.activities',
  required: 'teacher.column.required',
  stars: 'teacher.column.stars',
  badges: 'teacher.column.badges',
  achievements: 'teacher.column.achievements',
  report: 'teacher.column.report',
  words: 'teacher.column.words',
  exportedAt: 'teacher.column.exported_at',
  importedAt: 'teacher.column.imported_at',
}

function close() {
  store.modals.teacher = false
}

async function activate() {
  if (keyword.value.trim().length < MIN_KEYWORD) {
    toast(t('teacher.keyword_short', { n: MIN_KEYWORD }), 'warn')
    return
  }
  if (keyword.value !== keywordConfirm.value) {
    toast(t('teacher.keyword_mismatch'), 'warn')
    return
  }
  setTeacherProfile({ name: teacherName.value, school: school.value })
  await setTeacherKey(keyword.value)
  keyword.value = ''
  keywordConfirm.value = ''
  phase.value = 'open'
  toast(t('teacher.enabled'))
}

async function unlock() {
  busy.value = true
  const ok = await unlockTeacher(unlockKey.value)
  busy.value = false
  if (!ok) {
    toast(t('teacher.unlock_failed'), 'error')
    return
  }
  unlockKey.value = ''
  phase.value = 'open'
}

function lock() {
  lockSession()
  phase.value = 'locked'
}

async function changeKey() {
  const answer = await ask({
    title: t('teacher.change_key'),
    message: t('teacher.change_key_message'),
    confirmText: t('common.ok'),
    fields: [
      { key: 'current', label: t('teacher.current_keyword'), type: 'password' },
      { key: 'next', label: t('teacher.keyword'), type: 'password' },
      { key: 'confirm', label: t('teacher.keyword_confirm'), type: 'password' },
    ],
  })
  if (!answer) return
  if (!(await checkTeacherKey(answer.current))) {
    toast(t('teacher.unlock_failed'), 'error')
    return
  }
  if (String(answer.next || '').trim().length < MIN_KEYWORD) {
    toast(t('teacher.keyword_short', { n: MIN_KEYWORD }), 'warn')
    return
  }
  if (answer.next !== answer.confirm) {
    toast(t('teacher.keyword_mismatch'), 'warn')
    return
  }
  await setTeacherKey(answer.next)
  toast(t('teacher.key_changed'))
}

async function forgetKey() {
  const ok = await ask({
    title: t('teacher.forget_key'),
    message: t('teacher.forget_key_message'),
    confirmText: t('teacher.forget_key_confirm'),
    danger: true,
  })
  if (!ok) return
  clearTeacherKey()
  phase.value = 'setup'
  toast(t('teacher.forgot'))
}

function pickFiles() {
  fileInput.value?.click()
}

async function onFiles(event) {
  const files = [...(event.target.files || [])]
  event.target.value = ''
  if (!files.length) return
  busy.value = true
  let imported = 0
  let skipped = 0
  let sharedPassword = null

  for (const file of files) {
    const text = await file.text().catch(() => '')
    let data = null
    try {
      data = JSON.parse(text)
    } catch {
      skipped += 1
      continue
    }
    if (isRosterPayload(data)) {
      imported += applyRosterPayload(data)
      continue
    }
    const info = inspectBundle(text)
    if (!info) {
      skipped += 1
      continue
    }
    let password = ''
    if (info.encrypted) {
      if (sharedPassword === null) {
        const answer = await ask({
          title: t('teacher.import_password_title'),
          message: t('teacher.import_password_message'),
          confirmText: t('common.ok'),
          fields: [
            { key: 'password', label: t('teacher.import_password'), type: 'password', hint: t('teacher.import_password_hint') },
          ],
        })
        if (!answer) break
        sharedPassword = String(answer.password || '')
      }
      password = sharedPassword
    }
    let payload
    try {
      payload = await decodeBundle(text, password)
    } catch {
      skipped += 1
      continue
    }
    const entry = rosterEntryFromBundle(payload, { source: file.name })
    if (!entry) {
      skipped += 1
      continue
    }
    const result = upsertStudent(entry)
    if (result.added || result.updated) imported += 1
    else skipped += 1
  }

  busy.value = false
  if (imported) toast(t('teacher.imported', { n: imported }))
  else toast(t('teacher.import_failed'), 'warn')
  if (skipped) toast(t('teacher.import_skipped', { n: skipped }), 'warn')
}

function reportLabel(entry) {
  if (entry.reportOk) return t('teacher.report_ok')
  if (entry.reportHas) return t('teacher.report_draft')
  return t('teacher.report_none')
}

function reportClass(entry) {
  if (entry.reportOk) return 'ok'
  if (entry.reportHas) return 'warn'
  return 'none'
}

function exportCsv() {
  const headers = {}
  for (const field of ROSTER_FIELDS) headers[field] = t(COLUMN_KEYS[field])
  const csv = rosterCsv(teacher.students, { headers, yes: t('teacher.yes'), no: t('teacher.no') })
  download(`hivebr-turma-${new Date().toISOString().slice(0, 10)}.csv`, new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  toast(t('teacher.export_csv_done'))
}

function exportBackup() {
  const data = JSON.stringify(rosterPayload(), null, 2)
  download(`hivebr-turma-${new Date().toISOString().slice(0, 10)}.json`, new Blob([data], { type: 'application/json' }))
  toast(t('teacher.backup_done'))
}

async function clearAll() {
  const ok = await ask({
    title: t('teacher.clear_title'),
    message: t('teacher.clear_message'),
    confirmText: t('teacher.clear_confirm'),
    danger: true,
  })
  if (!ok) return
  clearRoster()
  toast(t('teacher.cleared'))
}

async function removeOne(entry) {
  const ok = await ask({
    title: t('teacher.remove_title'),
    message: t('teacher.remove_message', { student: entry.name || entry.id }),
    confirmText: t('teacher.remove_confirm'),
    danger: true,
  })
  if (!ok) return
  if (removeStudent(entry.id)) toast(t('teacher.removed'))
}

async function eraseAll() {
  const ok = await ask({
    title: t('teacher.reset_title'),
    message: t('teacher.reset_message'),
    confirmText: t('teacher.reset_confirm'),
    danger: true,
  })
  if (!ok) return
  resetTeacher()
  phase.value = 'setup'
  toast(t('teacher.reset_done'))
}
</script>
<template>
  <Modal :title="t('teacher.title')" :width="980" @close="close">
    <form v-if="phase === 'setup'" class="panel" @submit.prevent="activate">
      <p class="hint">{{ t('teacher.setup_hint') }}</p>
      <label class="field">
        <span>{{ t('teacher.name') }}</span>
        <input id="tf-name" v-model="teacherName" class="input" maxlength="60" data-autofocus />
      </label>
      <label class="field">
        <span>{{ t('teacher.school') }}</span>
        <input id="tf-school" v-model="school" class="input" maxlength="60" />
      </label>
      <label class="field">
        <span>{{ t('teacher.keyword') }}</span>
        <input id="tf-keyword" v-model="keyword" class="input" type="password" autocomplete="new-password" />
        <small class="faint">{{ t('teacher.keyword_hint', { n: MIN_KEYWORD }) }}</small>
      </label>
      <label class="field">
        <span>{{ t('teacher.keyword_confirm') }}</span>
        <input id="tf-keyword-confirm" v-model="keywordConfirm" class="input" type="password" autocomplete="new-password" />
      </label>
      <button class="btn primary" type="submit"><Icon name="lock" :size="13" />{{ t('teacher.enable') }}</button>
    </form>

    <form v-else-if="phase === 'locked'" class="panel" @submit.prevent="unlock">
      <p class="hint">{{ t('teacher.unlock_hint') }}</p>
      <label class="field">
        <span>{{ t('teacher.keyword') }}</span>
        <input id="tf-unlock" v-model="unlockKey" class="input" type="password" autocomplete="current-password" data-autofocus />
      </label>
      <button class="btn primary" type="submit" :disabled="busy"><Icon name="lock" :size="13" />{{ t('teacher.unlock') }}</button>
    </form>

    <div v-else class="open">
      <div class="top">
        <div class="who">
          <label class="field-inline">
            <span>{{ t('teacher.name') }}</span>
            <input class="input" :value="teacher.name" maxlength="60" @change="setTeacherProfile({ name: $event.target.value })" />
          </label>
          <label class="field-inline">
            <span>{{ t('teacher.school') }}</span>
            <input class="input" :value="teacher.school" maxlength="60" @change="setTeacherProfile({ school: $event.target.value })" />
          </label>
        </div>
        <div class="tools">
          <button class="btn ghost sm" @click="changeKey"><Icon name="lock" :size="12" />{{ t('teacher.change_key') }}</button>
          <button class="btn ghost sm" @click="forgetKey"><Icon name="refresh" :size="12" />{{ t('teacher.forget_key') }}</button>
          <button class="btn ghost sm" @click="lock"><Icon name="close" :size="12" />{{ t('teacher.lock') }}</button>
        </div>
      </div>

      <div class="stats">
        <span class="stat"><b>{{ fmtInt(summary.students) }}</b> {{ t('teacher.students') }}</span>
        <span class="stat"><b>{{ fmtInt(summary.averageXp) }}</b> {{ t('teacher.average_xp') }}</span>
        <span class="stat"><b>{{ fmtInt(summary.reports) }}</b> {{ t('teacher.reports') }}</span>
        <span class="stat"><b>{{ fmtInt(summary.completed) }}</b> {{ t('teacher.completed') }}</span>
      </div>

      <div class="bar">
        <button class="btn primary sm" :disabled="busy" @click="pickFiles"><Icon name="upload" :size="13" />{{ t('teacher.import') }}</button>
        <button class="btn ghost sm" :disabled="!teacher.students.length" @click="exportCsv"><Icon name="table" :size="13" />{{ t('teacher.export_csv') }}</button>
        <button class="btn ghost sm" :disabled="!teacher.students.length" @click="exportBackup"><Icon name="download" :size="13" />{{ t('teacher.export_backup') }}</button>
        <button class="btn ghost sm" :disabled="!teacher.students.length" @click="clearAll"><Icon name="trash" :size="13" />{{ t('teacher.clear') }}</button>
        <button class="btn ghost sm" @click="eraseAll"><Icon name="refresh" :size="13" />{{ t('teacher.reset') }}</button>
        <input ref="fileInput" class="teacher-file" type="file" accept="application/json,.json" multiple @change="onFiles" />
      </div>
      <p class="hint small">{{ t('teacher.import_hint') }}</p>

      <p v-if="!teacher.students.length" class="empty">{{ t('teacher.empty') }}</p>
      <table v-else class="roster">
        <thead>
          <tr>
            <th>{{ t('teacher.column.name') }}</th>
            <th>{{ t('teacher.column.id') }}</th>
            <th class="num">{{ t('teacher.column.xp') }}</th>
            <th class="num">{{ t('teacher.column.level') }}</th>
            <th class="num">{{ t('teacher.column.required') }}</th>
            <th class="num">{{ t('teacher.column.stars') }}</th>
            <th class="num">{{ t('teacher.column.badges') }}</th>
            <th>{{ t('teacher.column.report') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in teacher.students" :key="entry.id" :data-student-id="entry.id">
            <td class="who-cell">
              <b>{{ entry.name || t('teacher.no_name') }}</b>
              <span class="muted small">{{ entry.group || t('teacher.no_group') }}</span>
            </td>
            <td class="mono small">{{ entry.id }}</td>
            <td class="num">{{ fmtInt(entry.xp) }}</td>
            <td class="num">{{ entry.level }}</td>
            <td class="num">{{ entry.requiredDone }}/{{ entry.requiredTotal }}</td>
            <td class="num">{{ entry.stars }}</td>
            <td class="num">{{ entry.badges }}</td>
            <td>
              <span class="pill" :class="reportClass(entry)">{{ reportLabel(entry) }}</span>
            </td>
            <td class="num">
              <button class="btn ghost icon sm" :aria-label="t('teacher.remove')" :data-tip="t('teacher.remove')" @click="removeOne(entry)">
                <Icon name="trash" :size="12" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </Modal>
</template>
<style scoped>
.panel { display: flex; flex-direction: column; gap: var(--sp-4); max-width: 420px; margin: 0 auto; padding: var(--sp-4) 0 var(--sp-2); }
.hint { margin: 0; color: var(--text-muted); font-size: var(--fs-sm); line-height: 1.5; }
.hint.small { font-size: var(--fs-xs); margin: 0 0 var(--sp-4); }
.field { display: flex; flex-direction: column; gap: 4px; }
.field span { font-size: var(--fs-sm); color: var(--text-muted); }
.field-inline { display: flex; flex-direction: column; gap: 2px; min-width: 180px; }
.field-inline span { font-size: var(--fs-xs); color: var(--text-muted); }
.field-inline .input { height: 28px; }
.top { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--sp-4); flex-wrap: wrap; margin-bottom: var(--sp-4); }
.who { display: flex; align-items: flex-end; gap: var(--sp-4); flex-wrap: wrap; }
.tools { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.stats { display: flex; gap: var(--sp-5); flex-wrap: wrap; margin-bottom: var(--sp-4); padding: var(--sp-3) var(--sp-4); border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); font-size: var(--fs-xs); color: var(--text-muted); }
.stat b { color: var(--accent); font-size: var(--fs-md); }
.bar { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.teacher-file { display: none; }
.empty { padding: var(--sp-6); text-align: center; color: var(--text-muted); border: 1px dashed var(--border); border-radius: var(--radius); }
.roster { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); }
.roster th { text-align: left; font-weight: 500; color: var(--text-muted); font-size: var(--fs-xs); padding: 0 var(--sp-3) var(--sp-2); border-bottom: 1px solid var(--border); white-space: nowrap; }
.roster td { padding: var(--sp-2) var(--sp-3); border-bottom: 1px solid var(--border); vertical-align: middle; }
.roster tr:last-child td { border-bottom: none; }
.roster .num { text-align: right; }
.who-cell { display: flex; flex-direction: column; }
.pill { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: var(--radius-pill); font-size: var(--fs-xs); white-space: nowrap; }
.pill.ok { background: var(--accent-soft); color: var(--accent); }
.pill.warn { background: var(--warn-soft); color: var(--warn); }
.pill.none { background: var(--surface-3); color: var(--text-muted); }
</style>
