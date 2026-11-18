<script setup>
import { computed, ref } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import {
  store, ask, catalog, loadExample, learningSnapshot, download, toast,
  createLearningReport, submitLearningReport, findLearningReport,
  learningBundlePayload, applyLearningBundle,
} from '../state/store.js'
import { t } from '../i18n/index.js'
import { LEVELS, ACTIVITIES, ACHIEVEMENTS, activitiesForLevel, activityById, trackById, finalActivityForLevel } from '../learning/curriculum.js'
import {
  learning, levelForXp, xpForLevel, isActivityDone, activityStars,
  hasBadge, hasAchievement, setActiveActivity, resetProgress,
} from '../learning/progress.js'
import {
  student, ensureStudent, setStudentName, setStudentGroup, resetStudent,
} from '../learning/identity.js'
import { encodeBundle, decodeBundle, inspectBundle, cryptoAvailable } from '../learning/bundle.js'
import { evaluateActivity } from '../learning/validate.js'
import { reportRubric } from '../learning/report.js'

ensureStudent()

const studentName = computed({
  get: () => student.name,
  set: (value) => setStudentName(value),
})
const studentGroup = computed({
  get: () => student.group,
  set: (value) => setStudentGroup(value),
})

const level = computed(() => levelForXp(learning.xp))
const nextLevelXp = computed(() => xpForLevel(level.value + 1))
const levelPct = computed(() => {
  const from = xpForLevel(level.value) ?? 0
  const to = nextLevelXp.value
  if (!to) return 100
  return Math.max(0, Math.min(100, Math.round(((learning.xp - from) / (to - from)) * 100)))
})

const stats = computed(() => {
  const out = {}
  for (const lv of LEVELS) {
    const list = activitiesForLevel(lv.id)
    const done = list.filter((a) => isActivityDone(a.id)).length
    out[lv.id] = { done, total: list.length, pct: list.length ? Math.round((done / list.length) * 100) : 0 }
  }
  return out
})

const activeActivity = computed(() => activityById(learning.activeId))

// ---- final projects (one per level) ----
const finals = computed(() => {
  const out = {}
  for (const lv of LEVELS) {
    const activity = finalActivityForLevel(lv.id)
    if (!activity) continue
    const goal = activity.goals?.[0] || {}
    const report = findLearningReport(lv.id)
    out[lv.id] = {
      activity,
      goal,
      report,
      done: isActivityDone(activity.id),
      rubric: reportRubric(report?.content || '', goal),
    }
  }
  return out
})
const importInput = ref(null)
const CHECK_KEYS = {
  marker: 'learn.report.check.marker',
  sections: 'learn.report.check.sections',
  words: 'learn.report.check.words',
  no_todo: 'learn.report.check.no_todo',
}
function checkText(check, goal = {}) {
  const key = CHECK_KEYS[check.id]
  if (!key) return check.id
  return t(key, {
    n: check.id === 'sections' ? (goal.sections ?? 5) : (goal.minWords ?? 300),
  })
}

const earnedBadges = computed(() => {
  const seen = new Set()
  const out = []
  for (const a of ACTIVITIES) {
    if (a.badge && hasBadge(a.badge) && !seen.has(a.badge)) {
      seen.add(a.badge)
      out.push({ id: a.badge, labelKey: a.badgeKey })
    }
  }
  return out
})

const earnedAchievements = computed(() => ACHIEVEMENTS.filter((a) => hasAchievement(a.id)))

const liveResults = computed(() => {
  if (!activeActivity.value || isActivityDone(activeActivity.value.id)) return []
  return evaluateActivity(activeActivity.value, learningSnapshot()).results
})

