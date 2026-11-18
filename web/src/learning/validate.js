// Goal checks for learning activities.
//
// Every check is a pure function over a run context:
//   {
//     finished: { ok, stopped, error, files } | null,
//     evidence: {
//       t, laps, bestLap, maxLineError, lineSamples, collisions,
//       trail, trails, pathLength, pathLengthAtGoal, reachTime,
//       waypointCount, wpTotal, robots, source,
//     },
//     figures: [], reports: [], captures: [], console: [], source: '',
//   }
// Behaviour is checked first; source-code checks are deliberately secondary.

import { reportRubric } from './report.js'

function wrapAngle(angle) {
  return Math.atan2(Math.sin(angle), Math.cos(angle))
}

function trailOf(ctx) {
  const ev = ctx?.evidence || {}
  if (Array.isArray(ev.trail) && ev.trail.length) return ev.trail
  if (Array.isArray(ev.trails) && Array.isArray(ev.trails[0])) return ev.trails[0]
  return []
}

function distanceTo(point, x, y) {
  return Math.hypot(Number(point.x) - x, Number(point.y) - y)
}

/** Length of the polyline described by a trail. */
export function trailLength(trail) {
  let total = 0
  for (let i = 1; i < (trail?.length || 0); i += 1) {
    total += Math.hypot(trail[i].x - trail[i - 1].x, trail[i].y - trail[i - 1].y)
  }
  return total
}

/** Closest distance from the trail to (x, y), or Infinity when empty. */
export function trailMinDistance(trail, x, y) {
  let best = Infinity
  for (const point of trail || []) {
    const d = distanceTo(point, x, y)
    if (d < best) best = d
  }
  return best
}

/**
 * Visits a list of points in order. Each point is matched to the first trail
 * sample after the previous match, so a route that passes the stations in the
 * wrong order does not count.
 */
export function trailVisitsInOrder(trail, points) {
  const list = Array.isArray(points) ? points : []
  if (!list.length || !Array.isArray(trail) || !trail.length) return false
  let start = 0
  for (const point of list) {
    const x = Number(point?.x)
    const y = Number(point?.y)
    if (!Number.isFinite(x) || !Number.isFinite(y)) return false
    const tolerance = Number(point.tolerance) || 0.5
    let found = -1
    for (let i = start; i < trail.length; i += 1) {
      if (distanceTo(trail[i], x, y) <= tolerance) {
        found = i
        break
      }
    }
    if (found < 0) return false
    start = found + 1
  }
  return true
}

/** Fraction of an arena covered by the trail, on a grid of `cell` metres. */
export function coverageFraction(trail, { width = 20, height = 12, cell = 1 } = {}) {
  const w = Number(width)
  const h = Number(height)
  const size = Number(cell)
  if (!Array.isArray(trail) || !trail.length || !(w > 0) || !(h > 0) || !(size > 0)) return 0
  const cols = Math.max(1, Math.ceil(w / size))
  const rows = Math.max(1, Math.ceil(h / size))
  const seen = new Set()
  for (const point of trail) {
    const x = Number(point?.x)
    const y = Number(point?.y)
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue
    const cx = Math.floor(x / size)
    const cy = Math.floor(y / size)
    if (cx >= 0 && cx < cols && cy >= 0 && cy < rows) seen.add(cy * cols + cx)
  }
  return seen.size / (cols * rows)
}

