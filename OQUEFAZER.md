
-- é possível acrescentar um example para utilizar a biblioteca ompl junto com o simulador?

- seria possível implmentar também a simulação de um robo manipulador SCARA 3D (como o da epson ou similar ABB?) por exemplo com uma esteira com objetos coloridos (colocar na esteira uma detecção de cor), de forma que no código o usuário controla a esteira e o braço robótico para pegar esses objetos e colocar nas cestas correspondentes.

- o último do nível de aprendizado precisa fazer um relatório. avaliar o desenvolvimento por um relatório contendo os corretos, colocar um botão para submeter para avaliação ao chegar nas fases finais (crie a estrutura, para cada etapa iremos trabalhar no que precisa conter no relatório .md)

---

# Plano: organização dos exemplos + gamificação educacional

## Objetivo

Organizar a galeria de exemplos por categoria e criar uma trilha de aprendizagem
gamificada, com níveis, atividades, objetivos verificáveis, XP, medalhas e
progresso persistente. A sequência pedagógica vai do ensino técnico à graduação.

A avaliação de viabilidade é positiva: o catálogo já é um módulo de dados, a
galeria já tem busca/filtros, o runner devolve `ok`/`stopped`/`error`/`files`,
os frames trazem `line_error`, `lap_count`, `best_lap`, `finished` e
`collisions_total`, e o `localStorage` já é usado com chaves versionadas.

Limitação principal: não há backend. O progresso fica no navegador do aluno.
Para uso em sala, a solução é exportar/importar JSON; para nota oficial, será
necessário um backend ou assinatura de submissão.

## Decisão de arquitetura

- O **catálogo** continua sendo a lista de exemplos (`web/src/examples/catalog.js`).
- O **currículo** fica separado em `web/src/learning/`, referenciando exemplos por `id`.
- A **validação** é feita por comportamento (frames/telemetria/arquivos), não por
  texto do código.
- O **progresso** usa `localStorage` com a chave versionada
  `hivebr.web.learning.v1`, seguindo o padrão de `hivebr.web.prefs.v1`.
- A sequência é **recomendada, não bloqueante**: todos os níveis ficam visíveis,
  com o próximo passo em destaque. Bloqueio rígido só nos desafios de conclusão,
  se for desejado depois.

## Fase 1 — Organização por categoria

Status: concluída nesta rodada.

- [x] Adicionar `category`, `level` e `order` a cada entrada do catálogo.
- [x] Exportar `CATEGORY_IDS` e `LEVEL_IDS` em `catalog.js`.
- [x] Devolver os novos campos em `getCatalog()`.
- [x] Adicionar filtros de categoria e nível na galeria (`ExamplesModal.vue`).
- [x] Agrupar os cards por categoria, ordenando por nível e ordem.
- [x] Mostrar selo de nível em cada card.
- [x] Criar rótulos de categoria/nível em `pt-BR.js` e `en.js`.
- [x] Testar que todo exemplo tem categoria, nível e ordem válidos.

### Taxonomia adotada

| Categoria | Exemplos | Nível |
|---|---|---|
| Fundamentos | `demonstracao`, `inicio_rapido`, `importando_modulo` | 1 |
| Percepção e obstáculos | `lidar_desvio` | 2 |
| Seguidores de linha | `seguidor_de_linha`, `line_follower`, `multi_line_follower`, `run_hexagonal_holonomic_line_follower` | 2–4 |
| Locomoção e cinemática | `holonomico`, `run_hexagonal_holonomic` | 3 |
| Controle e navegação | `controle_robodiferencial`, `run_holonomic` | 3 |
| Enxame e multi-robô | `swarm_descentralizado`, `swarm_centralizado`, `decentralized_swarm`, `multi_robot_differential`, `decentralized_multiprocess` | 2–4 |

## Fase 2 — Estrutura de progresso e gamificação

Status: estrutura concluída nesta rodada; conteúdo completo fica para a Fase 3.

- [x] Criar `web/src/learning/curriculum.js` com níveis, trilhas e atividades.
- [x] Criar `web/src/learning/progress.js` com XP, medalhas, atividade ativa,
      persistência, reset e exportar/importar JSON.
- [x] Criar `web/src/learning/validate.js` com checagens puras por objetivo.
- [x] Acumular evidências de execução no `store.js` (frames + `finished`).
- [x] Avaliar a atividade ativa durante a telemetria e ao final da execução.
- [x] Criar `LearningModal.vue` com trilha por nível, progresso, atividades e medalhas.
- [x] Adicionar entrada “Aprender” na barra de ferramentas.
- [x] Registrar `store.modals.learning`.
- [x] Criar testes unitários de validação e de integridade do currículo.

### Modelo de dados do progresso

```js
// localStorage: hivebr.web.learning.v1
{
  v: 1,
  xp: 0,
  activeId: null,
  activities: {
    'volta-completa': {
      done: true,
      stars: 3,
      at: 1699999999999,
      evidence: { laps: 2, bestLap: 18.4, maxLineError: 0.03, collisions: 0 }
    }
  },
  badges: ['primeiro-passo', 'piloto-de-linha'],
  updatedAt: 1699999999999
}
```

