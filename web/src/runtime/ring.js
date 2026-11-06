// Single-producer / single-consumer ring buffer of JSON strings over SharedArrayBuffer.
//
// Ring SAB layout: Int32 header [0]=head (bytes written, monotonic, wraps at 2^32),
// [1]=tail (bytes consumed), then `capacity` bytes of data. Each message is a
// 4-byte little-endian length followed by UTF-8 bytes; both wrap around the end.
// Control SAB: Int32Array, index 0 is a sequence counter bumped (and notified) per push.

const HEADER_BYTES = 8
const DEFAULT_CAPACITY = 1 << 16

/** Allocates the buffers shared between the main thread and the worker. */
export function allocRing(capacity = DEFAULT_CAPACITY) {
  // Power of two, so byte positions stay consistent when the 32-bit counters wrap.
  capacity = 1 << Math.ceil(Math.log2(Math.max(16, capacity)))
  return {
    ring: new SharedArrayBuffer(HEADER_BYTES + capacity),
    control: new SharedArrayBuffer(16),
    interrupt: new SharedArrayBuffer(1),
  }
}

class RingBase {
  constructor(ring, control) {
    this.hdr = new Int32Array(ring, 0, 2)
    this.data = new Uint8Array(ring, HEADER_BYTES)
    this.cap = this.data.length
    this.control = new Int32Array(control)
  }
  _copyIn(pos, src) {
    const first = Math.min(src.length, this.cap - pos)
    this.data.set(first === src.length ? src : src.subarray(0, first), pos)
    if (first < src.length) this.data.set(src.subarray(first), 0)
  }
  _copyOut(pos, n) {
    const out = new Uint8Array(n)
    const first = Math.min(n, this.cap - pos)
    out.set(this.data.subarray(pos, pos + first), 0)
    if (first < n) out.set(this.data.subarray(0, n - first), first)
    return out
  }
}

export class RingWriter extends RingBase {
  static #enc = new TextEncoder()

  /** Returns false when the message does not fit (never blocks). */
  push(str) {
    const body = RingWriter.#enc.encode(str)
    const need = 4 + body.length
    const head = Atomics.load(this.hdr, 0) >>> 0
    const tail = Atomics.load(this.hdr, 1) >>> 0
    const used = (head - tail) >>> 0
    if (need > this.cap - used) return false
    const prefix = new Uint8Array(4)
    new DataView(prefix.buffer).setUint32(0, body.length, true)
    let pos = head % this.cap
    this._copyIn(pos, prefix)
    pos = (pos + 4) % this.cap
    this._copyIn(pos, body)
    Atomics.store(this.hdr, 0, (head + need) | 0)
    Atomics.add(this.control, 0, 1)
    Atomics.notify(this.control, 0)
    return true
  }
}

export class RingReader extends RingBase {
  constructor(ring, control) {
    super(ring, control)
    this.seen = Atomics.load(this.control, 0)
  }

  /** Next message or null if empty. */
  pop() {
    const seq = Atomics.load(this.control, 0)
    const head = Atomics.load(this.hdr, 0) >>> 0
    const tail = Atomics.load(this.hdr, 1) >>> 0
    if (head === tail) {
      this.seen = seq
      return null
    }
    let pos = tail % this.cap
    const prefix = this._copyOut(pos, 4)
    const len = new DataView(prefix.buffer).getUint32(0, true)
    pos = (pos + 4) % this.cap
    const body = this._copyOut(pos, len)
    Atomics.store(this.hdr, 1, (tail + 4 + len) | 0)
    return RingReader.#dec.decode(body)
  }
  static #dec = new TextDecoder()

  hasData() {
    return Atomics.load(this.hdr, 0) !== Atomics.load(this.hdr, 1)
  }

  /** Blocks up to `ms` (worker only); returns true if a command is (probably) available. */
  waitForCommand(ms) {
    if (this.hasData()) return true
    if (ms > 0) Atomics.wait(this.control, 0, this.seen, ms)
    return this.hasData()
  }
}
