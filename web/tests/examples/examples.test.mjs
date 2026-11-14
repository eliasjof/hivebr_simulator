// The examples menu and the examples gallery must use the same catalog, and
// every catalog entry must have a PT and an EN source in web/templates.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const WEB = path.resolve(HERE, '..', '..')
const SRC = path.join(WEB, 'src')
const read = (p) => fs.readFileSync(p, 'utf8')
const catalog = read(path.join(SRC, 'examples', 'catalog.js'))

const files = [...catalog.matchAll(/file:\s*'([^']+\.py)'/g)].map((m) => m[1])
const filenames = [...catalog.matchAll(/filename:\s*'([^']+\.py)'/g)].map((m) => m[1])
const extraFiles = [...catalog.matchAll(/files:\s*\[([^\]]*)\]/g)]
  .flatMap((m) => [...m[1].matchAll(/'([^']+\.py)'/g)].map((x) => x[1]))

test('o catálogo usa apenas web/templates (PT) e web/templates/en (EN)', () => {
  assert.doesNotMatch(catalog, /\.\.\/\.\.\/examples\//, 'catalog.js ainda lê de examples/')
  assert.match(catalog, /import\.meta\.glob\([\s\S]*templates\/\*\.py[\s\S]*templates\/en\/\*\.py/)
  assert.ok(files.length >= 7, 'poucos exemplos no catálogo')
  for (const name of files) {
    assert.ok(fs.existsSync(path.join(WEB, 'templates', name)), `falta templates/${name}`)
    assert.ok(fs.existsSync(path.join(WEB, 'templates', 'en', name)), `falta templates/en/${name}`)
  }
  for (const name of extraFiles) {
    assert.ok(fs.existsSync(path.join(WEB, 'templates', name)), `falta templates/${name}`)
    assert.ok(fs.existsSync(path.join(WEB, 'templates', 'en', name)), `falta templates/en/${name}`)
  }
})

test('nomes de arquivo localizados são .py, únicos e existem no catálogo', () => {
  assert.equal(filenames.length, files.length, 'cada exemplo EN precisa de um filename')
  assert.equal(new Set(filenames).size, filenames.length, 'nomes de arquivo em inglês repetidos')
  for (const name of filenames) assert.match(name, /\.py$/)
})

test('menu e galeria de exemplos usam o mesmo catálogo', () => {
  const menu = read(path.join(SRC, 'components', 'MenuBar.vue'))
  const gallery = read(path.join(SRC, 'components', 'ExamplesModal.vue'))
  assert.match(menu, /catalog/)
  assert.match(gallery, /catalog/)
  assert.match(menu, /catalog\.value\.filter/)
  assert.match(gallery, /catalog\.value\.filter/)
  assert.doesNotMatch(menu, /examples\.value.*\.slice\(/, 'o menu não pode truncar a lista de exemplos')
})

test('todo exemplo tem categoria, nível e ordem válidos', () => {
  const ids = [...catalog.matchAll(/\bid:\s*(?:'([^']+)'|[A-Z_]+)/g)].map((m) => m[1] || '(constante)')
  const categories = [...catalog.matchAll(/\bcategory:\s*'([^']+)'/g)].map((m) => m[1])
  const levels = [...catalog.matchAll(/\blevel:\s*(\d+)/g)].map((m) => Number(m[1]))
  const orders = [...catalog.matchAll(/\border:\s*(\d+)/g)].map((m) => Number(m[1]))
  assert.equal(categories.length, ids.length, 'cada exemplo precisa de category')
  assert.equal(levels.length, ids.length, 'cada exemplo precisa de level')
  assert.equal(orders.length, ids.length, 'cada exemplo precisa de order')

  const allowed = new Set(['fundamentos', 'python', 'percepcao', 'linha', 'locomocao', 'controle', 'planejamento', 'multirobo'])
  for (const c of categories) assert.ok(allowed.has(c), `categoria inválida: ${c}`)
  for (const l of levels) assert.ok(l >= 1 && l <= 4, `nível inválido: ${l}`)
  for (const o of orders) assert.ok(o > 0, `ordem inválida: ${o}`)
})
