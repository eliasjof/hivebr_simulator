// Learning curriculum: levels, tracks and activities.
//
// This module is intentionally free of user-facing text. Every label is an
// i18n key, so the pt-BR/en parity test keeps both languages in sync.
// Activities reference examples from web/src/examples/catalog.js by id.

export const LEVEL_IDS = [1, 2, 3, 4]

export const LEVELS = [
  { id: 1, labelKey: 'learn.level.1', summaryKey: 'learn.level.1_summary' },
  { id: 2, labelKey: 'learn.level.2', summaryKey: 'learn.level.2_summary' },
  { id: 3, labelKey: 'learn.level.3', summaryKey: 'learn.level.3_summary' },
  { id: 4, labelKey: 'learn.level.4', summaryKey: 'learn.level.4_summary' },
]

export const TRACKS = [
  {
    id: 'fundamentos', level: 1,
    titleKey: 'learn.track.fundamentos', summaryKey: 'learn.track.fundamentos_summary',
  },
  {
    id: 'linha', level: 2,
    titleKey: 'learn.track.linha', summaryKey: 'learn.track.linha_summary',
  },
  {
    id: 'percepcao', level: 2,
    titleKey: 'learn.track.percepcao', summaryKey: 'learn.track.percepcao_summary',
  },
  {
    id: 'controle', level: 3,
    titleKey: 'learn.track.controle', summaryKey: 'learn.track.controle_summary',
  },
  {
    id: 'multirobo', level: 4,
    titleKey: 'learn.track.multirobo', summaryKey: 'learn.track.multirobo_summary',
  },
]

// Sample activities for the phase-2 skeleton. Phase 3 expands this list.
export const ACTIVITIES = [
  {
    id: 'primeiro-movimento',
    level: 1,
    track: 'fundamentos',
    exampleId: 'inicio_rapido',
    xp: 50,
    badge: 'primeiro-passo',
    badgeKey: 'learn.badge.primeiro_passo',
    titleKey: 'learn.act.primeiro_movimento.title',
    briefKey: 'learn.act.primeiro_movimento.brief',
    hints: ['learn.act.primeiro_movimento.hint1'],
    goals: [{ kind: 'run_ok' }],
    starGoals: [],
  },
  {
    id: 'volta-completa',
    level: 2,
    track: 'linha',
    exampleId: 'seguidor_de_linha',
    xp: 100,
    badge: 'piloto-de-linha',
    badgeKey: 'learn.badge.piloto_de_linha',
    titleKey: 'learn.act.volta_completa.title',
    briefKey: 'learn.act.volta_completa.brief',
    hints: ['learn.act.volta_completa.hint1', 'learn.act.volta_completa.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'finish_lap', laps: 1 },
    ],
    starGoals: [
      { kind: 'lap_time_max', value: 30 },
      { kind: 'lap_time_max', value: 20 },
    ],
  },
  {
    id: 'desvio-limpo',
    level: 2,
    track: 'percepcao',
    exampleId: 'lidar_desvio',
    xp: 100,
    badge: 'desviador',
    badgeKey: 'learn.badge.desviador',
    titleKey: 'learn.act.desvio_limpo.title',
    briefKey: 'learn.act.desvio_limpo.brief',
    hints: ['learn.act.desvio_limpo.hint1'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'no_collision' },
    ],
    starGoals: [],
  },
]

export function activityById(id) {
  return ACTIVITIES.find((a) => a.id === id) || null
}

export function activitiesForLevel(level) {
  return ACTIVITIES.filter((a) => a.level === level)
}

export function trackById(id) {
  return TRACKS.find((t) => t.id === id) || null
}

export function levelById(id) {
  return LEVELS.find((l) => l.id === id) || null
}