### Objetivos suportados hoje

| Objetivo | Fonte |
|---|---|
| `run_ok` | `finished.ok` |
| `finish_lap` | `lap_count` dos frames |
| `lap_time_max` | `best_lap` |
| `line_error_max` | `line_error` acumulado |
| `no_collision` | `collisions_total` |
| `file_exists` | `finished.files` |
| `figure_min` | `store.figures` |
| `report_saved` | `store.reports` |
| `capture_saved` | `store.captures` |
| `console_has` | linhas do console |

## Fase 3 — Propostas de atividades (para aprovação)

Status: **concluída**. As ondas 3.1–3.4 foram aprovadas e implementadas juntas:
15 templates novos em PT/EN, 19 atividades no currículo, medalhas e conquistas
com emoji. A seção “Status de implementação” abaixo registra os detalhes e a
validação.

### Princípio: toda atividade exige mudar o código

Cada atividade segue o mesmo contrato:

1. Carrega um template com cabeçalho de atividade, um alvo explícito e blocos
   `# TODO` (ou `# COMPLETE`).
2. O aluno **edita o código** para cumprir o alvo; executar o exemplo original
   não basta.
3. A validação olha o **comportamento** (frames, trilha, telemetria, arquivos,
   figuras, console), não o texto do código.
4. A entrega é uma evidência concreta: trajetória, figura, arquivo ou saída.
5. A conclusão dá XP, estrelas e medalha.

Nas atividades de Python, o próprio template traz testes (`assert`) e imprime
`TUDO CERTO` quando o aluno completa as funções. Nas atividades com simulador,
o robô precisa atingir o alvo, completar a volta, desviar etc.

### Nova grade de níveis e trilhas

| Nível | Tema | Trilhas | Sequência de sala |
|---|---|---|---|
| 1 | Python e visualização | `python`, `fundamentos` | tipos, operações, numpy, matrizes, plot |
| 2 | Cinemática e controle | `cinematica`, `navegacao`, `linha` | vx/vy, v/ω, chegar ao alvo; seguidor de linha em paralelo |
| 3 | Percepção e desvio | `navegacao`, `percepcao` | chegar com orientação, APF com LiDAR |
| 4 | Planejamento de caminho | `planejamento` | BFS, A*, RRT, RRT*, curvas paramétricas |

A sequência continua **recomendada, não bloqueante**. O nível 2 tem duas
trilhas paralelas: cinemática/navegação e seguidor de linha.

Categorias novas no catálogo: `python` e `planejamento`. As demais atividades
reaproveitam `locomocao`, `controle`, `percepcao` e `linha`.

### Medalhas e conquistas (com emojis)

As três medalhas atuais já receberam emoji. A lista completa proposta é:

| Medalha | Emoji | Como obter | Atividade |
|---|---|---|---|
| Primeiro passo | 🥇 | executar o primeiro exemplo | `primeiro-movimento` |
| Pythonista | 🐍 | concluir tipos e operações | `python-tipos` |
| Mestre das matrizes | 🔢 | concluir numpy/matrizes | `python-numpy` |
| Visualizador | 📈 | plotar e salvar uma trajetória | `python-plot` |
| Holonômico | 🛞 | chegar ao alvo com vx/vy | `holonomico-vxvy` |
| Diferencial | ⚙️ | controlar v/ω | `diferencial-vomega` |
| Alvo alcançado | 🎯 | chegar ao alvo | `chegar-alvo` |
| Orientação | 🧭 | chegar com orientação | `chegar-alvo-orientacao` |
| Piloto de linha | 🏁 | completar uma volta | `volta-completa` |
| Bang-bang | ⚡ | seguir linha com bang-bang | `linha-bangbang` |
| Proporcional | 📏 | seguir linha com controle proporcional | `linha-proporcional` |
| Desviador | 🛡️ | desviar sem colidir | `desvio-limpo` |
| Campo potencial | 🧲 | APF com LiDAR | `apf-lidar` |
| Escape | 🌀 | sair de um mínimo local | `apf-minimo-local` |
| BFS | 🗺️ | planejar com BFS | `grid-bfs` |
| A* | ⭐ | planejar com A* | `grid-astar` |
| RRT | 🌳 | planejar com RRT | `rrt` |
| RRT* | ✨ | planejar com RRT* | `rrt-star` |
| Curvas | 〰️ | otimizar curva paramétrica | `curvas-parametricas` |
| Planejador | 🧠 | concluir todos os planejadores | conquista agregada |
| Mestre HiveBr | 🏆 | concluir o currículo | conquista agregada |

As duas conquistas agregadas exigem um pequeno conceito novo: uma lista de
`achievements` avaliada após cada conclusão (ex.: todos os `grid-*`, `rrt*` e
`curvas-parametricas` concluídos → 🧠; todas as atividades → 🏆).

### Objetivos novos necessários

Os objetivos atuais cobrem execução, voltas, linha, colisão, arquivos, figuras,
relatórios, capturas e console. Para as atividades novas faltam metas
geométricas e de desempenho:

