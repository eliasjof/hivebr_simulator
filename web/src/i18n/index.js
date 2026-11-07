// Internacionalização mínima (sem dependências): locale reativo, t(key, params), detecção e persistência.
import { ref, computed, watch } from 'vue'
import ptBR from './pt-BR.js'
import en from './en.js'

export const LOCALES = ['pt-BR', 'en']
export const STORAGE_KEY = 'hivebr.web.locale.v1' // 'auto' | 'pt-BR' | 'en'
const DICTS = { 'pt-BR': ptBR, en }

function readChoice() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'pt-BR' || v === 'en' ? v : 'auto'
  } catch { return 'auto' }
}

/** Qualquer variante de português vira pt-BR; todo o resto vira en. */
export function detectLocale(languages = (typeof navigator !== 'undefined' ? navigator.languages || [navigator.language] : [])) {
  for (const l of languages || []) {
    if (!l) continue
    return /^pt/i.test(l) ? 'pt-BR' : 'en'
  }
  return 'en'
}

/** Escolha do usuário: 'auto' segue o navegador. */
export const choice = ref(readChoice())
export const locale = ref(choice.value === 'auto' ? detectLocale() : choice.value)

export function setChoice(c) {
  choice.value = c === 'pt-BR' || c === 'en' ? c : 'auto'
  try {
    if (choice.value === 'auto') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, choice.value)
  } catch { /* cota cheia / modo privado */ }
  locale.value = choice.value === 'auto' ? detectLocale() : choice.value
}

const warned = new Set()
const isDev = typeof import.meta !== 'undefined' && !!import.meta.env?.DEV

function lookup(key) {
  const cur = DICTS[locale.value]?.[key]
  if (cur !== undefined) return cur
  const fb = en[key]
  if (fb !== undefined) {
    if (isDev && !warned.has(key)) { warned.add(key); console.warn(`[i18n] chave ausente em ${locale.value}: ${key}`) }
    return fb
  }
  if (isDev && !warned.has(key)) { warned.add(key); console.warn(`[i18n] chave desconhecida: ${key}`) }
  return key
}

/** Traduz `key`, substituindo `{nome}` pelos parâmetros. Lê `locale`, então é reativo em templates. */
export function t(key, params) {
  const s = lookup(key)
  return params ? s.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m)) : s
}

/** Plural simples: usa `key.one` quando n === 1 e `key.other` nos demais casos. */
export function tn(key, n, params) {
  return t(`${key}.${n === 1 ? 'one' : 'other'}`, { n: fmtInt(n), ...params })
}

/** Tradução opcional: devolve `fallback` se a chave não existir (para códigos vindos do Python). */
export function tOr(key, params, fallback) {
  if (DICTS[locale.value]?.[key] === undefined && en[key] === undefined) return fallback
  return t(key, params)
}

const nfCache = new Map()
/** Formata números no idioma atual (separador decimal). Exportações continuam em formato de máquina. */
export function fmtNum(v, digits = 2) {
  if (v == null || !Number.isFinite(Number(v))) return '—'
  const k = `${locale.value}|${digits}`
  let nf = nfCache.get(k)
  if (!nf) nfCache.set(k, (nf = new Intl.NumberFormat(locale.value, { minimumFractionDigits: digits, maximumFractionDigits: digits })))
  return nf.format(Number(v))
}
/** Até `digits` casas, sem zeros à direita (rótulos de eixo e tooltips). */
export function fmtMax(v, digits = 2) {
  if (v == null || !Number.isFinite(Number(v))) return '—'
  const k = `${locale.value}|max${digits}`
  let nf = nfCache.get(k)
  if (!nf) nfCache.set(k, (nf = new Intl.NumberFormat(locale.value, { minimumFractionDigits: 0, maximumFractionDigits: digits })))
  return nf.format(Number(v))
}
export function fmtInt(v) { return fmtNum(v, 0) }

export const localeLabel = computed(() => locale.value)

/** Mantém <html lang> e document.title em dia. */
export function syncDocument() {
  document.documentElement.lang = locale.value
  document.title = t('app.title')
}
watch(locale, () => { if (typeof document !== 'undefined') syncDocument() }, { immediate: typeof document !== 'undefined' })
