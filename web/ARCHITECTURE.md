# hiveBr Web — arquitetura

Versão do hiveBr que roda 100% no navegador. O usuário escreve Python que importa
`hivebr`; o código é interpretado no cliente (Pyodide/WebAssembly) e controla os
robôs, desenhados em canvas 2D por uma interface Vue 3.

## Princípios

1. **`src/hivebr` não é alterado nem copiado.** O pacote real é empacotado e
   executado no Pyodide: física, LiDAR, waypoints, colisão e logger são os mesmos
   do desktop. Só a camada pygame é substituída, por *stubs* em `web/python/`.
2. **Mesma semântica do desktop.** `sim.run()` / `exp.run()` bloqueiam até a
   simulação parar, e o código depois deles executa em seguida. Os exemplos de
   `examples/` rodam sem modificação.
3. **Nenhum servidor.** Site estático; Pyodide e wheels vêm do CDN jsDelivr.

## Visão geral

```
Thread principal (Vue)                      Web Worker (sim.worker.js)
┌───────────────────────────┐   postMessage ┌─────────────────────────────────┐
│ App.vue, janelas, editor  │ ◀──────────── │ Pyodide                         │
│ SimCanvas + renderer      │ scene/frame/… │  runner.py → código do usuário  │
│ store.js                  │               │   └ BrowserSimulator.step()     │
│ client.js ────────────────┼─ SAB (ring) ─▶│      host.poll() / host.sleep() │
└───────────────────────────┘ comandos UI   └─────────────────────────────────┘
```

Enquanto o Python executa, o worker está bloqueado e não processa `onmessage`.
Por isso os comandos durante a simulação passam por um `SharedArrayBuffer`
(exige `crossOriginIsolated`; ver `public/coi-sw.js`).

## Estrutura e responsáveis por área

```
web/
  package.json  vite.config.js  index.html  .gitignore        (runtime)
  public/coi-sw.js                                            (runtime)
  scripts/bundle-python.mjs   → gera public/hivebr-py.zip     (runtime)
  python/                                                     (python)
    pygame/__init__.py  pygame_gui/__init__.py  tkinter/__init__.py
    hivebr_web/__init__.py  host.py  simulator.py  serialize.py  commands.py  runner.py
    tests/
  templates/*.py   exemplos pensados para o navegador         (catalog)
  src/
    runtime/  ring.js  sim.worker.js  client.js               (runtime)
    canvas/   camera.js  renderer.js  robots.js  SimCanvas.vue (canvas)
    state/store.js                                            (ui)
    components/ ...                                           (ui)
    examples/catalog.js                                       (catalog)
    App.vue  main.js  styles.css                              (ui)
  tests/  e2e                                                 (integração)
```

## Sistema de arquivos no Pyodide

`hivebr-py.zip` é extraído em `/hivebr`:

```
/hivebr/src/hivebr/...      cópia de src/hivebr (sem explosion.png/recharge_place.png)
/hivebr/config/...          cópia de config/
/hivebr/examples/...        cópia de examples/
/hivebr/templates/...       cópia de web/templates/
/hivebr/web/pygame, pygame_gui, tkinter, hivebr_web   cópia de web/python/
```

`sys.path` recebe `/hivebr/web`, `/hivebr/src`, `/hivebr`. CWD é `/hivebr`. O código
do usuário é executado com `__name__ == "__main__"`,
`__file__ == "/hivebr/examples/user_script.py"` e `sys.argv == ["user_script.py"]`, para
que `Path(__file__).resolve().parent.parent` aponte para `/hivebr`.

## Interface `host` (Python ↔ JS)

`hivebr_web.host` guarda um objeto definido por `set_host(obj)`. No navegador é um
objeto JS do worker; nos testes, um fake Python. Métodos:

| método | descrição |
|---|---|
| `post(type: str, json_payload: str)` | envia mensagem à UI (`postMessage`) |
| `poll() -> str \| None` | próximo comando JSON da UI, ou `None` |
| `sleep(ms: float)` | dorme até `ms` ou até chegar comando (`Atomics.wait`) |
| `now() -> float` | relógio em ms (`performance.now()`) |

## Mensagens Python → UI

Worker encaminha como `{type, payload}` com `payload` sendo o **objeto já
parseado** em `client.js`. Floats arredondados a 4 casas.

- `scene` — ao criar simulador e quando cena estática mudar (`version` incrementa):
  ```js
  { version, title,
    world: { width, height, grid_size, show_origin, show_axes },
    colors: {...},                 // config["colors"] do engine
    theme: "dark"|"light",
    robots: [{ id, type, radius, length, width, wheel_base, color:[r,g,b],
               max_speed, max_omega, max_steer, num_sensors }],
    map:     { kind:"occupancy", png_b64, width_m, height_m, resolution } | null,
    lineMap: { png_b64, width_m, height_m, resolution } | null,
    // PNGs: primeira linha da imagem = maior y do mundo. Origem do retângulo em (0,0).
    lidar: { enabled, num_rays, range, fov_deg },
    noise: { enabled, sigma_v, sigma_omega },
    interaction: { collision_policy, robot_collision, comm_radius, show_robot_links },
    waypoints_cfg: { goal_tolerance, define_orientation, show_tolerance_circle },
    params: { max_speed, max_omega, max_steer, grid_size, noise_sigma, servo_max_speed },
    autostart: bool }
  ```
