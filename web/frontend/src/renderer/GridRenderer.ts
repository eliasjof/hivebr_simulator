import { Camera2D } from './Camera2D'

export class GridRenderer {
  render(ctx: CanvasRenderingContext2D, camera: Camera2D) {
    const gridSize = 1.0 // meters
    const worldTL = camera.screenToWorld(0, 0)
    const worldBR = camera.screenToWorld(camera.viewportWidth, camera.viewportHeight)

    const startX = Math.floor(worldTL.x / gridSize) * gridSize
    const endX = Math.ceil(worldBR.x / gridSize) * gridSize
    const startY = Math.floor(worldTL.y / gridSize) * gridSize
    const endY = Math.ceil(worldBR.y / gridSize) * gridSize

    ctx.strokeStyle = 'rgba(80, 80, 80, 0.5)'
    ctx.lineWidth = 1 / camera.zoom

    // Vertical lines
    for (let x = startX; x <= endX; x += gridSize) {
      const s = camera.worldToScreen(x, worldTL.y)
      const e = camera.worldToScreen(x, worldBR.y)
      ctx.beginPath()
      ctx.moveTo(s.x, s.y)
      ctx.lineTo(e.x, e.y)
      ctx.stroke()
    }

    // Horizontal lines
    for (let y = startY; y <= endY; y += gridSize) {
      const s = camera.worldToScreen(worldTL.x, y)
      const e = camera.worldToScreen(worldBR.x, y)
      ctx.beginPath()
      ctx.moveTo(s.x, s.y)
      ctx.lineTo(e.x, e.y)
      ctx.stroke()
    }

    // Origin axes
    ctx.strokeStyle = 'rgba(220, 50, 50, 0.8)'
    ctx.lineWidth = 2 / camera.zoom
    const ox = camera.worldToScreen(0, 0)
    ctx.beginPath()
    ctx.moveTo(ox.x - 20 / camera.zoom, ox.y)
    ctx.lineTo(ox.x + 20 / camera.zoom, ox.y)
    ctx.stroke()
    
    ctx.beginPath()
    ctx.moveTo(ox.x, ox.y - 20 / camera.zoom)
    ctx.lineTo(ox.x, ox.y + 20 / camera.zoom)
    ctx.stroke()
  }
}