const GOAL_KEYS = {
  run_ok: 'learn.goal.run_ok',
  finish_lap: 'learn.goal.finish_lap',
  lap_time_max: 'learn.goal.lap_time_max',
  line_error_max: 'learn.goal.line_error_max',
  no_collision: 'learn.goal.no_collision',
  file_exists: 'learn.goal.file_exists',
  figure_min: 'learn.goal.figure_min',
  report_saved: 'learn.goal.report_saved',
  report_rubric: 'learn.goal.report_rubric',
  capture_saved: 'learn.goal.capture_saved',
  console_has: 'learn.goal.console_has',
  reach_goal: 'learn.goal.reach_goal',
  orientation_error_max: 'learn.goal.orientation_error_max',
  time_max: 'learn.goal.time_max',
  path_length_max: 'learn.goal.path_length_max',
  min_travel: 'learn.goal.min_travel',
  waypoint_count_min: 'learn.goal.waypoint_count_min',
  robot_count: 'learn.goal.robot_count',
  visit_points: 'learn.goal.visit_points',
  points_covered: 'learn.goal.points_covered',
  robot_reach: 'learn.goal.robot_reach',
  coverage_min: 'learn.goal.coverage_min',
  code_uses: 'learn.goal.code_uses',
}
function goalText(goal) {
  const key = GOAL_KEYS[goal.kind]
  if (!key) return goal.kind
  return t(key, {
    laps: goal.laps ?? 1,
    value: goal.value ?? 0,
    path: goal.path ?? '',
    min: goal.min ?? 1,
    text: goal.text ?? '',
    x: goal.x ?? 0,
    y: goal.y ?? 0,
    n: goal.n ?? goal.points?.length ?? goal.targets?.length ?? 1,
    tolerance: goal.tolerance ?? 0.4,
    percent: Math.round((Number(goal.value) || 0) * 100),
    sections: goal.sections ?? 5,
    words: goal.minWords ?? 300,
  })
}

function trackLabel(activity) {
  const track = trackById(activity.track)
  return track ? t(track.titleKey) : ''
}

function regularActivities(levelId) {
  return activitiesForLevel(levelId).filter((activity) => !activity.final)
}

async function start(activity) {
  if (activity.final) {
    createLearningReport(activity.level)
    setActiveActivity(activity.id)
    store.modals.learning = false
    return
  }
  const example = catalog.value.find((e) => e.id === activity.exampleId)
  if (example) {
    const ok = await loadExample(example)
    if (!ok) return
  }
  setActiveActivity(activity.id)
  store.modals.learning = false
}

async function reset() {
  const ok = await ask({
    title: t('learn.reset_title'),
    message: t('learn.reset_message'),
    confirmText: t('learn.reset_confirm'),
    danger: true,
  })
  if (ok) resetProgress()
}

function generateReport(levelId) {
  const { created } = createLearningReport(levelId)
  toast(t(created ? 'learn.report.generated' : 'learn.report.exists'))
  store.modals.learning = false
}

function submitReport(levelId) {
  const result = submitLearningReport(levelId)
  if (!result.ok) {
    toast(t('learn.report.incomplete'), 'warn')
    return
  }
  store.modals.learning = false
}

async function copyStudentId() {
  try {
    await navigator.clipboard.writeText(student.id)
    toast(t('learn.profile_copied'))
  } catch {
    toast(t('learn.profile_copy_failed'), 'warn')
  }
}

async function removeProfile() {
  const ok = await ask({
    title: t('learn.profile_remove_title'),
    message: t('learn.profile_remove_message'),
    confirmText: t('learn.profile_remove_confirm'),
    danger: true,
  })
  if (!ok) return
  resetStudent()
  ensureStudent()
  toast(t('learn.profile_removed'))
}

async function exportProgressFile() {
  ensureStudent()
  const canProtect = cryptoAvailable()
  const result = await ask({
    title: t('learn.export_title'),
    message: t(canProtect ? 'learn.export_message' : 'learn.export_insecure'),
    confirmText: t('learn.export_confirm'),
    fields: [
      { key: 'password', label: t('learn.export_password'), type: 'password', hint: t('learn.export_password_hint') },
      { key: 'confirm', label: t('learn.export_password_confirm'), type: 'password' },
      { key: 'captures', label: t('learn.export_captures'), type: 'checkbox', value: true },
      { key: 'tabs', label: t('learn.export_tabs'), type: 'checkbox', value: false },
    ],
  })
  if (!result) return
  const password = String(result.password || '')
  if (password !== String(result.confirm || '')) {
    toast(t('learn.export_password_mismatch'), 'warn')
    return
  }
  if (password && !canProtect) {
    toast(t('learn.export_crypto_unavailable'), 'error')
    return
  }
  let text
  try {
    const payload = learningBundlePayload({
      includeCaptures: result.captures === true,
      includeTabs: result.tabs === true,
    })
    text = await encodeBundle(payload, password)
  } catch (e) {
    toast(t('learn.export_failed', { error: String(e?.message || e) }), 'error')
    return
  }
  const suffix = student.id ? `-${student.id}` : ''
  download(`hivebr-progress${suffix}.json`, new Blob([text], { type: 'application/json' }))
  toast(t(password ? 'learn.export_done_protected' : 'learn.export_done'))
}

