// Isometric renderer for the SCARA cell.
//
// The mobile engine is a top-down 2D world, so this scene is drawn by its own
// module. The projection is an orthographic isometric one, which gives a real
// third dimension (x, y and z) on the same 2D canvas used by the rest of the
// simulator.

import { t } from '../i18n/index.js'

const TAU = Math.PI * 2
const PAD = 44

/** Default orbit camera for the SCARA cell (yaw around Z, pitch above XY). */
export const DEFAULT_SCARA_CAMERA = {
  yaw: Math.PI / 4,
  pitch: 0.62,
  zoom: 1,
  panX: 0,
  panY: 0,
}

function cameraState(camera) {
  return { ...DEFAULT_SCARA_CAMERA, ...(camera || {}) }
}

/** World point (x, y, z) to the screen plane, before fitting. */
export function projectPoint(x, y, z, camera) {
  const c = cameraState(camera)
  const cy = Math.cos(c.yaw)
  const sy = Math.sin(c.yaw)
  const cp = Math.cos(c.pitch)
  const sp = Math.sin(c.pitch)
  const xr = x * cy - y * sy
  const yr = x * sy + y * cy
  return [xr, yr * sp - z * cp]
}

/** Backwards-compatible default isometric projection. */
export function isometric(x, y, z) {
  return projectPoint(x, y, z)
}

function css(rgb, alpha = 1) {
  const c = rgb || [200, 200, 200]
  return alpha >= 1
    ? `rgb(${c[0]}, ${c[1]}, ${c[2]})`
    : `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${alpha})`
}

function mix(a, b, k) {
  return [
    Math.round(a[0] + (b[0] - a[0]) * k),
    Math.round(a[1] + (b[1] - a[1]) * k),
    Math.round(a[2] + (b[2] - a[2]) * k),
  ]
}

function shade(rgb, k) {
  return k >= 0 ? mix(rgb, [255, 255, 255], k) : mix(rgb, [0, 0, 0], -k)
}

/**
 * Builds the projection for a canvas. Exported so unit tests can check that
 * the vertical axis really moves the point up the screen.
 *
 * The camera orbits around the cell centre: ``yaw`` turns the whole cell,
 * ``pitch`` tilts it towards the viewer, ``zoom`` scales the fitted view and
 * ``panX``/``panY`` slide it in screen pixels.
 */
export function makeView(scene, width, height, camera) {
  const cam = cameraState(camera)
  const belt = scene?.scara?.belt || { x0: 2.1, x1: 5.9 }
  const corners = [
    [-0.7, -2.5, 0], [belt.x1 + 0.5, -2.5, 0],
    [belt.x1 + 0.5, 3.1, 0], [-0.7, 3.1, 0],
    [-0.7, -2.5, 2.3], [belt.x1 + 0.5, 3.1, 2.3],
    [-0.7, 3.1, 2.3], [belt.x1 + 0.5, -2.5, 2.3],
  ]
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const [x, y, z] of corners) {
    const [px, py] = projectPoint(x, y, z, cam)
    minX = Math.min(minX, px); maxX = Math.max(maxX, px)
    minY = Math.min(minY, py); maxY = Math.max(maxY, py)
  }
  const fit = Math.min(
    (width - PAD * 2) / Math.max(0.1, maxX - minX),
    (height - PAD * 2) / Math.max(0.1, maxY - minY),
  )
  const scale = Math.max(0.05, fit * (cam.zoom || 1))
  const ox = width / 2 - ((minX + maxX) / 2) * scale + cam.panX
  const oy = height / 2 - ((minY + maxY) / 2) * scale + cam.panY
  const depth = (x, y, z) => {
    const cy = Math.cos(cam.yaw)
    const sy = Math.sin(cam.yaw)
    const cp = Math.cos(cam.pitch)
    const sp = Math.sin(cam.pitch)
    // Camera sits at yaw/pitch looking at the origin: larger = closer.
    return (x * sy + y * cy) * cp + z * sp
  }
  return {
    scale,
    width,
    height,
    camera: cam,
    project(x, y, z) {
      const [px, py] = projectPoint(x, y, z, cam)
      return [ox + px * scale, oy + py * scale]
    },
    depth,
    /** Screen-space distance (px) for a world length at a given depth. */
    px: (metres) => metres * scale,
  }
}

