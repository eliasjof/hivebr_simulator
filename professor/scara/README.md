# Solução do professor — célula SCARA (nível 5)

Material de correção, **não publicado na web**. Esta pasta fica fora de
`web/templates`, do catálogo de exemplos e do build do HiveBr Web, então nada
aqui aparece para o aluno.

## Arquivos

| Arquivo | Para que serve |
| --- | --- |
| `scara_esteira_resolvido.py` | Solução completa da atividade `scara-esteira`: tabela DH, matriz homogênea, cinemática direta/inversa, detecção de cor, pega e coloca. |
| `scara_cell_resolvido.urdf` | URDF resolvido da célula (ombro em 1.10 m, braços de 1.60 m e 1.40 m). É idêntico byte a byte ao modelo empacotado. |

## Como rodar fora do navegador

O script importa `hivebr_web`, então a raiz de `web/python` precisa estar no
`PYTHONPATH`:

```bash
cd web/python
PYTHONPATH=. python ../../professor/scara/scara_esteira_resolvido.py
```

Saída esperada (resumida):

```text
DH [...]
FK (3.0, 0.0, 1.1)
URDF {'name': 'hivebr_scara', 'links': 5, 'joints': 4, 'l1': 1.6, 'l2': 1.4, 'base_z': 1.1, ...}
Cor detectada: red
...
SCARA OK 4 0
```

O script grava `scara_relatorio.csv` no diretório em que foi executado.

## Geometria e movimento da garra

- O ombro fica em `z = 1.10`, acima da esteira (`0.55`), então o braço **precisa**
  descer para tocar a peça.
- O ponto de ferramenta é a **face inferior do eletroímã** (`link_3` em `z = 0`
  local, mesmo ponto do `tool_link`). Em `alvo["z"]` a altura é o **topo** da
  peça, não a correia; o desenho coloca o corpo abaixo desse ponto.
- A junta prismática `d3` move a haste telescópica: em repouso a garra fica em
  `TRANSIT_Z = 1.00`; na peça o topo está em `0.70` (`d3 = -0.40`); na cesta a
  altura é `BASKET_Z = 0.28` (`d3 = -0.82`, dentro do limite `-1.00`).
- O laço é encenado: viaja em `TRANSIT_Z`, desce até o topo da peça, pega, sobe,
  viaja até a cesta, desce até `BASKET_Z` e solta. Assim o eletroímã aparece
  descendo e subindo em cada ciclo, em vez de arrastar a peça na altura do
  ombro.

## Como usar no HiveBr Web (correção)

1. Abra a atividade **Célula SCARA 3D com esteira**.
2. Na aba `scara_cell.urdf`, substitua o conteúdo pelo arquivo
   `scara_cell_resolvido.urdf`.
3. Na aba `scara_esteira.py`, substitua as funções `tabela_dh`,
   `matriz_transformacao` e `cinematica_inversa` pelas versões do arquivo
   `scara_esteira_resolvido.py` (mantendo o restante do template).
4. Execute. O HUD deve mostrar `Colocados: 4`, a esteira ligada e as peças
   vermelhas, verdes e azuis nas cestas correspondentes.

## Respostas das etapas

- **`scara-dh`**
  ```python
  return [
      {"theta": "q1", "d": BASE_Z, "a": 0.0, "alpha": 0.0},
      {"theta": "q2", "d": 0.0, "a": L1, "alpha": 0.0},
      {"theta": 0.0, "d": "d3", "a": L2, "alpha": 0.0},
  ]
  ```
- **`scara-matrizes`**
  ```python
  ct, st = math.cos(theta), math.sin(theta)
  ca, sa = math.cos(alpha), math.sin(alpha)
  return [
      [ct, -st * ca, st * sa, a * ct],
      [st, ct * ca, -ct * sa, a * st],
      [0.0, sa, ca, d],
      [0.0, 0.0, 0.0, 1.0],
  ]
  ```
- **`scara-urdf`**: `joint_1` em `z = 1.10`, `joint_2` em `x = 1.60`,
  `joint_3` em `x = 1.40`.
- **`scara-esteira`**: use a lei dos cossenos para `q2`, `atan2` para `q1` e
  `d3 = z - BASE_Z`; a cor detectada chega em `alvo["color"]` e em
  `sim.held["color"]`. Suba para `TRANSIT_Z` entre alvos e desça até `alvo["z"]`
  (topo da peça) ou `BASKET_Z` antes de pegar/soltar.

## Validação desta versão

- `python web/python/tests/run_all.py test_scara`: **10/10**.
- `node --test "tests/**/*.test.mjs"` (em `web/`): **59/59**, incluindo o
  desenho do eletroímã, da peça presa e das pilhas nas cestas.
- `node tests/e2e/learning.e2e.mjs` (em `web/`): **18/18**, com `scara-esteira`
  concluindo no navegador e o progresso sobrevivendo ao recarregamento.
- Paridade AST PT/EN dos quatro pares SCARA: idêntica.
- `scara_esteira_resolvido.py` no terminal: `FK (3.0, 0.0, 1.1)` e
  `SCARA OK 4 0`.
- `web/public/hivebr-py.zip`: 193 arquivos, sem nenhuma entrada `professor` ou
  `resolvido`.
