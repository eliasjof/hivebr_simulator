<script setup>
import { onBeforeUnmount, onMounted, ref, toRaw, watch } from 'vue';
import { Renderer } from './renderer.js';

const props = defineProps({
  scene: { type: Object, default: null },
  tool: { type: String, default: 'select' },
  options: { type: Object, default: () => ({}) },
  interactive: { type: Boolean, default: true },
});

const emit = defineEmits([
  'add-waypoint',
  'waypoint-drag-orientation',
  'add-obstacle',
  'add-recharge',
  'context',
  'select-robot',
  'move-robot',
  'track-strokes',
  'cursor',
]);

const root = ref(null);
const canvas = ref(null);
const cursorStyle = ref('default');

let renderer = null;
let ro = null;
let pendingFit = false;
let fitKey = null;

// pointer state
const pointers = new Map(); // id -> {x, y}
let gesture = null; // active one-pointer gesture
let pinch = null; // {dist, cx, cy}
let spaceDown = false;
let strokes = [];
let preview = { strokes: null, arrow: null, robot: null };
let cursorRaf = 0;
let cursorPending = null;
const DRAG_PX = 6;

// ---- helpers -----------------------------------------------------------

function localXY(e) {
  const r = canvas.value.getBoundingClientRect();
  return [e.clientX - r.left, e.clientY - r.top];
}

function toWorld(px, py) {
  return renderer.camera.screenToWorld(px, py);
}

function isEditable(t) {
  if (!t || !t.tagName) return false;
  const tag = t.tagName.toLowerCase();
  return tag === 'input' || tag === 'textarea' || tag === 'select' || t.isContentEditable || !!(t.closest && t.closest('.cm-editor'));
}

function updateCursor() {
  if (gesture && gesture.kind === 'pan') cursorStyle.value = 'grabbing';
  else if (spaceDown) cursorStyle.value = 'grab';
  else if (!props.interactive) cursorStyle.value = 'grab';
  else {
    cursorStyle.value =
      { select: 'default', waypoint: 'crosshair', obstacle: 'crosshair', recharge: 'crosshair', draw: 'crosshair', move: 'move' }[props.tool] ||
      'default';
  }
}

function pushPreview() {
  if (!renderer) return;
  const p = {};
  if (strokes.length || preview.strokes) p.strokes = preview.strokes || strokes;
  if (preview.arrow) p.arrow = preview.arrow;
  if (preview.robot) p.robot = preview.robot;
  renderer.setPreview(Object.keys(p).length ? p : null);
}

function refreshStrokePreview() {
  preview.strokes = strokes.length ? strokes : null;
  pushPreview();
}

// ---- fit ---------------------------------------------------------------

function sceneFitKey(s) {
  if (!s) return null;
  const w = s.world || {};
  const m = s.lineMap || s.map;
  return [w.width, w.height, m ? m.width_m + 'x' + m.height_m + ':' + m.png_b64.length : 'nomap'].join('|');
}

function fit() {
  if (!renderer) return;
  const cam = renderer.camera;
  if (cam.width < 20 || cam.height < 20) {
    pendingFit = true;
    return;
  }
  renderer.fit(48);
  pendingFit = false;
}

function centerOn(x, y) {
  if (!renderer) return;
  renderer.centerOn(x, y);
  renderer.requestRender();
}

function zoomIn() {
  renderer.camera.zoomCenter(1.25);
  renderer.requestRender();
}
function zoomOut() {
  renderer.camera.zoomCenter(1 / 1.25);
  renderer.requestRender();
}
function getCamera() {
  return renderer ? renderer.camera : null;
}

// ---- pointer handling ----------------------------------------------------

function wantsPan(e, hit) {
  if (e.button === 1) return true;
  if (spaceDown && e.button === 0) return true;
  if (!props.interactive) return e.button === 0;
  if (e.button !== 0) return false;
  const isTouch = e.pointerType === 'touch';
  switch (props.tool) {
    case 'select':
      return !(hit && hit.type === 'robot');
    case 'move':
      return !(hit && hit.type === 'robot');
    case 'waypoint':
    case 'draw':
      return false;
    default:
      return isTouch; // obstacle / recharge: touch drag pans, a tap adds
  }
}

