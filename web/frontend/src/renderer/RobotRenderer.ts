import { Camera2D } from './Camera2D'
import type { RobotState } from '@/types'

export class RobotRenderer {
  private robotColors = [
    '#1e90ff', '#dc143c', '#32cd32', '#ffa500',
    '#9400d3', '#00ced1', '#ff69b4', '#ffd700',
  ]

  render(
    ctx: CanvasRenderingContext2D,
    camera: Camera2D,
    states: Record<string, RobotState>,
    collisions: Record<string, boolean>,
    selectedRobot: number
  ) {
    for (const [idStr, state] of Object.entries(states)) {
      const id = parseInt(idStr)
      const isSelected = id === selectedRobot
      const isColliding = collisions[idStr]

      this.drawRobot(ctx, camera, state, id, isSelected, isColliding)
    }
  }

  private drawRobot(
    ctx: CanvasRenderingContext2D,
    camera: Camera2D,
    state: RobotState,
    id: number,
    isSelected: boolean,
    isColliding: boolean
  ) {
    const pos = camera.worldToScreen(state.x, state.y)
    const radius = Math.max(8, state.radius * camera.zoom * 50)

    ctx.save()
    ctx.translate(pos.x, pos.y)
    ctx.rotate(state.theta)

    // Collision indicator (red pulsing)
    if (isColliding) {
      const pulseRadius = radius + 5 + Math.sin(Date.now() / 100) * 3
      ctx.beginPath()
      ctx.arc(0, 0, pulseRadius, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)'
      ctx.lineWidth = 3
      ctx.stroke()
    }

    // Robot body
    ctx.beginPath()
    ctx.arc(0, 0, radius, 0, Math.PI * 2)
    ctx.fillStyle = this.robotColors[id % this.robotColors.length]
    ctx.fill()

    // Selection ring
    if (isSelected) {
      ctx.strokeStyle = '#ffff00'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    // Direction indicator
    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.lineTo(radius * 1.2, 0)
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = Math.max(2, radius * 0.1)
    ctx.stroke()

    // Robot ID
    ctx.fillStyle = '#fff'
    ctx.font = `${Math.max(10, radius * 0.4)}px monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(id.toString(), 0, 0)

    ctx.restore()
  }
}