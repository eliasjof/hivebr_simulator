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
import {
  REPORT_MARKER, buildLearningReport, proseWordCount, reportRubric, updateReportIdentification,
} from '../../src/learning/report.js'

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
    if (activity.final) assert.equal(activity.exampleId, null, `final activity with example: ${activity.id}`)
    else assert.ok(exampleIds.has(activity.exampleId), `unknown example in ${activity.id}: ${activity.exampleId}`)
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
  // Every activity still references a catalog example, except the capstone.
  for (const activity of ACTIVITIES) {
    if (!activity.final) assert.ok(exampleIds.has(activity.exampleId), activity.id)
  }
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

// ---------------------------------------------------------------------------
// Phase 4: final report, rubric and progress export/import.
// ---------------------------------------------------------------------------
const LABELS = {
  title: 'Report', identification: 'Identification', student: 'Student', group: 'Class',
  date: 'Date', summary: 'Summary', activities: 'Activities', results: 'Results',
  figures: 'Figures', difficulties: 'Difficulties', conclusion: 'Conclusion',
  todo: 'TODO: write here.', none: 'None.', level: 'Level', activity: 'Activity',
  stars: 'Stars', xp: 'XP',
}
const ROWS = [
  { level: 1, track: 'Python', title: 'Types', stars: 3, xp: 40 },
  { level: 2, track: 'Navigation', title: 'Goal', stars: 2, xp: 70 },
]

