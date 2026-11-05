// pyodide_worker.js
// Pyodide Web Worker entry point - loads Pyodide and runs Python simulation

import * as pyodide from 'pyodide';

// Global state
let pyodideInstance = null;
let webSimulator = null;
let pendingRequests = new Map();
let requestId = 0;

// Load Pyodide from CDN
async function loadPyodide() {
  if (pyodideInstance) return pyodideInstance;

  console.log('[PyodideWorker] Loading Pyodide...');
  pyodideInstance = await pyodide.loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.1/full/",
    stdout: (msg) => postMessage({ type: 'pyodide_stdout', data: msg }),
    stderr: (msg) => postMessage({ type: 'pyodide_stderr', data: msg }),
  });

  // Install required packages
  console.log('[PyodideWorker] Installing packages...');
  await pyodideInstance.loadPackage(['numpy', 'pyyaml', 'scipy']);
  console.log('[PyodideWorker] Packages installed');

  // Load our simulation code
  await loadSimulationCode();

  return pyodideInstance;
}

async function loadSimulationCode() {
  // The simulation code will be injected here at build time
  // For now, we'll load it from a module
  try {
    const response = await fetch('web_simulator.py');
    const simCode = await response.text();
    
    await pyodideInstance.runPythonAsync(simCode);
    console.log('[PyodideWorker] Simulation code loaded');
  } catch (e) {
    console.error('[PyodideWorker] Failed to load simulation code:', e);
    throw e;
  }
}

// Handle messages from main thread
self.onmessage = async (event) => {
  const msg = event.data;
  const id = msg.id;

  if (!pyodideInstance) {
    await loadPyodide();
  }

  let result;

  try {
    switch (msg.type) {
      case 'init': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
result = sim.init(${JSON.stringify(msg.config)}, ${JSON.stringify(msg.user_code)})
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'step': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
result = sim.step(${msg.dt}, ${JSON.stringify(msg.commands || {})})
json.dumps(result)
        `);
        result = JSON.parse(result);
        
        // Also send state update broadcast
        if (result.success && result.states) {
          self.postMessage({ type: 'state_update', data: result });
        }
        break;
      }

      case 'set_waypoints': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
result = sim.set_waypoints(${msg.robot_id}, ${JSON.stringify(msg.waypoints)})
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'add_obstacle': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
result = sim.add_obstacle(${msg.x}, ${msg.y}, ${msg.radius})
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'load_map': {
        // Write image bytes to virtual filesystem
        const imageBytes = new Uint8Array(msg.image_bytes);
        pyodideInstance.FS.writeFile('/tmp/map.png', imageBytes);
        
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
with open('/tmp/map.png', 'rb') as f:
    img_bytes = f.read()
result = sim.load_occupancy_map(list(img_bytes), ${msg.resolution})
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'load_line_map': {
        const imageBytes = new Uint8Array(msg.image_bytes);
        pyodideInstance.FS.writeFile('/tmp/track.png', imageBytes);
        
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
with open('/tmp/track.png', 'rb') as f:
    img_bytes = f.read()
result = sim.load_line_map(list(img_bytes), ${msg.resolution})
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'reset': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
result = sim.reset()
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'export_log': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
result = sim.export_log("${msg.format || 'pkl'}")
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      case 'update_config': {
        result = await pyodideInstance.runPythonAsync(`
import json
sim = get_simulator()
if sim.core and sim.core.config:
    import copy
    sim.core.config = {**sim.core.config, **${JSON.stringify(msg.config || {})}}
result = {"success": True}
json.dumps(result)
        `);
        result = JSON.parse(result);
        break;
      }

      default:
        result = { success: false, error: 'Unknown message type: ' + msg.type };
    }

    // Send response for request-response pattern
    if (id !== undefined) {
      self.postMessage({ ...result, id });
    }

  } catch (error) {
    const errorResult = { 
      success: false, 
      error: error.message, 
      type: error.name,
      traceback: error.stack
    };
    if (id !== undefined) {
      self.postMessage({ ...errorResult, id });
    } else {
      self.postMessage({ type: 'error', data: errorResult });
    }
  }
};

// Signal ready
self.postMessage({ type: 'worker_ready' });