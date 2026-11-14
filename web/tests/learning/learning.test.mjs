// Learning curriculum integrity + pure goal checks.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  ACTIVITIES, ACHIEVEMENTS, LEVELS, TRACKS, LEVEL_IDS,
  activitiesForLevel, activityById, trackById,
} from '../../src/learning/curriculum.js'
import {
  GOAL_CHECKS, checkGoal, evaluateActivity, starsFor, trailLength, trailMinDistance,
} from '../../src/learning/validate.js'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const WEB = path.resolve(HERE, '..', '..')
const catalog = fs.readFileSync(path.join(WEB, 'src', 'examples', 'catalog.js'), 'utf8')

const exampleIds = new Set([
  ...catalog.matchAll(/\bid:\s*'([^']+)'/g),
].map((m) => m[1]))
exampleIds.add('demonstracao') // defined through DEMO_EXAMPLE_ID

test('curriculum references only real examples and known goal kinds', () => {
  const ids = new Set()
  for (const activity of ACTIVITIES) {
    assert.ok(!ids.has(activity.id), `duplicate activity id: ${activity.id}`)
    ids.add(activity.id)

    assert.ok(LEVEL_IDS.includes(activity.level), `invalid level in ${activity.id}`)
    assert.ok(exampleIds.has(activity.exampleId), `unknown example in ${activity.id}: ${activity.exampleId}`)
    assert.ok(trackById(activity.track), `unknown track in ${activity.id}: ${activity.track}`)
    assert.ok(activity.titleKey && activity.briefKey, `missing i18n keys in ${activity.id}`)
    assert.ok(Number(activity.xp) > 0, `missing xp in ${activity.id}`)

    for (const goal of [...activity.goals, ...(activity.starGoals || [])]) {
      assert.ok(GOAL_CHECKS[goal.kind], `unknown goal kind in ${activity.id}: ${goal.kind}`)
    }
  }

  for (const level of LEVELS) {
    assert.ok(LEVEL_IDS.includes(level.id), `invalid level id: ${level.id}`)
    assert.ok(level.labelKey && level.summaryKey, `missing level i18n keys: ${level.id}`)
  }
  for (const track of TRACKS) {
    assert.ok(track.titleKey && track.summaryKey, `missing track i18n keys: ${track.id}`)
  }
})

test('helpers filter activities and find entries', () => {
  assert.equal(activityById('primeiro-movimento')?.level, 1)
  assert.equal(activityById('missing'), null)
  assert.equal(trackById('linha')?.level, 2)
  assert.ok(activitiesForLevel(2).length >= 1)
})

const ctx = {
  finished: {
    ok: true, stopped: true, error: null,
    files: [{ path: '/home/pyodide/config/line_track.png', size: 10 }],
  },
  evidence: {
    t: 12, laps: 2, bestLap: 18.5, maxLineError: 0.03, lineSamples: 10, collisions: 0,
  },
  figures: [{}, {}],
  reports: [{}],
  captures: [],
  console: [{ kind: 'out', text: 'lap complete' }],
}