test('final report builder creates a complete skeleton with TODO prompts', () => {
  const report = buildLearningReport({
    labels: LABELS,
    rows: ROWS,
    captures: [{ id: 'cap_1', name: 'figure 1' }],
    date: new Date('2026-11-14T12:00:00Z'),
  })
  assert.ok(report.startsWith(REPORT_MARKER), 'missing learning-report marker')
  assert.equal((report.match(/^## /gm) || []).length, 7, 'expected seven sections')
  for (const heading of ['Identification', 'Summary', 'Activities', 'Results', 'Figures', 'Difficulties', 'Conclusion']) {
    assert.ok(report.includes(`## ${heading}`), `missing section ${heading}`)
  }
  assert.ok(report.includes('| 1 | Types | 3/3 | 40 XP |'), 'activity row missing')
  assert.ok(report.includes('![figure 1](capture:cap_1)'), 'capture link missing')
  assert.ok(report.includes(LABELS.todo), 'TODO prompts missing')
  assert.equal(reportRubric(report).ok, false, 'skeleton must not pass the rubric')
})

test('report rubric requires marker, sections, prose and no TODO', () => {
  const skeleton = buildLearningReport({ labels: LABELS, rows: ROWS })
  const prose = Array.from({ length: 60 }, (_, i) => `palavra${i}`).join(' ')
  const done = skeleton.replaceAll(LABELS.todo, prose)
  const result = reportRubric(done, { minWords: 50, sections: 7 })
  assert.equal(result.ok, true)
  assert.ok(result.words >= 50)

  assert.equal(reportRubric(done.replace(REPORT_MARKER, ''), { minWords: 50 }).ok, false)
  assert.equal(reportRubric(done.replace(/^## .*$/gm, ''), { minWords: 50 }).ok, false)
  assert.equal(reportRubric(done, { minWords: 10000 }).ok, false)
  assert.equal(reportRubric(`${done}\nTODO: rest`, { minWords: 50 }).ok, false)
})

test('proseWordCount ignores headings, tables, images and comments', () => {
  const text = `${REPORT_MARKER}\n# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n![x](capture:1)\n\numa duas três`
  assert.equal(proseWordCount(text), 3)
})

test('the capstone activity validates the saved report', () => {
  const final = activityById('relatorio-final')
  assert.ok(final, 'missing capstone activity')
  assert.equal(final.final, true)
  assert.equal(final.exampleId, null)
  assert.equal(final.level, 4)
  assert.equal(final.goals[0].kind, 'report_rubric')
  assert.ok(final.badgeKey)

  const content = buildLearningReport({ labels: LABELS, rows: ROWS })
    .replaceAll(LABELS.todo, Array.from({ length: 80 }, (_, i) => `texto${i}`).join(' '))
  assert.equal(checkGoal({ kind: 'report_rubric', minWords: 100, sections: 7 }, { reports: [] }), false)
  assert.equal(checkGoal({ kind: 'report_rubric', minWords: 100, sections: 7 }, { reports: [{ content }] }), true)
  assert.equal(checkGoal({ kind: 'report_rubric', minWords: 100, sections: 7 }, { reports: [{ content: 'curto' }] }), false)
})

test('progress export/import round-trips and rejects malformed files', async () => {
  const { learning, exportProgress, importProgress, resetProgress } = await import('../../src/learning/progress.js')
  resetProgress()
  learning.xp = 260
  learning.activeId = 'grid-astar'
  learning.activities = { 'grid-astar': { done: true, stars: 2, at: 1, evidence: null } }
  learning.badges = ['astar']

  const json = exportProgress()
  const data = JSON.parse(json)
  assert.equal(data.xp, 260)
  assert.equal(data.activities['grid-astar'].stars, 2)

  resetProgress()
  assert.equal(importProgress(json), true)
  assert.equal(learning.xp, 260)
  assert.equal(learning.activeId, 'grid-astar')
  assert.equal(learning.activities['grid-astar'].done, true)
  assert.ok(learning.badges.includes('astar'))

  assert.equal(importProgress('not json'), false)
  assert.equal(importProgress('{}'), false)
  assert.equal(importProgress('[]'), false)

  // Unknown types are sanitized instead of stored as-is.
  const dirty = JSON.stringify({
    v: 1, xp: -5, activities: { a: { done: 1, stars: 99 } }, badges: [1, 'ok'],
  })
  assert.equal(importProgress(dirty), true)
  assert.equal(learning.xp, 0)
  assert.equal(learning.activities.a.done, false)
  assert.equal(learning.activities.a.stars, 3)
  assert.deepEqual(learning.badges, ['ok'])

  resetProgress()
})

// ---------------------------------------------------------------------------
// Phase 5: contextual activities, fleet goals, identity and protected bundles.
// ---------------------------------------------------------------------------
test('phase 5 goals cover ordered visits, fleet coverage and area coverage', () => {
  const stops = [
    { x: 2, y: 2 }, { x: 5, y: 9 }, { x: 10, y: 2 }, { x: 15, y: 9 },
  ]
  const route = { x: 2, y: 2 }
  const delivery = {
    evidence: {
      trail: [
        route, { x: 5, y: 9 }, { x: 10, y: 2 }, { x: 15, y: 9 }, { x: 18, y: 4 },
      ],
    },
  }
  assert.equal(checkGoal({ kind: 'visit_points', points: stops }, delivery), true)
  assert.equal(checkGoal({ kind: 'visit_points', points: [...stops].reverse() }, delivery), false)
  assert.equal(checkGoal({ kind: 'visit_points', points: [...stops, { x: 9, y: 9 }] }, delivery), false)
  assert.equal(checkGoal({ kind: 'visit_points', points: [] }, delivery), false)

  // Each station only needs one visit; two robots split the route.
  const fleet = {
    evidence: {
      trails: [
        [{ x: 4, y: 2 }, { x: 4, y: 6 }, { x: 2, y: 8 }],
        [{ x: 12, y: 6 }, { x: 15, y: 9 }],
      ],
    },
  }
  assert.equal(checkGoal({
    kind: 'points_covered',
    tolerance: 0.6,
    points: [{ x: 4, y: 2 }, { x: 4, y: 6 }, { x: 2, y: 8 }, { x: 12, y: 6 }, { x: 15, y: 9 }],
  }, fleet), true)
  assert.equal(checkGoal({ kind: 'points_covered', points: [{ x: 9, y: 9 }] }, fleet), false)
  assert.equal(checkGoal({ kind: 'points_covered', points: [] }, fleet), false)

  // Robot i must reach targets[i].
  const drones = {
    evidence: {
      trails: [
        [{ x: 2, y: 2 }, { x: 8, y: 4 }],
        [{ x: 2, y: 10 }, { x: 8, y: 8 }],
        [{ x: 18, y: 2 }, { x: 12, y: 4 }],
        [{ x: 18, y: 10 }, { x: 12, y: 8 }],
      ],
    },
  }
  const targets = [
    { x: 8, y: 4, tolerance: 0.6 }, { x: 8, y: 8, tolerance: 0.6 },
    { x: 12, y: 4, tolerance: 0.6 }, { x: 12, y: 8, tolerance: 0.6 },
  ]
  assert.equal(checkGoal({ kind: 'robot_reach', targets }, drones), true)
  assert.equal(checkGoal({ kind: 'robot_reach', targets: [...targets].reverse() }, drones), false)
  assert.equal(checkGoal({ kind: 'robot_reach', targets: targets.slice(0, 2) }, drones), true)
  assert.equal(checkGoal({ kind: 'robot_reach', targets: [] }, drones), false)

  // Coverage counts the arena cells touched by the trail.
  const grid = []
  for (let x = 0.5; x < 20; x += 1) {
    for (let y = 0.5; y < 12; y += 1) grid.push({ x, y })
  }
  const covered = { evidence: { trail: grid } }
  assert.equal(checkGoal({ kind: 'coverage_min', width: 20, height: 12, cell: 1, value: 1 }, covered), true)
  assert.equal(checkGoal({ kind: 'coverage_min', width: 20, height: 12, cell: 1, value: 0.5 }, { evidence: { trail: grid.slice(0, 100) } }), false)
  assert.equal(checkGoal({ kind: 'coverage_min', width: 20, height: 12, cell: 1, value: 0.5 }, { evidence: { trail: [] } }), false)
})

test('phase 5 achievements require the contextual activities', () => {
  const byId = Object.fromEntries(ACHIEVEMENTS.map((a) => [a.id, a]))
  assert.deepEqual(byId.logistica.requires, ['planejamento-armazem', 'cobertura-agricola', 'replanejamento'])
  assert.deepEqual(byId.dados.requires, ['python-telemetria', 'python-diario', 'python-supervisor', 'python-lidar-listas'])
  assert.ok(byId.automacao.requires.includes('enxame-inventario'))
  assert.ok(byId.automacao.requires.includes('formacao-drones'))
  for (const id of [
    'patrulha-armazem', 'python-telemetria', 'cinematica-rodas', 'estacionar-doca',
    'faixa-adaptativa', 'apf-tunel', 'planejamento-armazem', 'enxame-inventario',
    'projeto-entrega',
  ]) {
    assert.ok(activityById(id), `missing contextual activity: ${id}`)
  }
  for (const achievement of ACHIEVEMENTS) {
    assert.ok(achievement.labelKey, `${achievement.id} sem labelKey`)
    for (const id of achievement.requires) assert.ok(activityById(id), `${achievement.id}: ${id}`)
  }
})

test('local student identity generates readable ids and survives a reset', async () => {
  const identity = await import('../../src/learning/identity.js')
  const pattern = /^HB-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/
  assert.match(identity.generateStudentId(), pattern)
  assert.equal(identity.generateStudentId().length, 'HB-AAAA-AAAA'.length)

  identity.resetStudent()
  const created = identity.ensureStudent()
  assert.match(created.id, pattern)
  identity.setStudentName('  Ana  ')
  identity.setStudentGroup('  Turma A  ')
  assert.equal(created.name, 'Ana')
  assert.equal(created.group, 'Turma A')
  assert.equal(identity.applyStudent({ id: 'HB-AAAA-BBBB', name: 'Bia', group: 'B' }), true)
  assert.equal(identity.student.id, 'HB-AAAA-BBBB')
  assert.equal(identity.applyStudent({}), false)
  assert.equal(identity.applyStudent({ id: '   ' }), false)

  const kept = identity.student.id
  identity.resetStudent()
  assert.equal(identity.student.id, '')
  identity.ensureStudent()
  assert.match(identity.student.id, pattern)
  assert.notEqual(identity.student.id, kept)
  identity.resetStudent()
})

test('protected bundles encrypt the payload and reject a wrong password', async () => {
  const bundle = await import('../../src/learning/bundle.js')
  const payload = {
    app: 'hivebr',
    student: { id: 'HB-AAAA-BBBB', name: 'Ana' },
    progress: { v: 1, xp: 42, activities: { a: { done: true, stars: 3 } } },
  }

  const plain = await bundle.encodeBundle(payload)
  const plainInfo = bundle.inspectBundle(plain)
  assert.equal(plainInfo.bundle, true)
  assert.equal(plainInfo.encrypted, false)
  assert.equal(plainInfo.version, 2)
  assert.deepEqual(await bundle.decodeBundle(plain), payload)

  const secret = await bundle.encodeBundle(payload, 'segredo')
  const secretInfo = bundle.inspectBundle(secret)
  assert.equal(secretInfo.bundle, true)
  assert.equal(secretInfo.encrypted, true)
  assert.equal(secretInfo.payload, null)
  const envelope = JSON.parse(secret)
  assert.equal(envelope.format, 'hivebr-progress')
  assert.equal(envelope.v, 2)
  assert.equal(envelope.crypto.alg, 'AES-GCM')
  assert.equal(envelope.crypto.kdf, 'PBKDF2-SHA256')
  assert.ok(envelope.crypto.salt && envelope.crypto.iv)
  assert.deepEqual(await bundle.decodeBundle(secret, 'segredo'), payload)
  await assert.rejects(bundle.decodeBundle(secret, 'errada'), /wrong-password/)
  await assert.rejects(bundle.decodeBundle(secret), /password-required/)

  // v1 files (plain progress at the top level) still decode.
  assert.deepEqual(await bundle.decodeBundle(JSON.stringify(payload)), payload)
  assert.equal(bundle.inspectBundle('not json'), null)
  assert.equal(bundle.inspectBundle('[]'), null)
})

test('xp thresholds match the expanded curriculum', async () => {
  const { XP_THRESHOLDS, levelForXp, xpForLevel } = await import('../../src/learning/progress.js')
  assert.deepEqual(XP_THRESHOLDS, [0, 300, 800, 1500])
  assert.equal(levelForXp(0), 1)
  assert.equal(levelForXp(299), 1)
  assert.equal(levelForXp(300), 2)
  assert.equal(levelForXp(799), 2)
  assert.equal(levelForXp(800), 3)
  assert.equal(levelForXp(1499), 3)
  assert.equal(levelForXp(1500), 4)
  assert.equal(xpForLevel(1), 0)
  assert.equal(xpForLevel(4), 1500)
  assert.equal(xpForLevel(5), null)
})

test('report identification updates without touching the student text', () => {
  const labels = {
    title: 'Relatório final', identification: 'Identificação', student: 'Aluno(a)',
    group: 'Turma', date: 'Data', summary: 'Resumo', activities: 'Atividades',
    results: 'Resultados', figures: 'Figuras', difficulties: 'Dificuldades',
    conclusion: 'Conclusão', todo: 'TODO: escreva aqui.', none: 'Nenhum item.',
    level: 'Nível', activity: 'Atividade', stars: 'Estrelas', xp: 'XP',
  }
  const content = buildLearningReport({
    labels,
    rows: [],
    studentName: 'Ana',
    groupName: 'Turma A',
    date: new Date('2026-03-02T12:00:00Z'),
  })
  const withProse = content.replace('TODO: escreva aqui.', 'Texto que o aluno escreveu.')
  const updated = updateReportIdentification(withProse, {
    labels,
    studentName: 'Ana Souza',
    groupName: 'Turma B',
    date: new Date('2026-03-02T12:00:00Z'),
  })
  assert.ok(updated.includes('| Aluno(a) | Ana Souza |'))
  assert.ok(updated.includes('| Turma | Turma B |'))
  assert.ok(updated.includes('| Data | 2026-03-02 |'))
  assert.ok(updated.includes('Texto que o aluno escreveu.'))
  assert.ok(updated.includes('## Resumo'))
  assert.equal((updated.match(/## Identificação/g) || []).length, 1)
  assert.equal(updateReportIdentification('sem cabeçalho', { labels }), 'sem cabeçalho')
})

test('teacher roster summarizes bundles, deduplicates and exports a sheet', async () => {
  const teacher = await import('../../src/learning/teacher.js')
  teacher.resetTeacher()

  const payload = {
    app: 'hivebr',
    exportedAt: 1000,
    student: { id: 'HB-AAAA-BBBB', name: 'Ana', group: 'Turma A' },
    progress: {
      v: 1,
      xp: 300,
      activities: {
        'python-tipos': { done: true, stars: 3 },
        'grid-astar': { done: true, stars: 2 },
        'relatorio-final': { done: true, stars: 1 },
      },
      badges: ['pythonista', 'astar'],
      achievements: ['planejador'],
    },
    reports: [],
  }
  const entry = teacher.rosterEntryFromBundle(payload, { source: 'ana.json' })
  assert.equal(entry.id, 'HB-AAAA-BBBB')
  assert.equal(entry.name, 'Ana')
  assert.equal(entry.group, 'Turma A')
  assert.equal(entry.xp, 300)
  assert.equal(entry.level, 2)
  assert.equal(entry.done, 3)
  assert.equal(entry.total, ACTIVITIES.length)
  assert.equal(entry.requiredDone, 2)
  assert.equal(entry.stars, 6)
  assert.equal(entry.badges, 2)
  assert.equal(entry.achievements, 1)
  assert.equal(entry.reportHas, false)
  assert.equal(entry.reportOk, false)
  assert.equal(entry.source, 'ana.json')

  assert.equal(teacher.rosterEntryFromBundle({ student: { id: 'X' } }), null)
  assert.equal(teacher.rosterEntryFromBundle({ student: { id: '' }, progress: { xp: 1, activities: {} } }), null)
  assert.equal(teacher.rosterEntryFromBundle(null), null)

  assert.deepEqual(teacher.upsertStudent(entry), { added: true, updated: false, stale: false })
  // An older export must not overwrite a newer one.
  const older = { ...entry, xp: 10, exportedAt: 500 }
  assert.equal(teacher.upsertStudent(older).stale, true)
  assert.equal(teacher.teacher.students[0].xp, 300)
  // A newer export replaces it.
  const newer = { ...entry, xp: 900, exportedAt: 2000, name: 'Ana Souza' }
  assert.equal(teacher.upsertStudent(newer).updated, true)
  assert.equal(teacher.teacher.students.length, 1)
  assert.equal(teacher.teacher.students[0].xp, 900)

  const summary = teacher.rosterSummary()
  assert.equal(summary.students, 1)
  assert.equal(summary.averageXp, 900)

  const csv = teacher.rosterCsv(teacher.teacher.students, {
    headers: { name: 'Aluno', id: 'ID', xp: 'XP' },
    yes: 'sim',
    no: 'não',
  })
  assert.ok(csv.startsWith('\ufeff'))
  const [head, row] = csv.slice(1).split('\r\n')
  // Unmapped columns fall back to the field name, so the sheet never loses data.
  assert.equal(
    head,
    'ID;Aluno;group;XP;level;activities;required;stars;badges;achievements;report;words;exportedAt;importedAt',
  )
  const cells = row.split(';')
  assert.deepEqual(
    cells.slice(0, 11),
    ['HB-AAAA-BBBB', 'Ana Souza', 'Turma A', '900', '3', '3/38', '2/30', '6', '2', '1', 'não'],
  )
  assert.equal(cells[11], '')
  assert.equal(cells[12], '1970-01-01')
  // Names with the separator are quoted.
  const quoted = teacher.rosterCsv([{ ...entry, name: 'Ana; "A"', group: 'A' }], { headers: { name: 'Aluno' } })
  assert.ok(quoted.includes('"Ana; ""A"""'))

  teacher.resetTeacher()
})

test('teacher keyword gates the panel without storing the plain text', async () => {
  const teacher = await import('../../src/learning/teacher.js')
  teacher.resetTeacher()
  assert.equal(teacher.teacher.configured, false)
  assert.equal(await teacher.checkTeacherKey('qualquer'), false)
  assert.equal(await teacher.setTeacherKey('abc'), false)
  assert.equal(await teacher.setTeacherKey('segredo'), true)
  assert.equal(teacher.teacher.configured, true)
  assert.ok(teacher.teacher.keyHash)
  assert.equal(teacher.teacher.keyHash.includes('segredo'), false)
  assert.equal(teacher.isSessionUnlocked(), true)

  teacher.lockSession()
  assert.equal(teacher.isSessionUnlocked(), false)
  assert.equal(await teacher.unlockTeacher('errada'), false)
  assert.equal(teacher.isSessionUnlocked(), false)
  assert.equal(await teacher.unlockTeacher('segredo'), true)
  assert.equal(teacher.isSessionUnlocked(), true)

  teacher.clearTeacherKey()
  assert.equal(teacher.teacher.configured, false)
  assert.equal(teacher.teacher.keyHash, '')
  teacher.resetTeacher()
})

test('teacher roster backup round-trips', async () => {
  const teacher = await import('../../src/learning/teacher.js')
  teacher.resetTeacher()
  teacher.setTeacherProfile({ name: 'Prof. Souza', school: 'Turma A' })
  const entry = teacher.rosterEntryFromBundle({
    exportedAt: 10,
    student: { id: 'HB-AAAA-BBBB', name: 'Ana', group: 'A' },
    progress: { xp: 10, activities: {} },
  })
  teacher.upsertStudent(entry)
  const backup = teacher.rosterPayload()
  assert.equal(backup.format, 'hivebr-roster')
  assert.equal(teacher.isRosterPayload(backup), true)
  assert.equal(teacher.isRosterPayload({ format: 'other' }), false)

  teacher.clearRoster()
  assert.equal(teacher.teacher.students.length, 0)
  assert.equal(teacher.applyRosterPayload(backup), 1)
  assert.equal(teacher.teacher.students.length, 1)
  assert.equal(teacher.teacher.students[0].id, 'HB-AAAA-BBBB')
  assert.equal(teacher.applyRosterPayload({ format: 'other' }), 0)
  assert.equal(teacher.applyRosterPayload(null), 0)
  teacher.resetTeacher()
})