function palette(theme) {
  const dark = theme !== 'light'
  return dark
    ? {
      floor: '#0e1826', grid: 'rgba(120, 150, 190, 0.16)', ink: '#e9f0fa',
      muted: '#9fb0c7', panel: 'rgba(10, 18, 30, 0.78)', belt: '#243448',
      beltTop: '#31465f', metal: '#9fb3cc', metalDark: '#53657c',
      shadow: 'rgba(0, 0, 0, 0.35)',
    }
    : {
      floor: '#eef2f6', grid: 'rgba(30, 60, 90, 0.12)', ink: '#17212e',
      muted: '#5d6d80', panel: 'rgba(255, 255, 255, 0.82)', belt: '#b9c6d4',
      beltTop: '#d4dee8', metal: '#5d728a', metalDark: '#33465b',
      shadow: 'rgba(30, 45, 60, 0.22)',
    }
}

function poly(ctx, points, fill, stroke = null, width = 1) {
  if (!points.length) return
  ctx.beginPath()
  ctx.moveTo(points[0][0], points[0][1])
  for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i][0], points[i][1])
  ctx.closePath()
  if (fill) { ctx.fillStyle = fill; ctx.fill() }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke() }
}

function box(ctx, view, x0, x1, y0, y1, z0, z1, topColor, sideColor, stroke) {
  const p = view.project
  const top = [p(x0, y0, z1), p(x1, y0, z1), p(x1, y1, z1), p(x0, y1, z1)]
  const front = [p(x0, y1, z1), p(x1, y1, z1), p(x1, y1, z0), p(x0, y1, z0)]
  const right = [p(x1, y1, z1), p(x1, y0, z1), p(x1, y0, z0), p(x1, y1, z0)]
  poly(ctx, front, sideColor, stroke, 1)
  poly(ctx, right, shade(sideColor, -0.08), stroke, 1)
  poly(ctx, top, topColor, stroke, 1)
}

function drawFloor(ctx, view, pal, scene) {
  const belt = scene.scara.belt
  const x0 = -1.2
  const x1 = belt.x1 + 1.0
  const y0 = -3.0
  const y1 = 3.6
  ctx.save()
  const corners = [
    view.project(x0, y0, 0), view.project(x1, y0, 0),
    view.project(x1, y1, 0), view.project(x0, y1, 0),
  ]
  poly(ctx, corners, pal.floor)

  ctx.strokeStyle = pal.grid
  ctx.lineWidth = 1
  for (let x = -1; x <= Math.ceil(belt.x1) + 1; x += 1) {
    const a = view.project(x, y0, 0)
    const b = view.project(x, y1, 0)
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke()
  }
  for (let y = -3; y <= 3; y += 1) {
    const a = view.project(x0, y, 0)
    const b = view.project(x1, y, 0)
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke()
  }
  ctx.restore()
}

function drawConveyor(ctx, view, pal, scene, frame) {
  const belt = scene.scara.belt
  const half = belt.width / 2
  const x0 = belt.x0 - 0.25
  const x1 = belt.x1 + 0.25
  const z = belt.z
  box(ctx, view, x0, x1, belt.y - half, belt.y + half, z - 0.18, z, pal.beltTop, pal.belt, pal.metalDark)

  // Moving stripes show the belt direction and speed.
  const speed = frame?.conveyor?.speed || 0
  const phase = ((frame?.t || 0) * Math.max(0.15, speed)) % 0.6
  ctx.save()
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.20)'
  ctx.lineWidth = 2
  for (let x = x0 + phase; x < x1; x += 0.6) {
    const a = view.project(x, belt.y - half + 0.06, z + 0.002)
    const b = view.project(x, belt.y + half - 0.06, z + 0.002)
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke()
  }
  ctx.restore()

  // Rollers at both ends.
  for (const x of [x0, x1]) {
    const c = view.project(x, belt.y, z - 0.09)
    ctx.beginPath()
    ctx.ellipse(c[0], c[1], 0.10 * view.scale, 0.05 * view.scale, 0, 0, TAU)
    ctx.fillStyle = pal.metalDark
    ctx.fill()
    ctx.strokeStyle = pal.metal
    ctx.lineWidth = 1.5
    ctx.stroke()
  }

  // Legs.
  for (const x of [x0 + 0.3, x1 - 0.3]) {
    for (const y of [belt.y - half + 0.1, belt.y + half - 0.1]) {
      const a = view.project(x, y, z - 0.18)
      const b = view.project(x, y, 0)
      ctx.beginPath()
      ctx.moveTo(a[0], a[1])
      ctx.lineTo(b[0], b[1])
      ctx.strokeStyle = pal.metalDark
      ctx.lineWidth = 3
      ctx.stroke()
    }
  }
}

