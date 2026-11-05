import { Camera2D } from './Camera2D'

export class LidarRenderer {
  render(_ctx: CanvasRenderingContext2D, _camera: Camera2D, lidar: Record<string, number[][]>) {
    for (const [_idStr, readings] of Object.entries(lidar)) {
      if (!readings.length) continue

      // We need robot position - for now assume it's at the first reading's hit point minus range
      // In a real implementation, we'd get this from the robot state
      
      for (const reading of readings) {
        const [_angle, _dist, _hitX, _hitY] = reading
        // We'd need robot position here - skipping for now
        // This renderer needs access to robot states
      }
    }
  }

  renderWithRobots(
    ctx: CanvasRenderingContext2D,
    camera: Camera2D,
    lidar: Record<string, number[][]>,
    states: Record<string, any>
  ) {
    for (const [_idStr, readings] of Object.entries(lidar)) {
      const state = states[_idStr]
      if (!state || !readings.length) continue

      const robotPos = camera.worldToScreen(state.x, state.y)

      for (const reading of readings) {
        const [_angle, dist, hitX, hitY] = reading
        if (hitX === undefined || hitY === undefined) continue

        const hitPos = camera.worldToScreen(hitX, hitY)
        const isHit = dist < 12.0 // range

        ctx.beginPath()
        ctx.moveTo(robotPos.x, robotPos.y)
        ctx.lineTo(hitPos.x, hitPos.y)
        ctx.strokeStyle = isHit ? 'rgba(0, 255, 255, 0.6)' : 'rgba(80, 120, 120, 0.3)'
        ctx.lineWidth = 1 / camera.zoom
        ctx.stroke()

        if (isHit) {
          ctx.beginPath()
          ctx.arc(hitPos.x, hitPos.y, Math.max(2, 3 / camera.zoom), 0, Math.PI * 2)
          ctx.fillStyle = 'rgba(0, 255, 255, 0.8)'
          ctx.fill()
        }
      }
    }
  }
}