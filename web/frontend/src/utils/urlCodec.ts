import * as lzstring from 'lz-string'

export interface ExperimentState {
  config: any
  code: string
}

export function encodeExperimentToURL(state: ExperimentState): void {
  try {
    const json = JSON.stringify(state)
    const compressed = lzstring.compressToEncodedURIComponent(json)
    const url = `${window.location.origin}${window.location.pathname}#${compressed}`
    window.history.replaceState(null, '', url)
  } catch (e) {
    console.warn('Failed to encode URL:', e)
  }
}

export function decodeExperimentFromURL(): ExperimentState | null {
  try {
    const hash = window.location.hash.slice(1)
    if (!hash) return null
    
    const json = lzstring.decompressFromEncodedURIComponent(hash)
    if (!json) return null
    
    return JSON.parse(json)
  } catch (e) {
    console.warn('Failed to decode URL:', e)
    return null
  }
}

export function shareExperiment(state: ExperimentState): string {
  const json = JSON.stringify(state)
  const compressed = lzstring.compressToEncodedURIComponent(json)
  return `${window.location.origin}${window.location.pathname}#${compressed}`
}