| Objetivo | Verifica | Evidência necessária |
|---|---|---|
| `reach_goal` | distância mínima até `(x, y)` ≤ `tolerance` | trilha do robô |
| `orientation_error_max` | `|wrap(theta - theta_goal)|` ≤ `value` no ponto mais próximo do alvo | trilha + `theta` |
| `time_max` | tempo até atingir o alvo ≤ `value` | `reachTime` ou `t` |
| `path_length_max` | comprimento percorrido até o alvo ≤ `value` | trilha |
| `min_travel` | comprimento percorrido ≥ `value` (garante que andou) | trilha |
| `waypoint_count_min` | nº de waypoints definidos ≥ `n` | `frame.waypoints` |
| `robot_count` | nº de robôs ≥ `n` | `frame.robots` |
| `code_uses` | fonte contém um token (secundário) | código da aba ativa |

`code_uses` é **secundário**: nunca será o único objetivo de uma atividade,
porque é fácil de burlar. A validação principal é sempre comportamental.

### Como a validação vai funcionar

A trilha resolve quase tudo sem mexer na serialização Python. O `store.js`
passa a acumular, além do que já acumula:

```js
// store.js — evidência acumulada (novos campos)
runEvidence = {
  t, robots, collisions, maxLineError, lineSamples, laps, bestLap,
  finished, finishTime,
  trails: [ [{ x, y, theta, t }, ...], ... ], // ~10 Hz, limite ~3000 pontos
  wpTotal, waypointCount,
  reachTime,          // primeiro instante dentro da tolerância do alvo
  pathLengthAtGoal,   // comprimento percorrido até o alvo
}
```

- `reach_goal`: menor distância da trilha até `(x, y)` ≤ `tolerance`.
  Ao cruzar a tolerância, grava `reachTime` e `pathLengthAtGoal`.
- `orientation_error_max`: entre os pontos dentro da tolerância de `(x, y)`,
  usa o mais próximo (ou o último) e compara `theta` com `theta_goal`.
- `time_max`: usa `reachTime` quando existe; senão, `t`.
- `path_length_max`: usa `pathLengthAtGoal` quando existe; senão, o comprimento
  total da trilha.
- `min_travel`: comprimento total da trilha ≥ `value`.
- `waypoint_count_min`: `waypointCount` (cache de `frame.waypoints`) ≥ `n`.

A amostragem da trilha é feita no cliente, a cada ~0,1 s de simulação, com
limite de pontos para não crescer sem controle. Não é necessário alterar o
`serialize.py`.

### Templates novos necessários

Todos precisam de versão PT (`web/templates/`) e EN (`web/templates/en/`) e de
entrada no catálogo com `category`, `level` e `order`.

| Template | Base | Simulador? | Objetivo |
|---|---|---|---|
| `python_tipos.py` | novo | não | tipos, operações, funções, `print` |
| `python_numpy.py` | novo | não | arrays, matrizes, rotação, plot |
| `python_plot.py` | novo | não | matplotlib e figura salva |
| `cinematica_holonomica.py` | `holonomico.py` | sim | `vx`/`vy` |
| `cinematica_diferencial.py` | `controle_robodiferencial.py` | sim | `v`/`omega` |
| `ir_para_alvo.py` | novo | sim | go-to-goal |
| `ir_para_pose.py` | novo | sim | go-to-pose com orientação |
| `apf_lidar.py` | `lidar_desvio.py` | sim | campo potencial explícito |
| `linha_bangbang.py` | `seguidor_de_linha.py` | sim | controle bang-bang |
| `linha_proporcional.py` | `seguidor_de_linha.py` | sim | controle proporcional |
| `grid_bfs.py` | novo | sim | BFS + waypoints |
| `grid_astar.py` | novo | sim | A* + waypoints |
| `rrt.py` | novo | sim | RRT + waypoints |
| `rrt_star.py` | novo | sim | RRT* + waypoints |
| `curvas_parametricas.py` | novo | sim | Bézier/spline + otimização |

São 15 templates × 2 idiomas = 30 arquivos. Por isso a implementação é
proposta em ondas (ver abaixo).

### Atividades propostas, na ordem da sala de aula

#### Etapa 1 — Python: tipos, operações, numpy, matrizes e plot

**A1.1 · 🐍 Tipos e operações** (`python-tipos`)
- Nível 1 · trilha `python` · template novo `python_tipos.py` (sem simulador).
- **Modificação:** completar `distancia_total()`, `velocidade_media()` e
  `converter_kmh()`; usar os cinco valores de `DISTANCIAS` e `TEMPOS`; imprimir
  com duas casas decimais.
- **Validação:** `run_ok`; `console_has: "TUDO CERTO"` (testes embutidos).
- **Entrega:** saída do console.
- **XP/medalha:** 40 XP · 🐍 Pythonista · esforço S (30–45 min).

**A1.2 · 🔢 NumPy e matrizes** (`python-numpy`)
- Nível 1 · trilha `python` · template novo `python_numpy.py`.
- **Modificação:** criar arrays, calcular média/desvio, montar a matriz de
  rotação `R(θ)`, aplicar a um vetor em `rotacionar()` e plotar antes/depois.
