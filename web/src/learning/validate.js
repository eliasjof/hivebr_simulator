// Goal checks for learning activities.
//
// Every check is a pure function over a run context:
//   {
//     finished: { ok, stopped, error, files } | null,
//     evidence: { t, laps, bestLap, maxLineError, lineSamples, collisions, ... },
//     figures: [], reports: [], captures: [], console: [],
//   }
// Behaviour is checked first; source-code checks are deliberately secondary.

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
