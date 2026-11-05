# Robot Sumo Competition System - Complete Guide

Sistema completo de competição de robô sumô estilo **RoboCore** para o simulador HiveBR.

## 📁 Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `sumo_referee.py` | **Sistema principal** - Árbitro, torneio, agentes base, runner |
| `sumo_competition.py` | Versão simples original |
| `sumo_competition_advanced.py` | Versão avançada com renderização customizada |
| `group_strategy_template.py` | Template para equipes criarem suas estratégias |
| `config/sumo_competition.yaml` | Configuração YAML da arena |
| `run_sumo.py` | Runner de linha de comando |
| `run_gui_match.py` | Exemplo de partida GUI |
| `test_referee_headless.py` | Testes unitários do árbitro |
| `SUMO_COMPETITION_GUIDE.md` | Este guia |

---

## 🚀 Início Rápido

### 1. Partida Demonstrativa (GUI)
```bash
python run_gui_match.py
```
Executa uma partida entre `AggressiveStrategy` vs `DefensiveStrategy` com árbitro e interface visual.

### 2. Criar Sua Estratégia
```bash
cp group_strategy_template.py minha_equipe.py
# Edite minha_equipe.py
```

### 3. Testar Sua Estratégia
```bash
python run_sumo.py minha_equipe.py
```

### 4. Torneio Completo
```bash
python run_sumo.py --tournament equipe1.py equipe2.py --matches 5
```

---

## 🏗️ Arquitetura do Sistema

### SumoReferee (Árbitro)
Responsabilidades:
- ✅ Detecta quando robôs saem do dohyo (círculo)
- ✅ Determina vencedor pelas regras RoboCore
- ✅ Gerencia tempo de partida
- ✅ Rastreia estatísticas (empurrões, tempo no ringue)

**Regras de Vitória:**
1. **Push-out**: Um robô empurra o outro para fora → vencedor imediato
2. **Ambos saem simultaneamente**: Quem saiu **por último** vence
3. **Tempo esgotado (30s)**: Robô que passou **mais tempo dentro** vence
4. **Empate**: Tempo igual dentro do ringue

### CompetitionAgent (Classe Base)
Métodos helper disponíveis para estratégias:

```python
# Verificação de posição
self.is_in_ring(x, y, margin=0.0)           # True se dentro do círculo
self.distance_to_center(state)               # Distância ao centro
self.distance_to_edge(state)                 # Distância à borda (+ = dentro)
self.get_ring_quadrant(state)                # Quadrante: NE, NW, SW, SE

# Oponente
self.get_opponent(neighbors)                 # RobotState ou None
self.distance_to_opponent(state, neighbors)  # Distância ao oponente
self.angle_to_opponent(state, neighbors)     # Ângulo relativo (-pi a pi)
self.predict_opponent(lookahead=0.5)         # Posição prevista

# Navegação
self.angle_to_target(state, tx, ty)          # Ângulo para alvo
self.angle_to_center(state)                  # Ângulo para centro
```

### Maquina de Estados Padrão
```python
SEARCH    # Procurando oponente (gira)
APPROACH  # Oponente longe - aproximar
ATTACK    # Oponente perto - atacar
DEFEND    # Voltar para centro
RETREAT   # Perto da borda - fugir
```

---

## 📝 Template de Estratégia (group_strategy_template.py)

```python
from sumo_referee import CompetitionAgent, Command, RobotState
from typing import Dict
import math

class MinhaEquipeAgent(CompetitionAgent):
    def __init__(self, robot_id=None, config=None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Minha Equipe"
        
        # PARÂMETROS AJUSTÁVEIS:
        self.attack_distance = 0.5     # Distância para iniciar ataque
        self.defend_distance = 0.8     # Distância para aproximar
        self.edge_margin = 0.15        # Margem de segurança da borda
        self.attack_speed = 3.0        # Velocidade máxima de ataque
        self.approach_speed = 1.5      # Velocidade de aproximação
        self.search_omega = 2.0        # Velocidade de busca (rad/s)
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        # 1. SEMPRE verificar se saiu do ringue
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        # 2. Atualizar rastreamento do oponente
        self.update_opponent_tracking(neighbors, 0.03)
        
        # 3. Obter info do oponente
        opp = self.get_opponent(neighbors)
        has_opp = opp is not None
        
        if has_opp:
            dist = self.distance_to_opponent(state, neighbors)
            angle = self.angle_to_opponent(state, neighbors)
        else:
            dist = float('inf')
            angle = 0.0
        
        dist_center = self.distance_to_center(state)
        edge_dist = self.distance_to_edge(state)
        
        # 4. SUA LÓGICA AQUI
        # Exemplo simples:
        if edge_dist < self.edge_margin:
            # Perto da borda - fugir para centro
            return self.retreat_behavior(state)
        
        if has_opp:
            if dist < self.attack_distance:
                return self.attack_behavior(state, dist, angle)
            elif dist < self.defend_distance:
                return self.approach_behavior(state, dist, angle)
        
        # Sem oponente ou longe - buscar ou defender centro
        if dist_center > 0.3:
            return self.defend_behavior(state)
        return self.search_behavior(state)
```

---

## ⚙️ Configuração da Arena (config/sumo_competition.yaml)

