# Solução do professor — célula SCARA (nível 5)

Material de correção, **não publicado na web**. Esta pasta fica fora de
`web/templates`, do catálogo de exemplos e do build do HiveBr Web, então nada
aqui aparece para o aluno.

## Arquivos

| Arquivo | Para que serve |
| --- | --- |
| `scara_esteira_resolvido.py` | Solução completa da atividade `scara-esteira`: tabela DH, matriz homogênea, cinemática direta/inversa, detecção de cor, pega e coloca. |
| `scara_cell_resolvido.urdf` | URDF resolvido da célula (ombro em 0.80 m, braços de 1.60 m e 1.40 m). |

## Como rodar fora do navegador

```bash
cd web/python
python ../../professor/scara/scara_esteira_resolvido.py
```

Saída esperada (resumida):

```text
DH [...]
FK (3.0, 0.0, 0.8)
URDF {'name': 'hivebr_scara', 'links': 5, 'joints': 4, 'l1': 1.6, 'l2': 1.4, 'base_z': 0.8, ...}
Cor detectada: red
...
SCARA OK 4 0
```

O script grava `scara_relatorio.csv` no diretório em que foi executado.

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
- **`scara-urdf`**: `joint_1` em `z = 0.80`, `joint_2` em `x = 1.60`,
  `joint_3` em `x = 1.40`.
- **`scara-esteira`**: use a lei dos cossenos para `q2`, `atan2` para `q1` e
  `d3 = z - BASE_Z`; a cor detectada chega em `alvo["color"]` e em
  `sim.held["color"]`.
