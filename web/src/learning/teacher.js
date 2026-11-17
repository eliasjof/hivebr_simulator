// Teacher mode: a local class roster assembled from student bundles.
//
// There is no server: the teacher imports the JSON files exported by the
// students and this module keeps a read-only summary of each one. The keyword
// only gates the panel; it does not protect the data from DevTools, so official
// grading still needs a backend or a teacher-signed file.
//
// The roster lives in its own localStorage key, next to (not inside) the
// student progress, so a teacher can use the same browser without mixing data.

import { reactive } from 'vue'
import { ACTIVITIES, FINAL_ACTIVITIES, finalActivityForLevel } from './curriculum.js'
import { reportRubric } from './report.js'
import { levelForXp } from './progress.js'

export const TEACHER_KEY = 'hivebr.web.teacher.v1'
export const ROSTER_FORMAT = 'hivebr-roster'
export const ROSTER_VERSION = 1
export const MIN_KEYWORD = 4

/** Columns exported to the class sheet, in order. */
export const ROSTER_FIELDS = [
  'id', 'name', 'group', 'xp', 'level', 'activities', 'required', 'stars',
  'badges', 'achievements', 'report', 'words', 'exportedAt', 'importedAt',
]

function lsGet(key, fallback) {
  try {
    if (typeof localStorage === 'undefined') return fallback
    const value = localStorage.getItem(key)
    return value ? JSON.parse(value) : fallback
  } catch {
    return fallback
  }
}

function lsSet(key, value) {
  try {
    if (typeof localStorage === 'undefined') return
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage unavailable or full */
  }
}

function lsRemove(key) {
  try {
    if (typeof localStorage === 'undefined') return
    localStorage.removeItem(key)
  } catch {
    /* storage unavailable */
  }
}

function randomHex(bytes) {
  const out = new Uint8Array(bytes)
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(out)
  } else {
    for (let i = 0; i < bytes; i += 1) out[i] = Math.floor(Math.random() * 256)
  }
  return [...out].map((b) => b.toString(16).padStart(2, '0')).join('')
}

/**
 * Hashes the keyword so the plain text never reaches localStorage.
 * SHA-256 when WebCrypto is available; otherwise a small FNV-1a fallback that
 * still keeps the keyword out of the file (it is a gate, not a password vault).
 */
export async function hashKeyword(text) {
  const value = String(text ?? '')
  if (typeof crypto !== 'undefined' && crypto.subtle && typeof TextEncoder !== 'undefined') {
    const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
    return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('')
  }
  let hash = 0x811c9dc5
  for (const char of value) {
    hash ^= char.codePointAt(0)
    hash = Math.imul(hash, 0x01000193) >>> 0
  }
  return 'fnv1a-' + hash.toString(16).padStart(8, '0')
}

function emptyTeacher() {
  return {
    v: 1,
    configured: false,
    keyHash: '',
    salt: '',
    name: '',
    school: '',
    students: [],
    updatedAt: 0,
  }
}

function clampInt(value, min, max) {
  const n = Math.round(Number(value) || 0)
  return Math.max(min, Math.min(max, n))
}

function sanitizeStudent(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const id = typeof raw.id === 'string' ? raw.id.trim().slice(0, 24) : ''
  if (!id) return null
  const xp = Math.max(0, Number(raw.xp) || 0)
  const reportTotal = clampInt(raw.reportTotal, 0, 99) || FINAL_ACTIVITIES.length
  // Roster backups from before phase 7 only know the level 4 capstone.
  const rawDone = raw.reportDone != null
    ? clampInt(raw.reportDone, 0, 99)
    : (raw.reportOk === true ? 1 : 0)
  const reportDone = Math.min(rawDone, reportTotal)
  return {
    id,
    name: typeof raw.name === 'string' ? raw.name.trim().slice(0, 60) : '',
    group: typeof raw.group === 'string' ? raw.group.trim().slice(0, 60) : '',
    xp,
    // Always derived from XP so an updated bundle cannot keep a stale level.
    level: clampInt(levelForXp(xp), 1, 9),
    done: clampInt(raw.done, 0, 999),
    total: clampInt(raw.total, 0, 999),
    requiredDone: clampInt(raw.requiredDone, 0, 999),
    requiredTotal: clampInt(raw.requiredTotal, 0, 999),
    stars: clampInt(raw.stars, 0, 9999),
    badges: clampInt(raw.badges, 0, 999),
    achievements: clampInt(raw.achievements, 0, 999),
    reportHas: raw.reportHas === true,
    reportDone,
    reportTotal,
    // Complete means all four level reports pass, not just the capstone.
    reportOk: reportTotal > 0 && reportDone >= reportTotal,
    reportWords: clampInt(raw.reportWords, 0, 999999),
    exportedAt: Number(raw.exportedAt) || 0,
    importedAt: Number(raw.importedAt) || 0,
    source: typeof raw.source === 'string' ? raw.source.slice(0, 80) : '',
  }
}

