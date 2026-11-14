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

/** Ordem de exibição das categorias na galeria. */
export const CATEGORY_IDS = ['fundamentos', 'python', 'percepcao', 'linha', 'locomocao', 'controle', 'planejamento', 'multirobo']

/** Níveis pedagógicos: 1 = técnico, 4 = graduação avançada. */
export const LEVEL_IDS = [1, 2, 3, 4]

// Todos os exemplos agora vêm de web/templates/ (PT) e web/templates/en/ (EN).
// Campos: id, file, group, category, level, order, readonly, pt/en com
// title/description/tags/robots/notes.
const ENTRIES = [
  {
    id: DEMO_EXAMPLE_ID, file: 'demonstracao.py', group: 'demo', category: 'fundamentos', level: 1, order: 10, readonly: true,
    pt: {
      title: 'Demonstração',
      description: 'Seis B-bots em duas patrulhas (três em cada rota fechada), com obstáculos, LiDAR, separação entre vizinhos e comunicação limitada. Roda em loop até você parar.',
      tags: ['demonstração', 'enxame', 'LiDAR', 'HiveBrAgent', 'obstáculos'], robots: '6 B-bots diferenciais (2 grupos)',
    },
    en: {
      filename: 'demo.py',
      title: 'Demo',
      description: 'Six B-bots in two patrols (three on each closed route), with obstacles, LiDAR, neighbour separation and limited communication. Loops until you stop it.',
      tags: ['demo', 'swarm', 'LiDAR', 'HiveBrAgent', 'obstacles'], robots: '6 differential B-bots (2 groups)',
    },
  },
  {
    id: 'inicio_rapido', file: 'inicio_rapido.py', group: 'tutorial', category: 'fundamentos', level: 1, order: 20,
    pt: { title: 'Início rápido', description: 'Um B-bot diferencial percorrendo uma rota de waypoints com um agente HiveBrAgent que vai até o objetivo.', tags: ['iniciante', 'waypoints', 'HiveBrAgent'], robots: '1 B-bot diferencial' },
    en: { filename: 'quick_start.py', title: 'Quick start', description: 'A differential B-bot driving a waypoint route with a HiveBrAgent that goes to the goal.', tags: ['beginner', 'waypoints', 'HiveBrAgent'], robots: '1 differential B-bot' },
  },
  {
    id: 'importando_modulo', file: 'importando_modulo.py', group: 'tutorial', category: 'fundamentos', level: 1, order: 30, files: ['agent_lib.py'],
    pt: { title: 'Importando outro script', description: 'O script principal importa uma classe e uma função definidas em agent_lib.py, outra aba carregada no editor. As duas abas são enviadas juntas para o Python, como módulos de um mesmo projeto.', tags: ['import', 'módulo', 'classe', 'função'], robots: '1 B-bot diferencial', notes: 'A aba agent_lib.py é a biblioteca importada; execute a aba importando_modulo.py.' },
    en: { filename: 'importing_module.py', title: 'Importing another script', description: 'The main script imports a class and a function defined in agent_lib.py, another tab loaded in the editor. Both tabs are sent together to Python, like modules in the same project.', tags: ['import', 'module', 'class', 'function'], robots: '1 differential B-bot', notes: 'The agent_lib.py tab is the imported library; run the importing_module.py tab.' },
  },
  {
    id: 'swarm_descentralizado', file: 'swarm_descentralizado.py', group: 'tutorial', category: 'multirobo', level: 2, order: 10,
    pt: { title: 'Enxame descentralizado', description: 'Quatro agentes HiveBrAgent, cada um com sua rota, separação entre vizinhos, comm_radius de 3 m e ligações entre os robôs visíveis.', tags: ['enxame', 'descentralizado', 'comm_radius', 'separação'], robots: '4 B-bots diferenciais' },
    en: { filename: 'decentralized_swarm_basic.py', title: 'Decentralized swarm', description: 'Four HiveBrAgent agents, each with its own route, neighbour separation, a 3 m comm_radius and visible links between robots.', tags: ['swarm', 'decentralized', 'comm_radius', 'separation'], robots: '4 differential B-bots' },
  },
  {
    id: 'swarm_centralizado', file: 'swarm_centralizado.py', group: 'tutorial', category: 'multirobo', level: 3, order: 20,
    pt: { title: 'Formação centralizada', description: 'Um SwarmController comanda os quatro B-bots e os mantém em círculo ao redor do centroide ou em linha. Devolve {id: (v, omega)}.', tags: ['centralizado', 'SwarmController', 'formação'], robots: '4 B-bots diferenciais' },
    en: { filename: 'centralized_formation.py', title: 'Centralized formation', description: 'A SwarmController drives the four B-bots and keeps them in a circle around the centroid or in a line. It returns {id: (v, omega)}.', tags: ['centralized', 'SwarmController', 'formation'], robots: '4 differential B-bots' },
  },
  {
    id: 'seguidor_de_linha', file: 'seguidor_de_linha.py', group: 'tutorial', category: 'linha', level: 2, order: 10,
    pt: { title: 'Seguidor de linha com PID', description: 'Gera uma pista fechada aleatória e segue a linha com cinco sensores TCRT5000 e um controlador PID. Mostra os tempos das voltas.', tags: ['linha', 'PID', 'sensores TCRT5000'], robots: '1 seguidor de linha', notes: 'Grava config/line_track.png na pasta de trabalho a cada execução.' },
    en: { filename: 'line_follower_pid.py', title: 'PID line follower', description: 'Generates a random closed track and follows the line with five TCRT5000 sensors and a PID controller. Shows the lap times.', tags: ['line', 'PID', 'TCRT5000 sensors'], robots: '1 line follower', notes: 'Writes config/line_track.png to the working folder on every run.' },
  },
  {
    id: 'holonomico', file: 'holonomico.py', group: 'tutorial', category: 'locomocao', level: 3, order: 10,
    pt: { title: 'Robô holonômico', description: 'Um robô omnidirecional hexagonal, com três rodas a 120°. O controlador devolve {"vx", "vy"}; a cinemática inversa original converte o comando em velocidades das rodas e o robô percorre um retângulo na arena.', tags: ['holonômico', 'hexagonal', 'Simulator', 'controlador'], robots: '1 robô hexagonal holonômico' },
    en: { filename: 'holonomic_robot.py', title: 'Holonomic robot', description: 'A hexagonal omnidirectional robot with three wheels at 120°. The controller returns {"vx", "vy"}; the original inverse kinematics turns the command into wheel speeds and the robot drives a rectangle around the arena.', tags: ['holonomic', 'hexagonal', 'Simulator', 'controller'], robots: '1 hexagonal holonomic robot' },
  },
  {
    id: 'lidar_desvio', file: 'lidar_desvio.py', group: 'tutorial', category: 'percepcao', level: 2, order: 10,
    pt: { title: 'LiDAR e desvio de obstáculos', description: 'Um B-bot diferencial com LiDAR ligado contorna três obstáculos usando um campo de forças sobre as leituras dos raios.', tags: ['LiDAR', 'obstáculos', 'desvio'], robots: '1 B-bot diferencial com LiDAR' },
    en: { filename: 'lidar_avoidance.py', title: 'LiDAR and obstacle avoidance', description: 'A differential B-bot with LiDAR on goes around three obstacles using a force field over the ray readings.', tags: ['LiDAR', 'obstacles', 'avoidance'], robots: '1 differential B-bot with LiDAR' },
  },
  {
    id: 'controle_robodiferencial', file: 'controle_robodiferencial.py', group: 'advanced', category: 'controle', level: 3, order: 10,
    pt: { title: 'Controle Kanayama (robô diferencial)', description: 'Controlador Kanayama (1990) de posição e orientação para um B-bot diferencial, com rota de cinco pontos, modelo de bateria e recarga.', tags: ['Kanayama', 'bateria', 'recarga'], robots: '1 B-bot diferencial' },
    en: { filename: 'kanayama_control.py', title: 'Kanayama control (differential robot)', description: 'Kanayama (1990) position and orientation controller for a differential B-bot, with a five-point route, battery model and recharging.', tags: ['Kanayama', 'battery', 'recharge'], robots: '1 differential B-bot' },
  },
  {
    id: 'decentralized_swarm', file: 'decentralized_swarm.py', group: 'advanced', category: 'multirobo', level: 4, order: 20,
    pt: { title: 'Enxame descentralizado', description: 'Quatro agentes HiveBrAgent com ganhos diferentes, rotas próprias e separação entre vizinhos. Usa comm_radius, LiDAR ligado e colisões resolvidas empurrando os robôs.', tags: ['enxame', 'HiveBrAgent', 'LiDAR'], robots: '4 B-bots diferenciais' },
    en: { filename: 'decentralized_swarm_advanced.py', title: 'Decentralized swarm', description: 'Four HiveBrAgent agents with different gains, their own routes and neighbour separation. Uses comm_radius, LiDAR on and collisions resolved by pushing robots apart.', tags: ['swarm', 'HiveBrAgent', 'LiDAR'], robots: '4 differential B-bots' },
  },
  {
    id: 'line_follower', file: 'line_follower.py', group: 'advanced', category: 'linha', level: 3, order: 20,
    pt: { title: 'Seguidor de linha', description: 'Seguidor de linha com sensores TCRT5000 e PID. Gera a pista aleatória em config/line_track.png e mostra os tempos das voltas.', tags: ['linha', 'PID', 'sensores TCRT5000'], robots: '1 seguidor de linha', notes: 'Aceita argumentos de linha de comando; no navegador valem os padrões.' },
    en: { filename: 'line_follower.py', title: 'Line follower', description: 'Line follower with TCRT5000 sensors and PID. Generates the random track in config/line_track.png and shows the lap times.', tags: ['line', 'PID', 'TCRT5000 sensors'], robots: '1 line follower', notes: 'Accepts command-line arguments; in the browser the defaults apply.' },
  },
  {
    id: 'multi_line_follower', file: 'multi_line_follower.py', group: 'advanced', category: 'linha', level: 3, order: 30,
    pt: { title: 'Vários seguidores de linha', description: 'Vários seguidores de linha na mesma pista, partindo do mesmo ponto, cada um com um conjunto de ganhos PID. Compara os tempos por volta.', tags: ['linha', 'PID', 'comparação de ganhos'], robots: '4 seguidores de linha' },
    en: { filename: 'multi_line_follower.py', title: 'Multiple line followers', description: 'Several line followers on the same track, starting from the same point, each with its own set of PID gains. Compares lap times.', tags: ['line', 'PID', 'gain comparison'], robots: '4 line followers' },
  },
  {
    id: 'multi_robot_differential', file: 'multi_robot_differential.py', group: 'advanced', category: 'multirobo', level: 4, order: 30,
    pt: { title: 'Frota de robôs diferenciais', description: 'Quatro B-bots diferenciais, cada um com rota e controlador Kanayama próprios. O LiDAR enxerga os outros robôs como obstáculos móveis.', tags: ['frota', 'Kanayama', 'LiDAR', 'colisão'], robots: '4 B-bots diferenciais' },
    en: { filename: 'differential_fleet.py', title: 'Differential robot fleet', description: 'Four differential B-bots, each with its own route and Kanayama controller. LiDAR sees the other robots as moving obstacles.', tags: ['fleet', 'Kanayama', 'LiDAR', 'collision'], robots: '4 differential B-bots' },
  },
  {
    id: 'run_hexagonal_holonomic', file: 'run_hexagonal_holonomic.py', group: 'advanced', category: 'locomocao', level: 3, order: 20,
    pt: { title: 'Robô hexagonal holonômico', description: 'Robô com três rodas omnidirecionais a 120°. Controle por servos com cinemática inversa e alocação de controle para respeitar o limite de velocidade das rodas.', tags: ['hexagonal', 'holonômico', 'cinemática inversa'], robots: '1 robô hexagonal holonômico' },
    en: { filename: 'hexagonal_holonomic.py', title: 'Hexagonal holonomic robot', description: 'Robot with three omnidirectional wheels at 120°. Servo control with inverse kinematics and control allocation to respect the wheel speed limit.', tags: ['hexagonal', 'holonomic', 'inverse kinematics'], robots: '1 hexagonal holonomic robot' },
  },
  {
    id: 'run_hexagonal_holonomic_line_follower', file: 'run_hexagonal_holonomic_line_follower.py', group: 'advanced', category: 'linha', level: 4, order: 40,
    pt: { title: 'Seguidor de linha hexagonal', description: 'Robô hexagonal com sensores TCRT5000 e PID sobre o erro da linha. O comando (v, omega) vira velocidades das rodas pela cinemática inversa.', tags: ['hexagonal', 'linha', 'PID'], robots: '1 robô hexagonal seguidor de linha', notes: 'O painel de texto (draw_callback) não aparece no navegador: a fonte do pygame é simulada e o texto não é desenhado.' },
    en: { filename: 'hexagonal_line_follower.py', title: 'Hexagonal line follower', description: 'Hexagonal robot with TCRT5000 sensors and PID on the line error. The (v, omega) command becomes wheel speeds through inverse kinematics.', tags: ['hexagonal', 'line', 'PID'], robots: '1 hexagonal line-follower robot', notes: 'The text panel (draw_callback) does not appear in the browser: the pygame font is simulated and text is not drawn.' },
  },
  {
    id: 'decentralized_multiprocess', file: 'decentralized_multiprocess.py', group: 'advanced', category: 'multirobo', level: 4, order: 40,
    pt: { title: 'Enxame descentralizado (multiprocess)', description: 'Enxame descentralizado com cada B-bot controlado em seu próprio núcleo de CPU via ProcessPoolExecutor.', tags: ['enxame', 'multiprocess', 'paralelo'], robots: '4 B-bots diferenciais' },
    en: { filename: 'decentralized_multiprocess.py', title: 'Decentralized swarm (multiprocess)', description: 'Decentralized swarm with each B-bot controlled on its own CPU core via ProcessPoolExecutor.', tags: ['swarm', 'multiprocess', 'parallel'], robots: '4 differential B-bots' },
  },
  {
    id: 'run_holonomic', file: 'run_holonomic.py', group: 'advanced', category: 'controle', level: 3, order: 20,
    pt: { title: 'Robô holonômico (campo potencial)', description: 'Robô holonômico com controlador de campo potencial e visualização de forças atrativas/repulsivas.', tags: ['holonômico', 'campo potencial', 'visualização'], robots: '1 B-bot holonômico' },
    en: { filename: 'holonomic_potential_field.py', title: 'Holonomic robot (potential field)', description: 'Holonomic robot with potential field controller and attractive/repulsive force visualization.', tags: ['holonomic', 'potential field', 'visualization'], robots: '1 holonomic B-bot' },
  },
  {
    id: 'python_tipos', file: 'python_tipos.py', group: 'tutorial', category: 'python', level: 1, order: 10,
    pt: { title: 'Tipos e operações em Python', description: 'Atividade: complete três funções (distância total, velocidade média e conversão para km/h) e veja os testes imprimirem TUDO CERTO.', tags: ['Python', 'funções', 'atividade'], robots: 'Nenhum robô — só Python' },
    en: { filename: 'python_types.py', title: 'Python types and operations', description: 'Activity: complete three functions (total distance, average speed and km/h conversion) and watch the tests print TUDO CERTO.', tags: ['Python', 'functions', 'activity'], robots: 'No robot — Python only' },
  },
  {
    id: 'python_numpy', file: 'python_numpy.py', group: 'tutorial', category: 'python', level: 1, order: 20,
    pt: { title: 'NumPy e matrizes de rotação', description: 'Atividade: monte a matriz de rotação 2D, aplique-a a um vetor e plote antes/depois.', tags: ['NumPy', 'matriz', 'rotação', 'atividade'], robots: 'Nenhum robô — só Python' },
    en: { filename: 'python_numpy.py', title: 'NumPy and rotation matrices', description: 'Activity: build the 2D rotation matrix, apply it to a vector and plot before/after.', tags: ['NumPy', 'matrix', 'rotation', 'activity'], robots: 'No robot — Python only' },
  },
  {
    id: 'python_plot', file: 'python_plot.py', group: 'tutorial', category: 'python', level: 1, order: 30,
    pt: { title: 'Plotando uma trajetória', description: 'Atividade: implemente uma lemniscata, plote com rótulos e salve trajetoria.png.', tags: ['matplotlib', 'gráfico', 'trajetória', 'atividade'], robots: 'Nenhum robô — só Python', notes: 'Grava trajetoria.png na pasta de trabalho a cada execução.' },
    en: { filename: 'python_plot.py', title: 'Plotting a trajectory', description: 'Activity: implement a lemniscate, plot it with labels and save trajetoria.png.', tags: ['matplotlib', 'plot', 'trajectory', 'activity'], robots: 'No robot — Python only', notes: 'Writes trajetoria.png to the working folder on every run.' },
  },
  {
    id: 'cinematica_holonomica', file: 'cinematica_holonomica.py', group: 'tutorial', category: 'locomocao', level: 2, order: 30,
    pt: { title: 'Holonômico: vx e vy', description: 'Atividade: complete o controlador proporcional vx = K·dx e vy = K·dy do robô hexagonal e leve-o até (12, 8).', tags: ['holonômico', 'vx', 'vy', 'atividade'], robots: '1 robô hexagonal holonômico' },
    en: { filename: 'holonomic_kinematics.py', title: 'Holonomic: vx and vy', description: 'Activity: complete the proportional controller vx = K*dx and vy = K*dy of the hexagonal robot and drive it to (12, 8).', tags: ['holonomic', 'vx', 'vy', 'activity'], robots: '1 hexagonal holonomic robot' },
  },
  {
    id: 'cinematica_diferencial', file: 'cinematica_diferencial.py', group: 'tutorial', category: 'locomocao', level: 2, order: 40,
    pt: { title: 'Diferencial: v e ω', description: 'Atividade: complete o modelo uniciclo com v e omega e leve o robô de (2, 2) a (14, 6).', tags: ['diferencial', 'v', 'omega', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'differential_kinematics.py', title: 'Differential: v and omega', description: 'Activity: complete the unicycle model with v and omega and drive the robot from (2, 2) to (14, 6).', tags: ['differential', 'v', 'omega', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'ir_para_alvo', file: 'ir_para_alvo.py', group: 'tutorial', category: 'controle', level: 2, order: 30,
    pt: { title: 'Ir para o alvo (go-to-goal)', description: 'Atividade: implemente distância, ângulo e ganhos proporcionais para chegar a (12, 9) sem colidir.', tags: ['go-to-goal', 'controle', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'go_to_goal.py', title: 'Go to goal', description: 'Activity: implement distance, heading and proportional gains to reach (12, 9) without colliding.', tags: ['go-to-goal', 'control', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'ir_para_pose', file: 'ir_para_pose.py', group: 'tutorial', category: 'controle', level: 3, order: 40,
    pt: { title: 'Ir para pose (x, y, θ)', description: 'Atividade: chegue a (12, 8) e termine apontando para π/2, primeiro aproximando e depois girando no lugar.', tags: ['pose', 'orientação', 'controle', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'go_to_pose.py', title: 'Go to pose (x, y, theta)', description: 'Activity: reach (12, 8) and finish facing pi/2, first approaching and then rotating in place.', tags: ['pose', 'orientation', 'control', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'apf_lidar', file: 'apf_lidar.py', group: 'advanced', category: 'percepcao', level: 3, order: 30,
    pt: { title: 'Campo potencial com LiDAR', description: 'Atividade: complete a repulsão dos raios do LiDAR e atravesse o corredor até (17, 6) sem colidir.', tags: ['APF', 'LiDAR', 'campo potencial', 'atividade'], robots: '1 B-bot diferencial com LiDAR' },
    en: { filename: 'apf_lidar.py', title: 'Potential field with LiDAR', description: 'Activity: complete the LiDAR ray repulsion and cross the corridor to (17, 6) without colliding.', tags: ['APF', 'LiDAR', 'potential field', 'activity'], robots: '1 differential B-bot with LiDAR' },
  },
  {
    id: 'linha_bangbang', file: 'linha_bangbang.py', group: 'tutorial', category: 'linha', level: 2, order: 40,
    pt: { title: 'Seguidor de linha bang-bang', description: 'Atividade: complete o controle liga-desliga (if/elif/else com LIMIAR) e faça o robô completar uma volta.', tags: ['linha', 'bang-bang', 'atividade'], robots: '1 seguidor de linha' },
    en: { filename: 'line_bangbang.py', title: 'Bang-bang line follower', description: 'Activity: complete the on-off control (if/elif/else with LIMIAR) and make the robot finish one lap.', tags: ['line', 'bang-bang', 'activity'], robots: '1 line follower' },
  },
  {
    id: 'linha_proporcional', file: 'linha_proporcional.py', group: 'tutorial', category: 'linha', level: 2, order: 50,
    pt: { title: 'Seguidor de linha proporcional', description: 'Atividade: implemente omega = KP·erro e complete uma volta com erro pequeno.', tags: ['linha', 'proporcional', 'atividade'], robots: '1 seguidor de linha' },
    en: { filename: 'line_proportional.py', title: 'Proportional line follower', description: 'Activity: implement omega = KP*error and finish a lap with a small error.', tags: ['line', 'proportional', 'activity'], robots: '1 line follower' },
  },
  {
    id: 'grid_bfs', file: 'grid_bfs.py', group: 'advanced', category: 'planejamento', level: 4, order: 10,
    pt: { title: 'Planejamento com BFS', description: 'Atividade: complete a busca em largura, reconstrua o caminho e publique os waypoints até (17, 9).', tags: ['BFS', 'planejamento', 'grade', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'grid_bfs.py', title: 'BFS path planning', description: 'Activity: complete the breadth-first search, rebuild the path and publish the waypoints to (17, 9).', tags: ['BFS', 'planning', 'grid', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'grid_astar', file: 'grid_astar.py', group: 'advanced', category: 'planejamento', level: 4, order: 20,
    pt: { title: 'Planejamento com A*', description: 'Atividade: implemente a heurística e a fila de prioridade do A* e compare o número de células expandidas com o BFS.', tags: ['A*', 'planejamento', 'grade', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'grid_astar.py', title: 'A* path planning', description: 'Activity: implement the A* heuristic and priority queue and compare the number of expanded cells with BFS.', tags: ['A*', 'planning', 'grid', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'rrt', file: 'rrt.py', group: 'advanced', category: 'planejamento', level: 4, order: 30,
    pt: { title: 'Planejamento com RRT', description: 'Atividade: implemente amostragem, steer e checagem de colisão da árvore RRT; a figura mostra a árvore e o caminho.', tags: ['RRT', 'amostragem', 'planejamento', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'rrt.py', title: 'RRT path planning', description: 'Activity: implement sampling, steer and collision checking for the RRT tree; the figure shows the tree and the path.', tags: ['RRT', 'sampling', 'planning', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'rrt_star', file: 'rrt_star.py', group: 'advanced', category: 'planejamento', level: 4, order: 40,
    pt: { title: 'Planejamento com RRT*', description: 'Atividade: adicione choose_parent e rewire para otimizar o caminho do RRT*.', tags: ['RRT*', 'otimização', 'planejamento', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'rrt_star.py', title: 'RRT* path planning', description: 'Activity: add choose_parent and rewire to optimize the RRT* path.', tags: ['RRT*', 'optimization', 'planning', 'activity'], robots: '1 differential B-bot' },
  },
  {
    id: 'curvas_parametricas', file: 'curvas_parametricas.py', group: 'advanced', category: 'planejamento', level: 4, order: 50,
    pt: { title: 'Curvas paramétricas (Bézier)', description: 'Atividade: implemente a curva de Bézier e o custo (comprimento + obstáculos + curvatura) e otimize os pontos de controle.', tags: ['Bézier', 'curvas', 'otimização', 'atividade'], robots: '1 B-bot diferencial' },
    en: { filename: 'parametric_curves.py', title: 'Parametric curves (Bezier)', description: 'Activity: implement the Bezier curve and the cost (length + obstacles + curvature) and optimize the control points.', tags: ['Bezier', 'curves', 'optimization', 'activity'], robots: '1 differential B-bot' },
  },
]

/** Catálogo no idioma pedido ('pt-BR' | 'en'): título, descrição, etiquetas, notas e código-fonte. */
export function getCatalog(locale) {
  const lang = locale === 'pt-BR' ? 'pt' : 'en'
  const folder = lang === 'en' ? TEMPLATE_EN : TEMPLATE
  return ENTRIES.map((e) => {
    const txt = e[lang]
    const source = fonte(`${folder}${e.file}`)
    const notes = txt.notes ? txt.notes : ''
    const filename = txt.filename || e.file
    // Abas extras do exemplo (módulos importados pelo script principal).
    const files = (e.files || []).map((name) => ({ name, source: fonte(`${folder}${name}`) }))
    return {
      id: e.id, group: e.group, category: e.category, level: e.level, order: e.order,
      readonly: !!e.readonly, filename, title: txt.title, description: txt.description,
      tags: txt.tags, robots: txt.robots, notes, source, files,
    }
  })
}

/** Compatibilidade: catálogo em português. */
export const CATALOG = getCatalog('pt-BR')