function pickImport() {
  importInput.value?.click()
}

async function onImportFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const text = await file.text()
  const info = inspectBundle(text)
  if (!info) {
    toast(t('learn.import_failed'), 'error')
    return
  }

  let password = ''
  if (info.encrypted) {
    const answer = await ask({
      title: t('learn.import_password_title'),
      message: t('learn.import_password_message'),
      confirmText: t('learn.import_confirm'),
      fields: [
        { key: 'password', label: t('learn.import_password'), type: 'password', hint: t('learn.import_password_hint') },
      ],
    })
    if (!answer) return
    password = String(answer.password || '')
    if (!password) {
      toast(t('learn.import_password_required'), 'warn')
      return
    }
  }

  let payload
  try {
    payload = await decodeBundle(text, password)
  } catch (e) {
    const key = String(e?.message) === 'wrong-password' ? 'learn.import_wrong_password' : 'learn.import_failed'
    toast(t(key), 'error')
    return
  }

  const progress = payload?.progress && typeof payload.progress === 'object' ? payload.progress : payload
  const importedStudent = payload?.student && typeof payload.student === 'object' ? payload.student : {}
  const xp = Math.max(0, Number(progress?.xp) || 0)
  const activities = progress?.activities && typeof progress.activities === 'object' ? Object.keys(progress.activities).length : 0
  const reportsCount = Array.isArray(payload?.reports) ? payload.reports.length : 0
  const who = importedStudent.name || importedStudent.id || t('learn.import_unknown_student')
  const different = !!importedStudent.id && !!student.id && importedStudent.id !== student.id
  const ok = await ask({
    title: t('learn.import_confirm_title'),
    message: t(different ? 'learn.import_confirm_message_other' : 'learn.import_confirm_message', {
      student: who, xp, activities, reports: reportsCount, current: student.id,
    }),
    confirmText: t('learn.import_confirm'),
  })
  if (!ok) return
  if (!applyLearningBundle(payload)) {
    toast(t('learn.import_failed'), 'error')
    return
  }
  toast(t('learn.import_done', { xp: learning.xp }))
}
</script>
<template>
  <Modal :title="t('learn.title')" :width="900" @close="store.modals.learning = false">
    <div class="head">
      <div class="xp">
        <Icon name="star" :size="16" />
        <b>{{ t('learn.xp', { xp: learning.xp }) }}</b>
        <span class="sep">·</span>
        <span>{{ t('learn.level_label', { n: level }) }}</span>
      </div>
      <div class="tools">
        <button class="btn ghost sm" @click="exportProgressFile"><Icon name="download" :size="13" />{{ t('learn.export') }}</button>
        <button class="btn ghost sm" @click="pickImport"><Icon name="upload" :size="13" />{{ t('learn.import') }}</button>
        <input ref="importInput" class="file-input" type="file" accept="application/json,.json" @change="onImportFile" />
        <button class="btn ghost sm" @click="reset"><Icon name="refresh" :size="13" />{{ t('learn.reset') }}</button>
      </div>
    </div>
    <div class="levelbar" :aria-label="t('learn.level_label', { n: level })">
      <i :style="{ width: levelPct + '%' }" />
    </div>

    <section class="profile" :aria-label="t('learn.profile')">
      <div class="profile-id">
        <span class="muted small">{{ t('learn.profile_id') }}</span>
        <b class="mono">{{ student.id }}</b>
        <button class="btn ghost sm" @click="copyStudentId"><Icon name="copy" :size="12" />{{ t('learn.profile_copy') }}</button>
      </div>
      <label class="field-inline">
        <span class="muted small">{{ t('learn.profile_name') }}</span>
        <input v-model="studentName" class="input" maxlength="60" />
      </label>
      <label class="field-inline">
        <span class="muted small">{{ t('learn.profile_group') }}</span>
        <input v-model="studentGroup" class="input" maxlength="60" />
      </label>
      <button class="btn ghost sm" @click="removeProfile"><Icon name="trash" :size="12" />{{ t('learn.profile_remove') }}</button>
    </section>

    <p class="intro">{{ t('learn.intro') }}</p>

    <p v-if="activeActivity" class="active">
      <Icon name="flag" :size="14" />
      <span><b>{{ t('learn.active') }}:</b> {{ t(activeActivity.titleKey) }}. {{ t('learn.active_hint') }}</span>
    </p>
    <ul v-if="liveResults.length" class="live" :aria-label="t('learn.goals')">
      <li v-for="(r, i) in liveResults" :key="i" :class="{ ok: r.ok }">
        <Icon :name="r.ok ? 'check' : 'dots'" :size="12" />{{ goalText(r.goal) }}
      </li>
    </ul>

    <section v-for="lv in LEVELS" :key="lv.id" class="lvl">
      <header class="lvl-h">
        <h3>{{ t(lv.labelKey) }}</h3>
        <span class="muted small">{{ t('learn.progress', { done: stats[lv.id].done, total: stats[lv.id].total }) }}</span>
      </header>
      <p class="muted small summary">{{ t(lv.summaryKey) }}</p>
      <div class="bar"><i :style="{ width: stats[lv.id].pct + '%' }" /></div>
      <div class="acts">
        <article v-for="a in regularActivities(lv.id)" :key="a.id" class="act" :data-activity-id="a.id">
          <div class="act-h">
            <b>{{ t(a.titleKey) }}</b>
            <span v-if="isActivityDone(a.id)" class="pill done"><Icon name="check" :size="12" />{{ t('learn.done') }}</span>
            <span v-else-if="learning.activeId === a.id" class="pill on">{{ t('learn.active') }}</span>
          </div>
          <p>{{ t(a.briefKey) }}</p>
          <div class="goals" :aria-label="t('learn.goals')">
            <span v-for="g in a.goals" :key="g.kind" class="tag">{{ goalText(g) }}</span>
          </div>
          <div class="act-f">
            <span class="muted small">{{ trackLabel(a) }}</span>
            <span class="stars">
              <Icon v-for="n in activityStars(a.id)" :key="n" name="star" :size="12" />
            </span>
            <span class="xp">{{ t('learn.xp', { xp: a.xp }) }}</span>
            <button class="btn primary sm" @click="start(a)">{{ isActivityDone(a.id) ? t('learn.continue') : t('learn.start') }}</button>
          </div>
        </article>
        <p v-if="!regularActivities(lv.id).length" class="muted small">{{ t('learn.no_activities') }}</p>
      </div>

      <section v-if="finals[lv.id]" class="final" :data-activity-id="finals[lv.id].activity.id">
        <header class="lvl-h">
          <h3>{{ t('learn.final') }} · {{ t(finals[lv.id].activity.titleKey) }}</h3>
          <span v-if="finals[lv.id].done" class="pill done"><Icon name="check" :size="12" />{{ t('learn.done') }}</span>
        </header>
        <p class="muted small summary">{{ t(finals[lv.id].activity.briefKey) }}</p>
        <div class="final-body">
          <div class="rubric">
            <b>{{ t('learn.report.rubric') }}</b>
            <ul>
              <li v-for="check in finals[lv.id].rubric.checks" :key="check.id" :class="{ ok: check.ok }">
                <Icon :name="check.ok ? 'check' : 'dots'" :size="12" />{{ checkText(check, finals[lv.id].goal) }}
              </li>
            </ul>
            <span class="muted small">{{ t('learn.report.words', { n: finals[lv.id].rubric.words }) }}</span>
          </div>
          <div class="final-actions">
            <button class="btn ghost sm" @click="generateReport(lv.id)">
              <Icon name="file" :size="13" />{{ t(finals[lv.id].report ? 'learn.report.open' : 'learn.report.generate') }}
            </button>
            <button class="btn primary sm" :disabled="finals[lv.id].done || !finals[lv.id].rubric.ok" @click="submitReport(lv.id)">
              <Icon name="check" :size="13" />{{ t('learn.report.submit') }}
            </button>
          </div>
        </div>
      </section>
    </section>

    <section class="badges">
      <h3>{{ t('learn.badges') }}</h3>
      <div v-if="earnedBadges.length" class="badge-list">
        <span v-for="b in earnedBadges" :key="b.id" class="badge"><Icon name="award" :size="14" />{{ t(b.labelKey) }}</span>
      </div>
      <p v-else class="muted small">{{ t('learn.no_badges') }}</p>
    </section>

    <section class="badges">
      <h3>{{ t('learn.achievements') }}</h3>
      <div v-if="earnedAchievements.length" class="badge-list">
        <span v-for="a in earnedAchievements" :key="a.id" class="badge"><Icon name="graduation" :size="14" />{{ t(a.labelKey) }}</span>
      </div>
      <p v-else class="muted small">{{ t('learn.no_achievements') }}</p>
    </section>
  </Modal>