function onPointerDown(e) {
  if (!renderer) return;
  const [px, py] = localXY(e);
  pointers.set(e.pointerId, { x: px, y: py });
  canvas.value.setPointerCapture?.(e.pointerId);
  if (e.button === 1) e.preventDefault();

  if (pointers.size === 2) {
    // switch to pinch: cancel any one-pointer gesture
    if (gesture && gesture.kind === 'draw') cancelStrokeInProgress();
    gesture = null;
    preview.arrow = null;
    preview.robot = null;
    pushPreview();
    const [a, b] = [...pointers.values()];
    pinch = { dist: Math.hypot(a.x - b.x, a.y - b.y) || 1, cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
    updateCursor();
    return;
  }
  if (pointers.size > 2) return;
  if (e.button === 2) return; // handled in contextmenu

  const [wx, wy] = toWorld(px, py);
  const hit = props.interactive ? renderer.hitTest(wx, wy) : null;

  if (wantsPan(e, hit)) {
    gesture = { kind: 'pan', id: e.pointerId, lx: px, ly: py, sx: px, sy: py, moved: false, hit };
    updateCursor();
    return;
  }
  if (!props.interactive || e.button !== 0) return;

  switch (props.tool) {
    case 'select':
      gesture = { kind: 'selectclick', id: e.pointerId, sx: px, sy: py, hit };
      break;
    case 'waypoint':
      gesture = { kind: 'waypoint', id: e.pointerId, sx: px, sy: py, wx, wy, dragging: false, shift: e.shiftKey };
      break;
    case 'obstacle':
    case 'recharge':
      gesture = { kind: 'click', id: e.pointerId, sx: px, sy: py, wx, wy };
      break;
    case 'draw':
      strokes.push([[wx, wy]]);
      gesture = { kind: 'draw', id: e.pointerId, lx: px, ly: py };
      refreshStrokePreview();
      break;
    case 'move':
      if (hit && hit.type === 'robot') {
        const pose = renderer.poseOf(hit.index);
        gesture = { kind: 'move', id: e.pointerId, index: hit.index, dx: pose.x - wx, dy: pose.y - wy, theta: pose.theta, x: pose.x, y: pose.y, moved: false, sx: px, sy: py };
      }
      break;
  }
}

function cancelStrokeInProgress() {
  if (strokes.length) strokes.pop();
  refreshStrokePreview();
}

function onPointerMove(e) {
  if (!renderer) return;
  const [px, py] = localXY(e);
  const rec = pointers.get(e.pointerId);

  if (e.pointerType !== 'touch' || !rec) {
    cursorPending = toWorld(px, py);
    if (!cursorRaf) {
      cursorRaf = requestAnimationFrame(() => {
        cursorRaf = 0;
        if (cursorPending) emit('cursor', { x: cursorPending[0], y: cursorPending[1] });
      });
    }
  }
  if (!rec) return;
  const prevX = rec.x;
  const prevY = rec.y;
  rec.x = px;
  rec.y = py;

  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
    const cx = (a.x + b.x) / 2;
    const cy = (a.y + b.y) / 2;
    const cam = renderer.camera;
    cam.panBy(cx - pinch.cx, cy - pinch.cy);
    cam.zoomAt(cx, cy, dist / pinch.dist);
    pinch = { dist, cx, cy };
    renderer.requestRender();
    return;
  }
  if (!gesture || gesture.id !== e.pointerId) return;
  const g = gesture;

  switch (g.kind) {
    case 'pan': {
      renderer.camera.panBy(px - g.lx, py - g.ly);
      g.lx = px;
      g.ly = py;
      renderer.requestRender();
      break;
    }
    case 'waypoint': {
      if (!g.dragging && Math.hypot(px - g.sx, py - g.sy) > DRAG_PX) g.dragging = true;
      if (g.dragging) {
        const [wx, wy] = toWorld(px, py);
        g.theta = Math.atan2(wy - g.wy, wx - g.wx);
        preview.arrow = { x: g.wx, y: g.wy, theta: g.theta };
        pushPreview();
      }
      break;
    }
    case 'draw': {
      if (Math.hypot(px - g.lx, py - g.ly) >= 2) {
        const [wx, wy] = toWorld(px, py);
        strokes[strokes.length - 1].push([wx, wy]);
        g.lx = px;
        g.ly = py;
        refreshStrokePreview();
      }
      break;
    }
    case 'move': {
      if (!g.moved && Math.hypot(px - g.sx, py - g.sy) > 3) g.moved = true;
      const [wx, wy] = toWorld(px, py);
      g.x = wx + g.dx;
      g.y = wy + g.dy;
      if (e.shiftKey) g.theta = Math.atan2(wy - g.y, wx - g.x);
      preview.robot = { index: g.index, x: g.x, y: g.y, theta: g.theta };
      pushPreview();
      break;
    }
  }
}

function endPointer(e, cancelled) {
  const rec = pointers.get(e.pointerId);
  if (!rec) return;
  const [px, py] = localXY(e);
  pointers.delete(e.pointerId);
  if (canvas.value.hasPointerCapture?.(e.pointerId)) canvas.value.releasePointerCapture(e.pointerId);

  if (pinch) {
    if (pointers.size < 2) pinch = null;
    return;
  }
  const g = gesture;
  if (!g || g.id !== e.pointerId) return;
  gesture = null;
  const wasDrag = Math.hypot(px - g.sx, py - g.sy) > DRAG_PX;

  if (!cancelled) {
    switch (g.kind) {
      case 'pan':
        break;
      case 'selectclick':
        if (!wasDrag && g.hit && g.hit.type === 'robot') emit('select-robot', { index: g.hit.index });
        break;
      case 'waypoint':
        if (g.dragging) emit('waypoint-drag-orientation', { x: g.wx, y: g.wy, theta: g.theta });
        else emit('add-waypoint', { x: g.wx, y: g.wy, shift: !!g.shift });
        break;
      case 'click':
        if (!wasDrag) emit(props.tool === 'recharge' ? 'add-recharge' : 'add-obstacle', { x: g.wx, y: g.wy });
        break;
      case 'draw':
        emit('track-strokes', { strokes: strokes.map((s) => s.slice()) });
        break;
      case 'move':
        emit('move-robot', { index: g.index, x: g.x, y: g.y, theta: g.theta });
        break;
    }
  } else if (g.kind === 'draw') {
    cancelStrokeInProgress();
  }
  preview.arrow = null;
  preview.robot = null;
  pushPreview();
  updateCursor();
}

