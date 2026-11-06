// World (metres, y up) <-> screen (CSS pixels, y down) transform.
// All screen values are CSS pixels; the renderer applies devicePixelRatio itself.

export const MIN_SCALE = 2; // px per metre
export const MAX_SCALE = 4000;

export class Camera {
  constructor() {
    this.cx = 0; // world point at the viewport centre
    this.cy = 0;
    this.scale = 50; // px per metre
    this.width = 1; // viewport size in CSS px
    this.height = 1;
    this.dpr = 1;
  }

  setViewport(width, height, dpr = 1) {
    // keep the world centre fixed on resize
    this.width = Math.max(1, width);
    this.height = Math.max(1, height);
    this.dpr = dpr || 1;
  }

  clampScale(s) {
    return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s));
  }

  worldToScreen(x, y) {
    return [
      this.width / 2 + (x - this.cx) * this.scale,
      this.height / 2 - (y - this.cy) * this.scale,
    ];
  }

  screenToWorld(px, py) {
    return [
      this.cx + (px - this.width / 2) / this.scale,
      this.cy - (py - this.height / 2) / this.scale,
    ];
  }

  // Pan by a screen delta (the content follows the pointer).
  panBy(dxPx, dyPx) {
    this.cx -= dxPx / this.scale;
    this.cy += dyPx / this.scale;
  }

  // Zoom by factor keeping the world point under (px, py) fixed.
  zoomAt(px, py, factor) {
    const [wx, wy] = this.screenToWorld(px, py);
    this.scale = this.clampScale(this.scale * factor);
    this.cx = wx - (px - this.width / 2) / this.scale;
    this.cy = wy + (py - this.height / 2) / this.scale;
  }

  zoomCenter(factor) {
    this.zoomAt(this.width / 2, this.height / 2, factor);
  }

  // Fit a world rect {x, y, w, h} (x,y = lower-left corner) with a margin in px.
  fit(rect, margin = 40) {
    const w = Math.max(rect.w, 1e-6);
    const h = Math.max(rect.h, 1e-6);
    const availW = Math.max(10, this.width - 2 * margin);
    const availH = Math.max(10, this.height - 2 * margin);
    this.scale = this.clampScale(Math.min(availW / w, availH / h));
    this.cx = rect.x + w / 2;
    this.cy = rect.y + h / 2;
  }

  // Visible world rect {minX, minY, maxX, maxY}.
  bounds() {
    const [minX, maxY] = this.screenToWorld(0, 0);
    const [maxX, minY] = this.screenToWorld(this.width, this.height);
    return { minX, minY, maxX, maxY };
  }

  state() {
    return { cx: this.cx, cy: this.cy, scale: this.scale, width: this.width, height: this.height, dpr: this.dpr };
  }
}
