/**
 * Translation service for user-generated content (scripts, reports, captures).
 * Uses MyMemory Translation API (free, no key required, rate limited).
 * Fallback: returns original text if translation fails.
 */

const MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
const CACHE_KEY = 'hivebr.web.translation_cache.v1'

/** In-memory cache to avoid repeated translations in the same session. */
const memoryCache = new Map()

/** Load persistent cache from localStorage. */
function loadCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (raw) {
      const obj = JSON.parse(raw)
      for (const [key, value] of Object.entries(obj)) {
        memoryCache.set(key, value)
      }
    }
  } catch { /* ignore */ }
}

/** Save cache to localStorage (debounced). */
let saveTimer = null
function scheduleSave() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    try {
      const obj = Object.fromEntries(memoryCache)
      localStorage.setItem(CACHE_KEY, JSON.stringify(obj))
    } catch { /* quota exceeded */ }
  }, 1000)
}

/** Build cache key: sourceLang|targetLang|text */
function cacheKey(text, sourceLang, targetLang) {
  return `${sourceLang}|${targetLang}|${text}`
}

/**
 * Translate text from sourceLang to targetLang.
 * @param {string} text - Text to translate
 * @param {string} sourceLang - Source language code ('pt-BR' or 'en')
 * @param {string} targetLang - Target language code ('pt-BR' or 'en')
 * @returns {Promise<string>} Translated text (or original on failure)
 */
export async function translateText(text, sourceLang, targetLang) {
  if (!text || !text.trim()) return text
  if (sourceLang === targetLang) return text

  // Normalize language codes
  const src = sourceLang === 'pt-BR' ? 'pt' : 'en'
  const tgt = targetLang === 'pt-BR' ? 'pt' : 'en'

  const key = cacheKey(text, src, tgt)

  // Check memory cache first
  if (memoryCache.has(key)) return memoryCache.get(key)

  // Check persistent cache (load on first use)
  if (memoryCache.size === 0) loadCache()
  if (memoryCache.has(key)) return memoryCache.get(key)

  try {
    const params = new URLSearchParams({
      q: text,
      langpair: `${src}|${tgt}`,
      // MyMemory optional: mt=1 for machine translation only
      mt: '1',
      // No API key needed for basic usage
    })

    const response = await fetch(`${MYMEMORY_URL}?${params}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data = await response.json()
    const translated = data?.responseData?.translatedText

    if (translated && typeof translated === 'string' && translated !== text) {
      memoryCache.set(key, translated)
      scheduleSave()
      return translated
    }
  } catch (e) {
    console.warn('[translate] MyMemory failed:', e.message)
  }

  // Fallback: return original text
  return text
}

/**
 * Translate multiple texts in parallel (with concurrency limit).
 * @param {string[]} texts - Array of texts to translate
 * @param {string} sourceLang - Source language
 * @param {string} targetLang - Target language
 * @param {number} concurrency - Max parallel requests (default 3)
 * @returns {Promise<string[]>} Array of translated texts
 */
export async function translateBatch(texts, sourceLang, targetLang, concurrency = 3) {
  const results = new Array(texts.length)
  const queue = texts.map((text, i) => ({ text, i }))

  async function worker() {
    while (queue.length) {
      const { text, i } = queue.shift()
      results[i] = await translateText(text, sourceLang, targetLang)
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, texts.length) }, worker))
  return results
}

/**
 * Detect if text is likely Portuguese (simple heuristic).
 * @param {string} text
 * @returns {boolean}
 */
export function looksLikePortuguese(text) {
  // Unicode ranges for Portuguese diacritics: áàâãçéêíóôõú + uppercase
  return /[\u00E1\u00E0\u00E2\u00E3\u00E7\u00E9\u00EA\u00ED\u00F3\u00F4\u00F5\u00FA\u00C1\u00C0\u00C2\u00C3\u00C7\u00C9\u00CA\u00CD\u00D3\u00D4\u00D5\u00DA]/.test(text)
}

/**
 * Clear translation cache.
 */
export function clearTranslationCache() {
  memoryCache.clear()
  try { localStorage.removeItem(CACHE_KEY) } catch { /* ignore */ }
}

/** Initialize cache on load. */
loadCache()