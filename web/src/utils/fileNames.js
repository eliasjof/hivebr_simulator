// File-name helpers shared by the editor store and the Python worker.
// Helper files keep their extension; only names without one default to `.py`.

/** Lower-case extension of a file name, including the dot ('' when absent). */
export function fileExtension(name) {
  const m = /\.([A-Za-z0-9]+)\s*$/.exec(String(name ?? '').trim())
  return m ? `.${m[1].toLowerCase()}` : ''
}

export function isPythonFile(name) {
  return fileExtension(name) === '.py'
}

/** Basename with its own extension kept; append `.py` only when it has none. */
export function normalizeFileName(name) {
  const base = String(name ?? '').trim().split(/[\\/]/).pop()
  if (!base) return 'user_script.py'
  return fileExtension(base) ? base : `${base}.py`
}

/**
 * Name safe to write inside the worker filesystem. Removes any directory part,
 * replaces unsupported characters, and defaults to `.py` when no extension is
 * present (sibling Python modules stay importable).
 */
export function safeFileName(name) {
  const base = String(name || 'user_script.py').split(/[\\/]/).pop().trim()
  const cleaned = base.replace(/[^\w.\- ]/g, '_') || 'user_script.py'
  return /\.[A-Za-z0-9]+$/.test(cleaned) ? cleaned : `${cleaned}.py`
}
