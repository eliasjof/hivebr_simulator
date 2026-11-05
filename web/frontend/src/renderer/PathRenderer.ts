import { Camera2D } from './Camera2D'

export class PathRenderer {
  render(
    ctx: CanvasRenderingContext2D,
    camera: Camera2D,
    states: Record<string, any>,
    showPaths: boolean
  ) {
    if (!showPaths) return

    const colors = [
      '#1e90ff', '#dc143c', '#32cd32', '#ffa500',
      '#9400d3', '#00ced1', '#ff69b4', '#ffd700',
    ]

    for (const [idStr, state] of Object.entries(states)) {
      const id = parseInt(idStr)
      const path = state.path // This would need to be tracked in the simulation
      
      if (!path || !Array.isArray(path) || path.length < 2) continue

      ctx.strokeStyle = colors[id % colors.length]
      ctx.lineWidth = 2 / camera.zoom
      ctx.globalAlpha = 0.7

      ctx.beginPath()
      for (let i = 0; i < path.length; i++) {
        const pos = camera.worldToScreen(path[i][0], path[i][1])
        if (i === 0) ctx.moveTo(pos.x, pos.y)
        else ctx.lineTo(pos.x, pos.y)
      }
      ctx.stroke()

      ctx.globalAlpha = 1
    }
  }
}