- **Validação:** `run_ok`; `console_has: "TUDO CERTO"`; `figure_min: 1`.
- **Entrega:** console + figura.
- **XP/medalha:** 50 XP · 🔢 Mestre das matrizes · esforço S/M.

**A1.3 · 📈 Plotando a trajetória** (`python-plot`)
- Nível 1 · trilha `python` · template novo `python_plot.py`.
- **Modificação:** implementar `trajetoria(t)` (círculo ou lemniscata), plotar
  com rótulos e legenda e salvar `trajetoria.png`.
- **Validação:** `run_ok`; `figure_min: 1`; `file_exists: "trajetoria.png"`;
  `console_has: "FIGURA SALVA"`.
- **Entrega:** figura + arquivo.
- **XP/medalha:** 50 XP · 📈 Visualizador · esforço S.

#### Etapa 2 — Cinemática: vx/vy e v/ω

**A2.1 · 🛞 Holonômico: vx e vy** (`holonomico-vxvy`)
- Nível 2 · trilha `cinematica` · template novo `cinematica_holonomica.py`,
  baseado em `holonomico.py`.
- **Modificação:** completar `controlador_holonomico()` com `vx = K*dx` e
  `vy = K*dy`; trocar `ALVO` para `(12, 8)`; respeitar `VELOCIDADE_MAXIMA`.
- **Validação:** `run_ok`; `reach_goal {x: 12, y: 8, tolerance: 0.4}`;
  `time_max: 25`; `no_collision`.
- **Estrelas:** `time_max: 18`; `path_length_max: 15`.
- **XP/medalha:** 60 XP · 🛞 Holonômico · esforço M.

**A2.2 · ⚙️ Diferencial: v e ω** (`diferencial-vomega`)
- Nível 2 · trilha `cinematica` · template novo `cinematica_diferencial.py`,
  baseado em `controle_robodiferencial.py`.
- **Modificação:** completar o modelo uniciclo: `v` e `omega` para descrever um
  arco/círculo de raio `R`; trocar `V` e `OMEGA`; comparar com o holonômico.
- **Validação:** `run_ok`; `reach_goal {x, y, tolerance: 0.4}`; `time_max`;
  `no_collision`.
- **Estrelas:** `path_length_max`; `time_max` mais curto.
- **XP/medalha:** 60 XP · ⚙️ Diferencial · esforço M.

#### Etapa 3 — Chegar ao alvo

**A2.3 · 🎯 Chegar ao alvo** (`chegar-alvo`)
- Nível 2 · trilha `navegacao` · template novo `ir_para_alvo.py`.
- **Modificação:** implementar go-to-goal: `dist`, `ang`,
  `v = min(VMAX, KP_DIST*dist)` e `omega = KP_ANG*ang`; trocar `ALVO` e ajustar
  os ganhos.
- **Validação:** `run_ok`; `reach_goal {x: 12, y: 9, tolerance: 0.35}`;
  `time_max: 30`; `no_collision`.
- **Estrelas:** `time_max: 22`; `path_length_max: 16`.
- **XP/medalha:** 70 XP · 🎯 Alvo alcançado · esforço M.

#### Etapa 4 — Chegar ao alvo com orientação

**A3.1 · 🧭 Chegar ao alvo com orientação** (`chegar-alvo-orientacao`)
- Nível 3 · trilha `navegacao` · template novo `ir_para_pose.py`.
- **Modificação:** usar waypoint `[x, y, theta]` e implementar controle de
  posição + orientação (duas etapas ou Kanayama simplificado); ajustar
  `K_ALPHA` e `K_BETA`.
- **Validação:** `run_ok`; `reach_goal {x, y, tolerance: 0.35}`;
  `orientation_error_max {x, y, theta, tolerance: 0.35, value: 0.175}` (10°);
  `no_collision`.
- **Estrelas:** `orientation_error_max` em 5°; `time_max`.
- **XP/medalha:** 80 XP · 🧭 Orientação · esforço M/L.

#### Etapa 5 — Desvio com campo potencial artificial e LiDAR

**A3.2 · 🧲 Campo potencial artificial com LiDAR** (`apf-lidar`)
- Nível 3 · trilha `percepcao` · template novo `apf_lidar.py`, baseado em
  `lidar_desvio.py`.
- **Modificação:** separar `forca_atrativa()` e `forca_repulsiva()`; completar
  o somatório dos raios; adicionar um quarto obstáculo; ajustar `K_ATR`,
  `K_REP` e `D0`.
- **Validação:** `run_ok`; `reach_goal {x: 17, y: 6, tolerance: 0.5}`;
  `no_collision`; `time_max: 45`.
- **Estrelas:** `time_max: 35`; `path_length_max`.
- **XP/medalha:** 90 XP · 🧲 Campo potencial · esforço L.