function drawBasket(ctx, view, pal, scene, basket) {
  const color = scene.scara.colors[basket.color] || [180, 180, 180]
  const size = 0.42
  const height = 0.34
  const x0 = basket.x - size
  const x1 = basket.x + size
  const y0 = basket.y - size
  const y1 = basket.y + size
  box(ctx, view, x0, x1, y0, y1, 0, height, shade(color, 0.15), shade(color, -0.18), shade(color, -0.42))
  // Open top: darker inner face and a coloured rim.
  const inner = [
    view.project(x0 + 0.08, y0 + 0.08, height + 0.002),
    view.project(x1 - 0.08, y0 + 0.08, height + 0.002),
    view.project(x1 - 0.08, y1 - 0.08, height + 0.002),
    view.project(x0 + 0.08, y1 - 0.08, height + 0.002),
  ]
  poly(ctx, inner, shade(color, -0.55))
  const label = view.project(basket.x, basket.y, height + 0.16)
  ctx.save()
  ctx.font = '600 12px system-ui, -apple-system, "Segoe UI", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = pal.ink
  ctx.fillText(String(basket.count ?? 0), label[0], label[1])
  ctx.restore()
}

function drawPart(ctx, view, pal, scene, part, lift = 0) {
  if (!part) return
  const color = scene.scara.colors[part.color] || [200, 200, 200]
  const x = Number(part.x)
  const y = Number(part.y)
  const z = Number(part.z) + lift
  const r = 0.115 * view.scale
  const ry = Math.max(3, r * 0.55)
  const top = view.project(x, y, z + 0.08)
  const bottom = view.project(x, y, z - 0.08)
  const shadow = view.project(x, y, 0.01)

  ctx.save()
  ctx.beginPath()
  ctx.ellipse(shadow[0], shadow[1], r * 1.25, ry * 1.25, 0, 0, TAU)
  ctx.fillStyle = pal.shadow
  ctx.fill()

  ctx.beginPath()
  ctx.rect(top[0] - r, top[1], r * 2, Math.max(2, bottom[1] - top[1]))
  ctx.fillStyle = shade(color, -0.12)
  ctx.fill()

  ctx.beginPath()
  ctx.ellipse(bottom[0], bottom[1], r, ry, 0, 0, TAU)
  ctx.fillStyle = shade(color, -0.28)
  ctx.fill()

  ctx.beginPath()
  ctx.ellipse(top[0], top[1], r, ry, 0, 0, TAU)
  ctx.fillStyle = shade(color, 0.16)
  ctx.fill()
  ctx.strokeStyle = shade(color, -0.35)
  ctx.lineWidth = 1
  ctx.stroke()

  ctx.beginPath()
  ctx.ellipse(top[0] - r * 0.25, top[1] - ry * 0.18, r * 0.35, ry * 0.35, 0, 0, TAU)
  ctx.fillStyle = 'rgba(255, 255, 255, 0.35)'
  ctx.fill()
  ctx.restore()
}

// ---------------------------------------------------------- matrices ----
// 4x4 homogeneous matrices, row-major, matching hivebr_web.urdf.
function mIdentity() {
  return [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
  ]
}

