// Protected progress bundles.
//
// A bundle is a JSON envelope. Without a password the payload is stored in
// clear text; with a password the payload is encrypted with AES-GCM-256 and the
// key is derived from the password with PBKDF2-SHA256.
//
// The password protects the exported file, not localStorage: anyone with
// DevTools can edit the local progress. Official grading still needs a backend
// or a teacher-signed file.

export const BUNDLE_FORMAT = 'hivebr-progress'
export const BUNDLE_VERSION = 2
export const KDF_ITERATIONS = 250000

export function bytesToB64(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value)
  let text = ''
  const chunk = 0x8000
  for (let i = 0; i < bytes.length; i += chunk) {
    text += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk))
  }
  return btoa(text)
}

export function b64ToBytes(text) {
  const binary = atob(String(text || ''))
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  return bytes
}

function webCrypto() {
  const value = globalThis.crypto
  if (!value || !value.subtle || typeof value.getRandomValues !== 'function') {
    throw new Error('crypto-unavailable')
  }
  return value
}

/** True when the browser can encrypt bundles (secure context). */
export function cryptoAvailable() {
  try {
    webCrypto()
    return true
  } catch {
    return false
  }
}

async function deriveKey(password, salt, iterations) {
  const subtle = webCrypto().subtle
  const base = await subtle.importKey(
    'raw',
    new TextEncoder().encode(String(password)),
    'PBKDF2',
    false,
    ['deriveKey'],
  )
  return subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations, hash: 'SHA-256' },
    base,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

/** Encrypts a JSON-serializable payload and returns the envelope object. */
export async function encryptPayload(payload, password, iterations = KDF_ITERATIONS) {
  const cryptoApi = webCrypto()
  const salt = cryptoApi.getRandomValues(new Uint8Array(16))
  const iv = cryptoApi.getRandomValues(new Uint8Array(12))
  const key = await deriveKey(password, salt, iterations)
  const data = new TextEncoder().encode(JSON.stringify(payload))
  const cipher = await cryptoApi.subtle.encrypt({ name: 'AES-GCM', iv }, key, data)
  return {
    format: BUNDLE_FORMAT,
    v: BUNDLE_VERSION,
    encrypted: true,
    crypto: {
      alg: 'AES-GCM',
      kdf: 'PBKDF2-SHA256',
      iterations,
      salt: bytesToB64(salt),
      iv: bytesToB64(iv),
    },
    payload: bytesToB64(new Uint8Array(cipher)),
  }
}

/** Decrypts an encrypted envelope. Throws on a wrong password or corrupt data. */
export async function decryptPayload(envelope, password) {
  const meta = envelope?.crypto || {}
  if (!meta.salt || !meta.iv || !envelope?.payload) throw new Error('invalid-bundle')
  const iterations = Number(meta.iterations) || KDF_ITERATIONS
  const salt = b64ToBytes(meta.salt)
  const iv = b64ToBytes(meta.iv)
  const key = await deriveKey(password, salt, iterations)
  try {
    const plain = await webCrypto().subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      b64ToBytes(envelope.payload),
    )
    return JSON.parse(new TextDecoder().decode(plain))
  } catch {
    throw new Error('wrong-password')
  }
}

/** Serializes a payload into a v2 bundle (encrypted only when password is set). */
export async function encodeBundle(payload, password = '') {
  const envelope = password
    ? await encryptPayload(payload, password)
    : { format: BUNDLE_FORMAT, v: BUNDLE_VERSION, encrypted: false, payload }
  return JSON.stringify(envelope, null, 2)
}

/** Reads a bundle header without decrypting it. */
export function inspectBundle(text) {
  try {
    const data = JSON.parse(text)
    if (!data || typeof data !== 'object' || Array.isArray(data)) return null
    if (data.format === BUNDLE_FORMAT) {
      return {
        bundle: true,
        encrypted: data.encrypted === true,
        version: Number(data.v) || 0,
        payload: data.encrypted === true ? null : data.payload,
      }
    }
    // v1: the progress object itself, at the top level.
    return { bundle: false, encrypted: false, version: 1, payload: data }
  } catch {
    return null
  }
}

/** Decodes a v1 or v2 bundle. Throws when the password is wrong or the file is invalid. */
export async function decodeBundle(text, password = '') {
  const info = inspectBundle(text)
  if (!info) throw new Error('invalid-bundle')
  if (!info.bundle) return info.payload
  if (info.encrypted) {
    if (!password) throw new Error('password-required')
    const data = JSON.parse(text)
    return decryptPayload(data, password)
  }
  return info.payload
}
