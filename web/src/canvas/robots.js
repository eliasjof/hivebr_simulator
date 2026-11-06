// Per-type robot drawing. Everything is drawn in a robot-local frame:
// +x forward, +y to the left (counter-clockwise), units in metres.

const TAU = Math.PI * 2;
const MIN_BODY_PX = 7; // below this radius on screen a fixed-size marker is added

export function canonicalType(t) {
  const s = String(t || '').toLowerCase();
  if (['holonomic', 'omni', 'omnidirectional'].includes(s)) return 'holonomic';
  if (['hexagonal_holonomic', 'hexagonal', 'hex_holonomic', '3wheel_holonomic'].includes(s)) return 'hexagonal_holonomic';
  if (['hexagonal_holonomic_line_follower', 'hex_holonomic_line_follower', '3wheel_holonomic_line_follower'].includes(s))
    return 'hexagonal_holonomic_line_follower';
  if (['ackermann', 'car', 'racecar'].includes(s)) return 'ackermann';
  if (s === 'boat') return 'boat';
  if (['line_follower', 'linefollower', 'line', 'line_tracker', 'tcrt5000', 'differential_line_follower'].includes(s))
    return 'line_follower';
  if (['differential_firstorder', 'firstorder', 'diff_tau'].includes(s)) return 'differential_firstorder';
  return 'differential';
}

export function rgb(c, a = 1) {
  const [r, g, b] = c || [128, 128, 128];
  return a >= 1 ? `rgb(${r | 0},${g | 0},${b | 0})` : `rgba(${r | 0},${g | 0},${b | 0},${a})`;
}

export function luminance(c) {
  const f = (v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
}

export function mix(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

// Ensure a colour is visible against a background colour by pushing it toward white/black.
export function ensureContrast(c, bg, minRatio = 2.2) {
  const lb = luminance(bg);
  let out = c;
  for (let i = 0; i < 8; i++) {
    const lc = luminance(out);
    const ratio = (Math.max(lb, lc) + 0.05) / (Math.min(lb, lc) + 0.05);
    if (ratio >= minRatio) break;
    out = mix(out, lb < 0.4 ? [255, 255, 255] : [0, 0, 0], 0.2);
  }
  return out;
}

// Geometry in metres for the robot, from the scene spec (with sane fallbacks).
export function robotGeometry(spec) {
  const type = canonicalType(spec.type);
  const radius = spec.radius > 0 ? spec.radius : spec.length > 0 ? Math.max(spec.length, spec.width || 0) / 2 : 0.1;
  const length = spec.length > 0 ? spec.length : radius * 2;
  const width = spec.width > 0 ? spec.width : radius * 1.4;
  const wheelBase = spec.wheel_base > 0 ? spec.wheel_base : length * 0.7;
  let extent = radius;
  if (type === 'ackermann' || type === 'line_follower') extent = Math.max(radius, Math.hypot(length, width) / 2);
  if (type.startsWith('hexagonal')) extent = hexRadius(spec, radius);
  return { type, radius, length, width, wheelBase, extent };
}

function hexRadius(spec, radius) {
  if (spec.length > 0 && spec.width > 0) return (Math.max(spec.length, spec.width) / 2) * 1.1;
  return radius;
}

function poly(ctx, pts) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
}

function rect(ctx, cx, cy, len, wid, ang = 0) {
  const c = Math.cos(ang);
  const s = Math.sin(ang);
  const hl = len / 2;
  const hw = wid / 2;
  const pts = [
    [hl, hw],
    [hl, -hw],
    [-hl, -hw],
    [-hl, hw],
  ].map(([x, y]) => [cx + x * c - y * s, cy + x * s + y * c]);
  poly(ctx, pts);
}

// Context passed in: { ctx, s (px/m), color, line (px width->metres), pal }
function wheelStyle(ctx, pal) {
  ctx.fillStyle = pal.wheel;
  ctx.strokeStyle = pal.wheelEdge;
}

function headingLine(ctx, k, len, pal, bodyColor) {
  const dark = luminance(bodyColor) > 0.5;
  ctx.strokeStyle = dark ? 'rgba(15,18,25,0.9)' : 'rgba(255,255,255,0.95)';
  ctx.lineWidth = 2.5 * k;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(len, 0);
  ctx.stroke();
}

function outline(ctx, k, pal, width = 1.5) {
  ctx.lineWidth = width * k;
  ctx.strokeStyle = pal.outline;
  ctx.lineJoin = 'round';
  ctx.stroke();
}

function drawDifferential(ctx, g, k, color, pal) {
  const r = g.radius;
  // wheels first (below the body)
  wheelStyle(ctx, pal);
  for (const sy of [1, -1]) {
    rect(ctx, 0, sy * r * 1.0, r * 0.8, r * 0.3);
    ctx.fill();
    ctx.lineWidth = k;
    ctx.stroke();
  }
  ctx.fillStyle = rgb(color);
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, TAU);
  ctx.fill();
  outline(ctx, k, pal);
  headingLine(ctx, k, r * 1.25, pal, color);
}

