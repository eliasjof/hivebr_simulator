// Local student identity.
//
// This is not a login: it is a stable label stored in the browser so an
// exported bundle can be matched to a student. It lives in its own key, so
// resetting the learning progress keeps the identity.
//
// Crockford base32 alphabet: no I, L, O or U (easy to read aloud and type).

import { reactive, watch } from 'vue'

export const STUDENT_KEY = 'hivebr.web.student.v1'
export const ID_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

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

function randomBytes(n) {
  const out = new Uint8Array(n)
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(out)
    return out
  }
  for (let i = 0; i < n; i += 1) out[i] = Math.floor(Math.random() * 256)
  return out
}

/** Generates a readable identifier such as HB-7Q3M-9K2F. */
export function generateStudentId() {
  const bytes = randomBytes(8)
  const code = [...bytes].map((byte) => ID_ALPHABET[byte % 32]).join('')
  return `HB-${code.slice(0, 4)}-${code.slice(4)}`
}

function empty() {
  return { v: 1, id: '', name: '', group: '', createdAt: 0 }
}

function sanitize(data) {
  const out = empty()
  if (!data || typeof data !== 'object' || Array.isArray(data)) return out
  out.id = typeof data.id === 'string' ? data.id.trim().slice(0, 24) : ''
  out.name = typeof data.name === 'string' ? data.name.trim().slice(0, 60) : ''
  out.group = typeof data.group === 'string' ? data.group.trim().slice(0, 60) : ''
  out.createdAt = Number(data.createdAt) || 0
  return out
}

function load() {
  return sanitize(lsGet(STUDENT_KEY, null))
}

function save() {
  lsSet(STUDENT_KEY, {
    v: 1,
    id: student.id,
    name: student.name,
    group: student.group,
    createdAt: student.createdAt,
  })
}

export const student = reactive(load())
watch(student, save, { deep: true })

/** Creates the identifier on first use and returns the profile. */
export function ensureStudent() {
  if (!student.id) {
    student.id = generateStudentId()
    student.createdAt = Date.now()
  }
  return student
}

export function setStudentName(name) {
  student.name = String(name ?? '').trim().slice(0, 60)
}

export function setStudentGroup(group) {
  student.group = String(group ?? '').trim().slice(0, 60)
}

/** Applies a profile read from an imported bundle. */
export function applyStudent(data) {
  const clean = sanitize(data)
  if (!clean.id) return false
  Object.assign(student, clean)
  return true
}

/** Removes the profile; the next ensureStudent() creates a new identifier. */
export function resetStudent() {
  Object.assign(student, empty())
  lsRemove(STUDENT_KEY)
}

export function studentDisplayName() {
  if (!student.id) return ''
  return student.name ? `${student.name} (${student.id})` : student.id
}
