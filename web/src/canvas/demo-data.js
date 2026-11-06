// Demo scene and frame generator covering all robot types, used for visual checks.

const TYPES = [
  { type: 'differential', radius: 0.22, color: [30, 144, 255] },
  { type: 'differential_firstorder', radius: 0.22, color: [0, 180, 160] },
  { type: 'holonomic', radius: 0.25, color: [240, 140, 40] },
  { type: 'hexagonal_holonomic', radius: 0.3, length: 0.5, width: 0.5, color: [170, 90, 230] },
  { type: 'hexagonal_holonomic_line_follower', radius: 0.3, length: 0.5, width: 0.5, color: [230, 80, 140] },
  { type: 'ackermann', radius: 0.5, length: 0.9, width: 0.5, wheel_base: 0.6, color: [220, 60, 60] },
  { type: 'boat', radius: 0.45, color: [60, 190, 90] },
  { type: 'line_follower', radius: 0.2, length: 0.3, width: 0.22, color: [250, 200, 40] },
];

function tinyPng() {
  // 8x4 checker-ish occupancy sample: top row = highest y. Black block on the top-left only.
  // Built at runtime with a canvas when available.
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas');
  c.width = 40;
  c.height = 24;
  const g = c.getContext('2d');
  g.fillStyle = '#fff';
  g.fillRect(0, 0, 40, 24);
  g.fillStyle = '#000';
  g.fillRect(0, 0, 14, 3); // top-left wall: must appear at the top-left of the world
  g.fillRect(36, 0, 4, 24);
  return c.toDataURL('image/png').split(',')[1];
}

export function makeDemoScene({ theme = 'dark', withMap = false } = {}) {
  const colors = theme === 'dark'
    ? { background: [18, 21, 28], grid: [40, 44, 54], robot: [30, 144, 255], obstacle: [0, 100, 0], waypoint: [180, 150, 0], goal: [140, 0, 255], path: [30, 144, 255], lidar: [0, 150, 150], red: [200, 0, 0] }
    : { background: [240, 240, 240], grid: [220, 220, 220], robot: [30, 144, 255], obstacle: [0, 100, 0], waypoint: [180, 150, 0], goal: [140, 0, 255], path: [30, 144, 255], lidar: [0, 150, 150], red: [200, 0, 0] };
  const png = withMap ? tinyPng() : null;
  return {
    version: 1,
    title: 'demo',
    world: { width: 20, height: 12, grid_size: 1, show_origin: true, show_axes: true },
    colors,
    theme,
    robots: TYPES.map((t, i) => ({
      id: 'R' + i,
      type: t.type,
      radius: t.radius,
      length: t.length || t.radius * 2,
      width: t.width || t.radius * 1.4,
      wheel_base: t.wheel_base || 0,
      color: t.color,
      max_speed: 1,
      max_omega: 2,
      max_steer: 0.6,
      num_sensors: 5,
    })),
    map: null,
    lineMap: png ? { png_b64: png, width_m: 20, height_m: 12, resolution: 0.5 } : null,
    lidar: { enabled: true, num_rays: 24, range: 3, fov_deg: 360 },
    noise: { enabled: false, sigma_v: 0, sigma_omega: 0 },
    interaction: { collision_policy: 'stop', robot_collision: true, comm_radius: 5, show_robot_links: true },
    waypoints_cfg: { goal_tolerance: 0.3, define_orientation: true, show_tolerance_circle: true },
    params: {},
    autostart: false,
  };
}

// t in seconds. Returns a frame matching the documented schema.
export function makeDemoFrame(scene, t = 0, { running = true, full = true } = {}) {
  const n = scene.robots.length;
  const robots = scene.robots.map((spec, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = 3 + col * 4.2 + 0.4 * Math.sin(t + i);
    const y = 3 + row * 5 + 0.3 * Math.cos(t + i);
    const theta = 0.5 + i * 0.6 + 0.2 * t;
    const cs = Math.cos(theta);
    const sn = Math.sin(theta);
    const lidar = [];
    for (let k = 0; k < 24; k++) {
      const a = (k / 24) * Math.PI * 2 + theta;
      const d = 1.2 + 1.2 * Math.abs(Math.sin(k * 0.7 + i));
      lidar.push([x + Math.cos(a) * d, y + Math.sin(a) * d]);
    }
    const extra = {};
    if (spec.type === 'ackermann' || spec.type === 'boat') extra.steer = 0.4;
    if (spec.type.startsWith('hexagonal')) extra.wheel_speeds = [0.8, -0.4, 0.2];
    if (spec.type === 'line_follower' || spec.type === 'hexagonal_holonomic_line_follower') {
      const half = spec.length / 2;
      extra.sensors = [];
      for (let k = 0; k < 5; k++) {
        const lx = half * 0.9;
        const ly = (k - 2) * spec.width * 0.2;
        extra.sensors.push({ x: x + lx * cs - ly * sn, y: y + lx * sn + ly * cs, value: k === 2 || k === 3 ? 1 : k * 0.1, on: k === 2 });
      }
    }
    return {
      id: spec.id,
      x, y, theta, v: 0.5, omega: 0.1,
      battery: 1 - i * 0.12, battery_enabled: i % 2 === 0, charging: i === 2, collision: false,
      path_epoch: 0,
      goal: null, wp_index: 1, wp_total: 3,
      lidar: i === 0 || i === 3 ? lidar : null,
      extra,
    };
  });
  const frame = { t, step: Math.round(t * 50), running, selected: 3, speed: 1, realtime_factor: 1, robots, collisions_total: 0, links: [[0, 1], [1, 2]] };
  if (full) {
    frame.wp_version = 1;
    frame.waypoints = scene.robots.map((_, i) => (i === 0 ? [[2, 8, null], [6, 9.5, Math.PI / 4], [10, 8, 0]] : i === 3 ? [[14, 9, 1.2], [17, 6]] : []));
    frame.obstacles_version = 1;
    frame.obstacles = [[10, 5.5, 0.6], [16, 4.5, 0.4], [4, 10, 0.3]];
    frame.recharge = [[18, 1.5], [1.5, 11]];
    frame.overlay = [
      { k: 'line', p: [[1, 1], [5, 2]], c: [255, 120, 0], w: 2 },
      { k: 'circle', p: [10, 2], r: 0.8, c: [255, 0, 200], w: 2 },
      { k: 'poly', p: [[12, 1], [14, 1.5], [13, 2.6]], c: [0, 200, 255], w: 2 },
    ];
  }
  return frame;
}