**A3.3 · 🌀 Escapando de mínimos locais** (`apf-minimo-local`, optativa)
- Nível 3/4 · trilha `percepcao` · mesmo template `apf_lidar.py`.
- **Modificação:** adicionar componente tangencial (ou perturbação) quando a
  repulsão saturar; criar um corredor com obstáculos que forme mínimo local.
- **Validação:** `run_ok`; `reach_goal`; `no_collision`.
- **XP/medalha:** 100 XP · 🌀 Escape · esforço L.

#### Etapa 6 — Seguidor de linha (trilha paralela)

**A2.4 · ⚡ Seguidor bang-bang** (`linha-bangbang`)
- Nível 2 · trilha `linha` · template novo `linha_bangbang.py`, simplificado de
  `seguidor_de_linha.py`.
- **Modificação:** completar o bloco: se `erro > LIMIAR`, `omega = +OMEGA`;
  se `erro < -LIMIAR`, `omega = -OMEGA`; senão `omega = 0`; ajustar `OMEGA` e
  `LIMIAR`.
- **Validação:** `run_ok`; `finish_lap {laps: 1}`; `no_collision`.
- **Estrelas:** `lap_time_max: 40`; `line_error_max: 0.55`.
- **XP/medalha:** 60 XP · ⚡ Bang-bang · esforço M.

**A2.5 · 📏 Seguidor proporcional** (`linha-proporcional`)
- Nível 2 · trilha `linha` · template novo `linha_proporcional.py`.
- **Modificação:** implementar `omega = KP * erro`; ajustar `KP`; comparar com
  o bang-bang na mesma pista.
- **Validação:** `run_ok`; `finish_lap {laps: 1}`; `line_error_max: 0.30`.
- **Estrelas:** `lap_time_max: 35`; `line_error_max: 0.26`.
- **XP/medalha:** 70 XP · 📏 Proporcional · esforço M.

#### Etapa 7 — Planejamento de caminho (nível avançado)

**A4.1 · 🗺️ BFS no grid** (`grid-bfs`)
- Nível 4 · trilha `planejamento` · template novo `grid_bfs.py`.
- **Modificação:** completar `bfs()` (fila, vizinhos 4/8, grade de ocupação) e
  `reconstruir_caminho()`; converter o caminho em waypoints para o robô.
- **Validação:** `run_ok`; `reach_goal`; `no_collision`;
  `console_has: "caminho="`.
- **Estrelas:** `path_length_max`; `time_max`.
- **XP/medalha:** 100 XP · 🗺️ BFS · esforço L.

**A4.2 · ⭐ A* no grid** (`grid-astar`)
- Nível 4 · trilha `planejamento` · template novo `grid_astar.py`.
- **Modificação:** implementar `heuristica()` (Manhattan/Euclidiana), fila de
  prioridade e custos `g`/`f`; comparar nós expandidos com o BFS.
- **Validação:** `run_ok`; `reach_goal`; `no_collision`;
  `console_has: "expandidos="`.
- **Estrelas:** `path_length_max`; `time_max`.
- **XP/medalha:** 110 XP · ⭐ A* · esforço L.

**A4.3 · 🌳 RRT** (`rrt`)
- Nível 4 · trilha `planejamento` · template novo `rrt.py`.
- **Modificação:** implementar `amostrar()`, `mais_proximo()`, `steer()`,
  `sem_colisao()` e viés para o alvo; plotar árvore + caminho.
- **Validação:** `run_ok`; `reach_goal`; `no_collision`; `figure_min: 1`.
- **Estrelas:** `path_length_max`; `time_max`.
- **XP/medalha:** 120 XP · 🌳 RRT · esforço L.

**A4.4 · ✨ RRT\*** (`rrt-star`)
- Nível 4 · trilha `planejamento` · template novo `rrt_star.py`.
- **Modificação:** adicionar `choose_parent()` e `rewire()` ao RRT; comparar o
  comprimento do caminho com o RRT.
- **Validação:** `run_ok`; `reach_goal`; `no_collision`; `figure_min: 1`.
- **Estrelas:** `path_length_max` (limiar calibrado entre RRT e RRT*);
  `time_max`.
- **XP/medalha:** 130 XP · ✨ RRT* · esforço XL.

**A4.5 · 〰️ Otimização com curvas paramétricas** (`curvas-parametricas`)
- Nível 4 · trilha `planejamento` · template novo `curvas_parametricas.py`.
- **Modificação:** implementar Bézier/B-spline `curva(pontos, t)`; otimizar os
  pontos de controle (comprimento + curvatura + repulsão dos obstáculos) com
  `scipy.optimize.minimize` ou descida de coordenadas; publicar waypoints.
- **Validação:** `run_ok`; `reach_goal`; `no_collision`;
  `path_length_max`; `figure_min: 1`.
- **Estrelas:** `path_length_max` mais curto; `time_max`.
- **XP/medalha:** 140 XP · 〰️ Curvas · esforço XL.

### Ordem de implementação sugerida

