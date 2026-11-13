// Ajustes visuais aplicados sobre o SVG que o matplotlib gera em plt.show().
// São mantidos no objeto da figura para sobreviver ao fechar/reabrir a janela.

export const GRID_DASHES = {
  solid: '',
  dashed: '5 3',
  dotted: '1 3',
  dashdot: '6 3 1 3',
  longdash: '10 4',
}

export function defaultFigureStyle() {
  return {
    colors: {},        // cor original (minúscula) -> cor nova
    lineWidth: '',     // vazio = manter a espessura do matplotlib
    textColor: '',     // vazio = manter
    spineColor: '',
    spineWidth: '',
    figureBg: '',
    axesBg: '',
    grid: {
      show: false,
      axis: 'both',    // both | x | y
      color: '#b0b0b0',
      width: 0.8,
      alpha: 1,
      dash: 'solid',
    },
    gridTouched: false,
  }
}

/** Garante que uma figura carregada tenha todas as opções de estilo. */
export function ensureFigureStyle(figure) {
  const base = defaultFigureStyle()
  if (!figure.style || typeof figure.style !== 'object') figure.style = base
  const style = figure.style
  for (const [key, value] of Object.entries(base)) {
    if (key === 'grid') {
      if (!style.grid || typeof style.grid !== 'object') style.grid = { ...value }
      for (const [gk, gv] of Object.entries(value)) {
        if (style.grid[gk] === undefined) style.grid[gk] = gv
      }
    } else if (style[key] === undefined) {
      style[key] = value
    }
  }
  if (!style.colors || typeof style.colors !== 'object') style.colors = {}
  return style
}