```yaml
sumo:
  ring_radius: 0.77       # Raio do dohyo (1.54m diâmetro)
  robot_radius: 0.10      # Raio do robô (20cm diâmetro)
  border_width: 0.05      # Largura da linha branca (shikiri-sen)
  start_distance: 0.45    # Distância inicial do centro
  match_duration: 30.0    # Duração da partida (segundos)

robot:
  max_speed: 3.0          # Velocidade linear máxima (m/s)
  max_omega: 6.0          # Velocidade angular máxima (rad/s)
```

### Personalizar para Sua Competição
```python
from sumo_referee import TournamentConfig, run_match

config = TournamentConfig(
    match_duration=60.0,      # 1 minuto
    ring_radius=0.77,
    robot_radius=0.10,
    border_width=0.05,
    start_distance=0.50,
    max_speed=2.5,            # Robôs mais lentos
    max_omega=5.0
)

run_match(MinhaEquipeAgent, OutraEquipeAgent, config=config)
```

---

## 🎮 Controles da Interface (GUI)

| Tecla | Ação |
|-------|------|
| `ESPAÇO` | Pausar/Retomar |
| `R` | Reiniciar partida |
| `1` / `2` | Selecionar robô 1/2 |
| `ESC` | Sair |

### Overlay de Competição
- **Topo**: Status da partida, tempo restante, nomes das equipes
- **Rodapé**: Posição de cada robô, distância ao centro, distância à borda, status DENTRO/FORA

---

## 🏆 Executando Torneios

```python
from sumo_referee import TournamentManager, TeamInfo
from minha_equipe import MinhaEquipeAgent
from outra_equipe import OutraEquipeAgent
from terceira_equipe import TerceiraEquipeAgent

# Criar torneio
tourney = TournamentManager()

# Adicionar equipes
tourney.add_team(TeamInfo("eq1", "Equipe Alpha", MinhaEquipeAgent, (30, 144, 255)))
tourney.add_team(TeamInfo("eq2", "Equipe Beta", OutraEquipeAgent, (220, 20, 60)))
tourney.add_team(TeamInfo("eq3", "Equipe Gamma", TerceiraEquipeAgent, (50, 205, 50)))

# Gerar confrontos (todos contra todos)
pairings = tourney.generate_pairings()
# [("eq1", "eq2"), ("eq1", "eq3"), ("eq2", "eq3")]

# Rodar cada partida
for team1_id, team2_id in pairings:
    # ... rodar partida com run_match ...
    # tourney.record_match(result)

# Ver classificação
standings = tourney.get_standings()
for i, team in enumerate(standings):
    print(f"{i+1}. {team['name']}: {team['points']} pts ({team['wins']}V-{team['draws']}E-{team['losses']}D)")

# Exportar resultados
tourney.export_results("torneio_resultados.json")
```

---

## 📊 Estratégias de Exemplo Inclusas

| Estratégia | Descrição | Estilo |
|------------|-----------|--------|
| `AggressiveStrategy` | Sempre carrega no oponente | Ofensivo puro |
| `DefensiveStrategy` | Fica no centro, contra-ataca | Defensivo |
| `SensorStrategy` | Lógica baseada em sensores simulados | Equilibrado |

### Usar como Base
```python
from sumo_referee import AggressiveStrategy

class MinhaVersaoMelhorada(AggressiveStrategy):
    def __init__(self, robot_id=None, config=None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Minha Versão"
        # Sobrescrever parâmetros
        self.attack_speed = 3.0
        self.search_omega = 1.5  # Busca mais lenta
    
    def loop(self, state, neighbors):
        # Sua lógica customizada ou super().loop()
        return super().loop(state, neighbors)
```

---

## 🔧 Dicas para Estratégias Vencedoras

1. **Priorize a borda**: Sempre verifique `distance_to_edge()` primeiro
2. **Preveja o oponente**: Use `predict_opponent(0.3)` para antecipar
3. **Controle de velocidade**: Velocidade máxima nem sempre é melhor
4. **Centro = vantagem**: Quem controla o centro tem mais espaço para manobrar
5. **Máquina de estados clara**: SEARCH → APPROACH → ATTACK / RETREAT
6. **Teste contra estilos diferentes**: Agressivo, Defensivo, Aleatório

---

## 🐛 Solução de Problemas

### Robôs não se movem
- Verifique se `loop()` retorna `Command(v, omega)`
- Confira se `v` e `omega` estão dentro dos limites (`max_speed`, `max_omega`)

### Robôs giram sem parar
- Posições iniciais devem ser opostas no eixo Y, se enfrentando
- Verifique `set_opponent()` foi chamado

### "Module not found"
```bash
pip install -e .  # Instala o pacote hivebr em modo desenvolvimento
```

### Partida não termina
- Verifique se `referee.update()` está sendo chamado a cada step
- Confira `match_duration` no config

---

## 📚 Referência Rápida - Command

```python
Command(v=1.5, omega=0.5)    # Frente 1.5 m/s, virar esquerda 0.5 rad/s
Command(v=0.0, omega=2.0)    # Girar no lugar (esquerda)
Command(v=-1.0, omega=0.0)   # Ré
Command(v=0.0, omega=0.0)    # Parado
```

Limites: `v ∈ [-3.0, 3.0]`, `omega ∈ [-6.0, 6.0]` (configurável)

---

## 📄 Licença

Parte do projeto HiveBR Simulator. Uso educacional e de pesquisa.

---

**Desenvolvido para competições de robótica estilo RoboCore** 🤖🏆