export const GOAL_CHECKS = {
  run_ok: (_goal, ctx) => ctx.finished?.ok === true,

  finish_lap: (goal, ctx) => (ctx.evidence?.laps ?? 0) >= (goal.laps ?? 1),

  lap_time_max: (goal, ctx) => {
    const best = ctx.evidence?.bestLap
    return best != null && best <= goal.value
  },

  line_error_max: (goal, ctx) => {
    if (!ctx.evidence?.lineSamples) return false
    return (ctx.evidence.maxLineError ?? 0) <= goal.value
  },

  no_collision: (_goal, ctx) => (ctx.evidence?.collisions ?? 0) === 0,

  // --- geometric / performance goals (phase 3) ---
  reach_goal: (goal, ctx) => {
    if (!Number.isFinite(goal.x) || !Number.isFinite(goal.y)) return false
    const tolerance = goal.tolerance ?? 0.4
    return trailMinDistance(trailOf(ctx), goal.x, goal.y) <= tolerance
  },

  orientation_error_max: (goal, ctx) => {
    if (!Number.isFinite(goal.x) || !Number.isFinite(goal.y) || !Number.isFinite(goal.theta)) return false
    const tolerance = goal.tolerance ?? 0.4
    const trail = trailOf(ctx)
    // Use the last point inside the goal tolerance: the robot may rotate in
    // place after arriving, and that final heading is the one that matters.
    let chosen = null
    for (const point of trail) {
      if (distanceTo(point, goal.x, goal.y) <= tolerance) chosen = point
    }
    if (!chosen || !Number.isFinite(chosen.theta)) return false
    return Math.abs(wrapAngle(chosen.theta - goal.theta)) <= goal.value
  },

  time_max: (goal, ctx) => {
    const t = ctx.evidence?.reachTime ?? ctx.evidence?.t
    return t != null && t <= goal.value
  },

  path_length_max: (goal, ctx) => {
    const length = ctx.evidence?.pathLengthAtGoal ?? ctx.evidence?.pathLength
    return length != null && length <= goal.value
  },

  min_travel: (goal, ctx) => (ctx.evidence?.pathLength ?? 0) >= goal.value,

  waypoint_count_min: (goal, ctx) => (ctx.evidence?.waypointCount ?? 0) >= (goal.n ?? 1),

  robot_count: (goal, ctx) => (ctx.evidence?.robots ?? 0) >= (goal.n ?? 1),

  // --- contextual applications (phase 5) ---
  // Every station must be visited in order; passing near the last one first
  // does not satisfy the goal.
  visit_points: (goal, ctx) => trailVisitsInOrder(trailOf(ctx), goal.points),

  // Each robot has its own trail. With `targets`, robot i must reach
  // targets[i]; with x/y, every robot must reach the same point.
  robot_reach: (goal, ctx) => {
    const trails = Array.isArray(ctx.evidence?.trails) ? ctx.evidence.trails : []
    if (Array.isArray(goal.targets) && goal.targets.length) {
      return goal.targets.every((target, i) => {
        const trail = trails[i]
        if (!Array.isArray(trail) || !trail.length) return false
        const x = Number(target?.x)
        const y = Number(target?.y)
        if (!Number.isFinite(x) || !Number.isFinite(y)) return false
        return trailMinDistance(trail, x, y) <= (Number(target.tolerance) || goal.tolerance || 0.5)
      })
    }
    if (!Number.isFinite(goal.x) || !Number.isFinite(goal.y)) return false
    const count = Math.max(1, Number(goal.n) || trails.length)
    const list = trails.slice(0, count)
    if (!list.length) return false
    const tolerance = Number(goal.tolerance) || 0.5
    return list.every((trail) => trailMinDistance(trail, goal.x, goal.y) <= tolerance)
  },

  // Every inventory point must be visited by at least one robot trail. Unlike
  // visit_points, the order across robots does not matter: the fleet works in
  // parallel and each station only needs one visit.
  points_covered: (goal, ctx) => {
    const trails = Array.isArray(ctx.evidence?.trails) ? ctx.evidence.trails : []
    const points = Array.isArray(goal.points) ? goal.points : []
    if (!points.length || !trails.length) return false
    const fallback = Number(goal.tolerance) || 0.6
    return points.every((point) => {
      const x = Number(point?.x)
      const y = Number(point?.y)
      if (!Number.isFinite(x) || !Number.isFinite(y)) return false
      const tolerance = Number(point.tolerance) || fallback
      return trails.some((trail) => (
        Array.isArray(trail) && trailMinDistance(trail, x, y) <= tolerance
      ))
    })
  },

  // Fraction of an arena covered by the trail (agricultural coverage).
  coverage_min: (goal, ctx) => {
    const fraction = coverageFraction(trailOf(ctx), {
      width: goal.width ?? 20,
      height: goal.height ?? 12,
      cell: goal.cell ?? 1,
    })
    return fraction >= (Number(goal.value) || 0)
  },

  // --- SCARA cell ---
  // Parts placed in the matching basket during the run.
  scara_placed: (goal, ctx) => (ctx.evidence?.scaraPlaced ?? 0) >= (goal.min ?? 1),

  // --- deliverables ---
  file_exists: (goal, ctx) => {
    const wanted = String(goal.path || '').replace(/\\/g, '/')
    if (!wanted) return false
    return (ctx.finished?.files || []).some((f) => String(f?.path || '').replace(/\\/g, '/').endsWith(wanted))
  },

  figure_min: (goal, ctx) => (ctx.figures?.length ?? 0) >= (goal.min ?? 1),

  report_saved: (goal, ctx) => (ctx.reports?.length ?? 0) >= (goal.min ?? 1),

  // The final report must have every section, enough prose and no TODO left.
  // When the goal names a level, only that level's learning report counts; the
  // legacy capstone report (no level) is treated as level 4.
  report_rubric: (goal, ctx) => (ctx.reports || []).some((report) => {
    if (goal.level != null) {
      const level = Number(report?.level) || 4
      if (report?.learning !== true || level !== Number(goal.level)) return false
    }
    return reportRubric(report?.content || '', goal).ok
  }),

  capture_saved: (goal, ctx) => (ctx.captures?.length ?? 0) >= (goal.min ?? 1),

  console_has: (goal, ctx) => {
    const wanted = String(goal.text || '')
    if (!wanted) return false
    return (ctx.console || []).some((line) => String(line?.text ?? line).includes(wanted))
  },

  // Secondary check: the source contains a token. Never the only goal.
  code_uses: (goal, ctx) => {
    const wanted = String(goal.text || '')
    if (!wanted) return false
    return String(ctx.source || '').includes(wanted)
  },
}

export function checkGoal(goal, ctx) {
  const fn = GOAL_CHECKS[goal?.kind]
  return fn ? !!fn(goal, ctx) : false
}

export function evaluateActivity(activity, ctx) {
  const results = (activity?.goals || []).map((goal) => ({ goal, ok: checkGoal(goal, ctx) }))
  return { ok: results.length > 0 && results.every((r) => r.ok), results }
}

/** 1 star for completing the activity, +1 per optional performance goal (max 3). */
export function starsFor(activity, ctx) {
  const extra = (activity?.starGoals || []).filter((goal) => checkGoal(goal, ctx)).length
  return Math.min(3, 1 + extra)
}