function onContextMenu(e) {
  e.preventDefault();
  if (!renderer) return;
  const [px, py] = localXY(e);
  const [x, y] = toWorld(px, py);
  const hit = renderer.hitTest(x, y);
  emit('context', { x, y, screenX: e.clientX, screenY: e.clientY, hit });
}

function onWheel(e) {
  if (!renderer) return;
  e.preventDefault();
  const [px, py] = localXY(e);
  let dy = e.deltaY;
  if (e.deltaMode === 1) dy *= 16;
  else if (e.deltaMode === 2) dy *= 400;
  const factor = Math.exp(-Math.max(-120, Math.min(120, dy)) * 0.0018);
  renderer.camera.zoomAt(px, py, factor);
  renderer.requestRender();
}

function onPointerLeave(e) {
  if (e.pointerType === 'touch') return;
  cursorPending = null;
  emit('cursor', null);
}

function onKeyDown(e) {
  if (e.code === 'Space' && !spaceDown && !isEditable(e.target)) {
    spaceDown = true;
    e.preventDefault();
    updateCursor();
  }
}
function onKeyUp(e) {
  if (e.code === 'Space' && spaceDown) {
    spaceDown = false;
    updateCursor();
  }
}
function onBlur() {
  spaceDown = false;
  updateCursor();
}

// ---- strokes API -----------------------------------------------------------

function clearStrokes() {
  strokes = [];
  refreshStrokePreview();
}
function getStrokes() {
  return strokes.map((s) => s.slice());
}
function undoStroke() {
  strokes.pop();
  refreshStrokePreview();
  emit('track-strokes', { strokes: getStrokes() });
}

// ---- lifecycle ---------------------------------------------------------------

function applyScene(s) {
  if (!renderer) return;
  renderer.setScene(s ? toRaw(s) : null);
  const key = sceneFitKey(s);
  if (key && key !== fitKey) {
    fitKey = key;
    fit();
  }
}

onMounted(() => {
  renderer = new Renderer(canvas.value);
  renderer.setOptions(toRaw(props.options));
  ro = new ResizeObserver(() => {
    renderer.resize();
    if (pendingFit) fit();
  });
  ro.observe(root.value);
  const el = canvas.value;
  el.addEventListener('wheel', onWheel, { passive: false });
  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('keyup', onKeyUp);
  window.addEventListener('blur', onBlur);
  applyScene(props.scene);
  updateCursor();
});

onBeforeUnmount(() => {
  ro && ro.disconnect();
  canvas.value && canvas.value.removeEventListener('wheel', onWheel);
  window.removeEventListener('keydown', onKeyDown);
  window.removeEventListener('keyup', onKeyUp);
  window.removeEventListener('blur', onBlur);
  if (cursorRaf) cancelAnimationFrame(cursorRaf);
  renderer && renderer.destroy();
  renderer = null;
});

watch(() => props.scene, (s) => applyScene(s));
watch(() => props.options, (o) => renderer && renderer.setOptions(toRaw(o)), { deep: true });
watch(() => [props.tool, props.interactive], () => {
  if (gesture && gesture.kind === 'draw') cancelStrokeInProgress();
  gesture = null;
  preview.arrow = null;
  preview.robot = null;
  pushPreview();
  updateCursor();
});

defineExpose({
  pushFrame: (frame) => renderer && renderer.pushFrame(frame),
  fit,
  centerOn,
  zoomIn,
  zoomOut,
  getCamera,
  clearStrokes,
  getStrokes,
  undoStroke,
  canvas: canvas,
});
</script>

<template>
  <div ref="root" class="sim-canvas" :style="{ cursor: cursorStyle }">
    <canvas
      ref="canvas"
      class="sim-canvas__surface"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="endPointer($event, false)"
      @pointercancel="endPointer($event, true)"
      @pointerleave="onPointerLeave"
      @contextmenu="onContextMenu"
    ></canvas>
  </div>
</template>

<style scoped>
.sim-canvas {
  position: absolute;
  inset: 0;
  overflow: hidden;
  user-select: none;
  -webkit-user-select: none;
}
.sim-canvas__surface {
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  outline: none;
  cursor: inherit;
}
</style>
