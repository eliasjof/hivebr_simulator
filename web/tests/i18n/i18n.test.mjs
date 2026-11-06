// Testes de internacionalização: mesmas chaves em pt-BR e en, todas as chaves usadas existem,
// e nenhum texto visível ao usuário fica fixo (em português) fora dos dicionários.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import pt from '../../src/i18n/pt-BR.js'
import en from '../../src/i18n/en.js'

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'src')

function walk(dir, out = []) {
  for (const n of fs.readdirSync(dir)) {
    const p = path.join(dir, n)
    if (fs.statSync(p).isDirectory()) walk(p, out)
    else if (/\.(vue|js)$/.test(n)) out.push(p)
  }
  return out
}
const files = walk(SRC)
const rel = (f) => path.relative(SRC, f)
const slots = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(',')

test('pt-BR e en têm exatamente as mesmas chaves, sem valores vazios e com os mesmos parâmetros', () => {
  const a = Object.keys(pt).sort(), b = Object.keys(en).sort()
  assert.deepEqual(a.filter((k) => !(k in en)), [], 'chaves só em pt-BR')
  assert.deepEqual(b.filter((k) => !(k in pt)), [], 'chaves só em en')
  for (const k of a) {
    assert.ok(String(pt[k]).length > 0 && String(en[k]).length > 0, `valor vazio em ${k}`)
    assert.equal(slots(pt[k]), slots(en[k]), `parâmetros {…} diferentes em ${k}`)
  }
})

// famílias de chaves montadas em tempo de execução
const DYNAMIC = [
  ...['select', 'waypoint', 'obstacle', 'recharge', 'move', 'draw'].map((k) => 'tool.' + k),
  ...['showGrid', 'showPaths', 'showLidar', 'showWaypoints', 'showLabels', 'showLinks'].map((k) => 'layers.' + k),
  ...['init', 'runtime', 'packages', 'files', 'python', 'scipy', 'imports', 'done', 'restart'].map((k) => 'boot.stage.' + k),
  ...['params', 'plots', 'map', 'robots'].map((k) => 'win.' + k),
  'run.run', 'run.running', 'run.stopping', 'run.loading',
  ...['restart_stop', 'restart_unresponsive', 'scipy_failed', 'packages_failed', 'invalid_command', 'unknown_command', 'command_failed',
    'map_load_failed', 'map_loaded', 'line_track_loaded', 'no_track_to_export', 'no_log_data', 'draw_callback_disabled'].map((k) => 'notice.' + k),
  ...['max_speed', 'max_omega', 'max_steer', 'grid_size', 'noise_sigma', 'servo_max_speed', 'goal_tolerance'].map((k) => 'params.' + k),
  'console.lines.one', 'console.lines.other', 'menubar.robot_one', 'menubar.robot_other',
]

