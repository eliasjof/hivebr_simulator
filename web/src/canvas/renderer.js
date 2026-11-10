import { Camera } from './camera.js';
import { drawRobot, drawBattery, robotGeometry, rgb, luminance, mix, ensureContrast } from './robots.js';

const TRAIL_CAP = 4000;
const TAU = Math.PI * 2;
const EFFECT_MS = 700;
const FONT = '11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
const FONT_UI = '600 11px system-ui, -apple-system, "Segoe UI", sans-serif';

const DEFAULT_OPTIONS = {
  showGrid: true,
  showPaths: true,
  showLidar: true,
  showWaypoints: true,
  showLabels: true,
  showLinks: true,
  interpolate: true,
  themeOverride: null, // 'dark' | 'light' | null
};

function angleLerp(a, b, t) {
  let d = ((b - a + Math.PI) % TAU + TAU) % TAU - Math.PI;
  return a + d * t;
}

function niceStep(base, scale, minPx) {
  let step = base > 0 ? base : 1;
  const mult = [2, 2.5, 2];
  let i = 0;
  let guard = 0;
  while (step * scale < minPx && guard++ < 60) step *= mult[i++ % 3];
  return step;
}

function fmt(v, step) {
  const dec = step >= 1 ? 0 : Math.min(4, Math.ceil(-Math.log10(step) + 1e-9));
  const s = v.toFixed(dec);
  return s === '-0' ? '0' : s;
}