test('goal checks cover run, lap, line, collision, files and deliverables', () => {
  assert.equal(checkGoal({ kind: 'run_ok' }, ctx), true)
  assert.equal(checkGoal({ kind: 'run_ok' }, { ...ctx, finished: { ok: false } }), false)

  assert.equal(checkGoal({ kind: 'finish_lap', laps: 1 }, ctx), true)
  assert.equal(checkGoal({ kind: 'finish_lap', laps: 3 }, ctx), false)

  assert.equal(checkGoal({ kind: 'lap_time_max', value: 20 }, ctx), true)
  assert.equal(checkGoal({ kind: 'lap_time_max', value: 10 }, ctx), false)

  assert.equal(checkGoal({ kind: 'line_error_max', value: 0.05 }, ctx), true)
  assert.equal(checkGoal({ kind: 'line_error_max', value: 0.01 }, ctx), false)
  assert.equal(checkGoal({ kind: 'line_error_max', value: 0.05 }, { ...ctx, evidence: { lineSamples: 0 } }), false)

  assert.equal(checkGoal({ kind: 'no_collision' }, ctx), true)
  assert.equal(checkGoal({ kind: 'no_collision' }, { ...ctx, evidence: { ...ctx.evidence, collisions: 1 } }), false)

  assert.equal(checkGoal({ kind: 'file_exists', path: 'config/line_track.png' }, ctx), true)
  assert.equal(checkGoal({ kind: 'file_exists', path: 'config/other.png' }, ctx), false)

  assert.equal(checkGoal({ kind: 'figure_min', min: 2 }, ctx), true)
  assert.equal(checkGoal({ kind: 'figure_min', min: 3 }, ctx), false)

  assert.equal(checkGoal({ kind: 'report_saved' }, ctx), true)
  assert.equal(checkGoal({ kind: 'capture_saved' }, ctx), false)
  assert.equal(checkGoal({ kind: 'console_has', text: 'lap complete' }, ctx), true)
  assert.equal(checkGoal({ kind: 'console_has', text: 'missing' }, ctx), false)
  assert.equal(checkGoal({ kind: 'unknown' }, ctx), false)
})

test('activity evaluation and stars', () => {
  const easy = { goals: [{ kind: 'run_ok' }, { kind: 'finish_lap', laps: 1 }] }
  assert.equal(evaluateActivity(easy, ctx).ok, true)
  assert.equal(evaluateActivity({ goals: [{ kind: 'finish_lap', laps: 3 }] }, ctx).ok, false)
  assert.equal(evaluateActivity({ goals: [] }, ctx).ok, false)

  const stars = { starGoals: [{ kind: 'lap_time_max', value: 20 }, { kind: 'lap_time_max', value: 10 }] }
  assert.equal(starsFor(stars, ctx), 2)
  assert.equal(starsFor({ starGoals: [] }, ctx), 1)
  assert.equal(starsFor({ starGoals: [{ kind: 'lap_time_max', value: 20 }, { kind: 'lap_time_max', value: 19 }] }, ctx), 3)
})

// ---------------------------------------------------------------------------
// Phase 3: geometric, performance and deliverable goals.
// ---------------------------------------------------------------------------
const trail = [
  { x: 2, y: 2, theta: 0, t: 0 },
  { x: 6, y: 4, theta: 0.2, t: 1 },
  { x: 12, y: 8, theta: Math.PI / 2, t: 2 },
]
const geom = {
  finished: { ok: true, stopped: true, error: null, files: [] },
  evidence: {
    t: 2, trail, trails: [trail], pathLength: 12.4, pathLengthAtGoal: 11.8,
    reachTime: 2, waypointCount: 12, wpTotal: 12, robots: 3, collisions: 0,
  },
  figures: [], reports: [], captures: [], console: [], source: 'vx = GANHO * dx',
}

test('trail helpers measure length and closest approach', () => {
  assert.ok(Math.abs(trailLength(trail) - (Math.hypot(4, 2) + Math.hypot(6, 4))) < 1e-9)
  assert.equal(trailLength([]), 0)
  assert.ok(Math.abs(trailMinDistance(trail, 12, 8)) < 1e-9)
  assert.ok(trailMinDistance(trail, 0, 0) > 2.5)
  assert.equal(trailMinDistance([], 0, 0), Infinity)
})

