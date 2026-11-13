// A new script run creates a new Python simulator whose scene version starts
// at 1 again. The renderer must not join the new run's first pose to the
// previous scene's trail.
import test from 'node:test'
import assert from 'node:assert/strict'

globalThis.window = { devicePixelRatio: 1 }
globalThis.requestAnimationFrame = () => 0
globalThis.cancelAnimationFrame = () => {}

const { Renderer } = await import('../../src/canvas/renderer.js')

function fakeCanvas() {
  return {
    width: 0, height: 0,
    getContext: () => ({}),
    getBoundingClientRect: () => ({ width: 640, height: 480 }),
  }
}

function scene(instance, version = 1, robots = 1) {
  return {
    instance, version,
    robots: Array.from({ length: robots }, (_, i) => ({ id: i })),
    world: { width: 20, height: 20 },
    theme: 'dark',
  }
}

function frame(x, y, { running = true } = {}) {
  return { t: 0, running, robots: [{ x, y, theta: 0, path_epoch: 0 }] }
}

function trailPoint(renderer, i = 0) {
  const tr = renderer.trails[i]
  const idx = tr.start * 2
  return [tr.buf[idx], tr.buf[idx + 1]]
}

test('a new simulator with a restarted scene version starts a fresh trail', () => {
  const r = new Renderer(fakeCanvas())

  r.setScene(scene('editor'))
  r.pushFrame(frame(2.5, 2.5))
  assert.equal(r.trails[0].count, 1)
  assert.deepEqual(trailPoint(r), [2.5, 2.5])

  // Running a script replaces the idle editor: same robot count, same version 1.
  r.setScene(scene('run-1'))
  assert.equal(r.trails.length, 0, 'the previous trail must be dropped')
  assert.equal(r.cur.length, 0, 'the previous pose must not be interpolated')

  r.pushFrame(frame(7, 4))
  assert.equal(r.trails[0].count, 1)
  assert.deepEqual(trailPoint(r), [7, 4], 'trail must start at the new pose')
})

test('a worker restart (new instance, version back to 1) also resets the trail', () => {
  const r = new Renderer(fakeCanvas())
  r.setScene(scene('before', 4))
  r.pushFrame(frame(1, 1))
  r.setScene(scene('after'))
  assert.equal(r.trails.length, 0)
  r.pushFrame(frame(9, 9))
  assert.deepEqual(trailPoint(r), [9, 9])
})

test('a collision draws the engine explosion sprite like the desktop', () => {
  const r = new Renderer(fakeCanvas())
  r.camera.scale = 100
  r.sprites.explosion = { complete: true, naturalWidth: 1024 }
  const calls = []
  const ctx = {
    globalAlpha: 1,
    save() {},
    restore() {},
    drawImage: (...args) => calls.push(args),
  }

  r._drawExplosion(ctx, 100, 50, 0.3)

  assert.equal(calls.length, 1)
  // 3 * radius * scale = 90 px, centred on the robot (same as the engine).
  const [, x, y, w, h] = calls[0]
  assert.ok(Math.abs(x - 55) < 1e-9 && Math.abs(y - 5) < 1e-9, calls[0])
  assert.ok(Math.abs(w - 90) < 1e-9 && Math.abs(h - 90) < 1e-9, calls[0])
  assert.ok(Math.abs(ctx.globalAlpha - 180 / 255) < 1e-12)
})

