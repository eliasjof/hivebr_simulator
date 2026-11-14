// Learning curriculum: levels, tracks, activities and achievements.
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
    id: 'python', level: 1,
    titleKey: 'learn.track.python', summaryKey: 'learn.track.python_summary',
  },
  {
    id: 'cinematica', level: 2,
    titleKey: 'learn.track.cinematica', summaryKey: 'learn.track.cinematica_summary',
  },
  {
    id: 'navegacao', level: 2,
    titleKey: 'learn.track.navegacao', summaryKey: 'learn.track.navegacao_summary',
  },
  {
    id: 'linha', level: 2,
    titleKey: 'learn.track.linha', summaryKey: 'learn.track.linha_summary',
  },
  {
    id: 'percepcao', level: 3,
    titleKey: 'learn.track.percepcao', summaryKey: 'learn.track.percepcao_summary',
  },
  {
    id: 'planejamento', level: 4,
    titleKey: 'learn.track.planejamento', summaryKey: 'learn.track.planejamento_summary',
  },
  {
    id: 'multirobo', level: 4,
    titleKey: 'learn.track.multirobo', summaryKey: 'learn.track.multirobo_summary',
  },
]

// Activities follow the classroom sequence:
//   1. Python basics and plotting
//   2. Kinematics (holonomic vx/vy and differential v/omega)
//   3. Reach a target
//   4. Reach a target with orientation
//   5. Artificial potential field with LiDAR
//   6. Line follower (bang-bang and proportional), in parallel
//   7. Path planning (BFS, A*, RRT, RRT*, parametric curves)
export const ACTIVITIES = [
  // ---------------------------------------------------------------- level 1
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
    id: 'python-tipos',
    level: 1,
    track: 'python',
    exampleId: 'python_tipos',
    xp: 40,
    badge: 'pythonista',
    badgeKey: 'learn.badge.pythonista',
    titleKey: 'learn.act.python_tipos.title',
    briefKey: 'learn.act.python_tipos.brief',
    hints: ['learn.act.python_tipos.hint1', 'learn.act.python_tipos.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'console_has', text: 'TUDO CERTO' },
    ],
    starGoals: [],
  },
  {
    id: 'python-numpy',
    level: 1,
    track: 'python',
    exampleId: 'python_numpy',
    xp: 50,
    badge: 'matrizes',
    badgeKey: 'learn.badge.matrizes',
    titleKey: 'learn.act.python_numpy.title',
    briefKey: 'learn.act.python_numpy.brief',
    hints: ['learn.act.python_numpy.hint1', 'learn.act.python_numpy.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'console_has', text: 'TUDO CERTO' },
      { kind: 'figure_min', min: 1 },
    ],
    starGoals: [],
  },
  {
    id: 'python-plot',
    level: 1,
    track: 'python',
    exampleId: 'python_plot',
    xp: 50,
    badge: 'visualizador',
    badgeKey: 'learn.badge.visualizador',
    titleKey: 'learn.act.python_plot.title',
    briefKey: 'learn.act.python_plot.brief',
    hints: ['learn.act.python_plot.hint1', 'learn.act.python_plot.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'console_has', text: 'FIGURA SALVA' },
      { kind: 'figure_min', min: 1 },
      { kind: 'file_exists', path: 'trajetoria.png' },
    ],
    starGoals: [],
  },

  // ---------------------------------------------------------------- level 2
  {
    id: 'holonomico-vxvy',
    level: 2,
    track: 'cinematica',
    exampleId: 'cinematica_holonomica',
    xp: 60,
    badge: 'holonomico',
    badgeKey: 'learn.badge.holonomico',
    titleKey: 'learn.act.holonomico_vxvy.title',
    briefKey: 'learn.act.holonomico_vxvy.brief',
    hints: ['learn.act.holonomico_vxvy.hint1', 'learn.act.holonomico_vxvy.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 12, y: 8, tolerance: 0.4 },
      { kind: 'time_max', value: 25 },
      { kind: 'no_collision' },
    ],
    starGoals: [
      { kind: 'time_max', value: 18 },
      { kind: 'path_length_max', value: 15 },
    ],
  },
  {
    id: 'diferencial-vomega',
    level: 2,
    track: 'cinematica',
    exampleId: 'cinematica_diferencial',
    xp: 60,
    badge: 'diferencial',
    badgeKey: 'learn.badge.diferencial',
    titleKey: 'learn.act.diferencial_vomega.title',
    briefKey: 'learn.act.diferencial_vomega.brief',
    hints: ['learn.act.diferencial_vomega.hint1', 'learn.act.diferencial_vomega.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 14, y: 6, tolerance: 0.5 },
      { kind: 'no_collision' },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 15 },
      { kind: 'time_max', value: 25 },
    ],
  },
  {
    id: 'chegar-alvo',
    level: 2,
    track: 'navegacao',
    exampleId: 'ir_para_alvo',
    xp: 70,
    badge: 'alvo',
    badgeKey: 'learn.badge.alvo',
    titleKey: 'learn.act.chegar_alvo.title',
    briefKey: 'learn.act.chegar_alvo.brief',
    hints: ['learn.act.chegar_alvo.hint1', 'learn.act.chegar_alvo.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 12, y: 9, tolerance: 0.35 },
      { kind: 'time_max', value: 30 },
      { kind: 'no_collision' },
    ],
    starGoals: [
      { kind: 'time_max', value: 22 },
      { kind: 'path_length_max', value: 16 },
    ],
  },
  {
    id: 'linha-bangbang',
    level: 2,
    track: 'linha',
    exampleId: 'linha_bangbang',
    xp: 60,
    badge: 'bangbang',
    badgeKey: 'learn.badge.bangbang',
    titleKey: 'learn.act.linha_bangbang.title',
    briefKey: 'learn.act.linha_bangbang.brief',
    hints: ['learn.act.linha_bangbang.hint1', 'learn.act.linha_bangbang.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'finish_lap', laps: 1 },
      { kind: 'no_collision' },
    ],
    starGoals: [
      { kind: 'lap_time_max', value: 40 },
      { kind: 'line_error_max', value: 0.55 },
    ],
  },
  {
    id: 'linha-proporcional',
    level: 2,
    track: 'linha',
    exampleId: 'linha_proporcional',
    xp: 70,
    badge: 'proporcional',
    badgeKey: 'learn.badge.proporcional',
    titleKey: 'learn.act.linha_proporcional.title',
    briefKey: 'learn.act.linha_proporcional.brief',
    hints: ['learn.act.linha_proporcional.hint1', 'learn.act.linha_proporcional.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'finish_lap', laps: 1 },
      { kind: 'line_error_max', value: 0.30 },
    ],
    starGoals: [
      { kind: 'lap_time_max', value: 35 },
      { kind: 'line_error_max', value: 0.26 },
    ],
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

  // ---------------------------------------------------------------- level 3
  {
    id: 'chegar-alvo-orientacao',
    level: 3,
    track: 'navegacao',
    exampleId: 'ir_para_pose',
    xp: 80,
    badge: 'orientacao',
    badgeKey: 'learn.badge.orientacao',
    titleKey: 'learn.act.chegar_alvo_orientacao.title',
    briefKey: 'learn.act.chegar_alvo_orientacao.brief',
    hints: ['learn.act.chegar_alvo_orientacao.hint1', 'learn.act.chegar_alvo_orientacao.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 12, y: 8, tolerance: 0.35 },
      { kind: 'orientation_error_max', x: 12, y: 8, theta: Math.PI / 2, tolerance: 0.35, value: 0.175 },
      { kind: 'no_collision' },
    ],
    starGoals: [
      { kind: 'orientation_error_max', x: 12, y: 8, theta: Math.PI / 2, tolerance: 0.35, value: 0.087 },
      { kind: 'time_max', value: 35 },
    ],
  },
  {
    id: 'apf-lidar',
    level: 3,
    track: 'percepcao',
    exampleId: 'apf_lidar',
    xp: 90,
    badge: 'campo-potencial',
    badgeKey: 'learn.badge.campo_potencial',
    titleKey: 'learn.act.apf_lidar.title',
    briefKey: 'learn.act.apf_lidar.brief',
    hints: ['learn.act.apf_lidar.hint1', 'learn.act.apf_lidar.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 6, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'time_max', value: 45 },
    ],
    starGoals: [
      { kind: 'time_max', value: 35 },
      { kind: 'path_length_max', value: 22 },
    ],
  },
  {
    id: 'apf-minimo-local',
    level: 3,
    track: 'percepcao',
    exampleId: 'apf_lidar',
    xp: 100,
    badge: 'escape',
    badgeKey: 'learn.badge.escape',
    titleKey: 'learn.act.apf_minimo_local.title',
    briefKey: 'learn.act.apf_minimo_local.brief',
    hints: ['learn.act.apf_minimo_local.hint1'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 6, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'time_max', value: 40 },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 20 },
    ],
    optional: true,
  },

  // ---------------------------------------------------------------- level 4
  {
    id: 'grid-bfs',
    level: 4,
    track: 'planejamento',
    exampleId: 'grid_bfs',
    xp: 100,
    badge: 'bfs',
    badgeKey: 'learn.badge.bfs',
    titleKey: 'learn.act.grid_bfs.title',
    briefKey: 'learn.act.grid_bfs.brief',
    hints: ['learn.act.grid_bfs.hint1', 'learn.act.grid_bfs.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 9, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'console_has', text: 'caminho=' },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 22 },
      { kind: 'time_max', value: 30 },
    ],
  },
  {
    id: 'grid-astar',
    level: 4,
    track: 'planejamento',
    exampleId: 'grid_astar',
    xp: 110,
    badge: 'astar',
    badgeKey: 'learn.badge.astar',
    titleKey: 'learn.act.grid_astar.title',
    briefKey: 'learn.act.grid_astar.brief',
    hints: ['learn.act.grid_astar.hint1', 'learn.act.grid_astar.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 9, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'console_has', text: 'expandidos=' },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 22 },
      { kind: 'time_max', value: 30 },
    ],
  },
  {
    id: 'rrt',
    level: 4,
    track: 'planejamento',
    exampleId: 'rrt',
    xp: 120,
    badge: 'rrt',
    badgeKey: 'learn.badge.rrt',
    titleKey: 'learn.act.rrt.title',
    briefKey: 'learn.act.rrt.brief',
    hints: ['learn.act.rrt.hint1', 'learn.act.rrt.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 9, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'figure_min', min: 1 },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 24 },
      { kind: 'time_max', value: 35 },
    ],
  },
  {
    id: 'rrt-star',
    level: 4,
    track: 'planejamento',
    exampleId: 'rrt_star',
    xp: 130,
    badge: 'rrt-star',
    badgeKey: 'learn.badge.rrt_star',
    titleKey: 'learn.act.rrt_star.title',
    briefKey: 'learn.act.rrt_star.brief',
    hints: ['learn.act.rrt_star.hint1', 'learn.act.rrt_star.hint2'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 9, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'figure_min', min: 1 },
      { kind: 'console_has', text: 'otimizado=True' },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 21 },
      { kind: 'time_max', value: 35 },
    ],
  },
  {
    id: 'curvas-parametricas',
    level: 4,
    track: 'planejamento',
    exampleId: 'curvas_parametricas',
    xp: 140,
    badge: 'curvas',
    badgeKey: 'learn.badge.curvas',
    titleKey: 'learn.act.curvas_parametricas.title',
    briefKey: 'learn.act.curvas_parametricas.brief',
    hints: ['learn.act.curvas_parametricas.hint1'],
    goals: [
      { kind: 'run_ok' },
      { kind: 'reach_goal', x: 17, y: 9, tolerance: 0.5 },
      { kind: 'no_collision' },
      { kind: 'figure_min', min: 1 },
      { kind: 'path_length_max', value: 23 },
    ],
    starGoals: [
      { kind: 'path_length_max', value: 19 },
      { kind: 'time_max', value: 35 },
    ],
  },
]

export const ACHIEVEMENTS = [
  {
    id: 'planejador',
    labelKey: 'learn.achievement.planejador',
    requires: ['grid-bfs', 'grid-astar', 'rrt', 'rrt-star', 'curvas-parametricas'],
  },
  {
    id: 'mestre',
    labelKey: 'learn.achievement.mestre',
    requires: ACTIVITIES.filter((a) => !a.optional).map((a) => a.id),
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
