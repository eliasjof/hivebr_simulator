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

  // --- deliverables ---
  file_exists: (goal, ctx) => {
    const wanted = String(goal.path || '').replace(/\\/g, '/')
    if (!wanted) return false
    return (ctx.finished?.files || []).some((f) => String(f?.path || '').replace(/\\/g, '/').endsWith(wanted))
  },

  figure_min: (goal, ctx) => (ctx.figures?.length ?? 0) >= (goal.min ?? 1),

  report_saved: (goal, ctx) => (ctx.reports?.length ?? 0) >= (goal.min ?? 1),

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