function buildPalette(scene, theme) {
  const dark = theme === 'dark';
  const sc = (scene && scene.colors) || {};
  const defBg = dark ? [18, 21, 28] : [244, 245, 247];
  let bg = defBg;
  if (sc.background) {
    const l = luminance(sc.background);
    if ((dark && l < 0.12) || (!dark && l > 0.5)) bg = sc.background;
  }
  const fg = dark ? [214, 220, 232] : [32, 38, 50];
  const pick = (c, d) => ensureContrast(c || d, bg, 2.4);
  const pal = {
    dark,
    bg,
    fg,
    bgCss: rgb(bg),
    text: rgb(mix(fg, bg, 0.12)),
    textDim: rgb(mix(fg, bg, 0.42)),
    halo: rgb(bg, 0.85),
    grid: dark ? 'rgba(255,255,255,0.075)' : 'rgba(20,30,50,0.09)',
    gridMajor: dark ? 'rgba(255,255,255,0.16)' : 'rgba(20,30,50,0.2)',
    border: dark ? 'rgba(255,255,255,0.28)' : 'rgba(20,30,50,0.38)',
    axisX: dark ? '#ff6b6b' : '#d12c2c',
    axisY: dark ? '#5fd38a' : '#1b8a4a',
    outline: dark ? 'rgba(0,0,0,0.75)' : 'rgba(10,16,30,0.8)',
    wheel: dark ? '#7a5230' : '#8b5a2b',
    wheelEdge: dark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.7)',
    rudder: dark ? '#c9d1d9' : '#3a4250',
    sensorBar: dark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.4)',
    sensorEdge: dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.9)',
    barBg: dark ? 'rgba(0,0,0,0.65)' : 'rgba(255,255,255,0.85)',
    paper: dark ? [226, 229, 235] : [255, 255, 255],
    obstacle: ensureContrast(sc.obstacle || [60, 150, 60], bg, 3.4),
    waypoint: pick(sc.waypoint, [200, 170, 0]),
    goal: pick(sc.goal, [160, 60, 255]),
    lidar: pick(sc.lidar, [0, 170, 170]),
    path: pick(sc.path, [30, 144, 255]),
    selection: dark ? '#ffd33d' : '#e36209',
    preview: dark ? '#ffd33d' : '#e36209',
  };
  return pal;
}

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.camera = new Camera();
    this.options = { ...DEFAULT_OPTIONS };
    this.scene = null;
    this.sceneVersion = -1;
    this.pal = buildPalette(null, 'dark');
    this.theme = 'dark';
    this.frame = null;
    this.robots = []; // latest frame robots
    this.cur = []; // {x,y,theta}
    this.prev = [];
    this.tCur = 0;
    this.tPrev = 0;
    this.snap = true;
    this.running = false;
    this.waypoints = [];
    this.obstacles = [];
    this.recharge = [];
    this.links = [];
    this.overlay = [];
    this.trails = [];
    this.effects = []; // per robot { t0 }
    this.lastCollision = [];
    this.preview = null;
    this.bitmaps = { map: null, line: null };
    this._mapKey = { map: null, line: null };
    this.selected = -1;
    this.dirty = true;
    this._raf = 0;
    this._destroyed = false;
    this._loop = this._loop.bind(this);
    this._raf = requestAnimationFrame(this._loop);
    this.resize();
  }

  // ---- inputs --------------------------------------------------------

  setScene(scene) {
    const prevCount = this.scene ? (this.scene.robots || []).length : -1;
    const prevVersion = this.sceneVersion;
    this.scene = scene || null;
    this.sceneVersion = scene ? scene.version : -1;
    const n = scene && scene.robots ? scene.robots.length : 0;
    if (n !== prevCount) {
      this.waypoints = [];
      this.cur = [];
      this.prev = [];
      this.robots = [];
      this.effects = [];
      this.lastCollision = [];
    }
    if (prevVersion !== this.sceneVersion || n !== prevCount) this._resetTrails();
    this._updateTheme();
    this._loadBitmaps(scene);
    this.dirty = true;
  }

  pushFrame(frame) {
    if (!frame) return;
    const now = performance.now();
    this.frame = frame;
    this.running = !!frame.running;
    this.selected = frame.selected ?? this.selected;
    const robots = frame.robots || [];
    // persistent collections
    if (frame.waypoints !== undefined) this.waypoints = frame.waypoints || [];
    if (frame.obstacles !== undefined) this.obstacles = frame.obstacles || [];
    if (frame.recharge !== undefined) this.recharge = frame.recharge || [];
    this.links = frame.links || [];
    this.overlay = frame.overlay || [];

    // interpolation bookkeeping
    const prevPoses = this.cur;
    this.prev = robots.map((r, i) => (prevPoses[i] ? prevPoses[i] : { x: r.x, y: r.y, theta: r.theta }));
    this.cur = robots.map((r) => ({ x: r.x, y: r.y, theta: r.theta }));
    this.tPrev = this.tCur || now - 16;
    this.tCur = now;
    this.snap = !frame.running || (this._lastT !== undefined && frame.t < this._lastT);
    this._lastT = frame.t;
    for (let i = 0; i < robots.length; i++) {
      const a = this.prev[i];
      const b = this.cur[i];
      if (Math.hypot(a.x - b.x, a.y - b.y) > 1.5) this.snap = true;
    }
    this.robots = robots;

    // trails and effects
    for (let i = 0; i < robots.length; i++) {
      const r = robots[i];
      let tr = this.trails[i];
      if (!tr) tr = this.trails[i] = this._newTrail();
      if (tr.epoch !== r.path_epoch) {
        tr.epoch = r.path_epoch;
        tr.count = 0;
        tr.start = 0;
      }
      const dx = r.x - tr.lx;
      const dy = r.y - tr.ly;
      if (tr.count === 0 || dx * dx + dy * dy > 1e-6) {
        const idx = ((tr.start + tr.count) % TRAIL_CAP) * 2;
        tr.buf[idx] = r.x;
        tr.buf[idx + 1] = r.y;
        if (tr.count < TRAIL_CAP) tr.count++;
        else tr.start = (tr.start + 1) % TRAIL_CAP;
        tr.lx = r.x;
        tr.ly = r.y;
      }
      const col = !!r.collision;
      if (col && !this.lastCollision[i]) this.effects[i] = { t0: now, x: r.x, y: r.y };
      this.lastCollision[i] = col;
    }
    this.dirty = true;
  }

  setOptions(opts) {
    Object.assign(this.options, opts || {});
    this._updateTheme();
    this.dirty = true;
  }

  setPreview(p) {
    this.preview = p || null;
    this.dirty = true;
  }

  requestRender() {
    this.dirty = true;
  }

  resize() {
    const c = this.canvas;
    const rect = c.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    const pw = Math.round(w * dpr);
    const ph = Math.round(h * dpr);
    if (c.width !== pw || c.height !== ph) {
      c.width = pw;
      c.height = ph;
    }
    this.camera.setViewport(w, h, dpr);
    this.dirty = true;
  }

  destroy() {
    this._destroyed = true;
    cancelAnimationFrame(this._raf);
    for (const k of ['map', 'line']) if (this.bitmaps[k] && this.bitmaps[k].close) this.bitmaps[k].close();
    this.bitmaps = { map: null, line: null };
  }

  // ---- queries -------------------------------------------------------

  // Rect (world) to fit: world rect or map rect.
  worldRect() {
    const s = this.scene;
    if (!s) return null;
    const m = s.lineMap || s.map;
    const w = m ? m.width_m : s.world && s.world.width;
    const h = m ? m.height_m : s.world && s.world.height;
    if (!(w > 0) || !(h > 0)) return null;
    return { x: 0, y: 0, w, h };
  }

  fit(margin = 48) {
    const r = this.worldRect();
    if (!r) return;
    this.camera.fit(r, margin);
    this.dirty = true;
  }

  centerOn(x, y) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    this.camera.cx = x;
    this.camera.cy = y;
    this.dirty = true;
  }

  poseOf(i) {
    return this._pose(i, performance.now());
  }

  hitTest(wx, wy) {
    const tol = 10 / this.camera.scale;
    const now = performance.now();
    const scene = this.scene;
    if (scene) {
      for (let i = this.robots.length - 1; i >= 0; i--) {
        const p = this._pose(i, now);
        const g = robotGeometry(scene.robots[i] || {});
        const rad = Math.max(g.extent, 8 / this.camera.scale);
        if (Math.hypot(p.x - wx, p.y - wy) <= rad) return { type: 'robot', index: i };
      }
    }
    for (let i = 0; i < this.waypoints.length; i++) {
      const list = this.waypoints[i] || [];
      for (let j = list.length - 1; j >= 0; j--) {
        if (Math.hypot(list[j][0] - wx, list[j][1] - wy) <= Math.max(tol, 0.02)) return { type: 'waypoint', robot: i, index: j };
      }
    }
    for (let i = this.obstacles.length - 1; i >= 0; i--) {
      const o = this.obstacles[i];
      if (Math.hypot(o[0] - wx, o[1] - wy) <= o[2]) return { type: 'obstacle', index: i };
    }
    for (let i = 0; i < this.recharge.length; i++) {
      const o = this.recharge[i];
      if (Math.hypot(o[0] - wx, o[1] - wy) <= Math.max(0.3, 12 / this.camera.scale)) return { type: 'recharge', index: i };
    }
    return null;
  }

  // ---- internals -----------------------------------------------------

  _newTrail() {
    return { buf: new Float32Array(TRAIL_CAP * 2), start: 0, count: 0, epoch: undefined, lx: 1e9, ly: 1e9 };
  }

  _resetTrails() {
    this.trails = [];
  }

  _updateTheme() {
    const t = this.options.themeOverride || (this.scene && this.scene.theme) || 'dark';
    this.theme = t === 'light' ? 'light' : 'dark';
    this.pal = buildPalette(this.scene, this.theme);
  }

  _loadBitmaps(scene) {
    const load = async (slot, spec) => {
      const key = spec ? spec.png_b64.length + ':' + spec.png_b64.slice(-32) + ':' + spec.png_b64.slice(0, 32) : null;
      if (key === this._mapKey[slot]) return;
      this._mapKey[slot] = key;
      const old = this.bitmaps[slot];
      this.bitmaps[slot] = null;
      if (old && old.close) old.close();
      if (!spec) return;
      try {
        const bin = atob(spec.png_b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'image/png' });
        const bmp = await createImageBitmap(blob);
        if (this._mapKey[slot] === key && !this._destroyed) {
          this.bitmaps[slot] = bmp;
          this.dirty = true;
        }
      } catch (e) {
        console.warn('map decode failed', e);
      }
    };
    load('map', scene && scene.map ? scene.map : null);
    load('line', scene && scene.lineMap ? scene.lineMap : null);
  }

  _pose(i, now) {
    const c = this.cur[i];
    if (!c) return { x: 0, y: 0, theta: 0 };
    if (!this.options.interpolate || this.snap || !this.running) return c;
    const p = this.prev[i] || c;
    const span = Math.min(250, Math.max(8, this.tCur - this.tPrev));
    const t = Math.min(1, Math.max(0, (now - this.tCur) / span));
    // render one frame behind: blend from prev to cur over span
    return { x: p.x + (c.x - p.x) * t, y: p.y + (c.y - p.y) * t, theta: angleLerp(p.theta, c.theta, t) };
  }

  _interpolating(now) {
    if (!this.options.interpolate || this.snap || !this.running) return false;
    const span = Math.min(250, Math.max(8, this.tCur - this.tPrev));
    return now - this.tCur < span + 16;
  }

  _loop(now) {
    if (this._destroyed) return;
    this._raf = requestAnimationFrame(this._loop);
    const t = performance.now();
    const effectsActive = this.effects.some((e) => e && t - e.t0 < EFFECT_MS);
    if (this.dirty || effectsActive || this._interpolating(t)) {
      this.dirty = false;
      try {
        this._draw(t);
      } catch (e) {
        console.error('render error', e);
      }
    }
  }

  _robotColor(i) {
    const spec = this.scene && this.scene.robots && this.scene.robots[i];
    const c = (spec && spec.color) || (this.scene && this.scene.colors && this.scene.colors.robot) || [30, 144, 255];
    return c;
  }

  _text(ctx, str, x, y, color, font = FONT, align = 'left', base = 'alphabetic') {
    ctx.font = font;
    ctx.textAlign = align;
    ctx.textBaseline = base;
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3;
    ctx.strokeStyle = this.pal.halo;
    ctx.strokeText(str, x, y);
    ctx.fillStyle = color;
    ctx.fillText(str, x, y);
  }

  _draw(now) {
    const ctx = this.ctx;
    const cam = this.camera;
    const pal = this.pal;
    const o = this.options;
    const dpr = cam.dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = pal.bgCss;
    ctx.fillRect(0, 0, cam.width, cam.height);
    const scene = this.scene;
    if (!scene) return;

    this._drawMaps(ctx);
    if (o.showGrid) this._drawGrid(ctx);
    this._drawWorldBorder(ctx);
    this._drawOrigin(ctx);
    if (o.showPaths) this._drawTrails(ctx, now);
    if (o.showLinks) this._drawLinks(ctx, now);
    this._drawObstacles(ctx);
    this._drawRecharge(ctx);
    if (o.showWaypoints) this._drawWaypoints(ctx);
    if (o.showLidar) this._drawLidar(ctx, now);
    this._drawRobots(ctx, now);
    this._drawOverlay(ctx);
    this._drawPreview(ctx, now);
    this._drawEffects(ctx, now);
  }

  _drawMaps(ctx) {
    const cam = this.camera;
    const sc = this.scene;
    for (const slot of ['map', 'line']) {
      const spec = slot === 'map' ? sc.map : sc.lineMap;
      if (!spec) continue;
      const [x0, y0] = cam.worldToScreen(0, spec.height_m);
      const w = spec.width_m * cam.scale;
      const h = spec.height_m * cam.scale;
      ctx.fillStyle = rgb(this.pal.paper);
      ctx.fillRect(x0, y0, w, h);
      const bmp = this.bitmaps[slot];
      if (bmp) {
        ctx.imageSmoothingEnabled = cam.scale * (spec.resolution || 0.01) < 1.5 ? true : false;
        ctx.drawImage(bmp, x0, y0, w, h);
        ctx.imageSmoothingEnabled = true;
      }
    }
  }

  _drawGrid(ctx) {
    const cam = this.camera;
    const pal = this.pal;
    const world = this.scene.world || {};
    const base = world.grid_size > 0 ? world.grid_size : 1;
    const step = niceStep(base, cam.scale, 26);
    const b = cam.bounds();
    const x0 = Math.floor(b.minX / step) * step;
    const y0 = Math.floor(b.minY / step) * step;
    const labelEvery = Math.max(1, Math.ceil(58 / (step * cam.scale)));
    const hasMap = !!(this.scene.map || this.scene.lineMap);
    const onPaper = hasMap;
    ctx.lineWidth = 1;
    const nx = Math.round((b.maxX - x0) / step) + 1;
    const ny = Math.round((b.maxY - y0) / step) + 1;
    if (nx > 600 || ny > 600) return;
    ctx.beginPath();
    ctx.strokeStyle = onPaper ? 'rgba(20,30,50,0.12)' : pal.grid;
    for (let i = 0; i <= nx; i++) {
      const v = x0 + i * step;
      const [sx] = cam.worldToScreen(v, 0);
      const px = Math.round(sx) + 0.5;
      ctx.moveTo(px, 0);
      ctx.lineTo(px, cam.height);
    }
    for (let j = 0; j <= ny; j++) {
      const v = y0 + j * step;
      const [, sy] = cam.worldToScreen(0, v);
      const py = Math.round(sy) + 0.5;
      ctx.moveTo(0, py);
      ctx.lineTo(cam.width, py);
    }
    ctx.stroke();

    // tick labels on the viewport edges
    const col = pal.textDim;
    for (let i = 0; i <= nx; i++) {
      const idx = Math.round((x0 + i * step) / step);
      if (idx % labelEvery !== 0) continue;
      const v = idx * step;
      const [sx] = cam.worldToScreen(v, 0);
      if (sx < 22 || sx > cam.width - 14) continue;
      this._text(ctx, fmt(v, step), sx, cam.height - 6, col, FONT, 'center');
    }
    for (let j = 0; j <= ny; j++) {
      const idx = Math.round((y0 + j * step) / step);
      if (idx % labelEvery !== 0) continue;
      const v = idx * step;
      const [, sy] = cam.worldToScreen(0, v);
      if (sy < 10 || sy > cam.height - 22) continue;
      this._text(ctx, fmt(v, step), 6, sy + 4, col, FONT, 'left');
    }
    this._text(ctx, 'x (m)', cam.width - 8, cam.height - 20, col, FONT, 'right');
    this._text(ctx, 'y (m)', 6, 14, col, FONT, 'left');
  }

  _drawWorldBorder(ctx) {
    const r = this.worldRect();
    if (!r) return;
    const cam = this.camera;
    const [x0, y0] = cam.worldToScreen(r.x, r.y + r.h);
    ctx.strokeStyle = this.pal.border;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x0, y0, r.w * cam.scale, r.h * cam.scale);
  }

  _drawOrigin(ctx) {
    const w = this.scene.world || {};
    const cam = this.camera;
    const pal = this.pal;
    const [ox, oy] = cam.worldToScreen(0, 0);
    if (w.show_axes !== false && this.options.showGrid) {
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = pal.axisX;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      ctx.moveTo(0, oy);
      ctx.lineTo(cam.width, oy);
      ctx.stroke();
      ctx.strokeStyle = pal.axisY;
      ctx.beginPath();
      ctx.moveTo(ox, 0);
      ctx.lineTo(ox, cam.height);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    if (w.show_origin !== false) {
      const len = 28;
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.strokeStyle = pal.axisX;
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(ox + len, oy);
      ctx.stroke();
      ctx.strokeStyle = pal.axisY;
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(ox, oy - len);
      ctx.stroke();
      ctx.fillStyle = pal.text;
      ctx.beginPath();
      ctx.arc(ox, oy, 3, 0, TAU);
      ctx.fill();
      this._text(ctx, 'O', ox - 7, oy + 13, pal.text, FONT_UI, 'right');
    }
  }

  _drawTrails(ctx, now) {
    const cam = this.camera;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    for (let i = 0; i < this.trails.length; i++) {
      const tr = this.trails[i];
      if (!tr || tr.count < 1) continue;
      const col = ensureContrast(this._robotColor(i), this.pal.bg, 1.8);
      ctx.strokeStyle = rgb(col, 0.75);
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let k = 0; k < tr.count; k++) {
        const idx = ((tr.start + k) % TRAIL_CAP) * 2;
        const x = cam.width / 2 + (tr.buf[idx] - cam.cx) * cam.scale;
        const y = cam.height / 2 - (tr.buf[idx + 1] - cam.cy) * cam.scale;
        if (k === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      const p = this._pose(i, now);
      const [px, py] = cam.worldToScreen(p.x, p.y);
      ctx.lineTo(px, py);
      ctx.stroke();
    }
  }

  _drawLinks(ctx, now) {
    if (!this.links || !this.links.length) return;
    const cam = this.camera;
    ctx.strokeStyle = this.pal.dark ? 'rgba(180,200,255,0.5)' : 'rgba(30,50,120,0.45)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 5]);
    ctx.beginPath();
    for (const [a, b] of this.links) {
      if (!this.cur[a] || !this.cur[b]) continue;
      const pa = this._pose(a, now);
      const pb = this._pose(b, now);
      const [ax, ay] = cam.worldToScreen(pa.x, pa.y);
      const [bx, by] = cam.worldToScreen(pb.x, pb.y);
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  _drawObstacles(ctx) {
    const cam = this.camera;
    const col = this.pal.obstacle;
    for (const o of this.obstacles) {
      const [sx, sy] = cam.worldToScreen(o[0], o[1]);
      const r = Math.max(2.5, o[2] * cam.scale);
      ctx.fillStyle = rgb(col, 0.85);
      ctx.beginPath();
      ctx.arc(sx, sy, r, 0, TAU);
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = this.pal.dark ? 'rgba(255,255,255,0.55)' : 'rgba(0,0,0,0.6)';
      ctx.stroke();
    }
  }

  _drawRecharge(ctx) {
    const cam = this.camera;
    for (const p of this.recharge) {
      const [sx, sy] = cam.worldToScreen(p[0], p[1]);
      const r = Math.max(10, 0.3 * cam.scale);
      ctx.fillStyle = this.pal.dark ? 'rgba(46,160,67,0.35)' : 'rgba(46,160,67,0.25)';
      ctx.beginPath();
      ctx.arc(sx, sy, r, 0, TAU);
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = this.pal.dark ? '#56d364' : '#1a7f37';
      ctx.stroke();
      // lightning bolt
      const u = r / 10;
      ctx.beginPath();
      ctx.moveTo(sx + 1.5 * u, sy - 7 * u);
      ctx.lineTo(sx - 4 * u, sy + 1 * u);
      ctx.lineTo(sx - 0.5 * u, sy + 1 * u);
      ctx.lineTo(sx - 1.5 * u, sy + 7 * u);
      ctx.lineTo(sx + 4 * u, sy - 1.5 * u);
      ctx.lineTo(sx + 0.5 * u, sy - 1.5 * u);
      ctx.closePath();
      ctx.fillStyle = this.pal.dark ? '#f5d547' : '#e0a800';
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = this.pal.outline;
      ctx.stroke();
    }
  }

  _drawArrow(ctx, x, y, theta, len, color, w = 2.5) {
    const ex = x + Math.cos(theta) * len;
    const ey = y - Math.sin(theta) * len;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = w;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(ex, ey);
    ctx.stroke();
    const h = 7;
    const a = -theta;
    ctx.beginPath();
    ctx.moveTo(ex + Math.cos(a) * h * 0.4, ey + Math.sin(a) * h * 0.4);
    ctx.lineTo(ex + Math.cos(a + 2.6) * h, ey + Math.sin(a + 2.6) * h);
    ctx.lineTo(ex + Math.cos(a - 2.6) * h, ey + Math.sin(a - 2.6) * h);
    ctx.closePath();
    ctx.fill();
  }

  _drawWaypoints(ctx) {
    const cam = this.camera;
    const cfg = (this.scene && this.scene.waypoints_cfg) || {};
    const multi = this.waypoints.length > 1;
    for (let i = 0; i < this.waypoints.length; i++) {
      const list = this.waypoints[i] || [];
      if (!list.length) continue;
      const st = this.robots[i] || {};
      const cur = st.wp_index ?? 0;
      const base = multi ? ensureContrast(this._robotColor(i), this.pal.bg, 2.2) : this.pal.waypoint;
      const goal = multi ? base : this.pal.goal;
      // connecting polyline
      ctx.strokeStyle = rgb(base, 0.35);
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      list.forEach((w, j) => {
        const [x, y] = cam.worldToScreen(w[0], w[1]);
        if (j === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);

      list.forEach((w, j) => {
        const [x, y] = cam.worldToScreen(w[0], w[1]);
        const isCur = j === cur;
        const done = j < cur;
        const col = isCur ? goal : base;
        if (cfg.show_tolerance_circle && cfg.goal_tolerance > 0 && (isCur || !done)) {
          ctx.beginPath();
          ctx.arc(x, y, cfg.goal_tolerance * cam.scale, 0, TAU);
          ctx.fillStyle = rgb(col, isCur ? 0.14 : 0.07);
          ctx.fill();
          ctx.strokeStyle = rgb(col, isCur ? 0.7 : 0.35);
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
        const hasTheta = w.length > 2 && w[2] !== null && w[2] !== undefined;
        if (hasTheta) this._drawArrow(ctx, x, y, w[2], isCur ? 30 : 24, rgb(col, done ? 0.5 : 1), 2.5);
        const rad = isCur ? 10 : 8.5;
        ctx.globalAlpha = done ? 0.55 : 1;
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, TAU);
        ctx.fillStyle = rgb(col);
        ctx.fill();
        ctx.lineWidth = isCur ? 2.5 : 1.5;
        ctx.strokeStyle = isCur ? (this.pal.dark ? '#ffffff' : '#111111') : this.pal.outline;
        ctx.stroke();
        ctx.globalAlpha = 1;
        const lum = luminance(col);
        this._numberLabel(ctx, String(j + 1), x, y, lum > 0.4 ? '#101418' : '#ffffff');
      });
    }
  }

  _numberLabel(ctx, str, x, y, color) {
    ctx.font = '700 10px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = color;
    ctx.fillText(str, x, y + 0.5);
  }

  _drawLidar(ctx, now) {
    const cam = this.camera;
    const col = this.pal.lidar;
    for (let i = 0; i < this.robots.length; i++) {
      const pts = this.robots[i].lidar;
      if (!pts || !pts.length) continue;
      // ray origin tracks the robot pose used for drawing the body, hits are from the frame
      const p = this.cur[i];
      const [ox, oy] = cam.worldToScreen(p.x, p.y);
      ctx.strokeStyle = rgb(col, this.pal.dark ? 0.07 : 0.09);
      ctx.lineWidth = 0.75;
      ctx.beginPath();
      for (const q of pts) {
        const [x, y] = cam.worldToScreen(q[0], q[1]);
        ctx.moveTo(ox, oy);
        ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.fillStyle = rgb(col, 0.6);
      for (const q of pts) {
        const [x, y] = cam.worldToScreen(q[0], q[1]);
        ctx.fillRect(x - 1, y - 1, 2, 2);
      }
    }
  }

  _drawRobots(ctx, now) {
    const cam = this.camera;
    const scene = this.scene;
    const o = this.options;
    for (let i = 0; i < this.robots.length; i++) {
      const spec = (scene.robots && scene.robots[i]) || {};
      const st = this.robots[i];
      const pose = this._pose(i, now);
      const color = this._robotColor(i);
      const g = drawRobot(ctx, cam, spec, st, pose, color, this.pal);
      const [sx, sy] = cam.worldToScreen(pose.x, pose.y);
      const rpx = Math.max(g.extent * cam.scale, 9);
      if (st.collision) {
        ctx.strokeStyle = '#f85149';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx, sy, rpx + 3, 0, TAU);
        ctx.stroke();
      }
      if (i === this.selected) {
        ctx.strokeStyle = this.pal.selection;
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.arc(sx, sy, rpx + 6, 0, TAU);
        ctx.stroke();
        ctx.setLineDash([]);
      }
      drawBattery(ctx, cam, g, st, pose, this.pal);
      if (o.showLabels) {
        const label = String(st.id ?? spec.id ?? i);
        this._text(ctx, label, sx, sy - rpx - (i === this.selected ? 12 : 7), this.pal.text, FONT_UI, 'center');
      }
    }
  }

  _drawOverlay(ctx) {
    const cam = this.camera;
    for (const it of this.overlay) {
      const c = it.c || [255, 255, 255];
      const col = ensureContrast(c, this.pal.bg, 1.6);
      ctx.strokeStyle = rgb(col);
      ctx.lineWidth = it.w || 1;
      ctx.lineJoin = 'round';
      if (it.k === 'line' || it.k === 'poly') {
        const pts = it.p || [];
        if (pts.length < 2) continue;
        ctx.beginPath();
        pts.forEach((q, j) => {
          const [x, y] = cam.worldToScreen(q[0], q[1]);
          if (j === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        if (it.k === 'poly') ctx.closePath();
        ctx.stroke();
      } else if (it.k === 'circle') {
        const [x, y] = cam.worldToScreen(it.p[0], it.p[1]);
        ctx.beginPath();
        ctx.arc(x, y, Math.max(1, (it.r || 0) * cam.scale), 0, TAU);
        ctx.stroke();
      }
    }
  }

  // preview = { strokes: [{points:[[x,y],...], width} | [[x,y],...]],
  //             arrow: {x,y,theta}, robot: {index,x,y,theta}, circle: {x,y,r}, point: {x,y} }
  _drawPreview(ctx, now) {
    const p = this.preview;
    if (!p) return;
    const cam = this.camera;
    const col = this.pal.preview;
    if (p.strokes) {
      ctx.strokeStyle = col;
      ctx.globalAlpha = 0.6;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      for (const s of p.strokes) {
        const pts = Array.isArray(s) ? s : s.points;
        const width = Array.isArray(s) ? p.width : s.width;
        if (!pts?.length) continue;
        ctx.lineWidth = Math.max(2, (width || p.width || 0.05) * cam.scale);
        ctx.beginPath();
        pts.forEach((q, j) => {
          const [x, y] = cam.worldToScreen(q[0], q[1]);
          if (j === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        if (pts.length === 1) ctx.lineTo(...cam.worldToScreen(pts[0][0] + 1e-4, pts[0][1]));
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    if (p.circle) {
      const [x, y] = cam.worldToScreen(p.circle.x, p.circle.y);
      ctx.strokeStyle = col;
      ctx.fillStyle = col;
      ctx.globalAlpha = 0.25;
      ctx.beginPath();
      ctx.arc(x, y, Math.max(3, p.circle.r * cam.scale), 0, TAU);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    if (p.arrow) {
      const [x, y] = cam.worldToScreen(p.arrow.x, p.arrow.y);
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, TAU);
      ctx.fillStyle = col;
      ctx.globalAlpha = 0.8;
      ctx.fill();
      ctx.globalAlpha = 1;
      this._drawArrow(ctx, x, y, p.arrow.theta, 40, col, 3);
    }
    if (p.robot && this.scene) {
      const spec = (this.scene.robots && this.scene.robots[p.robot.index]) || {};
      ctx.globalAlpha = 0.55;
      drawRobot(ctx, cam, spec, null, p.robot, this._robotColor(p.robot.index), this.pal);
      ctx.globalAlpha = 1;
    }
  }

  _drawEffects(ctx, now) {
    const cam = this.camera;
    for (let i = 0; i < this.effects.length; i++) {
      const e = this.effects[i];
      if (!e) continue;
      const t = (now - e.t0) / EFFECT_MS;
      if (t >= 1) {
        this.effects[i] = null;
        continue;
      }
      const p = this.cur[i] || e;
      const [x, y] = cam.worldToScreen(p.x, p.y);
      const ease = 1 - Math.pow(1 - t, 3);
      const R = 14 + 34 * ease;
      ctx.save();
      ctx.globalAlpha = 1 - t;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, R);
      grad.addColorStop(0, 'rgba(255,245,200,0.95)');
      grad.addColorStop(0.35, 'rgba(255,170,40,0.8)');
      grad.addColorStop(1, 'rgba(255,60,20,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, R, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = '#ff7a2f';
      ctx.lineWidth = 3 * (1 - t) + 1;
      ctx.beginPath();
      ctx.arc(x, y, R * 1.15, 0, TAU);
      ctx.stroke();
      // sparks
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#ffd24a';
      ctx.lineWidth = 2;
      for (let k = 0; k < 10; k++) {
        const a = (k / 10) * TAU + i;
        const r0 = R * 0.7;
        const r1 = R * (1.05 + 0.5 * ((k * 7) % 3) / 3);
        ctx.beginPath();
        ctx.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0);
        ctx.lineTo(x + Math.cos(a) * r1, y + Math.sin(a) * r1);
        ctx.stroke();
      }
      ctx.restore();
    }
  }
}
