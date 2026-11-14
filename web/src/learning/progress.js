// Learning progress: XP, stars, badges, achievements and the active activity.
//
// Persisted in localStorage under a versioned key, following the same pattern
// as hivebr.web.prefs.v1. Progress is local to the browser; export/import JSON
// is the bridge for classroom use until a backend exists.

import { reactive, watch } from 'vue'
import { ACHIEVEMENTS } from './curriculum.js'

export const LS_KEY = 'hivebr.web.learning.v1'

export const XP_THRESHOLDS = [0, 200, 500, 900]

function empty() {
  return {
    v: 1,
    xp: 0,
    activeId: null,
    activities: {},
    badges: [],
    achievements: [],
    updatedAt: 0,
  }
}

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

function load() {
  const data = lsGet(LS_KEY, null)
  if (!data || typeof data !== 'object') return empty()
  return {
    v: 1,
    xp: Math.max(0, Number(data.xp) || 0),
    activeId: typeof data.activeId === 'string' ? data.activeId : null,
    activities: data.activities && typeof data.activities === 'object' ? data.activities : {},
    badges: Array.isArray(data.badges) ? data.badges.filter((b) => typeof b === 'string') : [],
    achievements: Array.isArray(data.achievements) ? data.achievements.filter((b) => typeof b === 'string') : [],
    updatedAt: Number(data.updatedAt) || 0,
  }
}

function save() {
  lsSet(LS_KEY, {
    v: 1,
    xp: learning.xp,
    activeId: learning.activeId,
    activities: learning.activities,
    badges: learning.badges,
    achievements: learning.achievements,
    updatedAt: learning.updatedAt,
  })
}

export const learning = reactive(load())
watch(learning, save, { deep: true })

export function xpForLevel(level) {
  return XP_THRESHOLDS[level - 1] ?? null
}

export function levelForXp(xp) {
  let level = 1
  for (let i = 0; i < XP_THRESHOLDS.length; i += 1) {
    if (xp >= XP_THRESHOLDS[i]) level = i + 1
  }
  return level
}

export function isActivityDone(id) {
  return !!learning.activities[id]?.done
}

export function activityStars(id) {
  return learning.activities[id]?.stars ?? 0
}

export function hasBadge(id) {
  return learning.badges.includes(id)
}

export function hasAchievement(id) {
  return learning.achievements.includes(id)
}

export function setActiveActivity(id) {
  learning.activeId = id || null
  learning.updatedAt = Date.now()
}

/** Adds every achievement whose required activities are all done. */
export function syncAchievements() {
  const done = new Set(
    Object.entries(learning.activities)
      .filter(([, value]) => value?.done)
      .map(([id]) => id),
  )
  const newly = []
  for (const achievement of ACHIEVEMENTS) {
    if (learning.achievements.includes(achievement.id)) continue
    if (achievement.requires.every((id) => done.has(id))) {
      learning.achievements.push(achievement.id)
      newly.push(achievement)
    }
  }
  if (newly.length) learning.updatedAt = Date.now()
  return newly
}

export function completeActivity(activity, snapshot = {}, stars = 1) {
  if (!activity?.id) {
    return { first: false, xp: 0, badge: null, level: levelForXp(learning.xp), leveledUp: false, achievements: [] }
  }
  const previous = learning.activities[activity.id]
  const first = !previous?.done
  const beforeLevel = levelForXp(learning.xp)
  const bestStars = Math.max(previous?.stars || 0, stars)

  learning.activities[activity.id] = {
    done: true,
    stars: bestStars,
    at: Date.now(),
    evidence: snapshot.evidence || null,
  }
  if (first) learning.xp += Number(activity.xp) || 0
  if (activity.badge && !learning.badges.includes(activity.badge)) learning.badges.push(activity.badge)
  learning.updatedAt = Date.now()

  const achievements = syncAchievements()
  const level = levelForXp(learning.xp)
  return {
    first,
    xp: first ? Number(activity.xp) || 0 : 0,
    badge: first ? activity.badge : null,
    achievements,
    level,
    leveledUp: level > beforeLevel,
  }
}

export function resetProgress() {
  Object.assign(learning, empty())
  learning.updatedAt = Date.now()
}

export function exportProgress() {
  return JSON.stringify({
    v: 1,
    xp: learning.xp,
    activeId: learning.activeId,
    activities: learning.activities,
    badges: learning.badges,
    achievements: learning.achievements,
    updatedAt: learning.updatedAt,
  }, null, 2)
}

export function importProgress(json) {
  try {
    const data = JSON.parse(json)
    if (!data || typeof data !== 'object') return false
    learning.xp = Math.max(0, Number(data.xp) || 0)
    learning.activeId = typeof data.activeId === 'string' ? data.activeId : null
    learning.activities = data.activities && typeof data.activities === 'object' ? data.activities : {}
    learning.badges = Array.isArray(data.badges) ? data.badges.filter((b) => typeof b === 'string') : []
    learning.achievements = Array.isArray(data.achievements) ? data.achievements.filter((b) => typeof b === 'string') : []
    learning.updatedAt = Date.now()
    return true
  } catch {
    return false
  }
}
