// The SCARA cell uses an isometric projection on the 2D canvas. These checks
// pin down the third dimension: z must move a point up the screen without
// changing its horizontal position.
import test from 'node:test'
import assert from 'node:assert/strict'

const { isometric, makeView } = await import('../../src/canvas/scara.js')

test('isometric projection keeps z as the vertical axis', () => {
  const [x0, y0] = isometric(2, 1, 0)
  const [x1, y1] = isometric(2, 1, 1)
  assert.equal(x0, x1)
  assert.ok(y1 < y0, 'higher z must be higher on the screen')
})

test('makeView fits the cell and keeps the arm above the floor', () => {
  const scene = { scara: { belt: { x0: 2.1, x1: 5.9, width: 0.62 } } }
  const view = makeView(scene, 800, 600)
  assert.ok(view.scale > 0)

  const floor = view.project(3, 0, 0)
  const arm = view.project(3, 0, 1)
  assert.ok(arm[1] < floor[1], 'the arm must be drawn above the floor')
  for (const point of [floor, arm]) {
    assert.ok(Number.isFinite(point[0]) && Number.isFinite(point[1]))
    assert.ok(point[0] > 0 && point[0] < 800)
    assert.ok(point[1] > 0 && point[1] < 600)
  }
})

test('orbit, zoom and pan move the SCARA projection', () => {
  const scene = { scara: { belt: { x0: 2.1, x1: 5.9, width: 0.62 } } }
  const camera = { yaw: 0.2, pitch: 0.6, zoom: 1, panX: 0, panY: 0 }
  const base = makeView(scene, 800, 600, camera)
  const target = base.project(3, 0, 0.8)

  const turned = makeView(scene, 800, 600, { ...camera, yaw: 1.1 })
  const rotated = turned.project(3, 0, 0.8)
  assert.ok(Math.abs(rotated[0] - target[0]) > 1, 'yaw must rotate the cell')

  const tilted = makeView(scene, 800, 600, { ...camera, pitch: 1.2 })
  const raised = tilted.project(3, 0, 0.8)
  assert.ok(Math.abs(raised[1] - target[1]) > 1, 'pitch must tilt the cell')

  const zoomed = makeView(scene, 800, 600, { ...camera, zoom: 2 })
  assert.ok(Math.abs(zoomed.scale - base.scale * 2) < 1e-9, 'zoom must scale the view')

  const panned = makeView(scene, 800, 600, { ...camera, panX: 30, panY: -10 })
  const shifted = panned.project(3, 0, 0.8)
  assert.ok(Math.abs(shifted[0] - target[0] - 30) < 1e-9)
  assert.ok(Math.abs(shifted[1] - target[1] + 10) < 1e-9)
})
