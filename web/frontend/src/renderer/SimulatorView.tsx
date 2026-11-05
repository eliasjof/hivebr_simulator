import { useEffect, useRef, useState } from 'react'
import { useSimulatorStore } from '@/stores/simulatorStore'
import { useUIStore } from '@/stores/uiStore'
import { Camera2D } from './Camera2D'
import { RobotRenderer } from './RobotRenderer'
import { GridRenderer } from './GridRenderer'
import { ObstacleRenderer } from './ObstacleRenderer'
import { WaypointRenderer } from './WaypointRenderer'
import { LidarRenderer } from './LidarRenderer'
import { PathRenderer } from './PathRenderer'

export function SimulatorView() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  
  const { states, collisions, lidar, selectedRobot } = useSimulatorStore()
  const { showGrid, showLidar, showPaths, showWaypoints, theme: _theme } = useUIStore()

  // Camera state
  const cameraRef = useRef(new Camera2D())
  const [camera, _setCamera] = useState(cameraRef.current)

  // Renderers
    const robotRendererRef = useRef(new RobotRenderer())
    const gridRendererRef = useRef(new GridRenderer())
    const obstacleRendererRef = useRef(new ObstacleRenderer())
    const waypointRendererRef = useRef(new WaypointRenderer())
    const lidarRendererRef = useRef(new LidarRenderer())
    const pathRendererRef = useRef(new PathRenderer())

  // Handle resize
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect()
      if (rect) {
        canvas.width = rect.width * window.devicePixelRatio
        canvas.height = rect.height * window.devicePixelRatio
        canvas.style.width = `${rect.width}px`
        canvas.style.height = `${rect.height}px`
        setSize({ width: canvas.width, height: canvas.height })
        camera.resize(rect.width, rect.height)
      }
    }

    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [camera])

  // Mouse interaction
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    let isDragging = false
    let lastPos = { x: 0, y: 0 }

    const onMouseDown = (e: React.MouseEvent) => {
      if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
        isDragging = true
        lastPos = { x: e.clientX, y: e.clientY }
        canvas.style.cursor = 'grabbing'
      }
    }

    const onMouseMove = (e: React.MouseEvent) => {
      if (isDragging) {
        const dx = e.clientX - lastPos.x
        const dy = e.clientY - lastPos.y
        camera.pan(dx, dy)
        lastPos = { x: e.clientX, y: e.clientY }
      }
    }

    const onMouseUp = () => {
      isDragging = false
      canvas.style.cursor = ''
    }

    const onWheel = (e: React.WheelEvent) => {
      e.preventDefault()
      const rect = canvas.getBoundingClientRect()
      const mouseX = e.clientX - rect.left
      const mouseY = e.clientY - rect.top
      camera.zoomAt(mouseX, mouseY, e.deltaY > 0 ? -1 : 1)
    }

    canvas.addEventListener('mousedown', onMouseDown as any)
    window.addEventListener('mousemove', onMouseMove as any)
    window.addEventListener('mouseup', onMouseUp)
    canvas.addEventListener('wheel', onWheel as any, { passive: false })

    return () => {
      canvas.removeEventListener('mousedown', onMouseDown as any)
      window.removeEventListener('mousemove', onMouseMove as any)
      window.removeEventListener('mouseup', onMouseUp)
      canvas.removeEventListener('wheel', onWheel as any)
    }
  }, [camera])

  // Render loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || size.width === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number

    const render = () => {
      // Clear
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.clearRect(0, 0, size.width, size.height)

      // Apply camera transform
      ctx.save()
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
      camera.apply(ctx)

      // Render layers (back to front)
      if (showGrid) gridRendererRef.current.render(ctx, camera)
      obstacleRendererRef.current.render(ctx, camera, useSimulatorStore.getState().config)
      waypointRendererRef.current.render(ctx, camera, useSimulatorStore.getState())
      pathRendererRef.current.render(ctx, camera, states, showPaths)
      
      if (showLidar) lidarRendererRef.current.render(ctx, camera, lidar)
      robotRendererRef.current.render(ctx, camera, states, collisions, selectedRobot)

      ctx.restore()

      animationId = requestAnimationFrame(render)
    }

    render()
    return () => cancelAnimationFrame(animationId)
  }, [states, collisions, lidar, selectedRobot, showGrid, showLidar, showPaths, showWaypoints, size])

  return (
    <div className="simulator-view">
      <canvas ref={canvasRef} className="simulator-canvas" />
    </div>
  )
}