| Onda | Conteúdo | Dependências | Esforço |
|---|---|---|---|
| 3.1 | Nível 1: 3 atividades de Python + emojis | `console_has`, `figure_min`, `file_exists` | S/M |
| 3.2 | Nível 2: cinemática, alvo e linha (5 atividades) | trilha, `reach_goal`, `time_max`, `path_length_max` | M/L |
| 3.3 | Nível 3: orientação + APF (2–3 atividades) | `orientation_error_max`, calibração do APF | L |
| 3.4 | Nível 4: BFS, A*, RRT, RRT*, curvas (5 atividades) | templates de planejamento, figuras | XL |

Cada onda inclui templates PT/EN, entradas no catálogo, chaves de i18n,
medalhas, testes unitários e um teste headless de fumaça.

### Critérios de aceite da Fase 3

- Toda atividade nova tem template com `# TODO` e alvo explícito.
- O template original **não** passa na atividade sem edição (exceto o warm-up
  `primeiro-movimento`).
- Os objetivos são comportamentais; `code_uses` nunca é o único objetivo.
- XP, medalhas e estrelas persistem e aparecem com emoji no modal e no toast.
- `npm run test:i18n`, `npm run test:examples` e
  `node --test tests/learning/learning.test.mjs` passam.
- `npx vite build` passa.
- Um teste headless inicia ao menos uma atividade por nível, executa, conclui,
  recarrega e confere a persistência.

### Decisões aprovadas

1. Grade de níveis/trilhas e as 16 atividades (15 obrigatórias + 1 optativa):
   aprovadas.
2. Implementação: **todas as ondas de uma vez** (3.1 a 3.4).
3. `apf-minimo-local` e `curvas-parametricas` mantidas (a primeira optativa, a
   segunda obrigatória no nível 4).
4. `XP_THRESHOLDS = [0, 200, 500, 900]`.
5. Conquistas agregadas 🧠 Planejador e 🏆 Mestre HiveBr: aprovadas.

## Fase 3 — Status de implementação

Status: **concluída e validada**.

### Checklist

- [x] `validate.js`: `wrapAngle`, `trailOf`, `trailLength`, `trailMinDistance` e
      os objetivos `reach_goal`, `orientation_error_max`, `time_max`,
      `path_length_max`, `min_travel`, `waypoint_count_min`, `robot_count` e
      `code_uses` (secundário).
- [x] `progress.js`: XP `[0, 200, 500, 900]`, persistência de conquistas,
      `hasAchievement`, `syncAchievements` e retorno de conquistas em
      `completeActivity`.
- [x] `curriculum.js`: 8 trilhas, 19 atividades e `ACHIEVEMENTS`, com dicas,
      metas, estrelas e medalhas.
- [x] `store.js`: trilha por robô (~10 Hz), comprimento percorrido, instante e
      comprimento no alvo, waypoints, `runSource`/`runGoal`,
      `learningSnapshot()` e toasts de conquista.
- [x] `LearningModal.vue`: rótulos dos novos objetivos, checklist ao vivo,
      seção de conquistas e `data-activity-id` para testes.
- [x] 15 templates PT em `web/templates/` e 15 espelhos EN em
      `web/templates/en/`.
- [x] Catálogo com as 15 entradas, `category`, `level`, `order`, metadados PT/EN
      e as categorias novas `python` e `planejamento`.
- [x] i18n PT/EN com paridade de chaves e parâmetros; emojis nas medalhas e
      conquistas.
- [x] Testes unitários de currículo, objetivos, trilha, sequência de sala e
      conquistas.
- [x] Teste headless focado (`web/tests/e2e/learning.e2e.mjs`, via
      `npm run test:learning`): uma atividade por nível é iniciada, editada,
      executada, concluída e recarregada.

### Templates e atividades entregues

| Nível | Template | Atividade | Objetivo principal |
|---|---|---|---|
| 1 | `python_tipos.py` | `python-tipos` | `console_has: TUDO CERTO` |
| 1 | `python_numpy.py` | `python-numpy` | `console_has` + `figure_min` |
| 1 | `python_plot.py` | `python-plot` | figura + `trajetoria.png` |
| 2 | `cinematica_holonomica.py` | `holonomico-vxvy` | `reach_goal (12, 8)` |
| 2 | `cinematica_diferencial.py` | `diferencial-vomega` | `reach_goal (14, 6)` |
| 2 | `ir_para_alvo.py` | `chegar-alvo` | `reach_goal (12, 9)` |
| 2 | `linha_bangbang.py` | `linha-bangbang` | `finish_lap` |
| 2 | `linha_proporcional.py` | `linha-proporcional` | `finish_lap` + erro |
| 3 | `ir_para_pose.py` | `chegar-alvo-orientacao` | posição + orientação |
| 3 | `apf_lidar.py` | `apf-lidar` | `reach_goal` sem colisão |
| 4 | `grid_bfs.py` | `grid-bfs` | caminho + waypoints |
| 4 | `grid_astar.py` | `grid-astar` | caminho + `expandidos=` |
| 4 | `rrt.py` | `rrt` | caminho + figura |
| 4 | `rrt_star.py` | `rrt-star` | caminho otimizado + figura |
| 4 | `curvas_parametricas.py` | `curvas-parametricas` | curva de Bézier otimizada |