function drawHolonomic(ctx, g, k, color, pal) {
  const r = g.radius;
  wheelStyle(ctx, pal);
  const o = r * 0.62;
  for (const [x, y] of [[o, o], [o, -o], [-o, o], [-o, -o]]) {
    // omni wheels at 45 degrees
    const a = Math.atan2(y, x) + Math.PI / 2;
    rect(ctx, x * 1.05, y * 1.05, r * 0.55, r * 0.22, a);
    ctx.fill();
    ctx.lineWidth = k;
    ctx.stroke();
  }
  ctx.fillStyle = rgb(color);
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.95, 0, TAU);
  ctx.fill();
  outline(ctx, k, pal);
  bodyAxes(ctx, k, r * 1.15, pal);
}

function bodyAxes(ctx, k, len, pal) {
  ctx.lineCap = 'round';
  ctx.lineWidth = 2.2 * k;
  ctx.strokeStyle = pal.axisX;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(len, 0);
  ctx.stroke();
  ctx.strokeStyle = pal.axisY;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(0, len);
  ctx.stroke();
  // arrowheads
  const h = Math.min(len * 0.28, 8 * k);
  ctx.fillStyle = pal.axisX;
  ctx.beginPath();
  ctx.moveTo(len + h * 0.6, 0);
  ctx.lineTo(len - h * 0.4, h * 0.5);
  ctx.lineTo(len - h * 0.4, -h * 0.5);
  ctx.fill();
  ctx.fillStyle = pal.axisY;
  ctx.beginPath();
  ctx.moveTo(0, len + h * 0.6);
  ctx.lineTo(h * 0.5, len - h * 0.4);
  ctx.lineTo(-h * 0.5, len - h * 0.4);
  ctx.fill();
}

const WHEEL_COLORS = ['#ff6464', '#64d264', '#6496ff'];

function drawHexagonal(ctx, spec, g, st, k, color, pal) {
  const R = hexRadius(spec, g.radius);
  const apothem = R * Math.cos(Math.PI / 6);
  const wheelAngles = [Math.PI / 3, Math.PI, (5 * Math.PI) / 3];
  const wheelLen = R * 0.6;
  const wheelWid = R * 0.2;
  const ws = st && st.extra && st.extra.wheel_speeds;
  let maxWs = 1e-6;
  if (ws) for (const v of ws) maxWs = Math.max(maxWs, Math.abs(v));
  const ref = Math.max(maxWs, spec.max_speed > 0 ? spec.max_speed : 0);

  // wheels
  for (let i = 0; i < 3; i++) {
    const pa = wheelAngles[i];
    const ta = pa + Math.PI / 2;
    const cx = Math.cos(pa) * (apothem + wheelWid * 0.25);
    const cy = Math.sin(pa) * (apothem + wheelWid * 0.25);
    rect(ctx, cx, cy, wheelLen, wheelWid, ta);
    ctx.fillStyle = WHEEL_COLORS[i];
    ctx.fill();
    ctx.lineWidth = k;
    ctx.strokeStyle = pal.wheelEdge;
    ctx.stroke();
  }
  // body
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3 + Math.PI / 6;
    pts.push([R * Math.cos(a), R * Math.sin(a)]);
  }
  poly(ctx, pts);
  ctx.fillStyle = rgb(color);
  ctx.fill();
  outline(ctx, k, pal);

  // wheel speed indicators: arrows along each wheel tangent, length ~ speed
  if (ws) {
    for (let i = 0; i < 3 && i < ws.length; i++) {
      const pa = wheelAngles[i];
      const ta = pa + Math.PI / 2;
      const f = Math.max(-1, Math.min(1, ws[i] / ref));
      if (Math.abs(f) < 0.02) continue;
      const cx = Math.cos(pa) * apothem * 0.72;
      const cy = Math.sin(pa) * apothem * 0.72;
      const len = f * R * 0.8;
      const dx = Math.cos(ta) * len;
      const dy = Math.sin(ta) * len;
      ctx.strokeStyle = WHEEL_COLORS[i];
      ctx.lineWidth = 2.6 * k;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + dx, cy + dy);
      ctx.stroke();
      // arrow head
      const sgn = Math.sign(f);
      const hl = Math.min(Math.abs(len) * 0.5, 6 * k);
      const ux = Math.cos(ta) * sgn;
      const uy = Math.sin(ta) * sgn;
      ctx.fillStyle = WHEEL_COLORS[i];
      ctx.beginPath();
      ctx.moveTo(cx + dx + ux * hl * 0.6, cy + dy + uy * hl * 0.6);
      ctx.lineTo(cx + dx - ux * hl * 0.5 - uy * hl * 0.5, cy + dy - uy * hl * 0.5 + ux * hl * 0.5);
      ctx.lineTo(cx + dx - ux * hl * 0.5 + uy * hl * 0.5, cy + dy - uy * hl * 0.5 - ux * hl * 0.5);
      ctx.fill();
    }
  }
  bodyAxes(ctx, k, R * 0.85, pal);
}

