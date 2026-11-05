import { Camera2D } from './Camera2D'

export class WaypointRenderer {
  render(ctx: CanvasRenderingContext2D, camera: Camera2D, store: any) {
    const { waypoints, config } = store
    if (!waypoints) return

    const tol = config?.waypoints?.goal_tolerance || 0.5

    for (const [_idStr, wps] of Object.entries(waypoints)) {
      const wpList = wps as number[][]
      if (!wpList.length) continue

      // Draw lines between waypoints
      ctx.strokeStyle = 'rgba(255, 140, 0, 0.5)'
      ctx.lineWidth = 2 / camera.zoom
      ctx.setLineDash([10 / camera.zoom, 5 / camera.zoom])
      
      ctx.beginPath()
      for (let i = 0; i < wpList.length; i++) {
        const pos = camera.worldToScreen(wpList[i][0], wpList[i][1])
        if (i === 0) ctx.moveTo(pos.x, pos.y)
        else ctx.lineTo(pos.x, pos.y)
      }
      ctx.stroke()
      ctx.setLineDash([])

      // Draw waypoint circles
      wpList.forEach((wp, i) => {
        const pos = camera.worldToScreen(wp[0], wp[1])
        const radius = Math.max(6, 12 / camera.zoom)
        
        // Current waypoint is larger
        const isCurrent = i === 0 // TODO: track current index per robot
        const r = isCurrent ? radius * 1.5 : radius

        ctx.beginPath()
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2)
        ctx.fillStyle = isCurrent ? '#39ff14' : '#ff8c00'
        ctx.fill()
        ctx.strokeStyle = '#000'
        ctx.lineWidth = 2 / camera.zoom
        ctx.stroke()

        // Tolerance circle
        const tolRadius = tol * camera.zoom * 50
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, tolRadius, 0, Math.PI * 2)
        ctx.strokeStyle = isCurrent ? 'rgba(57, 255, 20, 0.5)' : 'rgba(255, 140, 0, 0.3)'
        ctx.lineWidth = 1 / camera.zoom
        ctx.stroke()

        // Orientation arrow
        if (wp.length > 2 && !isNaN(wp[2])) {
          const angle = wp[2]
          const arrowLen = radius * 2
          const endX = pos.x + Math.cos(angle) * arrowLen
          const endY = pos.y + Math.sin(angle) * arrowLen
          
          ctx.beginPath()
          ctx.moveTo(pos.x, pos.y)
          ctx.lineTo(endX, endY)
          ctx.strokeStyle = '#000'
          ctx.lineWidth = 2 / camera.zoom
          ctx.stroke()
        }
      })
    }
  }
}