- `frame` — no máximo 60 Hz, e só quando algo mudou:
  ```js
  { t, step, running, selected, speed, realtime_factor,
    robots: [{ id, x, y, theta, v, omega, battery, battery_enabled, charging, collision,
               path_epoch,          // incrementa quando o path é limpo; UI zera o rastro
               goal: [x,y,th?]|null, wp_index, wp_total,
               lidar: [[x,y], ...] | null,  // pontos de impacto, se LiDAR ligado
               extra: { /* só o que o tipo tiver */
                 steer, wheel_speeds:[...],
                 sensors:[{x,y,value,on}], line_error, line_lost,
                 lap_count, lap_times, best_lap, finished, finish_time } }],
    wp_version,                     // muda quando waypoints mudam
    waypoints: [[[x,y,th?],...], ...] | undefined,  // só quando wp_version muda
    obstacles_version,
    obstacles: [[x,y,r],...] | undefined,           // só quando muda
    recharge:  [[x,y],...]   | undefined,           // junto com obstacles
    links: [[i,j],...] | undefined,                 // se show_robot_links
    overlay: [ {k:"line",p:[[x,y],[x,y]],c:[r,g,b],w},
               {k:"circle",p:[x,y],r,c,w},
               {k:"poly",p:[[x,y],...],c,w} ] | undefined,  // draw_callback, em metros
    collisions_total }
  ```
- `log_data` — resposta a `get_log` ou `logger.plot()`:
  `{ open: bool, robots: [{ id, type, color, t:[], x:[], y:[], theta:[], v:[], omega:[], v_cmd:[], omega_cmd:[], err_pos:[], err_theta:[], segments:[] }], collisions: [str] }`.
- `file` — download gerado: `{ name, mime, b64 }`.
- `figure` — `plt.show()`/`savefig` capturado: `{ title, png_b64 }`.
- `notice` — aviso para a UI: `{ level: "info"|"warn"|"error", text }`.

O worker também emite (fora do Python):
- `boot` `{ stage, progress(0..1), text }` (mensagens do carregamento de pacotes vão só para `boot`, nunca para stdout; ao iniciar uma execução o worker emite `stage: "done"`), `ready` `{ pyodide_version, interactive }`
- `stdout` `{ text }`, `stderr` `{ text }` (por linha)
- `run_started` `{ }`
- `finished` `{ ok, stopped, error: { type, message, traceback, line } | null, files: [{path,size}] }`

## Comandos UI → Python (JSON no ring, campo `cmd`)

`start` · `pause` · `toggle` · `step_once` · `reset` · `stop`
`set_speed {factor}` (0 = máximo) · `select_robot {index}`
`add_waypoint {robot,x,y,theta?}` · `clear_waypoints {robot?}` · `remove_waypoint {robot,index}`
`add_obstacle {x,y,r}` · `remove_obstacle {index}` · `clear_obstacles`
`add_recharge {x,y}` · `remove_recharge {index}` · `clear_path {robot?}`
`set_pose {robot,x,y,theta}`
`set_param {name,value}` — `max_speed|max_omega|max_steer|grid_size|noise_sigma|servo_max_speed|goal_tolerance`
`toggle_lidar` · `toggle_noise`
`load_map {name,b64,resolution,kind?}` (`kind`: `occupancy` (padrão) ou `line` → `world.load_line_map`) · `clear_map` (remove mapa de ocupação e pista)
`track_apply {strokes:[[[x,y],...],...]}` · `track_clear` · `track_export`
`save_config` → `file` yaml
`export_log {format:"csv"|"pkl"}` → `file` · `get_log {open}` → `log_data` · `reset_logger`
`refresh` → força `scene` + `frame` completos

## Mensagens UI → worker (fora de execução, `postMessage`)

`init { zipUrl, sab: {ring, control, interrupt}|null, pyodideUrl }` · `run { code, autostart }` ·
`read_file { id, path }` → `file_content { id, b64 }`.

## Parada em três níveis (`client.stop()`)

1. comando `stop` → `sim.running = False`; `run()` retorna e o resto do script executa;
2. sem `finished` após 1,5 s → grava `2` no interrupt buffer (`KeyboardInterrupt`);
3. sem `finished` após mais 1,5 s → `worker.terminate()` e novo boot, com aviso.

## Fallback sem `crossOriginIsolated`

Sem SAB: `poll()` retorna `None`, `sleep` faz espera ativa curta, `ready.interactive=false`.
A UI mostra um aviso, a simulação executa, e Parar usa `terminate()`.
