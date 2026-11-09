// Catálogo de exemplos do editor.
// Todos os .py entram como texto bruto (?raw) no momento do build a partir de
// web/templates/ (PT) e web/templates/en/ (EN). Os caminhos abaixo
// são relativos a este arquivo (web/src/examples/).

const raw = import.meta.glob(
  ['../../templates/*.py', '../../templates/en/*.py'],
  { query: '?raw', import: 'default', eager: true },
)

const TEMPLATE = '../../templates/'
const TEMPLATE_EN = '../../templates/en/'

function fonte(caminho) {
  const texto = raw[caminho]
  if (texto === undefined) throw new Error(`Example not included in the build: ${caminho}`)
  return texto
}

export const DEFAULT_EXAMPLE_ID = 'inicio_rapido'
export const DEMO_EXAMPLE_ID = 'demonstracao'

// Todos os exemplos agora vêm de web/templates/ (PT) e web/templates/en/ (EN).
// Campos: id, file, group, readonly, pt/en com title/description/tags/robots/notes
const ENTRIES = [
  {
    id: DEMO_EXAMPLE_ID, file: 'demonstracao.py', group: 'demo', readonly: true,
    pt: {
      title: 'Demonstração',
      description: 'Seis B-bots em duas patrulhas (três em cada rota fechada), com obstáculos, LiDAR, separação entre vizinhos e comunicação limitada. Roda em loop até você parar.',
      tags: ['demonstração', 'enxame', 'LiDAR', 'HiveBrAgent', 'obstáculos'], robots: '6 B-bots diferenciais (2 grupos)',
    },
    en: {
      title: 'Demo',
      description: 'Six B-bots in two patrols (three on each closed route), with obstacles, LiDAR, neighbour separation and limited communication. Loops until you stop it.',
      tags: ['demo', 'swarm', 'LiDAR', 'HiveBrAgent', 'obstacles'], robots: '6 differential B-bots (2 groups)',
    },
  },
  {
    id: 'inicio_rapido', file: 'inicio_rapido.py', group: 'tutorial',
    pt: { title: 'Início rápido', description: 'Um B-bot diferencial percorrendo uma rota de waypoints com um agente HiveBrAgent que vai até o objetivo.', tags: ['iniciante', 'waypoints', 'HiveBrAgent'], robots: '1 B-bot diferencial' },
    en: { title: 'Quick start', description: 'A differential B-bot driving a waypoint route with a HiveBrAgent that goes to the goal.', tags: ['beginner', 'waypoints', 'HiveBrAgent'], robots: '1 differential B-bot' },
  },
  {
    id: 'swarm_descentralizado', file: 'swarm_descentralizado.py', group: 'tutorial',
    pt: { title: 'Enxame descentralizado', description: 'Quatro agentes HiveBrAgent, cada um com sua rota, separação entre vizinhos, comm_radius de 3 m e ligações entre os robôs visíveis.', tags: ['enxame', 'descentralizado', 'comm_radius', 'separação'], robots: '4 B-bots diferenciais' },
    en: { title: 'Decentralized swarm', description: 'Four HiveBrAgent agents, each with its own route, neighbour separation, a 3 m comm_radius and visible links between robots.', tags: ['swarm', 'decentralized', 'comm_radius', 'separation'], robots: '4 differential B-bots' },
  },
  {
    id: 'swarm_centralizado', file: 'swarm_centralizado.py', group: 'tutorial',
    pt: { title: 'Formação centralizada', description: 'Um SwarmController comanda os quatro B-bots e os mantém em círculo ao redor do centroide ou em linha. Devolve {id: (v, omega)}.', tags: ['centralizado', 'SwarmController', 'formação'], robots: '4 B-bots diferenciais' },
    en: { title: 'Centralized formation', description: 'A SwarmController drives the four B-bots and keeps them in a circle around the centroid or in a line. It returns {id: (v, omega)}.', tags: ['centralized', 'SwarmController', 'formation'], robots: '4 differential B-bots' },
  },
  {
    id: 'seguidor_de_linha', file: 'seguidor_de_linha.py', group: 'tutorial',
    pt: { title: 'Seguidor de linha com PID', description: 'Gera uma pista fechada aleatória e segue a linha com cinco sensores TCRT5000 e um controlador PID. Mostra os tempos das voltas.', tags: ['linha', 'PID', 'sensores TCRT5000'], robots: '1 seguidor de linha', notes: 'Grava config/line_track.png na pasta de trabalho a cada execução.' },
    en: { title: 'PID line follower', description: 'Generates a random closed track and follows the line with five TCRT5000 sensors and a PID controller. Shows the lap times.', tags: ['line', 'PID', 'TCRT5000 sensors'], robots: '1 line follower', notes: 'Writes config/line_track.png to the working folder on every run.' },
  },
  {
    id: 'holonomico', file: 'holonomico.py', group: 'tutorial',
    pt: { title: 'Robô holonômico', description: 'Um robô omnidirecional que anda em qualquer direção. O controlador devolve {"vx", "vy"} e percorre um retângulo na arena.', tags: ['holonômico', 'Simulator', 'controlador'], robots: '1 B-bot holonômico' },
    en: { title: 'Holonomic robot', description: 'An omnidirectional robot that moves in any direction. The controller returns {"vx", "vy"} and drives a rectangle around the arena.', tags: ['holonomic', 'Simulator', 'controller'], robots: '1 holonomic B-bot' },
  },
  {
    id: 'lidar_desvio', file: 'lidar_desvio.py', group: 'tutorial',
    pt: { title: 'LiDAR e desvio de obstáculos', description: 'Um B-bot diferencial com LiDAR ligado contorna três obstáculos usando um campo de forças sobre as leituras dos raios.', tags: ['LiDAR', 'obstáculos', 'desvio'], robots: '1 B-bot diferencial com LiDAR' },
    en: { title: 'LiDAR and obstacle avoidance', description: 'A differential B-bot with LiDAR on goes around three obstacles using a force field over the ray readings.', tags: ['LiDAR', 'obstacles', 'avoidance'], robots: '1 differential B-bot with LiDAR' },
  },
  {
    id: 'controle_robodiferencial', file: 'controle_robodiferencial.py', group: 'advanced',
    pt: { title: 'Controle Kanayama (robô diferencial)', description: 'Controlador Kanayama (1990) de posição e orientação para um B-bot diferencial, com rota de cinco pontos, modelo de bateria e recarga.', tags: ['Kanayama', 'bateria', 'recarga'], robots: '1 B-bot diferencial' },
    en: { title: 'Kanayama control (differential robot)', description: 'Kanayama (1990) position and orientation controller for a differential B-bot, with a five-point route, battery model and recharging.', tags: ['Kanayama', 'battery', 'recharge'], robots: '1 differential B-bot' },
  },
  {
    id: 'decentralized_swarm', file: 'decentralized_swarm.py', group: 'advanced',
    pt: { title: 'Enxame descentralizado', description: 'Quatro agentes HiveBrAgent com ganhos diferentes, rotas próprias e separação entre vizinhos. Usa comm_radius, LiDAR ligado e colisões resolvidas empurrando os robôs.', tags: ['enxame', 'HiveBrAgent', 'LiDAR'], robots: '4 B-bots diferenciais' },
    en: { title: 'Decentralized swarm', description: 'Four HiveBrAgent agents with different gains, their own routes and neighbour separation. Uses comm_radius, LiDAR on and collisions resolved by pushing robots apart.', tags: ['swarm', 'HiveBrAgent', 'LiDAR'], robots: '4 differential B-bots' },
  },
  {
    id: 'line_follower', file: 'line_follower.py', group: 'advanced',
    pt: { title: 'Seguidor de linha', description: 'Seguidor de linha com sensores TCRT5000 e PID. Gera a pista aleatória em config/line_track.png e mostra os tempos das voltas.', tags: ['linha', 'PID', 'sensores TCRT5000'], robots: '1 seguidor de linha', notes: 'Aceita argumentos de linha de comando; no navegador valem os padrões.' },
    en: { title: 'Line follower', description: 'Line follower with TCRT5000 sensors and PID. Generates the random track in config/line_track.png and shows the lap times.', tags: ['line', 'PID', 'TCRT5000 sensors'], robots: '1 line follower', notes: 'Accepts command-line arguments; in the browser the defaults apply.' },
  },
  {
    id: 'multi_line_follower', file: 'multi_line_follower.py', group: 'advanced',
    pt: { title: 'Vários seguidores de linha', description: 'Vários seguidores de linha na mesma pista, partindo do mesmo ponto, cada um com um conjunto de ganhos PID. Compara os tempos por volta.', tags: ['linha', 'PID', 'comparação de ganhos'], robots: '4 seguidores de linha' },
    en: { title: 'Multiple line followers', description: 'Several line followers on the same track, starting from the same point, each with its own set of PID gains. Compares lap times.', tags: ['line', 'PID', 'gain comparison'], robots: '4 line followers' },
  },
  {
    id: 'multi_robot_differential', file: 'multi_robot_differential.py', group: 'advanced',
    pt: { title: 'Frota de robôs diferenciais', description: 'Quatro B-bots diferenciais, cada um com rota e controlador Kanayama próprios. O LiDAR enxerga os outros robôs como obstáculos móveis.', tags: ['frota', 'Kanayama', 'LiDAR', 'colisão'], robots: '4 B-bots diferenciais' },
    en: { title: 'Differential robot fleet', description: 'Four differential B-bots, each with its own route and Kanayama controller. LiDAR sees the other robots as moving obstacles.', tags: ['fleet', 'Kanayama', 'LiDAR', 'collision'], robots: '4 differential B-bots' },
  },
  {
    id: 'run_hexagonal_holonomic', file: 'run_hexagonal_holonomic.py', group: 'advanced',
    pt: { title: 'Robô hexagonal holonômico', description: 'Robô com três rodas omnidirecionais a 120°. Controle por servos com cinemática inversa e alocação de controle para respeitar o limite de velocidade das rodas.', tags: ['hexagonal', 'holonômico', 'cinemática inversa'], robots: '1 robô hexagonal holonômico' },
    en: { title: 'Hexagonal holonomic robot', description: 'Robot with three omnidirectional wheels at 120°. Servo control with inverse kinematics and control allocation to respect the wheel speed limit.', tags: ['hexagonal', 'holonomic', 'inverse kinematics'], robots: '1 hexagonal holonomic robot' },
  },
  {
    id: 'run_hexagonal_holonomic_line_follower', file: 'run_hexagonal_holonomic_line_follower.py', group: 'advanced',
    pt: { title: 'Seguidor de linha hexagonal', description: 'Robô hexagonal com sensores TCRT5000 e PID sobre o erro da linha. O comando (v, omega) vira velocidades das rodas pela cinemática inversa.', tags: ['hexagonal', 'linha', 'PID'], robots: '1 robô hexagonal seguidor de linha', notes: 'O painel de texto (draw_callback) não aparece no navegador: a fonte do pygame é simulada e o texto não é desenhado.' },
    en: { title: 'Hexagonal line follower', description: 'Hexagonal robot with TCRT5000 sensors and PID on the line error. The (v, omega) command becomes wheel speeds through inverse kinematics.', tags: ['hexagonal', 'line', 'PID'], robots: '1 hexagonal line-follower robot', notes: 'The text panel (draw_callback) does not appear in the browser: the pygame font is simulated and text is not drawn.' },
  },
  {
    id: 'decentralized_multiprocess', file: 'decentralized_multiprocess.py', group: 'advanced',
    pt: { title: 'Enxame descentralizado (multiprocess)', description: 'Enxame descentralizado com cada B-bot controlado em seu próprio núcleo de CPU via ProcessPoolExecutor.', tags: ['enxame', 'multiprocess', 'paralelo'], robots: '4 B-bots diferenciais' },
    en: { title: 'Decentralized swarm (multiprocess)', description: 'Decentralized swarm with each B-bot controlled on its own CPU core via ProcessPoolExecutor.', tags: ['swarm', 'multiprocess', 'parallel'], robots: '4 differential B-bots' },
  },
  {
    id: 'run_holonomic', file: 'run_holonomic.py', group: 'advanced',
    pt: { title: 'Robô holonômico (campo potencial)', description: 'Robô holonômico com controlador de campo potencial e visualização de forças atrativas/repulsivas.', tags: ['holonômico', 'campo potencial', 'visualização'], robots: '1 B-bot holonômico' },
    en: { title: 'Holonomic robot (potential field)', description: 'Holonomic robot with potential field controller and attractive/repulsive force visualization.', tags: ['holonomic', 'potential field', 'visualization'], robots: '1 holonomic B-bot' },
  },
]

/** Catálogo no idioma pedido ('pt-BR' | 'en'): título, descrição, etiquetas, notas e código-fonte. */
export function getCatalog(locale) {
  const lang = locale === 'pt-BR' ? 'pt' : 'en'
  return ENTRIES.map((e) => {
    const txt = e[lang]
    const source = fonte(`${lang === 'en' ? TEMPLATE_EN : TEMPLATE}${e.file}`)
    const notes = txt.notes ? txt.notes : ''
    return { id: e.id, group: e.group, readonly: !!e.readonly, title: txt.title, description: txt.description, tags: txt.tags, robots: txt.robots, notes, source }
  })
}

/** Compatibilidade: catálogo em português. */
export const CATALOG = getCatalog('pt-BR')