function drawAckermann(ctx, g, st, k, color, pal) {
  const L = g.length;
  const W = g.width;
  const steer = (st && st.extra && st.extra.steer) || 0;
  // translucent footprint circle (collision radius)
  ctx.fillStyle = rgb(color, 0.16);
  ctx.beginPath();
  ctx.arc(0, 0, g.radius, 0, TAU);
  ctx.fill();
  ctx.lineWidth = k;
  ctx.setLineDash([4 * k, 4 * k]);
  ctx.strokeStyle = rgb(color, 0.5);
  ctx.stroke();
  ctx.setLineDash([]);

  const wl = L * 0.18;
  const ww = W * 0.14;
  const hwb = g.wheelBase / 2;
  const track = W / 2;
  wheelStyle(ctx, pal);
  for (const [x, y, a] of [
    [hwb, track, steer],
    [hwb, -track, steer],
    [-hwb, track, 0],
    [-hwb, -track, 0],
  ]) {
    rect(ctx, x, y, wl, ww, a);
    ctx.fill();
    ctx.lineWidth = k;
    ctx.stroke();
  }
  // body
  rect(ctx, 0, 0, L, W);
  ctx.fillStyle = rgb(color);
  ctx.fill();
  outline(ctx, k, pal);
  // cabin / windshield to read the front direction
  rect(ctx, L * 0.1, 0, L * 0.3, W * 0.7);
  ctx.fillStyle = 'rgba(0,0,0,0.28)';
  ctx.fill();
  headingLine(ctx, k, L / 2, pal, color);
}

function drawBoat(ctx, g, st, k, color, pal) {
  const r = g.radius;
  const W = 0.9 * r;
  const L = Math.sqrt(4 * r * r - W * W);
  const steer = (st && st.extra && st.extra.steer) || 0;
  ctx.fillStyle = rgb(color, 0.16);
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, TAU);
  ctx.fill();
  // rudder
  const rx = -0.5 * L;
  const rl = L * 0.28;
  ctx.strokeStyle = pal.rudder;
  ctx.lineWidth = 3 * k;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(rx, 0);
  ctx.lineTo(rx - Math.cos(steer) * rl, -Math.sin(steer) * rl);
  ctx.stroke();
  // hull
  poly(ctx, [
    [-0.5 * L, -0.5 * W],
    [0.25 * L, -0.5 * W],
    [0.5 * L, 0],
    [0.25 * L, 0.5 * W],
    [-0.5 * L, 0.5 * W],
  ]);
  ctx.fillStyle = rgb(color);
  ctx.fill();
  outline(ctx, k, pal, 2);
  // bow highlight
  poly(ctx, [
    [0.5 * L, 0],
    [0.2 * L, -0.25 * W],
    [0.2 * L, 0.25 * W],
  ]);
  ctx.fillStyle = 'rgba(255,255,255,0.28)';
  ctx.fill();
  headingLine(ctx, k, L * 0.55, pal, color);
}

