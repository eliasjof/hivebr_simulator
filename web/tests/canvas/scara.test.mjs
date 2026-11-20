// The SCARA cell uses an isometric projection on the 2D canvas. These checks
// pin down the third dimension: z must move a point up the screen without
// changing its horizontal position.
import test from 'node:test'
import assert from 'node:assert/strict'

const { isometric, makeView, scaraJointFrames } = await import('../../src/canvas/scara.js')

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

test('DH joint frames follow the SCARA chain and expose the joint centres', () => {
  const model = {
    base: 'base_link',
    chain: [
      { name: 'joint_1', type: 'revolute', motion: 'q1', axis: [0, 0, 1], origin: { xyz: [0, 0, 1.1] }, child: 'link_1' },
      { name: 'joint_2', type: 'revolute', motion: 'q2', axis: [0, 0, 1], origin: { xyz: [1.6, 0, 0] }, child: 'link_2' },
      { name: 'joint_3', type: 'prismatic', motion: 'd3', axis: [0, 0, 1], origin: { xyz: [1.4, 0, 0] }, child: 'link_3' },
      { name: 'joint_4', type: 'fixed', origin: { xyz: [0, 0, 0] }, child: 'tool_link' },
    ],
    links: {
      base_link: { visuals: [] },
      link_1: { visuals: [{ origin: { xyz: [0, 0, 0] }, geometry: { type: 'cylinder', radius: 0.24, length: 0.22 } }] },
      link_2: { visuals: [{ origin: { xyz: [0, 0, 0] }, geometry: { type: 'cylinder', radius: 0.20, length: 0.20 } }] },
      link_3: { visuals: [] },
      tool_link: { visuals: [] },
    },
  }
  const frames = scaraJointFrames({ scara: { model } }, { arm: { q1: 0, q2: 0, d3: -0.4 } })
  assert.equal(frames.length, 3)
  const near = (a, b) => Math.abs(a - b) < 1e-9
  assert.ok(frames[0].origin.every((v, i) => near(v, [0, 0, 1.1][i])), 'frame 1 sits on the shoulder')
  assert.ok(frames[1].origin.every((v, i) => near(v, [1.6, 0, 1.1][i])), 'frame 2 sits on the elbow')
  assert.ok(frames[2].origin.every((v, i) => near(v, [3.0, 0, 0.7][i])), 'frame 3 sits on the tool point')
  assert.ok(frames[2].center.every((v, i) => near(v, [3.0, 0, 1.1][i])), 'prismatic centre stays at the wrist')
  assert.ok(frames[0].housing.radius > 0.24, 'shoulder housing wraps the link cylinder')
  assert.equal(frames[2].housing, null, 'the prismatic joint has no revolute housing')
})

test('the DH layer can be disabled and still draws the smoothed joints', async () => {
  const { drawScaraScene } = await import('../../src/canvas/scara.js')
  const { t } = await import('../../src/i18n/index.js')
  const legend = t('scara.frames')
  const texts = []
  let ellipses = 0
  const ctx = new Proxy({}, {
    get(_target, prop) {
      if (prop === 'fillText') return (text) => texts.push(String(text))
      if (prop === 'measureText') return () => ({ width: 20 })
      if (prop === 'ellipse') return () => { ellipses += 1 }
      return () => {}
    },
    set() { return true },
  })
  const colors = { red: [220, 64, 56], green: [58, 176, 92], blue: [58, 118, 216] }
  const scene = {
    kind: 'scara',
    scara: {
      belt: { x0: 2.1, x1: 5.9, y: 0, z: 0.55, width: 0.62 },
      base_z: 1.1, l1: 1.6, l2: 1.4, part_height: 0.15,
      baskets: [], colors, model: null,
    },
  }
  const frame = {
    t: 1,
    scara: { placed: 0, rejected: 0, conveyor: { on: false, speed: 0 }, arm: { q1: 0, q2: 0, d3: 0 }, objects: [], event: '' },
  }
  drawScaraScene(ctx, scene, frame, 'dark', 800, 600, undefined, { showFrames: true })
  assert.ok(ellipses > 0, 'joint housings use smooth ellipse caps')
  assert.ok(texts.includes('J1') && texts.includes('J2') && texts.includes('J3'), 'joint centres are labelled')
  assert.ok(texts.includes('{0}'), 'the fixed base frame is labelled')
  assert.ok(texts.includes(legend), 'the DH legend is shown')

  texts.length = 0
  drawScaraScene(ctx, scene, frame, 'dark', 800, 600, undefined, { showFrames: false })
  assert.ok(!texts.includes('J1'), 'disabling the layer hides the frame labels')
  assert.ok(!texts.includes('{0}'), 'disabling the layer hides the base frame')
  assert.ok(!texts.includes(legend), 'disabling the layer hides the legend')
})

test('the three baskets carry their number on the camera-facing wall', async () => {
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
  const colors = { red: [220, 64, 56], green: [58, 176, 92], blue: [58, 118, 216] }
  const baskets = [
    { id: 'red', color: 'red', x: 0.55, y: 2.1, count: 0 },
    { id: 'green', color: 'green', x: 1.85, y: 1.85, count: 0 },
    { id: 'blue', color: 'blue', x: 2.2, y: -1.15, count: 0 },
  ]
  const scene = {
    kind: 'scara',
    scara: {
      belt: { x0: 2.1, x1: 5.9, y: 0, z: 0.55, width: 0.62 },
      base_z: 1.1, l1: 1.6, l2: 1.4, part_height: 0.15,
      baskets, colors, model: null,
    },
  }
  const frame = {
    t: 1,
    scara: {
      placed: 0, rejected: 0, conveyor: { on: false, speed: 0 },
      arm: { q1: 0, q2: 0, d3: 0 }, tip: { x: 0, y: 0, z: 0.7 },
      objects: [], baskets, event: '',
    },
  }
  drawScaraScene(ctx, scene, frame, 'dark', 800, 600)

  for (const id of ['1', '2', '3']) {
    assert.ok(texts.includes(id), `basket number ${id} is painted on the wall: ${texts.join(' | ')}`)
  }
})