function load() {
  const data = lsGet(TEACHER_KEY, null)
  if (!data || typeof data !== 'object' || Array.isArray(data)) return emptyTeacher()
  const out = emptyTeacher()
  out.configured = data.configured === true
  out.keyHash = typeof data.keyHash === 'string' ? data.keyHash : ''
  out.salt = typeof data.salt === 'string' ? data.salt : ''
  out.name = typeof data.name === 'string' ? data.name.trim().slice(0, 60) : ''
  out.school = typeof data.school === 'string' ? data.school.trim().slice(0, 60) : ''
  out.students = Array.isArray(data.students) ? data.students.map(sanitizeStudent).filter(Boolean) : []
  out.updatedAt = Number(data.updatedAt) || 0
  sortRoster(out.students)
  return out
}

function save() {
  lsSet(TEACHER_KEY, {
    v: 1,
    configured: teacher.configured,
    keyHash: teacher.keyHash,
    salt: teacher.salt,
    name: teacher.name,
    school: teacher.school,
    students: teacher.students,
    updatedAt: teacher.updatedAt,
  })
}

export const teacher = reactive(load())

// Explicit saves (instead of a deep watcher) keep the roster predictable when a
// bundle replaces a whole student entry.
function persist() {
  teacher.updatedAt = Date.now()
  save()
}

// ---- roster -----------------------------------------------------------------

function sortRoster(list) {
  list.sort((a, b) => (
    a.group.localeCompare(b.group)
    || a.name.localeCompare(b.name)
    || a.id.localeCompare(b.id)
  ))
  return list
}

/** Counts activities, stars and the report rubric for one progress object. */
export function summarizeProgress(progress = {}) {
  const activities = progress && typeof progress.activities === 'object' && progress.activities
    ? progress.activities
    : {}
  const known = new Set(ACTIVITIES.map((activity) => activity.id))
  const doneIds = Object.keys(activities).filter((id) => known.has(id) && activities[id]?.done === true)
  const required = ACTIVITIES.filter((activity) => !activity.optional && !activity.final)
  const xp = Math.max(0, Number(progress?.xp) || 0)
  const stars = doneIds.reduce(
    (sum, id) => sum + Math.max(0, Math.min(3, Number(activities[id]?.stars) || 0)),
    0,
  )
  return {
    xp,
    level: levelForXp(xp),
    done: doneIds.length,
    total: ACTIVITIES.length,
    requiredDone: required.filter((activity) => doneIds.includes(activity.id)).length,
    requiredTotal: required.length,
    stars,
    badges: Array.isArray(progress?.badges) ? progress.badges.filter((b) => typeof b === 'string').length : 0,
    achievements: Array.isArray(progress?.achievements)
      ? progress.achievements.filter((b) => typeof b === 'string').length
      : 0,
  }
}

/** Summary of every level report found inside a bundle. */
export function summarizeReport(reports) {
  const list = (Array.isArray(reports) ? reports : [])
    .filter((item) => item && item.learning && typeof item.content === 'string')
  const passed = new Set()
  let words = 0
  for (const report of list) {
    const level = Number(report.level) > 0 ? Number(report.level) : 4
    const goal = finalActivityForLevel(level)?.goals?.[0] || {}
    const rubric = reportRubric(report.content, goal)
    words += rubric.words
    if (rubric.ok) passed.add(level)
  }
  const reportTotal = FINAL_ACTIVITIES.length
  return {
    reportHas: list.length > 0,
    reportDone: passed.size,
    reportTotal,
    reportOk: reportTotal > 0 && passed.size >= reportTotal,
    reportWords: words,
  }
}

/**
 * Builds a roster entry from a decoded bundle payload.
 * Returns null when the file has no usable student identity or progress.
 */
export function rosterEntryFromBundle(payload, meta = {}) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
  const progress = payload.progress && typeof payload.progress === 'object' ? payload.progress : payload
  if (!Number.isFinite(Number(progress?.xp))) return null
  if (!progress?.activities || typeof progress.activities !== 'object' || Array.isArray(progress.activities)) return null
  const identity = payload.student && typeof payload.student === 'object' ? payload.student : {}
  const id = typeof identity.id === 'string' ? identity.id.trim().slice(0, 24) : ''
  if (!id) return null
  return sanitizeStudent({
    id,
    name: identity.name,
    group: identity.group,
    ...summarizeProgress(progress),
    ...summarizeReport(payload.reports),
    exportedAt: Number(payload.exportedAt) || Date.now(),
    importedAt: Date.now(),
    source: meta.source,
  })
}

/** Adds or refreshes a student. Older exports never overwrite newer ones. */
export function upsertStudent(entry) {
  const clean = sanitizeStudent(entry)
  if (!clean) return { added: false, updated: false, stale: false }
  const index = teacher.students.findIndex((item) => item.id === clean.id)
  if (index < 0) {
    teacher.students.push(clean)
    sortRoster(teacher.students)
    persist()
    return { added: true, updated: false, stale: false }
  }
  const current = teacher.students[index]
  if ((clean.exportedAt || 0) >= (current.exportedAt || 0)) {
    teacher.students[index] = clean
    sortRoster(teacher.students)
    persist()
    return { added: false, updated: true, stale: false }
  }
  current.importedAt = Math.max(current.importedAt || 0, clean.importedAt || 0)
  persist()
  return { added: false, updated: false, stale: true }
}

