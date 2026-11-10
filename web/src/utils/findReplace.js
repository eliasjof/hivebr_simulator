// Find and replace helpers shared by the YAML config editor.
// All offsets are plain string indices into the original text.

export function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** Start offsets of every occurrence of `needle` in `text`. */
export function findMatches(text, needle, matchCase = false) {
  const pat = String(needle || '')
  if (!pat) return []
  const hay = matchCase ? text : text.toLowerCase()
  const what = matchCase ? pat : pat.toLowerCase()
  const out = []
  let i = hay.indexOf(what)
  while (i !== -1) {
    out.push(i)
    i = hay.indexOf(what, i + what.length)
  }
  return out
}

/**
 * Pick the match to jump to. Going forward starts at `end`; going back
 * starts before `start`. Both wrap around.
 */
export function nextMatchIndex(matches, { start = 0, end = start, dir = 1 } = {}) {
  if (!matches.length) return -1
  if (dir > 0) {
    const pos = matches.find((s) => s >= end)
    return pos === undefined ? matches[0] : pos
  }
  const before = matches.filter((s) => s < start)
  return before.length ? before[before.length - 1] : matches[matches.length - 1]
}

/** Replace every occurrence and report how many were replaced. */
export function replaceAllMatches(text, needle, replacement, matchCase = false) {
  const list = findMatches(text, needle, matchCase)
  if (!list.length) return { text, count: 0 }
  const re = new RegExp(escapeRegExp(needle), matchCase ? 'g' : 'gi')
  return { text: text.replace(re, () => replacement), count: list.length }
}