### Limiares calibrados

Os valores foram medidos com as soluções de referência no harness Python e
ajustados para exigir a modificação do código sem punir pequenas variações de
controlador.

| Atividade | Métrica | Limiar |
|---|---|---|
| `linha-bangbang` | erro máximo de linha (estrela) | 0,55 |
| `linha-proporcional` | erro máximo de linha (meta) | 0,30 |
| `linha-proporcional` | erro máximo de linha (estrela) | 0,26 |
| `holonomico-vxvy` | tempo (meta/estrela) | 25 s / 18 s |
| `diferencial-vomega` | tempo (estrela) | 25 s |
| `chegar-alvo` | tempo (meta/estrela) | 30 s / 22 s |
| `chegar-alvo-orientacao` | erro angular (meta/estrela) | 0,175 / 0,087 rad |
| `apf-lidar` | tempo (meta/estrela) | 45 s / 35 s |
| `grid-bfs` / `grid-astar` | comprimento (estrela) | 22 m |
| `grid-bfs` / `grid-astar` | tempo (estrela) | 30 s |
| `rrt` / `rrt-star` / `curvas` | comprimento (estrela) | 22 m / 22 m / 20 m |

O erro de linha é quantizado pelo motor em 0, 0,25 e 0,5; por isso os limiares
ficam logo acima desses degraus, e não em valores contínuos pequenos.

### Validação comportamental (harness Python)

Soluções de referência (frames reais do simulador):

| Atividade | Resultado |
|---|---|
| `cinematica_holonomica` | alvo (11,83; 7,90), 8,49 s, 11,47 m |
| `cinematica_diferencial` | alvo (13,82; 5,94), 13,05 s, 12,46 m |
| `ir_para_alvo` | alvo (11,84; 8,88), 10,56 s, 12,04 m |
| `ir_para_pose` | alvo (11,92; 7,95), θ ≈ 1,522 rad, 13,95 s |
| `apf_lidar` | alvo (16,82; 6,16), 23,1 s, 17,84 m, 0 colisões |
| `linha_bangbang` | 1 volta em 31,56 s |
| `linha_proporcional` | 1 volta em 30,21–32,19 s |
| `grid_bfs` | (17,11; 9,11), 28,26 s, 18,39 m |
| `grid_astar` | (17,11; 9,11), 28,41 s, 18,29 m, 198 expandidos |
| `rrt` | (16,70; 8,72), 32,25 s, 21,80 m, 1 figura |
| `rrt_star` | (16,70; 8,72), 25,35 s, 20,22 m, 1 figura |
| `curvas_parametricas` | (16,86; 8,86), 22,44 s, 16,98 m, 1 figura |

Templates **sem** a modificação:

| Atividade | Resultado |
|---|---|
| `python_tipos` / `python_numpy` / `python_plot` | `NotImplementedError` |
| `cinematica_holonomica` | robô parado; não chega ao alvo |
| `cinematica_diferencial` | robô parado; não chega ao alvo |
| `ir_para_alvo` / `ir_para_pose` | robô parado; não chega ao alvo |
| `apf_lidar` | para em (6,20; 6,00) com 1 colisão |
| `linha_bangbang` / `linha_proporcional` | 0 voltas; sai da pista em ~4 s |
| `grid_bfs` / `grid_astar` | sem caminho; não chega ao alvo |
| `rrt` / `rrt_star` | sem árvore; não chega ao alvo |
| `curvas_parametricas` | curva `[INICIO, INICIO]`; não chega ao alvo |

### Validação desta fase

- `node --test` (learning, examples, i18n, utils, canvas, tokens): 34/34.
- `npx vite build`: concluído.
- `python -m py_compile` nos 66 templates PT/EN: OK.
- Paridade AST PT/EN dos 15 pares novos: OK.
- Teste headless `learning.e2e.mjs`: 5/5 (4 atividades + persistência/emojis).
  - nível 1: `python-tipos` concluiu e gravou 40 XP + 🐍;
  - nível 2: `holonomico-vxvy` concluiu e gravou 60 XP + 🛞;
  - nível 3: `chegar-alvo-orientacao` concluiu e gravou 80 XP + 🧭;
  - nível 4: `grid-astar` concluiu e gravou 110 XP + ⭐;
  - após recarregar, XP, atividades e emojis continuavam no `localStorage`.

### Falhas conhecidas fora do escopo

Seis testes Python já falhavam antes desta fase, por diferenças de ambiente
(separadores de caminho no Windows, encoding cp1252 e templates antigos):
`test_example_hexagonal_holonomic`, `test_example_multi_line_follower`,
`test_files_reported_and_modules_purged`, `test_script_environment`,
`test_en_templates_have_identical_logic` e
`test_templates_run_in_both_languages`.

`test_en_templates_have_identical_logic` para no `line_follower.py`
pré-existente; os 15 pares novos foram comparados separadamente e têm AST
idêntica. Nenhuma dessas falhas envolve os templates ou o currículo desta fase.


## Fase 4 — Currículo completo e recursos de sala

Status: pendente.

