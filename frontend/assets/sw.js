/* 知衡健康 service worker: offline shell only, never caches API responses. */
const CACHE = "zhiheng-shell-v51";
const SHELL = [
  "/",
  "/assets/styles.css",
  "/assets/app.js",
  "/assets/ui-core.js",
  "/assets/graph3d.js",
  "/assets/modules/deps.js",
  "/assets/modules/review.js",
  "/assets/modules/insights.js",
  "/assets/modules/knowledge.js",
  "/assets/modules/graph-view.js",
  "/assets/modules/inspector.js",
  "/assets/modules/records.js",
  "/assets/modules/lifestyle.js",
  "/assets/modules/body-map.js",
  "/assets/modules/anatomy-atlas.js",
  "/vendor/three/three.module.min.js",
  "/vendor/three/addons/controls/OrbitControls.js",
  "/vendor/three/addons/utils/BufferGeometryUtils.js",
  "/vendor/three/addons/postprocessing/EffectComposer.js",
  "/vendor/three/addons/postprocessing/Pass.js",
  "/vendor/three/addons/postprocessing/RenderPass.js",
  "/vendor/three/addons/postprocessing/ShaderPass.js",
  "/vendor/three/addons/postprocessing/MaskPass.js",
  "/vendor/three/addons/postprocessing/UnrealBloomPass.js",
  "/vendor/three/addons/postprocessing/OutputPass.js",
  "/vendor/three/addons/shaders/CopyShader.js",
  "/vendor/three/addons/shaders/LuminosityHighPassShader.js",
  "/vendor/three/addons/shaders/OutputShader.js",
  "/vendor/three/addons/libs/fflate.module.js",
  "/models/anatomy-terms-zh-auto.json",
  "/assets/icon.svg",
  "/assets/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (
    request.method !== "GET" ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/models/")
  ) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok && url.origin === self.location.origin) {
            const clone = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached || caches.match("/"));
      return cached || network;
    })
  );
});