function mMul(a, b) {
  const out = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
  for (let i = 0; i < 4; i += 1) {
    for (let j = 0; j < 4; j += 1) {
      let sum = 0
      for (let k = 0; k < 4; k += 1) sum += a[i][k] * b[k][j]
      out[i][j] = sum
    }
  }
  return out
}

function mTranslate(x, y, z) {
  const m = mIdentity()
  m[0][3] = Number(x) || 0
  m[1][3] = Number(y) || 0
  m[2][3] = Number(z) || 0
  return m
}

function mRx(a) {
  const c = Math.cos(a)
  const s = Math.sin(a)
  return [[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]]
}

function mRy(a) {
  const c = Math.cos(a)
  const s = Math.sin(a)
  return [[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]]
}

function mRz(a) {
  const c = Math.cos(a)
  const s = Math.sin(a)
  return [[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
}

function mRpy(rpy) {
  const [r, p, y] = rpy || [0, 0, 0]
  return mMul(mMul(mRz(y), mRy(p)), mRx(r))
}

function mAxisAngle(axis, angle) {
  const [ax0, ay0, az0] = axis || [0, 0, 1]
  const norm = Math.hypot(ax0, ay0, az0)
  if (!(norm > 1e-12)) return mIdentity()
  const ax = ax0 / norm
  const ay = ay0 / norm
  const az = az0 / norm
  const c = Math.cos(angle)
  const s = Math.sin(angle)
  const k = 1 - c
  return [
    [c + ax * ax * k, ax * ay * k - az * s, ax * az * k + ay * s, 0],
    [ay * ax * k + az * s, c + ay * ay * k, ay * az * k - ax * s, 0],
    [az * ax * k - ay * s, az * ay * k + ax * s, c + az * az * k, 0],
    [0, 0, 0, 1],
  ]
}

function mPoint(m, p) {
  const [x, y, z] = p
  return [
    m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
    m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
    m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
  ]
}

function originMatrix(origin) {
  const xyz = origin?.xyz || [0, 0, 0]
  return mMul(mTranslate(xyz[0], xyz[1], xyz[2]), mRpy(origin?.rpy))
}

function jointValue(joint, values) {
  const motion = joint.motion
  if (motion && values[motion] !== undefined) return Number(values[motion]) || 0
  if (values[joint.name] !== undefined) return Number(values[joint.name]) || 0
  return 0
}

function jointMatrix(joint, value) {
  const base = originMatrix(joint.origin)
  let motion = mIdentity()
  if (joint.type === 'revolute' || joint.type === 'continuous') {
    motion = mAxisAngle(joint.axis, value)
  } else if (joint.type === 'prismatic') {
    const [ax, ay, az] = joint.axis || [0, 0, 1]
    const norm = Math.hypot(ax, ay, az) || 1
    motion = mTranslate((ax / norm) * value, (ay / norm) * value, (az / norm) * value)
  }
  return mMul(base, motion)
}

function chainTransforms(model, values) {
  const transforms = {}
  const base = model?.base || 'base_link'
  transforms[base] = mIdentity()
  let current = mIdentity()
  for (const joint of model?.chain || []) {
    current = mMul(current, jointMatrix(joint, jointValue(joint, values || {})))
    transforms[joint.child] = current
  }
  return transforms
}

// ---------------------------------------------------------- geometry ----
function materialColor(material, pal) {
  const rgba = material?.color
  if (!Array.isArray(rgba) || rgba.length < 3) return hexToRgb(pal.metal)
  return [
    Math.round(Math.max(0, Math.min(1, rgba[0])) * 255),
    Math.round(Math.max(0, Math.min(1, rgba[1])) * 255),
    Math.round(Math.max(0, Math.min(1, rgba[2])) * 255),
  ]
}

function hexToRgb(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ''))
  if (!m) return [160, 170, 185]
  const n = parseInt(m[1], 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function faceNormal(a, b, c) {
  const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
  const v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]
  const n = [
    u[1] * v[2] - u[2] * v[1],
    u[2] * v[0] - u[0] * v[2],
    u[0] * v[1] - u[1] * v[0],
  ]
  const len = Math.hypot(n[0], n[1], n[2])
  return len > 1e-9 ? [n[0] / len, n[1] / len, n[2] / len] : [0, 0, 1]
}

const LIGHT = (() => {
  const v = [-0.38, -0.55, 0.74]
  const len = Math.hypot(...v)
  return v.map((n) => n / len)
})()

function addFace(faces, view, worldPoints, color) {
  const pts = worldPoints.map((p) => view.project(p[0], p[1], p[2]))
  let depth = 0
  for (const p of worldPoints) depth += view.depth(p[0], p[1], p[2])
  depth /= Math.max(1, worldPoints.length)
  const normal = faceNormal(worldPoints[0], worldPoints[1], worldPoints[2])
  const lit = Math.abs(normal[0] * LIGHT[0] + normal[1] * LIGHT[1] + normal[2] * LIGHT[2])
  const k = 0.32 + 0.68 * lit
  faces.push({ pts, depth, fill: mix(shade(color, -0.45), shade(color, 0.22), k) })
}

function addBox(faces, view, world, size, color) {
  const [sx, sy, sz] = size || [0.1, 0.1, 0.1]
  const hx = sx / 2
  const hy = sy / 2
  const hz = sz / 2
  const local = [
    [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
    [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz],
  ]
  const p = local.map((v) => mPoint(world, v))
  const quads = [
    [0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
    [2, 3, 7, 6], [0, 4, 7, 3], [1, 2, 6, 5],
  ]
  for (const q of quads) addFace(faces, view, q.map((i) => p[i]), color)
}

function addCylinder(faces, view, world, radius, length, color, sides = 18) {
  const r = Math.max(0.001, radius)
  const h = Math.max(0.001, length)
  const top = []
  const bottom = []
  for (let i = 0; i < sides; i += 1) {
    const a = (i / sides) * TAU
    const x = Math.cos(a) * r
    const y = Math.sin(a) * r
    top.push(mPoint(world, [x, y, h / 2]))
    bottom.push(mPoint(world, [x, y, -h / 2]))
  }
  addFace(faces, view, top, color)
  addFace(faces, view, bottom.slice().reverse(), color)
  for (let i = 0; i < sides; i += 1) {
    const j = (i + 1) % sides
    addFace(faces, view, [top[i], top[j], bottom[j], bottom[i]], color)
  }
}

function addSphere(faces, view, world, radius, color) {
  const r = Math.max(0.001, radius)
  const local = [
    [r, 0, 0], [-r, 0, 0], [0, r, 0], [0, -r, 0], [0, 0, r], [0, 0, -r],
  ]
  const p = local.map((v) => mPoint(world, v))
  const tris = [
    [0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
    [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5],
  ]
  for (const tri of tris) addFace(faces, view, tri.map((i) => p[i]), color)
}

function collectModelFaces(faces, view, pal, model, values) {
  const transforms = chainTransforms(model, values)
  for (const [name, linkMatrix] of Object.entries(transforms)) {
    const link = model.links?.[name]
    if (!link) continue
    for (const visual of link.visuals || []) {
      const world = mMul(linkMatrix, originMatrix(visual.origin))
      const color = materialColor(visual.material, pal)
      const g = visual.geometry || {}
      if (g.type === 'box') addBox(faces, view, world, g.size, color)
      else if (g.type === 'cylinder') addCylinder(faces, view, world, g.radius, g.length, color)
      else if (g.type === 'sphere') addSphere(faces, view, world, g.radius, color)
      else if (g.type === 'mesh') addBox(faces, view, world, [0.12, 0.12, 0.12], color)
    }
  }
}

function drawFaces(ctx, faces, pal) {
  faces.sort((a, b) => a.depth - b.depth)
  ctx.save()
  ctx.lineJoin = 'round'
  ctx.lineWidth = 0.8
  for (const f of faces) {
    if (!f.pts.length) continue
    ctx.beginPath()
    ctx.moveTo(f.pts[0][0], f.pts[0][1])
    for (let i = 1; i < f.pts.length; i += 1) ctx.lineTo(f.pts[i][0], f.pts[i][1])
    ctx.closePath()
    ctx.fillStyle = css(f.fill)
    ctx.fill()
    ctx.strokeStyle = pal.shadow
    ctx.stroke()
  }
  ctx.restore()
}

function drawModelArm(ctx, view, pal, scene, frame) {
  const model = scene.scara?.model
  if (!model || !model.chain || !model.chain.length) return false
  const arm = frame?.arm || {}
  const values = {}
  for (const joint of model.chain) {
    if (joint.motion) values[joint.motion] = Number(arm[joint.motion]) || 0
  }
  const faces = []
  collectModelFaces(faces, view, pal, model, values)
  drawFaces(ctx, faces, pal)
  return true
}

function drawArm(ctx, view, pal, scene, frame) {
  const s = scene.scara
  const arm = frame?.arm || { q1: 0, q2: 0, d3: 0 }
  const tip = frame?.tip || { x: 0, y: 0, z: s.base_z }
  const q1 = Number(arm.q1) || 0
  const elbowX = s.l1 * Math.cos(q1)
  const elbowY = s.l1 * Math.sin(q1)

  const base = view.project(0, 0, 0)
  const shoulder = view.project(0, 0, s.base_z)
  const elbow = view.project(elbowX, elbowY, s.base_z)
  const wrist = view.project(tip.x, tip.y, s.base_z)
  const quill = view.project(tip.x, tip.y, tip.z)

  // Base cylinder.
  const baseTop = view.project(0, 0, s.base_z * 0.42)
  const baseR = 0.34 * view.scale
  ctx.save()
  ctx.beginPath()
  ctx.ellipse(base[0], base[1], baseR, baseR * 0.55, 0, 0, TAU)
  ctx.fillStyle = pal.metalDark
  ctx.fill()
  ctx.beginPath()
  ctx.rect(base[0] - baseR, baseTop[1], baseR * 2, base[1] - baseTop[1])
  ctx.fillStyle = shade(pal.metalDark, -0.12)
  ctx.fill()
  ctx.beginPath()
  ctx.ellipse(baseTop[0], baseTop[1], baseR, baseR * 0.55, 0, 0, TAU)
  ctx.fillStyle = pal.metal
  ctx.fill()
  ctx.strokeStyle = pal.metalDark
  ctx.lineWidth = 1.5
  ctx.stroke()
  ctx.restore()

  // Links.
  ctx.save()
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  const link = (a, b, width, color) => {
    ctx.beginPath()
    ctx.moveTo(a[0], a[1])
    ctx.lineTo(b[0], b[1])
    ctx.strokeStyle = pal.metalDark
    ctx.lineWidth = width + 3
    ctx.stroke()
    ctx.strokeStyle = color
    ctx.lineWidth = width
    ctx.stroke()
  }
  link(shoulder, elbow, 13, pal.metal)
  link(elbow, wrist, 10, shade(pal.metal, 0.06))
  link(wrist, quill, 6, shade(pal.metal, -0.08))

  for (const [p, r] of [[shoulder, 9], [elbow, 8], [wrist, 6]]) {
    ctx.beginPath()
    ctx.arc(p[0], p[1], r, 0, TAU)
    ctx.fillStyle = pal.metal
    ctx.fill()
    ctx.strokeStyle = pal.metalDark
    ctx.lineWidth = 2
    ctx.stroke()
  }

  // Gripper.
  const grip = 7
  ctx.strokeStyle = pal.ink
  ctx.lineWidth = 2.5
  ctx.beginPath()
  ctx.moveTo(quill[0] - grip, quill[1] + 4)
  ctx.lineTo(quill[0] + grip, quill[1] + 4)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(quill[0] - grip, quill[1] + 4)
  ctx.lineTo(quill[0] - grip + 3, quill[1] + 11)
  ctx.moveTo(quill[0] + grip, quill[1] + 4)
  ctx.lineTo(quill[0] + grip - 3, quill[1] + 11)
  ctx.stroke()
  ctx.restore()
}

function eventText(event) {
  const raw = String(event || '')
  const [key, color] = raw.split(':')
  if (!key) return ''
  const base = t(key)
  return color ? `${base} ${t(`scara.color.${color}`)}` : base
}

function drawHud(ctx, view, pal, scene, frame) {
  const s = frame?.scara || {}
  ctx.save()
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'

  ctx.font = '700 16px system-ui, -apple-system, "Segoe UI", sans-serif'
  ctx.fillStyle = pal.ink
  ctx.fillText(t('scara.title'), PAD, PAD - 22)

  ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
  ctx.fillStyle = pal.muted
  const arm = s.arm || {}
  ctx.fillText(
    `q1=${Number(arm.q1 || 0).toFixed(2)}  q2=${Number(arm.q2 || 0).toFixed(2)}  d3=${Number(arm.d3 || 0).toFixed(2)}`,
    PAD,
    PAD - 2,
  )

  // Stats panel.
  const lines = [
    `${t('scara.placed')}: ${s.placed ?? 0}`,
    `${t('scara.rejected')}: ${s.rejected ?? 0}`,
    `${t('scara.conveyor')}: ${s.conveyor?.on ? `${Number(s.conveyor.speed || 0).toFixed(2)} m/s` : t('scara.stopped')}`,
  ]
  ctx.font = '600 12px system-ui, -apple-system, "Segoe UI", sans-serif'
  const panelW = 176
  const panelH = 20 + lines.length * 18
  const px = view.width - PAD - panelW
  const py = PAD - 24
  ctx.fillStyle = pal.panel
  ctx.beginPath()
  ctx.roundRect(px, py, panelW, panelH, 8)
  ctx.fill()
  ctx.strokeStyle = pal.grid
  ctx.lineWidth = 1
  ctx.stroke()
  ctx.fillStyle = pal.ink
  lines.forEach((line, i) => ctx.fillText(line, px + 12, py + 10 + i * 18))

  // Camera hint: the SCARA cell is drawn with its own orbit camera.
  ctx.font = '11px system-ui, -apple-system, "Segoe UI", sans-serif'
  ctx.fillStyle = pal.muted
  ctx.globalAlpha = 0.85
  ctx.fillText(t('scara.controls'), PAD, view.height - PAD - 24)
  ctx.globalAlpha = 1

  // Event line.
  const event = eventText(s.event)
  if (event) {
    ctx.font = '600 12px system-ui, -apple-system, "Segoe UI", sans-serif'
    ctx.fillStyle = pal.muted
    ctx.fillText(event, PAD, view.height - PAD - 4)
  }

  // Colour legend.
  const colors = scene.scara.colors || {}
  let lx = view.width - PAD - 8
  ctx.textAlign = 'right'
  for (const name of ['blue', 'green', 'red']) {
    const label = t(`scara.color.${name}`)
    ctx.fillStyle = pal.muted
    ctx.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif'
    ctx.fillText(label, lx, view.height - PAD - 4)
    const tw = ctx.measureText(label).width
    ctx.beginPath()
    ctx.arc(lx - tw - 10, view.height - PAD + 1, 5, 0, TAU)
    ctx.fillStyle = css(colors[name] || [180, 180, 180])
    ctx.fill()
    lx -= tw + 26
  }
  ctx.restore()
}

export function drawScaraScene(ctx, scene, frame, theme, width, height, camera) {
  if (!scene || !scene.scara) return
  const pal = palette(theme)
  const view = makeView(scene, width, height, camera)
  const state = frame?.scara || {}
  const sc = scene.scara

  drawFloor(ctx, view, pal, scene)
  drawConveyor(ctx, view, pal, scene, state)

  for (const basket of sc.baskets || []) {
    const live = (state.baskets || []).find((b) => b.id === basket.id) || basket
    drawBasket(ctx, view, pal, scene, live)
  }

  const parts = [...(state.objects || [])]
  if (state.held) parts.push({ ...state.held, held: true })
  parts.sort((a, b) => (a.y + a.x) - (b.y + b.x))
  for (const part of parts) drawPart(ctx, view, pal, scene, part)

  if (!drawModelArm(ctx, view, pal, scene, state)) drawArm(ctx, view, pal, scene, state)
  drawHud(ctx, view, pal, scene, state)
}
