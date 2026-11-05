import { Camera2D } from './Camera2D'

export class ObstacleRenderer {
  render(ctx: CanvasRenderingContext2D, camera: Camera2D, config: any) {
    const world = config?.world
    if (!world?.obstacles) return

    for (const obs of world.obstacles) {
      const [x, y, r] = obs
      const pos = camera.worldToScreen(x, y)
      const radius = Math.max(3, r * camera.zoom * 50)

      ctx.beginPath()
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(40, 120, 40, 0.8)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(0, 100, 0, 1)'
      ctx.lineWidth = 2 / camera.zoom
      ctx.stroke()

      // Safety margin circle
      if (world.robot_safety_margin > 0) {
        const safetyRadius = radius + world.robot_safety_margin * camera.zoom * 50
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, safetyRadius, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(40, 120, 40, 0.3)'
        ctx.lineWidth = 1 / camera.zoom
        ctx.setLineDash([5 / camera.zoom, 5 / camera.zoom])
        ctx.stroke()
        ctx.setLineDash([])
      }
    }
  }
}