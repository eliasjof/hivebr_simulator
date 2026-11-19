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

// A compact box is six quads, not three. Adding every face to a single list
// and sorting by depth lets the camera orbit around a solid body instead of
// showing only the front, right and top planes.
function addSlab(faces, view, x0, x1, y0, y1, z0, z1, color, segments = 1) {
  const n = Math.max(1, Math.ceil(segments))
  for (let i = 0; i < n; i += 1) {
    const xa = x0 + ((x1 - x0) * i) / n
    const xb = x0 + ((x1 - x0) * (i + 1)) / n
    addFace(faces, view, [[xa, y0, z1], [xb, y0, z1], [xb, y1, z1], [xa, y1, z1]], color)
    addFace(faces, view, [[xa, y0, z0], [xb, y0, z0], [xb, y1, z0], [xa, y1, z0]], color)
    addFace(faces, view, [[xa, y1, z1], [xb, y1, z1], [xb, y1, z0], [xa, y1, z0]], color)
    addFace(faces, view, [[xa, y0, z1], [xb, y0, z1], [xb, y0, z0], [xa, y0, z0]], color)
  }
  addFace(faces, view, [[x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [x0, y0, z0]], color)
  addFace(faces, view, [[x1, y0, z1], [x1, y1, z1], [x1, y1, z0], [x1, y0, z0]], color)
}

function addCylinderY(faces, view, cx, cy, cz, radius, length, color, sides = 20) {
  const world = mMul(mTranslate(cx, cy, cz), mRx(Math.PI / 2))
  addCylinder(faces, view, world, radius, length, color, sides)
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

function addConveyorFaces(faces, view, pal, scene, state) {
  const belt = scene.scara.belt
  const half = belt.width / 2
  const x0 = belt.x0 - 0.30
  const x1 = belt.x1 + 0.30
  const zTop = belt.z
  const steel = hexToRgb(pal.metal)
  const dark = hexToRgb(pal.metalDark)
  const beltTop = hexToRgb(pal.beltTop)

  // Chassis: a solid frame that supports the belt, with a full underside.
  addSlab(faces, view, x0, x1, belt.y - half - 0.10, belt.y + half + 0.10, zTop - 0.26, zTop - 0.12, dark, 14)
  // Belt surface, tiled so parts on top sort correctly from any camera angle.
  addSlab(faces, view, x0 + 0.10, x1 - 0.10, belt.y - half, belt.y + half, zTop - 0.03, zTop, beltTop, 18)
  // Side rails with a steel cap.
  for (const side of [-1, 1]) {
    const y = belt.y + side * (half + 0.07)
    addSlab(faces, view, x0, x1, y - 0.07, y + 0.07, zTop - 0.16, zTop + 0.07, dark, 14)
    addSlab(faces, view, x0, x1, y - 0.08, y + 0.08, zTop + 0.07, zTop + 0.10, steel, 14)
  }
  // Legs and feet.
  for (const x of [x0 + 0.40, x1 - 0.40]) {
    for (const side of [-1, 1]) {
      const y = belt.y + side * (half - 0.04)
      addSlab(faces, view, x - 0.06, x + 0.06, y - 0.06, y + 0.06, 0.04, zTop - 0.26, steel)
      addSlab(faces, view, x - 0.15, x + 0.15, y - 0.15, y + 0.15, 0, 0.05, dark)
    }
  }
  // Rollers at both ends.
  for (const x of [x0 + 0.10, x1 - 0.10]) {
    addCylinderY(faces, view, x, belt.y, zTop - 0.10, 0.095, half * 2 + 0.02, steel, 20)
  }

  // Moving stripes show the belt direction and speed.
  const speed = state?.conveyor?.speed || 0
  const phase = ((state?.t || 0) * Math.max(0.15, speed)) % 0.55
  const stripe = mix(hexToRgb(pal.belt), [255, 255, 255], 0.24)
  for (let x = x0 + 0.10 + phase; x < x1 - 0.10; x += 0.55) {
    addFace(faces, view, [
      [x, belt.y - half + 0.03, zTop + 0.004],
      [x + 0.05, belt.y - half + 0.03, zTop + 0.004],
      [x + 0.05, belt.y + half - 0.03, zTop + 0.004],
      [x, belt.y + half - 0.03, zTop + 0.004],
    ], stripe)
  }
}

function addBasketFaces(faces, view, pal, scene, basket, labels) {
  const color = scene.scara.colors[basket.color] || [180, 180, 180]
  const half = 0.31
  const wall = 0.05
  const height = 0.36
  const x = Number(basket.x)
  const y = Number(basket.y)
  const inner = shade(color, -0.42)

  // Floor and four walls make a real open box instead of one flat plate.
  addSlab(faces, view, x - half, x + half, y - half, y + half, 0, 0.05, inner)
  addSlab(faces, view, x - half, x + half, y - half, y - half + wall, 0.05, height, color)
  addSlab(faces, view, x - half, x + half, y + half - wall, y + half, 0.05, height, color)
  addSlab(faces, view, x - half, x - half + wall, y - half + wall, y + half - wall, 0.05, height, color)
  addSlab(faces, view, x + half - wall, x + half, y - half + wall, y + half - wall, 0.05, height, color)
  // A bright rim catches the light and reads as a coloured basket.
  const rim = shade(color, 0.18)
  addSlab(faces, view, x - half, x + half, y - half, y - half + wall, height, height + 0.03, rim)
  addSlab(faces, view, x - half, x + half, y + half - wall, y + half, height, height + 0.03, rim)
  addSlab(faces, view, x - half, x - half + wall, y - half + wall, y + half - wall, height, height + 0.03, rim)
  addSlab(faces, view, x + half - wall, x + half, y - half + wall, y + half - wall, height, height + 0.03, rim)

  labels.push({
    x, y, z: height + 0.20,
    text: String(basket.count ?? 0),
    color,
  })
}

function addPartFaces(faces, view, pal, scene, part) {
  if (!part) return
  const color = scene.scara.colors[part.color] || [200, 200, 200]
  const x = Number(part.x)
  const y = Number(part.y)
  const z = Number(part.z)
  const radius = 0.105
  const height = 0.15
  // Solid coloured puck: body, darker base and a bright machined top.
  addCylinder(faces, view, mTranslate(x, y, z + height / 2), radius, height, color, 22)
  addCylinder(faces, view, mTranslate(x, y, z + height + 0.004), radius * 0.58, 0.012, shade(color, 0.24), 18)
}

function drawBasketLabels(ctx, view, pal, labels) {
  ctx.save()
  ctx.font = '700 12px system-ui, -apple-system, "Segoe UI", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (const label of labels) {
    const p = view.project(label.x, label.y, label.z)
    const w = 26
    const h = 18
    ctx.beginPath()
    ctx.roundRect(p[0] - w / 2, p[1] - h / 2, w, h, 9)
    ctx.fillStyle = pal.panel
    ctx.fill()
    ctx.strokeStyle = css(label.color)
    ctx.lineWidth = 1.4
    ctx.stroke()
    ctx.fillStyle = pal.ink
    ctx.fillText(label.text, p[0], p[1] + 1)
  }
  ctx.restore()
}

function drawContactShadows(ctx, view, pal, scene) {
  ctx.save()
  ctx.fillStyle = pal.shadow
  const spots = [{ x: 0, y: 0, r: 0.95 }]
  for (const basket of scene.scara.baskets || []) spots.push({ x: basket.x, y: basket.y, r: 0.48 })
  for (const spot of spots) {
    const p = view.project(spot.x, spot.y, 0.006)
    const r = spot.r * view.scale
    ctx.beginPath()
    ctx.ellipse(p[0], p[1], r, r * 0.52, 0, 0, TAU)
    ctx.fill()
  }
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
  if (!worldPoints || worldPoints.length < 3) return
  const pts = worldPoints.map((p) => view.project(p[0], p[1], p[2]))
  let depth = 0
  for (const p of worldPoints) depth += view.depth(p[0], p[1], p[2])
  depth /= Math.max(1, worldPoints.length)
  const normal = faceNormal(worldPoints[0], worldPoints[1], worldPoints[2])
  // Two-sided lighting: the painter sort removes the back faces, so the
  // absolute value keeps every visible face readable from any orbit angle.
  const lit = Math.abs(normal[0] * LIGHT[0] + normal[1] * LIGHT[1] + normal[2] * LIGHT[2])
  const k = 0.26 + 0.74 * lit
  const fill = mix(shade(color, -0.48), shade(color, 0.28), k)
  faces.push({ pts, depth, fill, edge: shade(fill, -0.42) })
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

function addCylinder(faces, view, world, radius, length, color, sides = 24) {
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
    addFace(faces, view, [top[i], bottom[i], bottom[j], top[j]], color)
  }
}

function addSphere(faces, view, world, radius, color, slices = 14, stacks = 8) {
  const r = Math.max(0.001, radius)
  const point = (theta, phi) => mPoint(world, [
    r * Math.sin(phi) * Math.cos(theta),
    r * Math.sin(phi) * Math.sin(theta),
    r * Math.cos(phi),
  ])
  for (let i = 0; i < stacks; i += 1) {
    const phi0 = (Math.PI * i) / stacks
    const phi1 = (Math.PI * (i + 1)) / stacks
    for (let j = 0; j < slices; j += 1) {
      const theta0 = (TAU * j) / slices
      const theta1 = (TAU * (j + 1)) / slices
      addFace(faces, view, [
        point(theta0, phi0), point(theta1, phi0),
        point(theta1, phi1), point(theta0, phi1),
      ], color)
    }
  }
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
  ctx.lineWidth = 0.7
  for (const f of faces) {
    if (!f.pts.length) continue
    ctx.beginPath()
    ctx.moveTo(f.pts[0][0], f.pts[0][1])
    for (let i = 1; i < f.pts.length; i += 1) ctx.lineTo(f.pts[i][0], f.pts[i][1])
    ctx.closePath()
    ctx.fillStyle = css(f.fill)
    ctx.fill()
    ctx.strokeStyle = css(f.edge)
    ctx.globalAlpha = 0.55
    ctx.stroke()
    ctx.globalAlpha = 1
  }
  ctx.restore()
}

function addModelFaces(faces, view, pal, scene, state) {
  const model = scene.scara?.model
  if (!model || !model.chain || !model.chain.length) return false
  const arm = state?.arm || {}
  const values = {}
  for (const joint of model.chain) {
    if (joint.motion) values[joint.motion] = Number(arm[joint.motion]) || 0
  }
  collectModelFaces(faces, view, pal, model, values)
  return true
}

function drawArm(ctx, view, pal, scene, frame) {
  const s = scene.scara
  const metal = hexToRgb(pal.metal)
  const dark = hexToRgb(pal.metalDark)
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
  ctx.fillStyle = css(dark)
  ctx.fill()
  ctx.beginPath()
  ctx.rect(base[0] - baseR, baseTop[1], baseR * 2, base[1] - baseTop[1])
  ctx.fillStyle = css(shade(dark, -0.12))
  ctx.fill()
  ctx.beginPath()
  ctx.ellipse(baseTop[0], baseTop[1], baseR, baseR * 0.55, 0, 0, TAU)
  ctx.fillStyle = css(metal)
  ctx.fill()
  ctx.strokeStyle = css(dark)
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
    ctx.strokeStyle = css(dark)
    ctx.lineWidth = width + 3
    ctx.stroke()
    ctx.strokeStyle = css(color)
    ctx.lineWidth = width
    ctx.stroke()
  }
  link(shoulder, elbow, 13, metal)
  link(elbow, wrist, 10, shade(metal, 0.06))
  link(wrist, quill, 6, shade(metal, -0.08))

  for (const [p, r] of [[shoulder, 9], [elbow, 8], [wrist, 6]]) {
    ctx.beginPath()
    ctx.arc(p[0], p[1], r, 0, TAU)
    ctx.fillStyle = css(metal)
    ctx.fill()
    ctx.strokeStyle = css(dark)
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

function drawHud(ctx, view, pal, scene, state) {
  const s = state || {}
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
  drawContactShadows(ctx, view, pal, scene)

  // Every solid body contributes faces to one list; the painter sort then
  // resolves the conveyor, the table, the baskets, the parts and the arm.
  const faces = []
  const labels = []

  // Mounting plate under the robot: a compact table instead of a floating arm.
  addSlab(faces, view, -0.70, 0.70, -0.70, 0.70, 0, 0.05, hexToRgb(pal.metalDark))
  addSlab(faces, view, -0.56, 0.56, -0.56, 0.56, 0.05, 0.10, hexToRgb(pal.metal))

  addConveyorFaces(faces, view, pal, scene, state)

  for (const basket of sc.baskets || []) {
    const live = (state.baskets || []).find((b) => b.id === basket.id) || basket
    addBasketFaces(faces, view, pal, scene, live, labels)
  }

  const parts = [...(state.objects || [])]
  if (state.held) parts.push({ ...state.held, held: true })
  for (const part of parts) addPartFaces(faces, view, pal, scene, part)

  const hasModel = addModelFaces(faces, view, pal, scene, state)

  drawFaces(ctx, faces, pal)
  drawBasketLabels(ctx, view, pal, labels)
  if (!hasModel) drawArm(ctx, view, pal, scene, state)
  drawHud(ctx, view, pal, scene, state)
}