export function removeStudent(id) {
  const before = teacher.students.length
  teacher.students = teacher.students.filter((item) => item.id !== id)
  if (teacher.students.length === before) return false
  persist()
  return true
}

export function clearRoster() {
  teacher.students = []
  persist()
}

export function rosterSummary(entries = teacher.students) {
  const list = Array.isArray(entries) ? entries : []
  const students = list.length
  const totalXp = list.reduce((sum, item) => sum + (Number(item.xp) || 0), 0)
  return {
    students,
    averageXp: students ? Math.round(totalXp / students) : 0,
    reports: list.filter((item) => item.reportOk).length,
    completed: list.filter((item) => item.requiredTotal > 0 && item.requiredDone >= item.requiredTotal).length,
  }
}

// ---- keyword gate -----------------------------------------------------------

let sessionUnlocked = false

export function isSessionUnlocked() {
  return sessionUnlocked
}

export function lockSession() {
  sessionUnlocked = false
}

/** Sets (or replaces) the keyword and unlocks the current session. */
export async function setTeacherKey(keyword) {
  const clean = String(keyword ?? '').trim()
  if (clean.length < MIN_KEYWORD) return false
  teacher.salt = randomHex(8)
  teacher.keyHash = await hashKeyword(`${teacher.salt}:${clean}`)
  teacher.configured = true
  sessionUnlocked = true
  persist()
  return true
}

export async function checkTeacherKey(keyword) {
  if (!teacher.configured || !teacher.keyHash) return false
  const hash = await hashKeyword(`${teacher.salt}:${String(keyword ?? '').trim()}`)
  return hash === teacher.keyHash
}

export async function unlockTeacher(keyword) {
  const ok = await checkTeacherKey(keyword)
  if (ok) sessionUnlocked = true
  return ok
}

/** Forgets the keyword and the session; the roster is kept. */
export function clearTeacherKey() {
  teacher.configured = false
  teacher.keyHash = ''
  teacher.salt = ''
  sessionUnlocked = false
  persist()
}

export function setTeacherProfile({ name, school } = {}) {
  if (typeof name === 'string') teacher.name = name.trim().slice(0, 60)
  if (typeof school === 'string') teacher.school = school.trim().slice(0, 60)
  persist()
}

/** Removes the whole teacher state (keyword and roster). */
export function resetTeacher() {
  Object.assign(teacher, emptyTeacher())
  sessionUnlocked = false
  lsRemove(TEACHER_KEY)
}

// ---- export -----------------------------------------------------------------

function csvCell(value) {
  const text = value == null ? '' : String(value)
  if (!/[;"\r\n]/.test(text)) return text
  return `"${text.replace(/"/g, '""')}"`
}

function day(value) {
  const n = Number(value)
  if (!n) return ''
  try {
    return new Date(n).toISOString().slice(0, 10)
  } catch {
    return ''
  }
}

function fieldValue(entry, field) {
  switch (field) {
    case 'activities': return `${entry.done}/${entry.total}`
    case 'required': return `${entry.requiredDone}/${entry.requiredTotal}`
    case 'report': return `${entry.reportDone ?? 0}/${entry.reportTotal ?? 0}`
    case 'words': return entry.reportWords ?? 0
    case 'exportedAt':
    case 'importedAt': return day(entry[field])
    default: return entry[field] ?? ''
  }
}

/**
 * Class sheet as CSV. `headers` maps ROSTER_FIELDS to localized labels.
 */
export function rosterCsv(entries = teacher.students, { headers = {} } = {}) {
  const head = ROSTER_FIELDS.map((field) => csvCell(headers[field] ?? field))
  const lines = [head.join(';')]
  for (const entry of entries) {
    lines.push(ROSTER_FIELDS.map((field) => csvCell(fieldValue(entry, field))).join(';'))
  }
  // BOM + CRLF so Excel opens the accents correctly.
  return '\ufeff' + lines.join('\r\n') + '\r\n'
}

/** Portable backup of the roster (same file can be re-imported later). */
export function rosterPayload() {
  return {
    format: ROSTER_FORMAT,
    v: ROSTER_VERSION,
    exportedAt: Date.now(),
    name: teacher.name,
    school: teacher.school,
    students: teacher.students.map((item) => ({ ...item })),
  }
}

/** Merges a roster backup. Returns how many students were added or updated. */
export function applyRosterPayload(data) {
  if (!data || typeof data !== 'object' || data.format !== ROSTER_FORMAT) return 0
  if (!Array.isArray(data.students)) return 0
  if (!teacher.name && typeof data.name === 'string') teacher.name = data.name.trim().slice(0, 60)
  if (!teacher.school && typeof data.school === 'string') teacher.school = data.school.trim().slice(0, 60)
  let count = 0
  for (const raw of data.students) {
    const result = upsertStudent(raw)
    if (result.added || result.updated) count += 1
  }
  return count
}

export function isRosterPayload(data) {
  return !!data && typeof data === 'object' && data.format === ROSTER_FORMAT && Array.isArray(data.students)
}
