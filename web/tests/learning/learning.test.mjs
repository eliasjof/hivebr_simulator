// Learning curriculum integrity + pure goal checks.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  ACTIVITIES, LEVELS, TRACKS, LEVEL_IDS,
  activitiesForLevel, activityById, trackById,
} from '../../src/learning/curriculum.js'
import { GOAL_CHECKS, checkGoal, evaluateActivity, starsFor } from '../../src/learning/validate.js'

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
