export class Camera2D {
  x = 0
  y = 0
  zoom = 1
  viewportWidth = 800
  viewportHeight = 600
  minZoom = 0.1
  maxZoom = 10

  constructor(viewportWidth = 800, viewportHeight = 600) {
    this.viewportWidth = viewportWidth
    this.viewportHeight = viewportHeight
  }

  resize(width: number, height: number) {
    this.viewportWidth = width
    this.viewportHeight = height
  }

  pan(dx: number, dy: number) {
    this.x -= dx / this.zoom
    this.y -= dy / this.zoom
  }

  zoomAt(screenX: number, screenY: number, direction: number) {
    const factor = direction > 0 ? 1.1 : 1 / 1.1
    const newZoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.zoom * factor))
    
    if (newZoom !== this.zoom) {
      // Zoom towards mouse position
      const worldBefore = this.screenToWorld(screenX, screenY)
      this.zoom = newZoom
      const worldAfter = this.screenToWorld(screenX, screenY)
      this.x += worldBefore.x - worldAfter.x
      this.y += worldBefore.y - worldAfter.y
    }
  }

  screenToWorld(screenX: number, screenY: number): { x: number; y: number } {
    return {
      x: this.x + screenX / this.zoom,
      y: this.y + screenY / this.zoom,
    }
  }

  worldToScreen(worldX: number, worldY: number): { x: number; y: number } {
    return {
      x: (worldX - this.x) * this.zoom,
      y: (worldY - this.y) * this.zoom,
    }
  }

  apply(ctx: CanvasRenderingContext2D) {
    ctx.translate(this.viewportWidth / 2, this.viewportHeight / 2)
    ctx.scale(this.zoom, this.zoom)
    ctx.translate(-this.x, -this.y)
  }
}