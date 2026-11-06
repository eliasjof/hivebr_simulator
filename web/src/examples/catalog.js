// Catálogo de exemplos do editor.
// Os .py entram como texto bruto (?raw) no momento do build: os templates de
// web/templates/ e os exemplos do repositório em examples/. Os caminhos abaixo
// são relativos a este arquivo (web/src/examples/).

const raw = import.meta.glob(['../../templates/*.py', '../../../examples/*.py'], {
  query: '?raw',
  import: 'default',
  eager: true,
})

const TEMPLATE = '../../templates/'
const REPO = '../../../examples/'

function fonte(caminho) {
  const texto = raw[caminho]
  if (texto === undefined) throw new Error(`Exemplo não incluído no build: ${caminho}`)
  return texto
}

const TUTORIAIS = 'Tutoriais'
const EXEMPLOS_REPO = 'Exemplos do repositório'
const DEMONSTRACAO = 'Demonstração'

export const DEFAULT_EXAMPLE_ID = 'inicio_rapido'
export const DEMO_EXAMPLE_ID = 'demonstracao'

export const CATALOG = [
  {
    id: DEMO_EXAMPLE_ID,
    title: 'Demonstração',
    description:
      'Seis B-bots em duas patrulhas (três em cada rota fechada), com obstáculos, LiDAR, separação entre vizinhos e comunicação limitada. Roda em loop até você parar.',
    tags: ['demonstração', 'enxame', 'LiDAR', 'HiveBrAgent', 'obstáculos'],
    robots: '6 B-bots diferenciais (2 grupos)',
    source: fonte(`${TEMPLATE}demonstracao.py`),
    group: DEMONSTRACAO,
    readonly: true,
  },

  // ---------------------------------------------------------------- Tutoriais
  {
    id: 'inicio_rapido',
    title: 'Início rápido',
    description:
      'Um B-bot diferencial percorrendo uma rota de waypoints com um agente HiveBrAgent que vai até o objetivo.',
    tags: ['iniciante', 'waypoints', 'HiveBrAgent'],
    robots: '1 B-bot diferencial',
    source: fonte(`${TEMPLATE}inicio_rapido.py`),
    group: TUTORIAIS,
  },
  {
    id: 'swarm_descentralizado',
    title: 'Enxame descentralizado',
    description:
      'Quatro agentes HiveBrAgent, cada um com sua rota, separação entre vizinhos, comm_radius de 3 m e ligações entre os robôs visíveis.',
    tags: ['enxame', 'descentralizado', 'comm_radius', 'separação'],
    robots: '4 B-bots diferenciais',
    source: fonte(`${TEMPLATE}swarm_descentralizado.py`),
    group: TUTORIAIS,
  },
  {
    id: 'swarm_centralizado',
    title: 'Formação centralizada',
    description:
      'Um SwarmController comanda os quatro B-bots e os mantém em círculo ao redor do centroide ou em linha. Devolve {id: (v, omega)}.',
    tags: ['centralizado', 'SwarmController', 'formação'],
    robots: '4 B-bots diferenciais',
    source: fonte(`${TEMPLATE}swarm_centralizado.py`),
    group: TUTORIAIS,
  },
  {
    id: 'seguidor_de_linha',
    title: 'Seguidor de linha com PID',
    description:
      'Gera uma pista fechada aleatória e segue a linha com cinco sensores TCRT5000 e um controlador PID. Mostra os tempos das voltas.',
    tags: ['linha', 'PID', 'sensores TCRT5000'],
    robots: '1 seguidor de linha',
    source: fonte(`${TEMPLATE}seguidor_de_linha.py`),
    group: TUTORIAIS,
    notes: 'Grava config/line_track.png na pasta de trabalho a cada execução.',
  },
  {
    id: 'holonomico',
    title: 'Robô holonômico',
    description:
      'Um robô omnidirecional que anda em qualquer direção. O controlador devolve {"vx", "vy"} e percorre um retângulo na arena.',
    tags: ['holonômico', 'Simulator', 'controlador'],
    robots: '1 B-bot holonômico',
    source: fonte(`${TEMPLATE}holonomico.py`),
    group: TUTORIAIS,
  },
  {
    id: 'lidar_desvio',
    title: 'LiDAR e desvio de obstáculos',
    description:
      'Um B-bot diferencial com LiDAR ligado contorna três obstáculos usando um campo de forças sobre as leituras dos raios.',
    tags: ['LiDAR', 'obstáculos', 'desvio'],
    robots: '1 B-bot diferencial com LiDAR',
    source: fonte(`${TEMPLATE}lidar_desvio.py`),
    group: TUTORIAIS,
  },

  // ----------------------------------------------------- Exemplos do repositório
  {
    id: 'controle_robodiferencial',
    title: 'Controle Kanayama (robô diferencial)',
    description:
      'Controlador Kanayama (1990) de posição e orientação para um B-bot diferencial, com rota de cinco pontos, modelo de bateria e recarga.',
    tags: ['Kanayama', 'bateria', 'recarga'],
    robots: '1 B-bot diferencial',
    source: fonte(`${REPO}controle_robodiferencial.py`),
    group: EXEMPLOS_REPO,
  },
  {
    id: 'decentralized_swarm',
    title: 'Enxame descentralizado',
    description:
      'Quatro agentes HiveBrAgent com ganhos diferentes, rotas próprias e separação entre vizinhos. Usa comm_radius, LiDAR ligado e colisões resolvidas empurrando os robôs.',
    tags: ['enxame', 'HiveBrAgent', 'LiDAR'],
    robots: '4 B-bots diferenciais',
    source: fonte(`${REPO}decentralized_swarm.py`),
    group: EXEMPLOS_REPO,
  },
  {
    id: 'line_follower',
    title: 'Seguidor de linha',
    description:
      'Seguidor de linha com sensores TCRT5000 e PID. Gera a pista aleatória em config/line_track.png e mostra os tempos das voltas.',
    tags: ['linha', 'PID', 'sensores TCRT5000'],
    robots: '1 seguidor de linha',
    source: fonte(`${REPO}line_follower.py`),
    group: EXEMPLOS_REPO,
    notes: 'Aceita argumentos de linha de comando; no navegador valem os padrões.',
  },
  {
    id: 'multi_line_follower',
    title: 'Vários seguidores de linha',
    description:
      'Vários seguidores de linha na mesma pista, partindo do mesmo ponto, cada um com um conjunto de ganhos PID. Compara os tempos por volta.',
    tags: ['linha', 'PID', 'comparação de ganhos'],
    robots: '4 seguidores de linha',
    source: fonte(`${REPO}multi_line_follower.py`),
    group: EXEMPLOS_REPO,
  },
  {
    id: 'multi_robot_differential',
    title: 'Frota de robôs diferenciais',
    description:
      'Quatro B-bots diferenciais, cada um com rota e controlador Kanayama próprios. O LiDAR enxerga os outros robôs como obstáculos móveis.',
    tags: ['frota', 'Kanayama', 'LiDAR', 'colisão'],
    robots: '4 B-bots diferenciais',
    source: fonte(`${REPO}multi_robot_differential.py`),
    group: EXEMPLOS_REPO,
  },
  {
    id: 'run_hexagonal_holonomic',
    title: 'Robô hexagonal holonômico',
    description:
      'Robô com três rodas omnidirecionais a 120°. Controle por servos com cinemática inversa e alocação de controle para respeitar o limite de velocidade das rodas.',
    tags: ['hexagonal', 'holonômico', 'cinemática inversa'],
    robots: '1 robô hexagonal holonômico',
    source: fonte(`${REPO}run_hexagonal_holonomic.py`),
    group: EXEMPLOS_REPO,
  },
  {
    id: 'run_hexagonal_holonomic_line_follower',
    title: 'Seguidor de linha hexagonal',
    description:
      'Robô hexagonal com sensores TCRT5000 e PID sobre o erro da linha. O comando (v, omega) vira velocidades das rodas pela cinemática inversa.',
    tags: ['hexagonal', 'linha', 'PID'],
    robots: '1 robô hexagonal seguidor de linha',
    source: fonte(`${REPO}run_hexagonal_holonomic_line_follower.py`),
    group: EXEMPLOS_REPO,
    notes: 'O painel de texto (draw_callback) não aparece no navegador: a fonte do pygame é simulada e o texto não é desenhado.',
  },
]
