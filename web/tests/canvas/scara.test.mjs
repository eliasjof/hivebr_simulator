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

test('the HUD reads the counters and pose from the SCARA frame', async () => {
  const { drawScaraScene } = await import('../../src/canvas/scara.js')
  const texts = []
  const ctx = new Proxy({}, {
    get(_target, prop) {
      if (prop === 'fillText') return (text) => texts.push(String(text))
      if (prop === 'measureText') return () => ({ width: 20 })
      return () => {}
    },
    set() { return true },
  })
  const scene = {
    kind: 'scara',
    scara: {
      belt: { x0: 2.1, x1: 5.9, y: 0, z: 0.55, width: 0.62 },
      base_z: 1.1,
      part_height: 0.15,
      baskets: [],
      colors: { red: [220, 64, 56], green: [58, 176, 92], blue: [58, 118, 216] },
      model: null,
    },
  }
  const frame = {
    t: 1,
    scara: {
      placed: 4,
      rejected: 0,
      conveyor: { on: true, speed: 0.55 },
      arm: { q1: 0.5, q2: 1.5, d3: -0.5 },
      tip: { x: 2.4, y: 0.1, z: 0.7 },
      event: '',
    },
  }
  drawScaraScene(ctx, scene, frame, 'dark', 800, 600)

  assert.ok(texts.some((s) => s.endsWith(': 4')), `placed counter missing: ${texts.join(' | ')}`)
  assert.ok(texts.some((s) => s.includes('0.55')), 'conveyor speed missing from the HUD')
  assert.ok(texts.some((s) => s.includes('q1=0.50')), 'joint pose missing from the HUD')
})

test('the SCARA scene draws the magnet, the held part and the basket piles', async () => {
  const { drawScaraScene } = await import('../../src/canvas/scara.js')
  const texts = []
  const ctx = new Proxy({}, {
    get(_target, prop) {
      if (prop === 'fillText') return (text) => texts.push(String(text))
      if (prop === 'measureText') return () => ({ width: 20 })
      return () => {}
    },
    set() { return true },
  })
  const model = {
    base: 'base_link',
    chain: [{
      name: 'joint_3',
      type: 'prismatic',
      motion: 'd3',
      axis: [0, 0, 1],
      origin: { xyz: [0, 0, 0] },
      child: 'link_3',
    }],
    links: {
      base_link: { visuals: [] },
      link_3: {
        visuals: [{
          origin: { xyz: [0, 0, 0] },
          geometry: { type: 'cylinder', radius: 0.075, length: 0.04 },
          material: { color: [0.24, 0.55, 0.95, 1] },
        }],
      },
    },
  }
  const colors = { red: [220, 64, 56], green: [58, 176, 92], blue: [58, 118, 216] }
  const basket = { id: 'red', color: 'red', x: 0.55, y: 2.1, count: 2 }
  const scene = {
    kind: 'scara',
    scara: {
      belt: { x0: 2.1, x1: 5.9, y: 0, z: 0.55, width: 0.62 },
      base_z: 1.1,
      part_height: 0.15,
      baskets: [basket],
      colors,
      model,
    },
  }
  const frame = {
    t: 2,
    scara: {
      placed: 2,
      rejected: 0,
      conveyor: { on: true, speed: 0.55 },
      arm: { q1: 0.2, q2: 0.9, d3: -0.5 },
      tip: { x: 2.6, y: 0, z: 0.7 },
      objects: [{ id: 1, color: 'blue', x: 4.0, y: 0, z: 0.7 }],
      held: { id: 2, color: 'green', x: 2.6, y: 0, z: 0.7 },
      baskets: [basket],
      event: '',
    },
  }
  assert.doesNotThrow(() => drawScaraScene(ctx, scene, frame, 'dark', 800, 600))
  assert.ok(texts.some((s) => s.endsWith(': 2')), `basket/placed counter missing: ${texts.join(' | ')}`)
})
