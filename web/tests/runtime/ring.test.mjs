import test from 'node:test'
import assert from 'node:assert/strict'
import { Worker } from 'node:worker_threads'
import { allocRing, RingWriter, RingReader } from '../../src/runtime/ring.js'

test('push/pop roundtrip, empty returns null', () => {
  const b = allocRing(1024)
  const w = new RingWriter(b.ring, b.control)
  const r = new RingReader(b.ring, b.control)
  assert.equal(r.pop(), null)
  assert.ok(w.push('{"cmd":"pause"}'))
  assert.ok(w.push('olá ção ✓'))
  assert.equal(r.pop(), '{"cmd":"pause"}')
  assert.equal(r.pop(), 'olá ção ✓')
  assert.equal(r.pop(), null)
})

test('wraparound with many messages', () => {
  const b = allocRing(64)
  const w = new RingWriter(b.ring, b.control)
  const r = new RingReader(b.ring, b.control)
  for (let i = 0; i < 2000; i++) {
    const s = `m${i}-` + 'x'.repeat(i % 23)
    assert.ok(w.push(s), `push ${i}`)
    if (i % 3 === 0) assert.ok(w.push('é' + i))
    assert.equal(r.pop(), s)
    if (i % 3 === 0) assert.equal(r.pop(), 'é' + i)
  }
})

test('overflow returns false and recovers', () => {
  const b = allocRing(32)
  const w = new RingWriter(b.ring, b.control)
  const r = new RingReader(b.ring, b.control)
  assert.ok(w.push('a'.repeat(20)))
  assert.equal(w.push('b'.repeat(20)), false)
  assert.equal(w.push('c'.repeat(100)), false)
  assert.equal(r.pop(), 'a'.repeat(20))
  assert.ok(w.push('b'.repeat(20)))
  assert.equal(r.pop(), 'b'.repeat(20))
})

test('counters survive 32-bit wrap', () => {
  const b = allocRing(64)
  const hdr = new Int32Array(b.ring, 0, 2)
  const start = (2 ** 31 - 40) | 0
  // capacity 64 divides 2^32, so position stays consistent across the wrap
  const aligned = start - (((start % 64) + 64) % 64)
  hdr[0] = aligned
  hdr[1] = aligned
  const w = new RingWriter(b.ring, b.control)
  const r = new RingReader(b.ring, b.control)
  for (let i = 0; i < 50; i++) {
    assert.ok(w.push('wrap' + i))
    assert.equal(r.pop(), 'wrap' + i)
  }
})

test('waitForCommand times out, then wakes early on push from another thread', async () => {
  const b = allocRing(1024)
  const r = new RingReader(b.ring, b.control)
  assert.equal(r.pop(), null)
  let t = performance.now()
  assert.equal(r.waitForCommand(50), false)
  assert.ok(performance.now() - t >= 40)

  const code = `
    import { workerData } from 'node:worker_threads'
    import { RingWriter } from ${JSON.stringify(new URL('../../src/runtime/ring.js', import.meta.url).href)}
    const w = new RingWriter(workerData.ring, workerData.control)
    setTimeout(() => w.push('wake'), 150)
  `
  const worker = new Worker(code, { eval: true, workerData: { ring: b.ring, control: b.control } })
  t = performance.now()
  const got = r.waitForCommand(5000)
  const dt = performance.now() - t
  assert.equal(got, true)
  assert.ok(dt < 2000, `woke after ${dt}ms`)
  assert.equal(r.pop(), 'wake')
  await worker.terminate()
})