test('toda chave usada no código existe (literais e famílias dinâmicas)', () => {
  const used = new Map()
  const add = (k, f) => { if (!used.has(k)) used.set(k, f) }
  for (const f of files) {
    if (/^i18n\/(pt-BR|en|cm-phrases)\.js$/.test(rel(f))) continue
    const src = fs.readFileSync(f, 'utf8')
    for (const m of src.matchAll(/\bt(Or)?\(\s*'([a-zA-Z0-9_.]+)'/g)) { if (!m[2].endsWith('.')) add(m[2], rel(f)) } // prefixos dinâmicos ('tool.' + id) ficam em DYNAMIC
    for (const m of src.matchAll(/\btn\(\s*'([a-zA-Z0-9_.]+)'/g)) { add(m[1] + '.one', rel(f)); add(m[1] + '.other', rel(f)) }
    for (const m of src.matchAll(/\b(?:titleKey|labelKey):\s*'([a-zA-Z0-9_.]+)'/g)) add(m[1], rel(f))
    for (const m of src.matchAll(/\b(?:help|map)\.[a-z_0-9]+'/g)) { /* chaves em tabelas: cobertas abaixo */ }
    // tabelas de chaves ('help.k_run' etc.) escritas como literais 'ns.nome'
    for (const m of src.matchAll(/'((?:help|plots|boot|run|sim)\.[a-z_0-9]+)'/g)) add(m[1], rel(f))
  }
  for (const k of DYNAMIC) add(k, '(dinâmica)')
  const missing = [...used].filter(([k]) => !(k in en) || !(k in pt)).map(([k, f]) => `${k} (${f})`)
  assert.deepEqual(missing, [], 'chaves usadas e ausentes')
})

test('nenhuma chave de dicionário fica órfã', () => {
  const blob = files.filter((f) => !/^i18n\/(pt-BR|en|cm-phrases)\.js$/.test(rel(f))).map((f) => fs.readFileSync(f, 'utf8')).join('\n')
  const dyn = new Set(DYNAMIC)
  const orphan = Object.keys(en).filter((k) => !dyn.has(k) && !blob.includes(`'${k}'`) && !blob.includes(`'${k.replace(/\.(one|other)$/, '')}'`))
  assert.deepEqual(orphan, [], 'chaves nunca usadas')
})

// ---- lint de texto fixo ----
const PT_ACCENT = /[áàâãçéêíóôõúÁÀÂÃÇÉÊÍÓÔÕÚ]/
const PT_WORDS = /\b(Executar|Executando|Parar|Parando|Salvar|Salvo|Abrir|Fechar|Limpar|Novo|Nova|Nenhum|Nenhuma|Erro|Aplicar|Remover|Adicionar|Carregar|Carregando|Mapa|Ajuda|Exemplos?|Cancelar|Voltar|Pausar|Iniciar|Reiniciar|Arquivo|Editar|Exibir|Simulação|Ferramentas?|Gráficos?|Parâmetros|Telemetria|Navegador|Robôs?|Obstáculos?|Recarga|Aguardando|Selecionar|Desenhar|Pista|Camadas|Idioma|Botão|Tela|Código)\b/

function stripComments(src) {
  return src.replace(/<!--[\s\S]*?-->/g, (m) => m.replace(/[^\n]/g, ' ')).replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '))
    .replace(/(^|[^:'"`])\/\/.*$/gm, '$1')
}
function scanRegions(f) {
  const src = fs.readFileSync(f, 'utf8')
  if (!f.endsWith('.vue')) return [['script', src]]
  const out = []
  const tpl = src.match(/<template>([\s\S]*)<\/template>/)
  if (tpl) out.push(['template', tpl[1]])
  for (const m of src.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) out.push(['script', m[1]])
  return out
}

// dados e dicionários, que contêm texto por natureza
const LINT_SKIP = [/^i18n\//, /^examples\/catalog\.js$/]

test('nenhum texto visível em português fica fixo nos componentes e no estado', () => {
  const hits = []
  for (const f of files) {
    if (LINT_SKIP.some((re) => re.test(rel(f)))) continue
    for (const [kind, body] of scanRegions(f)) {
      stripComments(body).split('\n').forEach((line, i) => {
        // ignora o que está dentro de {{ t('…') }} etc.: só procuramos texto literal
        const noKeys = line.replace(/\bt(Or|n)?\(\s*'[^']*'/g, '').replace(/\b(?:titleKey|labelKey):\s*'[^']*'/g, '')
        if (PT_ACCENT.test(noKeys) || PT_WORDS.test(noKeys)) hits.push(`${rel(f)}:${i + 1} [${kind}] ${line.trim().slice(0, 110)}`)
      })
    }
  }
  assert.deepEqual(hits, [], 'texto em português fixo:\n' + hits.join('\n'))
})

test('os modelos em templates/en não têm português e os dois idiomas do catálogo existem', async () => {
  const { getCatalog } = await import('../../src/examples/catalog.js').catch(() => ({ getCatalog: null }))
  // o catálogo usa import.meta.glob (Vite); fora do Vite só conferimos os arquivos
  const tpl = path.resolve(SRC, '..', 'templates')
  const names = fs.readdirSync(tpl).filter((n) => n.endsWith('.py'))
  assert.ok(names.length >= 7)
  for (const n of names) {
    const en = path.join(tpl, 'en', n)
    assert.ok(fs.existsSync(en), `falta templates/en/${n}`)
    assert.ok(!PT_ACCENT.test(fs.readFileSync(en, 'utf8')), `templates/en/${n} contém acentos`)
  }
  void getCatalog
})

test('detecção de idioma: qualquer pt* vira pt-BR e o resto vira en', async () => {
  const globalThisNav = globalThis.navigator
  const store = new Map()
  globalThis.localStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) }
  const { detectLocale } = await import('../../src/i18n/index.js')
  assert.equal(detectLocale(['pt-PT', 'en']), 'pt-BR')
  assert.equal(detectLocale(['pt']), 'pt-BR')
  assert.equal(detectLocale(['en-US']), 'en')
  assert.equal(detectLocale(['fr-FR', 'pt-BR']), 'en')
  assert.equal(detectLocale([]), 'en')
  void globalThisNav
})