</template>
<style scoped>
.head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-4); flex-wrap: wrap; }
.tools { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.file-input { display: none; }
.xp { display: flex; align-items: center; gap: var(--sp-2); color: var(--accent); font-size: var(--fs-md); }
.xp .sep { color: var(--text-muted); }
.levelbar { height: 6px; margin: var(--sp-3) 0 var(--sp-4); background: var(--surface-3); border-radius: var(--radius-pill); overflow: hidden; }
.levelbar i { display: block; height: 100%; background: var(--accent); transition: width var(--dur) var(--ease); }
.profile { display: flex; align-items: flex-end; gap: var(--sp-4); flex-wrap: wrap; margin: 0 0 var(--sp-5); padding: var(--sp-3) var(--sp-4); border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); }
.profile-id { display: flex; align-items: center; gap: var(--sp-2); }
.profile-id b { letter-spacing: 0.06em; }
.field-inline { display: flex; flex-direction: column; gap: 2px; min-width: 150px; }
.field-inline .input { height: 28px; }
.intro { margin: 0 0 var(--sp-5); color: var(--text-muted); font-size: var(--fs-sm); line-height: 1.5; }
.active { display: flex; align-items: flex-start; gap: var(--sp-3); margin: 0 0 var(--sp-5); padding: var(--sp-4) var(--sp-5); border: 1px solid var(--accent); border-radius: var(--radius); background: var(--accent-soft); color: var(--text); font-size: var(--fs-sm); }
.active svg { flex: none; color: var(--accent); margin-top: 2px; }
.live { display: flex; flex-direction: column; gap: 4px; margin: 0 0 var(--sp-5); padding: var(--sp-3) var(--sp-4); list-style: none; border: 1px dashed var(--border); border-radius: var(--radius); font-size: var(--fs-xs); color: var(--text-muted); }
.live li { display: flex; align-items: center; gap: 6px; }
.live li.ok { color: var(--accent); }
.lvl { margin-bottom: var(--sp-6); }
.lvl-h { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-4); }
.lvl-h h3 { margin: 0; font-size: var(--fs-md); }
.summary { margin: var(--sp-2) 0 var(--sp-3); }
.bar { height: 5px; background: var(--surface-3); border-radius: var(--radius-pill); overflow: hidden; margin-bottom: var(--sp-4); }
.bar i { display: block; height: 100%; background: var(--accent); transition: width var(--dur) var(--ease); }
.acts { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.act { display: flex; flex-direction: column; gap: var(--sp-3); padding: var(--sp-4); border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); }
.act-h { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); }
.act p { margin: 0; color: var(--text-muted); font-size: var(--fs-sm); line-height: 1.45; }
.goals { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: var(--radius-pill); font-size: var(--fs-xs); }
.pill.done { background: var(--surface-3); color: var(--text); }
.pill.on { background: var(--accent-soft); color: var(--accent); }
.act-f { margin-top: auto; display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; }
.act-f .btn { margin-left: auto; }
.stars { display: inline-flex; gap: 1px; color: var(--accent); }
.xp { font-size: var(--fs-xs); color: var(--text-muted); }
.badges h3 { margin: 0 0 var(--sp-3); font-size: var(--fs-md); }
.badge-list { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: var(--sp-2) 10px; border: 1px solid var(--accent); border-radius: var(--radius-pill); background: var(--accent-soft); color: var(--accent); font-size: var(--fs-sm); }
.final { margin: var(--sp-6) 0; padding: var(--sp-4) var(--sp-5); border: 1px dashed var(--accent); border-radius: var(--radius); background: var(--surface-2); }
.final-body { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-4); flex-wrap: wrap; }
.rubric { display: flex; flex-direction: column; gap: var(--sp-2); font-size: var(--fs-sm); }
.rubric ul { display: flex; flex-direction: column; gap: 4px; margin: 0; padding: 0; list-style: none; color: var(--text-muted); font-size: var(--fs-xs); }
.rubric li { display: flex; align-items: center; gap: 6px; }
.rubric li.ok { color: var(--accent); }
.final-actions { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
</style>