test('geometric goals use the recorded trail, not just the source code', () => {
  assert.equal(checkGoal({ kind: 'reach_goal', x: 12, y: 8, tolerance: 0.4 }, geom), true)
  assert.equal(checkGoal({ kind: 'reach_goal', x: 17, y: 9, tolerance: 0.4 }, geom), false)
  assert.equal(checkGoal({ kind: 'reach_goal', x: 12, y: 8, tolerance: 0.4 }, { ...geom, evidence: { ...geom.evidence, trail: [], trails: [] } }), false)

  assert.equal(checkGoal({ kind: 'orientation_error_max', x: 12, y: 8, theta: Math.PI / 2, tolerance: 0.4, value: 0.05 }, geom), true)
  assert.equal(checkGoal({ kind: 'orientation_error_max', x: 12, y: 8, theta: 0, tolerance: 0.4, value: 0.05 }, geom), false)
  // A heading far from the target point must not count.
  assert.equal(checkGoal({ kind: 'orientation_error_max', x: 17, y: 9, theta: Math.PI / 2, tolerance: 0.4, value: 0.05 }, geom), false)
})

test('performance, waypoint and robot-count goals', () => {
  assert.equal(checkGoal({ kind: 'time_max', value: 3 }, geom), true)
  assert.equal(checkGoal({ kind: 'time_max', value: 1 }, geom), false)
  assert.equal(checkGoal({ kind: 'time_max', value: 3 }, { ...geom, evidence: {} }), false)

  assert.equal(checkGoal({ kind: 'path_length_max', value: 13 }, geom), true)
  assert.equal(checkGoal({ kind: 'path_length_max', value: 11 }, geom), false)
  assert.equal(checkGoal({ kind: 'path_length_max', value: 13 }, { ...geom, evidence: { ...geom.evidence, pathLengthAtGoal: null } }), true)

  assert.equal(checkGoal({ kind: 'min_travel', value: 12 }, geom), true)
  assert.equal(checkGoal({ kind: 'min_travel', value: 13 }, geom), false)

  assert.equal(checkGoal({ kind: 'waypoint_count_min', n: 12 }, geom), true)
  assert.equal(checkGoal({ kind: 'waypoint_count_min', n: 13 }, geom), false)

  assert.equal(checkGoal({ kind: 'robot_count', n: 3 }, geom), true)
  assert.equal(checkGoal({ kind: 'robot_count', n: 4 }, geom), false)
})

test('code_uses is a secondary check over the run source', () => {
  assert.equal(checkGoal({ kind: 'code_uses', text: 'GANHO * dx' }, geom), true)
  assert.equal(checkGoal({ kind: 'code_uses', text: 'not there' }, geom), false)
  assert.equal(checkGoal({ kind: 'code_uses', text: '' }, geom), false)
})

test('phase 3 activities cover the classroom sequence and real examples', () => {
  const expected = [
    'python-tipos', 'python-numpy', 'python-plot',
    'holonomico-vxvy', 'diferencial-vomega',
    'chegar-alvo', 'chegar-alvo-orientacao', 'apf-lidar',
    'linha-bangbang', 'linha-proporcional',
    'grid-bfs', 'grid-astar', 'rrt', 'rrt-star', 'curvas-parametricas',
  ]
  for (const id of expected) assert.ok(activityById(id), `missing activity: ${id}`)
  for (const id of ['python', 'cinematica', 'navegacao', 'planejamento']) {
    assert.ok(trackById(id), `missing track: ${id}`)
  }
  // Every activity still references a catalog example.
  for (const activity of ACTIVITIES) assert.ok(exampleIds.has(activity.exampleId), activity.id)
})

test('achievements require the expected activities', () => {
  const byId = Object.fromEntries(ACHIEVEMENTS.map((a) => [a.id, a]))
  assert.deepEqual(
    byId.planejador.requires,
    ['grid-bfs', 'grid-astar', 'rrt', 'rrt-star', 'curvas-parametricas'],
  )
  assert.deepEqual(
    byId.mestre.requires,
    ACTIVITIES.filter((a) => !a.optional).map((a) => a.id),
  )
  for (const achievement of ACHIEVEMENTS) {
    assert.ok(achievement.labelKey, `${achievement.id} sem labelKey`)
    for (const id of achievement.requires) assert.ok(activityById(id), `${achievement.id}: ${id}`)
  }
})
