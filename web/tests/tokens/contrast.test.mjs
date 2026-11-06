// Contraste dos tokens de cor (WCAG): texto >= 4.5:1 nos dois temas, a partir de src/styles.css.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const css = fs.readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'src', 'styles.css'), 'utf8')

function block(selectorRe) {
  const m = css.match(selectorRe)
  assert.ok(m, 'bloco não encontrado: ' + selectorRe)
  const start = css.indexOf('{', m.index)
  let depth = 0, i = start
  for (; i < css.length; i++) { if (css[i] === '{') depth++; else if (css[i] === '}' && --depth === 0) break }
  return css.slice(start + 1, i)
}
const vars = (b) => Object.fromEntries([...b.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim().replace(/\s*\/\*.*$/, '')]))
const light = { ...vars(block(/:root \{/)), ...vars(block(/:root, :root\[data-theme="light"\] \{/)) }
const dark = { ...light, ...vars(block(/:root\[data-theme="dark"\] \{/)) }

const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }
function parse(c) {
  const h = c.match(/^#([0-9a-f]{6})$/i)
  if (h) return [0, 2, 4].map((i) => parseInt(h[1].slice(i, i + 2), 16))
  throw new Error('cor sólida esperada: ' + c)
}
function lum(c) { const [r, g, b] = parse(c); return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) }
function ratio(a, b) { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05) }

// [primeiro plano, fundo]
const PAIRS = [
  ['--on-solid', '--ok'], ['--on-solid', '--danger'], ['--accent-ink', '--accent'],
  ['--text', '--surface'], ['--text', '--surface-2'], ['--text-muted', '--surface'], ['--text-muted', '--surface-2'],
  ['--accent', '--surface'], ['--ok', '--surface'], ['--warn', '--surface'], ['--danger', '--surface'],
  ['--topbar-text', '--topbar'], ['--topbar-muted', '--topbar'], ['--tooltip-text', '--topbar'],
]
for (const [name, theme] of [['claro', light], ['escuro', dark]]) {
  test(`contraste >= 4.5:1 no tema ${name}`, () => {
    const low = []
    for (const [fg, bg] of PAIRS) {
      const r = ratio(theme[fg], theme[bg])
      if (r < 4.5) low.push(`${fg} sobre ${bg}: ${r.toFixed(2)}`)
    }
    assert.deepEqual(low, [])
  })
}
test('relatório', () => {
  for (const [name, theme] of [['claro', light], ['escuro', dark]]) {
    console.log(name, PAIRS.map(([f, b]) => `${f}/${b}=${ratio(theme[f], theme[b]).toFixed(2)}`).join(' '))
  }
})