- [ ] Atividades dos níveis 3 e 4 (Kanayama, holonômico, enxame, formação).
- [ ] Atividades abertas com briefing, rubrica e entrega (relatório/figura/captura).
- [ ] Exportar/importar progresso pela interface.
- [ ] Modo professor: código de turma, acompanhamento e exportação da turma.
- [ ] Backend opcional para nota oficial.

## Riscos e cuidados

1. **Progresso local**: pode ser perdido ao limpar o navegador; exportar/importar resolve.
2. **Validação no cliente é contornável**: adequada para uso formativo, não para nota.
3. **Pyodide é lento**: atividades devem ter metas curtas e tempo-limite.
4. **Demo em loop**: a validação precisa ser incremental, não só no `finished`.
5. **i18n**: toda chave nova precisa existir em PT e EN; o teste de paridade cobra isso.
6. **Criatividade**: metas objetivas + rubrica/entrega, não só checagem automática.

## Critérios de aceite da Fase 1 + estrutura da Fase 2

- A galeria mostra filtros de categoria e nível e agrupa os exemplos por categoria.
- Todo exemplo tem `category`, `level` e `order` válidos.
- O modal “Aprender” abre, mostra os quatro níveis, atividades, XP e medalhas.
- Iniciar uma atividade carrega o exemplo correspondente e a marca como ativa.
- Executar o exemplo ativo e cumprir os objetivos grava o progresso e mostra o toast.
- Recarregar a página mantém XP, atividades concluídas e medalhas.
- `npm run test:i18n`, `npm run test:examples` e os testes de `learning/` passam.
- O build de produção (`npx vite build`) continua funcionando.

## Validação da Fase 1 + estrutura da Fase 2

Registro histórico da rodada anterior; a validação da Fase 3 está na seção
“Fase 3 — Status de implementação”.

- `npm run test:i18n`: 6/6.
- `npm run test:examples`: 4/4.
- `node --test tests/learning/learning.test.mjs`: 4/4.
- `npx vite build`: concluído.
- Verificação em navegador headless (Edge), servindo `web/dist` com COOP/COEP:
  - a galeria abriu com 6 grupos de categoria;
  - o filtro “Fundamentos” deixou apenas 3 cards;
  - o filtro “Nível 2” mostrou apenas cards de nível 2;
  - o modal “Aprender” abriu com 4 níveis e 3 atividades;
  - “Iniciar atividade” carregou `inicio_rapido.py`;
  - executar e parar concluiu “Primeiro movimento” (+50 XP, medalha “Primeiro passo”);
  - ao reabrir o modal, o XP e a medalha continuavam gravados no `localStorage`.
- O fluxo e2e `p. categorias e trilha de aprendizagem` foi adicionado para cobrir
  filtros, grupos e abertura do modal na suíte completa.



## Estado atual do repositório

Fases 1, 2 e 3 concluídas e validadas. O trabalho está **sem commit** nesta
rodada.

Arquivos principais desta fase:

- `OQUEFAZER.md` (este plano);
- `web/src/learning/curriculum.js`, `progress.js` e `validate.js`;
- `web/src/components/LearningModal.vue`;
- `web/src/state/store.js` (evidências de execução e conquistas);
- `web/tests/learning/learning.test.mjs`;
- `web/tests/e2e/learning.e2e.mjs`;
- 15 templates PT em `web/templates/` e 15 espelhos EN em `web/templates/en/`;
- novas entradas e categorias em `web/src/examples/catalog.js`.

Pendências conhecidas:

- o progresso ainda é local; exportar/importar pela interface e o modo
  professor ficam para a Fase 4;
- seis testes Python antigos falham por diferenças de ambiente, sem relação com
  os templates ou o currículo desta fase;
- a suíte e2e completa continua instável neste ambiente; o teste focado
  `npm run test:learning` é a validação headless de referência.

Próximos passos:

1. Revisar o diff e commitar a Fase 3.
2. Implementar exportar/importar progresso na interface (Fase 4).
3. Definir o conteúdo do relatório final e o botão de submissão (Fase 4).

### Emojis de medalhas e conquistas

Todas as 19 medalhas e as 2 conquistas agregadas já têm emoji no rótulo i18n
(PT e EN), então o emoji aparece tanto no chip da medalha quanto no toast:

| Chave | Emoji | Chave | Emoji |
|---|---|---|---|
| `primeiro_passo` | 🥇 | `pythonista` | 🐍 |
| `matrizes` | 🔢 | `visualizador` | 📈 |
| `holonomico` | 🛞 | `diferencial` | ⚙️ |
| `alvo` | 🎯 | `bangbang` | ⚡ |
| `proporcional` | 📏 | `piloto_de_linha` | 🏁 |
| `desviador` | 🛡️ | `orientacao` | 🧭 |
| `campo_potencial` | 🧲 | `escape` | 🌀 |
| `bfs` | 🗺️ | `astar` | ⭐ |
| `rrt` | 🌳 | `rrt_star` | ✨ |
| `curvas` | 〰️ | `planejador` | 🧠 |
| `mestre` | 🏆 | | |
