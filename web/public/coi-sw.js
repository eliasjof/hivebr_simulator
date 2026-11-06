/* Enables cross-origin isolation on static hosts that cannot set COOP/COEP.
 * Loaded as a classic script by the page and as a service worker script. */
if (typeof window === 'undefined') {
  // ---- service worker context ----
  self.addEventListener('install', () => self.skipWaiting())
  self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()))
  self.addEventListener('message', (e) => {
    if (e.data && e.data.type === 'deregister') {
      self.registration.unregister().then(() => self.clients.matchAll()).then((cs) => cs.forEach((c) => c.navigate(c.url)))
    }
  })
  self.addEventListener('fetch', (e) => {
    const r = e.request
    if (r.cache === 'only-if-cached' && r.mode !== 'same-origin') return
    e.respondWith(
      fetch(r)
        .then((res) => {
          if (res.status === 0 || res.type === 'opaque') return res
          const h = new Headers(res.headers)
          h.set('Cross-Origin-Embedder-Policy', 'require-corp')
          h.set('Cross-Origin-Opener-Policy', 'same-origin')
          h.set('Cross-Origin-Resource-Policy', 'cross-origin')
          return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h })
        })
        .catch((err) => { console.error('coi-sw fetch failed', err); return Response.error() }),
    )
  })
} else if (!window.crossOriginIsolated && window.isSecureContext && 'serviceWorker' in navigator) {
  // ---- page context ----
  const key = 'hivebr-coi-reloaded'
  const script = document.currentScript && document.currentScript.src
  if (script && !sessionStorage.getItem(key)) {
    navigator.serviceWorker.register(script).then(
      (reg) => {
        const reload = () => { sessionStorage.setItem(key, '1'); window.location.reload() }
        if (reg.active && !navigator.serviceWorker.controller) {
          reload()
        } else {
          reg.addEventListener('updatefound', () => {
            const w = reg.installing
            if (w) w.addEventListener('statechange', () => { if (w.state === 'activated') reload() })
          })
          if (!reg.installing && !reg.waiting && !reg.active) return
          if (reg.installing) {
            reg.installing.addEventListener('statechange', function () { if (this.state === 'activated') reload() })
          }
        }
      },
      (err) => console.warn('coi-sw registration failed', err),
    )
  }
}