function drawLineFollower(ctx, spec, g, k, color, pal) {
  const hl = g.length / 2;
  const hw = g.width / 2;
  wheelStyle(ctx, pal);
  for (const sy of [1, -1]) {
    rect(ctx, -hl * 0.1, sy * (hw + g.width * 0.04), g.length * 0.4, g.width * 0.12);
    ctx.fill();
  }
  rect(ctx, 0, 0, g.length, g.width);
  ctx.fillStyle = rgb(color);
  ctx.fill();
  outline(ctx, k, pal, 2);
  headingLine(ctx, k, hl, pal, color);
}

// Sensor dots are drawn in world coordinates by the renderer (they carry world positions).
export function drawSensors(ctx, cam, st, pal) {
  const sensors = st && st.extra && st.extra.sensors;
  if (!sensors || !sensors.length) return;
  const rad = Math.max(2.4, 0.006 * cam.scale);
  const pts = sensors.map((q) => cam.worldToScreen(q.x, q.y));
  // sensor bar
  if (pts.length > 1) {
    ctx.strokeStyle = pal.sensorBar;
    ctx.lineWidth = Math.max(1, rad * 0.7);
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    ctx.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]);
    ctx.stroke();
  }
  for (let i = 0; i < sensors.length; i++) {
    const v = Math.max(0, Math.min(1, sensors[i].value ?? (sensors[i].on ? 1 : 0)));
    const base = [70, 70, 70];
    const line = [255, 50, 50];
    ctx.fillStyle = rgb(mix(base, line, v));
    ctx.beginPath();
    ctx.arc(pts[i][0], pts[i][1], rad, 0, TAU);
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = pal.sensorEdge;
    ctx.stroke();
  }
}

// Draw one robot. pose = {x, y, theta}. pal = palette from the renderer.
export function drawRobot(ctx, cam, spec, st, pose, color, pal, opts = {}) {
  const g = robotGeometry(spec);
  const s = cam.scale;
  const [sx, sy] = cam.worldToScreen(pose.x, pose.y);
  const k = 1 / s; // one CSS pixel in metres

  ctx.save();
  ctx.translate(sx, sy);
  ctx.rotate(-pose.theta);
  ctx.scale(s, -s);
  switch (g.type) {
    case 'holonomic':
      drawHolonomic(ctx, g, k, color, pal);
      break;
    case 'hexagonal_holonomic':
    case 'hexagonal_holonomic_line_follower':
      drawHexagonal(ctx, spec, g, st, k, color, pal);
      break;
    case 'ackermann':
      drawAckermann(ctx, g, st, k, color, pal);
      break;
    case 'boat':
      drawBoat(ctx, g, st, k, color, pal);
      break;
    case 'line_follower':
      drawLineFollower(ctx, spec, g, k, color, pal);
      break;
    default:
      drawDifferential(ctx, g, k, color, pal);
  }
  ctx.restore();

  if (g.type === 'line_follower' || g.type === 'hexagonal_holonomic_line_follower') drawSensors(ctx, cam, st, pal);

  // fixed-size marker for very small robots so they stay visible
  if (g.extent * s < MIN_BODY_PX) {
    ctx.save();
    ctx.translate(sx, sy);
    ctx.rotate(-pose.theta);
    ctx.fillStyle = rgb(color, 0.9);
    ctx.strokeStyle = pal.outline;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(9, 0);
    ctx.lineTo(-6, 6);
    ctx.lineTo(-3.5, 0);
    ctx.lineTo(-6, -6);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
  return g;
}

// Battery bar below the robot (screen space).
export function drawBattery(ctx, cam, g, st, pose, pal) {
  if (!st || !st.battery_enabled) return;
  let b = Number(st.battery);
  if (!isFinite(b)) return;
  if (b > 1.0001) b /= 100;
  b = Math.max(0, Math.min(1, b));
  const [sx, sy] = cam.worldToScreen(pose.x, pose.y);
  const w = Math.max(26, g.extent * cam.scale * 1.8);
  const h = 5;
  const y = sy + Math.max(g.extent * cam.scale, 8) + 6;
  ctx.fillStyle = pal.barBg;
  ctx.fillRect(sx - w / 2 - 1, y - 1, w + 2, h + 2);
  ctx.fillStyle = b > 0.5 ? '#3fb950' : b > 0.2 ? '#d29922' : '#f85149';
  ctx.fillRect(sx - w / 2, y, w * b, h);
  if (st.charging) {
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(sx - w / 2 - 1.5, y - 1.5, w + 3, h + 3);
  }
}
