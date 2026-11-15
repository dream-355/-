import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { gunzipSync } from "three/addons/libs/fflate.module.js";

const SYSTEM_META = {
  skeletal: { label: "骨骼", color: "#b8d8ff" },
  skull: { label: "颅面骨", color: "#d7e8ff" },
  muscular: { label: "肌肉", color: "#c77d8a" },
  cardiac: { label: "心脏", color: "#ff7185" },
  sensory: { label: "感觉器官", color: "#8edceb" },
  arterial: { label: "动脉", color: "#ff5b6d" },
  venous: { label: "静脉", color: "#4b8cff" },
  nervous: { label: "神经系统", color: "#f1cf6e" },
  brain: { label: "脑区", color: "#b9a0ff" },
  respiratory: { label: "呼吸系统", color: "#4ba4c4" },
  digestive: { label: "消化系统", color: "#e9b96e" },
  urinary: { label: "泌尿系统", color: "#ef9c6c" },
  lymphatic: { label: "淋巴系统", color: "#88d49a" },
  endocrine: { label: "内分泌系统", color: "#e5a6d9" },
  reproductive: { label: "生殖系统", color: "#e39cb7" },
  pregnancy: { label: "孕期结构（参考）", color: "#e5a1bd" },
  integumentary: { label: "体表", color: "#68dce5" },
  borrowed: { label: "参考骨骼（男性来源）", color: "#8f9aa8" },
  "donor-muscle": { label: "供体腿部肌肉（女性来源）", color: "#ba7f82" },
  connective: { label: "结缔组织", color: "#a7c6c0" },
};

const DEFAULT_VISIBLE = [
  "integumentary",
  "skeletal",
  "skull",
  "respiratory",
  "digestive",
  "urinary",
  "cardiac",
  "endocrine",
  "lymphatic",
];

const SYSTEM_PRIORITY = {
  respiratory: 0,
  digestive: 1,
  urinary: 3,
  cardiac: 4,
  endocrine: 5,
  reproductive: 6,
  sensory: 7,
  brain: 8,
  nervous: 9,
  skeletal: 10,
  skull: 11,
  connective: 12,
  lymphatic: 13,
  arterial: 14,
  venous: 15,
  integumentary: 16,
  muscular: 17,
  "donor-muscle": 18,
  pregnancy: 19,
  borrowed: 20,
};

const MANIFESTS = {
  male: "/models/atlas.json",
  female: "/models/atlas-female.json",
};
const DATA_VERSION = "20261106-29";

const SOURCE = {
  male: "成年男性三维参考解剖",
  female: "成年女性三维参考解剖",
};

const ZH_OVERRIDES = {
  uterus: "子宫",
  cervix: "子宫颈",
  vagina: "阴道",
  "left ovary": "左侧卵巢",
  "right ovary": "右侧卵巢",
  ovary: "卵巢",
  "left fallopian tube": "左侧输卵管",
  "right fallopian tube": "右侧输卵管",
  "fallopian tube": "输卵管",
  "uterine tube": "输卵管",
  "ampulla of uterine tube": "输卵管壶腹部",
  "fimbriae of uterine tube": "输卵管伞",
  "isthmus of fallopian tube": "输卵管峡部",
  "uterine tube infundibulum": "输卵管漏斗部",
  "abdominal ostium of uterine tube": "输卵管腹腔口",
  "anterior wall of uterus": "子宫前壁",
  "posterior wall of uterus": "子宫后壁",
  "body of uterus": "子宫体",
  "fundus of uterus": "子宫底",
  "lower uterine segment": "子宫下段",
  cornua: "子宫角",
  "internal cervical os": "子宫颈内口",
  "external cervical os": "子宫颈外口",
  "cervicovaginal junction": "子宫颈阴道交界",
  "left round ligament of uterus": "左侧子宫圆韧带",
  "right round ligament of uterus": "右侧子宫圆韧带",
  "left cardinal ligament of uterus": "左侧子宫主韧带",
  "right cardinal ligament of uterus": "右侧子宫主韧带",
  "left uterosacral ligament": "左侧子宫骶韧带",
  "right uterosacral ligament": "右侧子宫骶韧带",
  "left uterine artery": "左侧子宫动脉",
  "right uterine artery": "右侧子宫动脉",
  "left uterine vein": "左侧子宫静脉",
  "right uterine vein": "右侧子宫静脉",
  "mesovarium (left)": "左侧卵巢系膜",
  "mesovarium (right)": "右侧卵巢系膜",
  "ovarian ligament (left)": "左侧卵巢固有韧带",
  "ovarian ligament (right)": "右侧卵巢固有韧带",
  "suspensory ligament of ovary (left)": "左侧卵巢悬韧带",
  "suspensory ligament of ovary (right)": "右侧卵巢悬韧带",
  "mammary lobes (left)": "左侧乳腺叶",
  "mammary lobes (right)": "右侧乳腺叶",
  "mammary gland": "乳腺",
  "placenta vessels": "胎盘血管",
  "umbilical cord": "脐带",
  "umbilical artery": "脐动脉",
  "umbilical vein": "脐静脉",
  "uterovesical pouch": "膀胱子宫陷凹",
  omentum: "大网膜",
  "epiploic appendage of transverse colon": "横结肠脂肪垂",
  "duodenum horizontal": "十二指肠水平部",
  "ileum terminal": "回肠末端",
  "hepatic flexure of colon": "结肠肝曲",
  "splenic flexure of colon": "结肠脾曲",
  "vermiform appendix": "阑尾",
  "marginal artery of drummond": "德拉蒙德边缘动脉",
  "perirhinal gyrus rostral part of fugt (left)": "鼻周回吻侧部（左）",
  "perirhinal gyrus rostral part of fugt (right)": "鼻周回吻侧部（右）",
  "schlemm's canal (left)": "施莱姆管（左）",
  "schlemm's canal (right)": "施莱姆管（右）",
  "transverse temporal gyrus heschls gyrus (left)": "赫施尔颞横回（左）",
  "transverse temporal gyrus heschls gyrus (right)": "赫施尔颞横回（右）",
  prostate: "前列腺",
  "prostate gland": "前列腺",
  testis: "睾丸",
  "left testis": "左侧睾丸",
  "right testis": "右侧睾丸",
  vagina: "阴道",
};

function hasChinese(text) {
  return /[\u3400-\u9fff]/u.test(String(text || ""));
}

function pointerTap(distance, threshold) {
  return Number.isFinite(distance) && distance <= threshold;
}

export class AnatomyAtlasViewer {
  constructor(canvas, callbacks = {}) {
    this.canvas = canvas;
    this.canvas._anatomyViewer = this;
    this.callbacks = callbacks;
    this.sex = "male";
    this.ready = false;
    this.loading = false;
    this.selectionMode = "orbit";
    this.depth = 0;
    this.throatMode = false;
    this.zoom = 1;
    this.defaultDistance = 2.5;
    this.modelCenter = new THREE.Vector3(0, 0.84, 0);
    this.modelRadius = 0.9;
    this.bodyScale = new THREE.Vector3(1, 1, 1);
    this.visibleSystems = new Set(DEFAULT_VISIBLE);
    this.selectedIds = [];
    this.isolated = false;
    this.disposables = [];
    this.meshes = [];
    this.pointClouds = [];
    this.pickers = [];
    this.pointerState = null;
    this.modelDragState = null;
    this.viewOffsetX = 0;
    this.viewOffsetY = 0;
    this.generation = 0;
    this.abortController = null;
    this.translations = {};
    this.lastFrame = 0;
    this.lastHoverAt = 0;
    this.hoverTimer = null;

    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    this.renderer.setClearColor(0x020a17, 1);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.92;
    this.renderer.localClippingEnabled = true;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x020a17);
    this.scene.fog = new THREE.FogExp2(0x020a17, 0.055);
    this.camera = new THREE.PerspectiveCamera(34, 1, 0.005, 40);
    this.camera.position.set(0, 1.02, 3);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.set(0, 0.86, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.09;
    this.controls.enableZoom = false;
    this.controls.enablePan = false;
    this.controls.zoomToCursor = false;
    this.controls.rotateSpeed = 0.72;
    this.controls.minDistance = 1;
    this.controls.maxDistance = 8.6;
    this.controls.minPolarAngle = 0;
    this.controls.maxPolarAngle = Math.PI;
    this.controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    this.controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
    this.controls.mouseButtons.RIGHT = -1;
    this.controls.touches.ONE = THREE.TOUCH.ROTATE;
    this.controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
    this.controls.addEventListener("change", () => {
      this.dirty = true;
    });

    this.scene.add(new THREE.HemisphereLight(0xbdefff, 0x071326, 0.95));
    const keyLight = new THREE.DirectionalLight(0xc4f8ff, 1.6);
    keyLight.position.set(-2.2, 3.8, 3.4);
    this.scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0x278fff, 1.35);
    rimLight.position.set(2.4, 1.8, -3);
    this.scene.add(rimLight);

    this.composer = new EffectComposer(this.renderer);
    this.renderPass = new RenderPass(this.scene, this.camera);
    this.bloomPass = new UnrealBloomPass(
      new THREE.Vector2(1, 1),
      0.44,
      0.34,
      0.76,
    );
    this.outputPass = new OutputPass();
    this.composer.addPass(this.renderPass);
    this.composer.addPass(this.bloomPass);
    this.composer.addPass(this.outputPass);

    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.buildAtmosphere();
    this.bindEvents();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    this.resize();
    this.termPromise = this.loadTranslationTerms();
    this.setSex("male");
    this.animate();
  }

  async loadTranslationTerms() {
    try {
      const responses = await Promise.all([
        fetch(`/models/anatomy-terms-zh.json?v=${DATA_VERSION}`),
        fetch(`/models/anatomy-terms-zh-auto.json?v=${DATA_VERSION}`),
      ]);
      const payloads = await Promise.all(
        responses.map((response) => (response.ok ? response.json() : null)),
      );
      this.translations = {
        ...(payloads[0]?.terms || {}),
        ...(payloads[1]?.terms || {}),
      };
    } catch {
      this.translations = {};
    }
  }

  buildAtmosphere() {
    const count = 540;
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const radius = 0.7 + Math.random() * 2.7;
      const angle = Math.random() * Math.PI * 2;
      positions[index * 3] = Math.cos(angle) * radius;
      positions[index * 3 + 1] = -0.15 + Math.random() * 2.3;
      positions[index * 3 + 2] = Math.sin(angle) * radius;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
      color: 0x58d9ff,
      size: 0.006,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    });
    this.atmosphere = new THREE.Points(geometry, material);
    this.scene.add(this.atmosphere);
  }

  bindEvents() {
    this.onPointerDown = (event) => {
      if (event.button !== undefined && event.button !== 0) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      this.pointerState = {
        startX: x,
        startY: y,
        x,
        y,
        moved: 0,
        pointerId: event.pointerId,
      };
      if (this.selectionMode === "box") {
        event.preventDefault();
        this.controls.enabled = false;
        this.canvas.setPointerCapture?.(event.pointerId);
        this.updateSelectionBox();
        return;
      }
      const partIndex = this.ready ? this.findPartAt(x, y, true) : -1;
      if (partIndex >= 0) {
        event.preventDefault();
        this.controls.enabled = false;
        this.canvas.setPointerCapture?.(event.pointerId);
        this.startModelDrag(event);
      } else {
        this.controls.enabled = true;
        this.controls.enableRotate = true;
      }
    };
    this.onPointerMove = (event) => {
      if (this.modelDragState) {
        if (event.pointerId !== this.modelDragState.pointerId) return;
        event.preventDefault();
        this.updateModelDrag(event);
        return;
      }
      if (!this.pointerState) {
        if (!this.ready) return;
        this.queueHover(event);
        return;
      }
      const rect = this.canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      this.pointerState.moved += Math.hypot(x - this.pointerState.x, y - this.pointerState.y);
      this.pointerState.x = x;
      this.pointerState.y = y;
      if (this.selectionMode === "box") this.updateSelectionBox();
    };
    this.onPointerUp = (event) => {
      if (!this.pointerState) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const state = this.pointerState;
      this.pointerState = null;
      if (this.canvas.hasPointerCapture?.(event.pointerId)) {
        this.canvas.releasePointerCapture(event.pointerId);
      }
      this.controls.enabled = true;
      if (this.modelDragState) {
        this.endModelDrag();
        if (pointerTap(state.moved, 6)) this.pickAt(x, y);
        return;
      }
      if (this.selectionMode === "box") {
        this.updateSelectionBox();
        const width = Math.abs(x - state.startX);
        const height = Math.abs(y - state.startY);
        this.hideSelectionBox();
        if (width > 8 && height > 8) this.selectBox(state.startX, state.startY, x, y);
        return;
      }
      if (pointerTap(state.moved, 6)) this.pickAt(x, y);
    };
    this.onPointerCancel = (event) => {
      if (this.modelDragState) this.endModelDrag();
      this.pointerState = null;
      this.controls.enabled = true;
      this.hideSelectionBox();
    };
    this.onContextMenu = (event) => event.preventDefault();
    this.onWheel = (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!this.ready) return;
      const deltaScale =
        event.deltaMode === 1
          ? 16
          : event.deltaMode === 2
            ? this.canvas.clientHeight
            : 1;
      const factor = Math.exp(
        -THREE.MathUtils.clamp(event.deltaY * deltaScale, -800, 800) * 0.00075,
      );
      this.setZoom(this.zoom * factor);
    };
    this.canvas.addEventListener("pointerdown", this.onPointerDown, {
      capture: true,
    });
    this.canvas.addEventListener("pointermove", this.onPointerMove);
    this.canvas.addEventListener("pointerup", this.onPointerUp);
    this.canvas.addEventListener("pointercancel", this.onPointerCancel);
    this.canvas.addEventListener("pointerleave", () => this.setHover(null));
    this.canvas.addEventListener("contextmenu", this.onContextMenu);
    this.canvas.addEventListener("wheel", this.onWheel, { passive: false });
  }

  startModelDrag(event) {
    this.modelDragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offsetX: this.viewOffsetX,
      offsetY: this.viewOffsetY,
    };
    this.controls.enableRotate = false;
    this.canvas.style.cursor = "grabbing";
  }

  updateModelDrag(event) {
    const x = event.clientX - this.canvas.getBoundingClientRect().left;
    const y = event.clientY - this.canvas.getBoundingClientRect().top;
    if (this.pointerState) {
      this.pointerState.moved += Math.hypot(
        x - this.pointerState.x,
        y - this.pointerState.y,
      );
      this.pointerState.x = x;
      this.pointerState.y = y;
    }
    this.viewOffsetX =
      this.modelDragState.offsetX -
      (event.clientX - this.modelDragState.startX) / this.zoom;
    this.viewOffsetY =
      this.modelDragState.offsetY -
      (event.clientY - this.modelDragState.startY) / this.zoom;
    this.applyViewProjection();
  }

  endModelDrag() {
    this.modelDragState = null;
    this.controls.enabled = true;
    this.controls.enableRotate = true;
    this.canvas.style.cursor = "grab";
  }

  applyViewProjection() {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (!width || !height) return;
    this.camera.updateProjectionMatrix();
    const projection = this.camera.projectionMatrix.elements;
    projection[8] += (2 * this.viewOffsetX * this.camera.zoom) / width;
    projection[9] -= (2 * this.viewOffsetY * this.camera.zoom) / height;
    this.camera.projectionMatrixInverse
      .copy(this.camera.projectionMatrix)
      .invert();
    this.dirty = true;
  }

  queueHover(event) {
    const now = performance.now();
    if (this.hoverTimer || now - this.lastHoverAt < 90) return;
    this.lastHoverAt = now;
    this.hoverTimer = requestAnimationFrame(() => {
      this.hoverTimer = null;
      const rect = this.canvas.getBoundingClientRect();
      const index = this.findPartAt(event.clientX - rect.left, event.clientY - rect.top, false);
      this.setHover(index);
    });
  }

  setHover(index) {
    if (!this.ready || index < 0) {
      this.canvas.style.cursor = this.selectionMode === "box" ? "crosshair" : "grab";
      this.callbacks.onHover?.(null);
      return;
    }
    this.canvas.style.cursor = "pointer";
    this.callbacks.onHover?.(this.displayPart(this.parts[index]));
  }

  updateSelectionBox() {
    const box = document.querySelector("#body-map-selection-box");
    if (!box || !this.pointerState) return;
    const x = Math.min(this.pointerState.startX, this.pointerState.x);
    const y = Math.min(this.pointerState.startY, this.pointerState.y);
    box.style.setProperty("--box-left", `${x}px`);
    box.style.setProperty("--box-top", `${y}px`);
    box.style.setProperty("--box-width", `${Math.abs(this.pointerState.x - this.pointerState.startX)}px`);
    box.style.setProperty("--box-height", `${Math.abs(this.pointerState.y - this.pointerState.startY)}px`);
    box.hidden = false;
  }

  hideSelectionBox() {
    const box = document.querySelector("#body-map-selection-box");
    if (box) box.hidden = true;
  }

  async setSex(sex) {
    if (!MANIFESTS[sex] || (this.loading && this.sex === sex)) return;
    this.sex = sex;
    this.generation += 1;
    const generation = this.generation;
    this.abortController?.abort();
    this.abortController = new AbortController();
    this.clearAtlas();
    this.loading = true;
    this.ready = false;
    this.callbacks.onLoading?.(1, `正在载入${sex === "female" ? "女性" : "男性"}解剖数据`);
    try {
      const response = await fetch(`${MANIFESTS[sex]}?v=${DATA_VERSION}`, {
        signal: this.abortController.signal,
      });
      if (!response.ok) throw new Error("解剖目录载入失败");
      const manifest = await response.json();
      await this.termPromise;
      if (generation !== this.generation) return;
      this.manifest = manifest;
      this.parts = manifest.parts;
      this.concepts = manifest.concepts;
      this.chunks = manifest.chunks;
      this.bodyScale.fromArray(manifest.bodyScale || [1, 1, 1]);
      this.root.scale.copy(this.bodyScale);
      this.width = THREE.MathUtils.ceilPowerOfTwo(this.parts.length);
      this.stateData = new Float32Array(this.width * 4);
      this.selectionData = new Uint8Array(this.width * 4);
      this.partTexture = new THREE.DataTexture(
        this.stateData,
        this.width,
        1,
        THREE.RGBAFormat,
        THREE.FloatType,
      );
      this.selectionTexture = new THREE.DataTexture(
        this.selectionData,
        this.width,
        1,
        THREE.RGBAFormat,
      );
      this.partTexture.minFilter = THREE.NearestFilter;
      this.partTexture.magFilter = THREE.NearestFilter;
      this.selectionTexture.minFilter = THREE.NearestFilter;
      this.selectionTexture.magFilter = THREE.NearestFilter;
      this.partTexture.needsUpdate = true;
      this.selectionTexture.needsUpdate = true;
      this.disposables.push(this.partTexture, this.selectionTexture);
      this.bounds = this.parts.map((part) => new THREE.Box3(
        new THREE.Vector3().fromArray(part.bounds[0]).multiply(this.bodyScale),
        new THREE.Vector3().fromArray(part.bounds[1]).multiply(this.bodyScale),
      ));
      this.centers = this.bounds.map((box) => box.getCenter(new THREE.Vector3()));
      this.pickers = new Array(this.parts.length);
      this.materials = new Map();
      this.visibleSystems = new Set(DEFAULT_VISIBLE);
      this.systems = Object.keys(SYSTEM_META)
        .map((id) => ({
          id,
          ...SYSTEM_META[id],
          label:
            id === "reproductive"
              ? `${sex === "female" ? "女性" : "男性"}生殖系统`
              : SYSTEM_META[id].label,
          count: this.parts.filter((part) => part.system === id).length,
        }))
        .filter(
          (system) =>
            system.count > 0 &&
            !(sex === "female" && system.id === "borrowed"),
        );
      this.callbacks.onReady?.({
        sex,
        source: SOURCE[sex],
        partCount: this.parts.filter(
          (part) => !(sex === "female" && part.system === "borrowed"),
        ).length,
        conceptCount: this.concepts.length,
        systems: this.systems,
        visibleSystems: [...this.visibleSystems],
        totalBytes: this.chunks.reduce((total, chunk) => total + (chunk.gzipBytes || chunk.bytes), 0),
      });
      this.updateVisibility();
      this.selectedIds = [];
      this.updateSelectionTexture();
      this.fitCamera();

      let completed = 0;
      let cursor = 0;
      const workers = Array.from({ length: 3 }, async () => {
        while (cursor < this.chunks.length) {
          const chunkIndex = cursor;
          cursor += 1;
          await this.loadChunk(chunkIndex, generation);
          completed += 1;
          this.callbacks.onLoading?.(
            Math.round((completed / this.chunks.length) * 100),
            `正在解析${sex === "female" ? "女性" : "男性"}解剖结构`,
          );
        }
      });
      await Promise.all(workers);
      if (generation !== this.generation) return;
      this.loading = false;
      this.ready = true;
      this.dirty = true;
      this.callbacks.onLoading?.(100, "解剖模型已就绪");
    } catch (error) {
      if (error?.name === "AbortError") return;
      this.loading = false;
      this.callbacks.onError?.(error?.message || "三维解剖模型载入失败");
    }
  }

  async loadChunk(chunkIndex, generation) {
    const chunk = this.chunks[chunkIndex];
    const compressed = Boolean(chunk.gzip);
    const sourceUrl = `${compressed ? chunk.gzip : chunk.url}?v=${DATA_VERSION}`;
    const decode = async (bypassCache = false) => {
      const url = bypassCache
        ? `${sourceUrl}${sourceUrl.includes("?") ? "&" : "?"}retry=${Date.now()}`
        : sourceUrl;
      const response = await fetch(url, {
        signal: this.abortController.signal,
        cache: bypassCache ? "no-store" : "default",
      });
      if (!response.ok) throw new Error("解剖几何文件载入失败");
      let buffer = await response.arrayBuffer();
      const signature = new Uint8Array(buffer, 0, Math.min(2, buffer.byteLength));
      const gzip = signature[0] === 0x1f && signature[1] === 0x8b;
      if (gzip) {
        if (typeof DecompressionStream !== "undefined") {
          buffer = await new Response(
            new Blob([buffer]).stream().pipeThrough(new DecompressionStream("gzip")),
          ).arrayBuffer();
        } else {
          const decoded = gunzipSync(new Uint8Array(buffer));
          buffer = decoded.buffer.slice(decoded.byteOffset, decoded.byteOffset + decoded.byteLength);
        }
      }
      if (buffer.byteLength !== chunk.bytes) throw new Error("解剖几何文件不完整");
      return buffer;
    };
    let buffer;
    try {
      buffer = await decode(false);
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      this.callbacks.onLoading?.(
        Math.round(((chunkIndex + 1) / this.chunks.length) * 100),
        "检测到缓存不完整，正在重新载入",
      );
      buffer = await decode(true);
    }
    if (generation !== this.generation) return;

    const groups = new Map();
    const skinPieces = [];
    const breastPieces = [];
    this.parts.forEach((part, partIndex) => {
      if (part.chunk !== chunkIndex) return;
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
          new Float32Array(buffer, part.positions, part.vertexCount * 3),
          3,
        ),
      );
      geometry.setAttribute(
        "normal",
        new THREE.BufferAttribute(
          new Int16Array(buffer, part.normals, part.vertexCount * 3),
          3,
          true,
        ),
      );
      geometry.setIndex(
        new THREE.BufferAttribute(
          new Uint32Array(buffer, part.indices, part.indexCount),
          1,
        ),
      );
      geometry.boundingBox = this.bounds[partIndex].clone();
      geometry.computeBoundingSphere();
      geometry.setAttribute(
        "partIndex",
        new THREE.BufferAttribute(
          new Float32Array(part.vertexCount).fill(partIndex),
          1,
        ),
      );
      this.pickers[partIndex] = new THREE.Mesh(geometry);
      this.pickers[partIndex].scale.copy(this.bodyScale);
      this.pickers[partIndex].matrixAutoUpdate = false;
      this.pickers[partIndex].updateMatrix();
      this.pickers[partIndex].matrixWorld.copy(this.pickers[partIndex].matrix);
      this.disposables.push(geometry);
      const isSkin =
        part.name.toLowerCase() === "skin" || part.name === "皮肤";
      const isFemaleBreastSurface =
        this.sex === "female" &&
        /areol|nipple|mammary|lactiferous|fat \(|suspensory ligament/i.test(
          part.name,
        );
      if (part.system === "integumentary" && isSkin) {
        skinPieces.push(geometry);
      } else if (part.system === "integumentary" && isFemaleBreastSurface) {
        breastPieces.push(geometry);
      }
      const list = groups.get(part.system) || [];
      list.push(geometry);
      groups.set(part.system, list);
    });

    for (const [system, geometries] of groups) {
      if (generation !== this.generation) return;
      const merged = mergeGeometries(geometries, false);
      if (!merged) continue;
      this.disposables.push(merged);
      const material = this.systemMaterial(system);
      const mesh = new THREE.Mesh(merged, material);
      mesh.frustumCulled = false;
      mesh.userData.system = system;
      this.root.add(mesh);
      this.meshes.push(mesh);
      if (system === "integumentary") {
        const pointsMaterial = new THREE.ShaderMaterial({
          uniforms: {
            partState: { value: this.partTexture },
            stateWidth: { value: this.width },
            pointColor: {
              value: new THREE.Color(
                this.sex === "female"
                  ? 0x1f7f98
                  : (document.documentElement.dataset.theme === "light" ? 0x148aa3 : 0x56cbe4),
              ),
            },
            pointSize: { value: this.sex === "female" ? 0.0105 : 0.015 },
            pointOpacity: { value: this.sex === "female" ? 0.2 : 0.26 },
            chestDim: { value: this.sex === "female" ? 1 : 0 },
            femaleSkinMask: { value: this.sex === "female" ? 1 : 0 },
          },
          vertexShader: `
            attribute float partIndex;
            uniform sampler2D partState;
            uniform float stateWidth;
            uniform float pointSize;
            uniform float pointOpacity;
            uniform float chestDim;
            uniform float femaleSkinMask;
            varying float vVisible;
            varying float vAlpha;
            void main() {
              vec2 stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5);
              vec4 state = texture2D(partState, stateUv);
              vec3 transformed = position + state.xyz;
              vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.0);
              gl_PointSize = max(1.0, pointSize * (300.0 / max(0.2, -mvPosition.z)));
              gl_Position = projectionMatrix * mvPosition;
              vVisible = state.w;
              float lowerPelvis = smoothstep(0.76, 0.79, transformed.y) *
                (1.0 - smoothstep(0.88, 0.92, transformed.y));
              float centerPelvis = 1.0 - smoothstep(0.035, 0.06, abs(transformed.x));
              float frontPelvis = smoothstep(-0.005, 0.025, transformed.z);
              if (femaleSkinMask > 0.5 &&
                  lowerPelvis * centerPelvis * frontPelvis > 0.08) {
                vVisible = 0.0;
              }
              float chest = exp(-pow((transformed.y - 1.17) / 0.15, 2.0));
              vAlpha = pointOpacity * (1.0 - chest * chestDim * 0.58);
            }
          `,
          fragmentShader: `
            uniform vec3 pointColor;
            varying float vVisible;
            varying float vAlpha;
            void main() {
              if (vVisible < 0.5) discard;
              float radial = length(gl_PointCoord - vec2(0.5));
              if (radial > 0.5) discard;
              float glow = 1.0 - smoothstep(0.24, 0.5, radial);
              gl_FragColor = vec4(pointColor, vAlpha * glow);
            }
          `,
          transparent: true,
          depthWrite: false,
          blending: THREE.NormalBlending,
        });
        const pointGeometry = skinPieces.length > 1
          ? mergeGeometries(skinPieces, false)
          : (skinPieces[0] || null);
        if (pointGeometry) {
          if (pointGeometry !== skinPieces[0]) {
            this.disposables.push(pointGeometry);
          }
          const points = new THREE.Points(pointGeometry, pointsMaterial);
          points.frustumCulled = false;
          this.root.add(points);
          this.pointClouds.push(points);
        }
        this.disposables.push(pointsMaterial);
        if (breastPieces.length) {
          const breastGeometry =
            breastPieces.length > 1
              ? mergeGeometries(breastPieces, false)
              : breastPieces[0];
          if (breastGeometry) {
            const breastMaterial = pointsMaterial.clone();
            breastMaterial.uniforms = {
              ...pointsMaterial.uniforms,
              pointColor: {
                value: new THREE.Color(
                  document.documentElement.dataset.theme === "light"
                    ? 0xb6577d
                    : 0xd1789f,
                ),
              },
              pointSize: { value: 0.013 },
              pointOpacity: { value: 0.45 },
              chestDim: { value: 0 },
              femaleSkinMask: { value: 1 },
            };
            const breastPoints = new THREE.Points(
              breastGeometry,
              breastMaterial,
            );
            breastPoints.frustumCulled = false;
            breastPoints.renderOrder = 2;
            breastPoints.userData.breast = true;
            this.root.add(breastPoints);
            this.pointClouds.push(breastPoints);
            if (breastGeometry !== breastPieces[0]) {
              this.disposables.push(breastGeometry);
            }
            this.disposables.push(breastMaterial);
          }
        }
      }
    }
    this.dirty = true;
  }

  systemMaterial(system) {
    if (this.materials.has(system)) return this.materials.get(system);
    const meta = SYSTEM_META[system] || { color: "#88a9b7" };
    const color = new THREE.Color(meta.color);
    const transparent = system === "integumentary";
    const material = new THREE.MeshStandardMaterial({
      color,
      emissive: color.clone().multiplyScalar(transparent ? 0.06 : 0.1),
      emissiveIntensity: transparent ? 0.16 : 0.34,
      metalness: 0.04,
      roughness: 0.48,
      side: THREE.DoubleSide,
      transparent,
      opacity: transparent
        ? (
            this.sex === "female"
              ? (document.documentElement.dataset.theme === "light" ? 0.035 : 0.018)
              : (document.documentElement.dataset.theme === "light" ? 0.045 : 0.025)
          )
        : 0.94,
      depthWrite: !transparent,
    });
    material.onBeforeCompile = (shader) => {
      shader.uniforms.partState = { value: this.partTexture };
      shader.uniforms.selectionState = { value: this.selectionTexture };
      shader.uniforms.stateWidth = { value: this.width };
      shader.uniforms.selectionIntensity = { value: 0 };
      material.userData.shader = shader;
      shader.vertexShader =
        "attribute float partIndex;\n" +
        "uniform sampler2D partState;\n" +
        "uniform sampler2D selectionState;\n" +
        "uniform float stateWidth;\n" +
        "uniform float selectionIntensity;\n" +
        "varying float partVisible;\n" +
        "varying float partSelected;\n" +
        shader.vertexShader;
      shader.vertexShader = shader.vertexShader.replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\n" +
        "vec2 stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5);\n" +
        "vec4 state = texture2D(partState, stateUv);\n" +
        "transformed += state.xyz;\n" +
        "partVisible = state.w;\n" +
        "partSelected = texture2D(selectionState, stateUv).r;",
      );
      shader.fragmentShader =
        "varying float partVisible;\n" +
        "varying float partSelected;\n" +
        "uniform float selectionIntensity;\n" +
        shader.fragmentShader;
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <clipping_planes_fragment>",
        "#include <clipping_planes_fragment>\nif (partVisible < 0.5) discard;",
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <color_fragment>",
        "#include <color_fragment>\n" +
        "diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.24, 0.96, 1.0), partSelected * selectionIntensity);\n" +
        "diffuseColor.a = mix(diffuseColor.a, 1.0, partSelected * selectionIntensity);",
      );
    };
    this.materials.set(system, material);
    this.disposables.push(material);
    return material;
  }

  clearAtlas() {
    this.controls.enabled = true;
    this.root.scale.set(1, 1, 1);
    this.pointers = null;
    this.ready = false;
    this.hideSelectionBox();
    this.pointClouds = [];
    this.meshes = [];
    this.pickers = [];
    this.materials?.clear();
    while (this.root.children.length) this.root.remove(this.root.children[0]);
    for (const item of this.disposables) {
      if (item?.dispose) item.dispose();
    }
    this.disposables = [];
    this.partTexture = null;
    this.selectionTexture = null;
    this.parts = [];
    this.concepts = [];
    this.selectedIds = [];
    this.isolated = false;
  }

  updateVisibility() {
    if (!this.partTexture || !this.parts) return;
    const selected = new Set(this.selectedIds);
    this.parts.forEach((part, index) => {
      const isFemaleBreastSurface =
        this.sex === "female" &&
        part.system === "integumentary" &&
        /areol|nipple|mammary|lactiferous|fat \(|suspensory ligament/i.test(
          part.name,
        );
      const isBodyShell =
        part.system !== "integumentary" ||
        part.name.toLowerCase() === "skin" ||
        part.name === "皮肤" ||
        isFemaleBreastSurface;
      const visible = this.isolated
        ? selected.has(part.id)
        : this.visibleSystems.has(part.system) && isBodyShell;
      this.stateData[index * 4] = 0;
      this.stateData[index * 4 + 1] = 0;
      this.stateData[index * 4 + 2] = 0;
      this.stateData[index * 4 + 3] = visible ? 1 : 0;
    });
    this.partTexture.needsUpdate = true;
    this.pointClouds.forEach((cloud) => {
      cloud.visible = this.visibleSystems.has("integumentary") && !this.isolated;
    });
    this.dirty = true;
    this.composer?.render();
  }

  updateSelectionTexture() {
    if (!this.selectionTexture) return;
    const selected = new Set(this.selectedIds);
    this.selectionData.fill(0);
    this.parts.forEach((part, index) => {
      if (selected.has(part.id)) this.selectionData[index * 4] = 255;
    });
    this.selectionTexture.needsUpdate = true;
    const selectionIntensity = selected.size <= 12 ? 0.52 : 0.08;
    this.materials?.forEach((material) => {
      const shader = material.userData?.shader;
      if (shader?.uniforms?.selectionIntensity) {
        shader.uniforms.selectionIntensity.value = selectionIntensity;
      }
    });
    this.updateVisibility();
  }

  setThroatEmphasis(active) {
    this.throatMode = Boolean(active);
    this.materials?.forEach((material, system) => {
      const layered =
        this.throatMode && ["skeletal", "skull"].includes(system);
      material.transparent = layered || system === "integumentary";
      material.opacity = layered
        ? 0.28
        : system === "integumentary"
          ? (
              this.sex === "female"
                ? (document.documentElement.dataset.theme === "light" ? 0.035 : 0.018)
                : (document.documentElement.dataset.theme === "light" ? 0.045 : 0.025)
            )
          : 0.94;
      material.depthWrite = !material.transparent;
      material.needsUpdate = true;
    });
    this.dirty = true;
  }

  setSystemVisible(system, visible) {
    this.isolated = false;
    if (visible) this.visibleSystems.add(system);
    else this.visibleSystems.delete(system);
    this.updateVisibility();
    this.callbacks.onSystemsChange?.([...this.visibleSystems]);
  }

  setSelectionMode(mode) {
    this.selectionMode = mode === "box" ? "box" : "orbit";
    this.controls.enabled = true;
    this.canvas.style.cursor = this.selectionMode === "box" ? "crosshair" : "grab";
    this.hideSelectionBox();
  }

  setDepth(value) {
    this.depth = Math.max(0, Math.min(1, Number(value) || 0));
    const skin = this.materials?.get("integumentary");
    if (skin) {
      const baseOpacity =
        this.sex === "female"
          ? (document.documentElement.dataset.theme === "light" ? 0.035 : 0.018)
          : (document.documentElement.dataset.theme === "light" ? 0.045 : 0.025);
      skin.opacity = baseOpacity * (1 - this.depth);
      skin.depthWrite = false;
      skin.needsUpdate = true;
    }
    this.pointClouds.forEach((cloud) => {
      const base = this.sex === "female" ? 0.05 : 0.1;
      const shaderOpacity = cloud.userData?.breast
        ? 0.45
        : this.sex === "female"
          ? 0.2
          : 0.26;
      if (cloud.material?.uniforms?.pointOpacity) {
        cloud.material.uniforms.pointOpacity.value =
          shaderOpacity * (1 - this.depth);
      } else {
        cloud.material.opacity = base * (1 - this.depth);
      }
    });
    this.dirty = true;
  }

  setZoom(value) {
    this.zoom = Math.max(0.35, Math.min(5, Number(value) || 1));
    this.camera.zoom = this.zoom;
    this.applyViewProjection();
    this.controls.update();
    this.callbacks.onZoom?.(this.zoom);
    return this.zoom;
  }

  setView(view) {
    const direction = {
      front: new THREE.Vector3(0, 0.02, 1),
      back: new THREE.Vector3(0, 0.02, -1),
      side: new THREE.Vector3(1, 0.02, 0),
      threeQuarter: new THREE.Vector3(0.72, 0.04, 1).normalize(),
    }[view] || new THREE.Vector3(0.72, 0.04, 1).normalize();
    const distance = this.camera.position.distanceTo(this.controls.target);
    this.camera.position.copy(this.controls.target).addScaledVector(direction, distance);
    this.controls.update();
    this.dirty = true;
  }

  resetView() {
    this.fitCamera();
  }

  fitCamera() {
    const box = new THREE.Box3();
    this.bounds?.forEach((bounds, index) => {
      const system = this.parts[index]?.system;
      if (this.visibleSystems.has(system)) box.union(bounds);
    });
    if (box.isEmpty()) {
      const scaleY = this.bodyScale.y || 1;
      box.set(
        new THREE.Vector3(-0.85, -0.12 * scaleY, -0.35),
        new THREE.Vector3(0.85, 1.78 * scaleY, 0.35),
      );
    }
    const center = box.getCenter(new THREE.Vector3());
    const radius = Math.max(0.25, box.getBoundingSphere(new THREE.Sphere()).radius);
    const verticalFov = THREE.MathUtils.degToRad(this.camera.fov);
    const horizontalFov =
      2 * Math.atan(
        Math.tan(verticalFov / 2) * Math.max(0.65, this.camera.aspect),
      );
    const limitingFov = Math.min(verticalFov, horizontalFov);
    const distance = Math.max(
      1.2,
      (radius / Math.sin(limitingFov / 2)) * 1.08,
    );
    this.modelCenter.copy(center);
    this.modelRadius = radius;
    this.defaultDistance = distance;
    this.controls.target.copy(center);
    this.controls.minDistance = Math.max(0.12, distance / 5);
    this.controls.maxDistance = distance * 3;
    this.camera.position.set(center.x, center.y, center.z + distance);
    this.zoom = 1;
    this.camera.zoom = 1;
    this.viewOffsetX = 0;
    this.viewOffsetY = 0;
    this.applyViewProjection();
    this.callbacks.onZoom?.(1);
    this.controls.update();
    this.dirty = true;
  }

  displayName(name) {
    if (hasChinese(name)) return name;
    const key = String(name || "").toLowerCase().trim();
    return ZH_OVERRIDES[key] || this.translations[key] || name;
  }

  displayPart(part) {
    if (!part) return null;
    return {
      ...part,
      displayName: this.displayName(part.name),
      systemLabel: SYSTEM_META[part.system]?.label || part.system,
    };
  }

  search(query) {
    const q = String(query || "").trim().toLowerCase();
    if (!q || !this.concepts) return [];
    const rank = (concept) => {
      const display = this.displayName(concept.name).toLowerCase();
      if (display === q || concept.name.toLowerCase() === q) return 0;
      if (display.startsWith(q) || concept.name.toLowerCase().startsWith(q)) return 1;
      return 2;
    };
    return this.concepts
      .filter((concept) => {
        if (
          this.sex === "female" &&
          concept.elements.every((id) => {
            const part = this.parts.find((item) => item.id === id);
            return part?.system === "borrowed";
          })
        ) {
          return false;
        }
        const display = this.displayName(concept.name).toLowerCase();
        return (
          concept.name.toLowerCase().includes(q) ||
          display.includes(q) ||
          concept.id.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => rank(a) - rank(b) || a.name.length - b.name.length)
      .slice(0, 60)
      .map((concept) => ({ ...concept, displayName: this.displayName(concept.name) }));
  }

  expandThroat() {
    if (!this.ready) return;
    const chineseTerms = /[口舌腭咽喉会厌声带杓环悬雍扁桃唇颊颌牙齿涎]/u;
    const englishTerms =
      /mouth|oral|tongue|palate|tonsil|pharynx|larynx|epiglott|vocal|arytenoid|cricoid|thyroid cartilage|trachea|uvula|hyoid|buccal|lip|cheek|maxilla|mandible|jaw|salivary|submandibular|sublingual|parotid|frenulum|papill/i;
    const excluded = /bronch|lung|alveol|支气管|肺段/u;
    const allowedSystems = new Set([
      "skeletal",
      "skull",
      "muscular",
      "respiratory",
      "digestive",
      "connective",
      "arterial",
      "venous",
      "lymphatic",
    ]);
    const ids = this.parts
      .filter((part) => {
        const name = part.name;
        const isTrachea = name === "气管" || name.toLowerCase() === "trachea";
        const bounds = this.bounds[this.parts.indexOf(part)];
        const centerY = (bounds.min.y + bounds.max.y) / 2;
        const upperAirway =
          /咽|喉|会厌|声带|气管|pharynx|larynx|trachea/i.test(name);
        const confinedToHead = centerY >= 1.43 && bounds.min.y >= 1.4;
        return (
          allowedSystems.has(part.system) &&
          centerY <= 1.62 &&
          (confinedToHead || upperAirway) &&
          (chineseTerms.test(name) || englishTerms.test(name) || isTrachea) &&
          !excluded.test(name)
        );
      })
      .sort(
        (left, right) =>
          (SYSTEM_PRIORITY[left.system] ?? 99) -
            (SYSTEM_PRIORITY[right.system] ?? 99) ||
          left.name.localeCompare(right.name, "zh-CN"),
      )
      .map((part) => part.id);
    if (!ids.length) {
      this.callbacks.onError?.("当前模型没有可用的口腔与咽喉细分结构。");
      return;
    }
    this.setDepth(0.72);
    this.setView("front");
    this.selectParts(ids.slice(0, 180), "口腔与咽喉深部", {
      isolate: true,
      focus: true,
      throat: true,
    });
  }

  selectConcept(concept, options = {}) {
    if (!concept) return;
    this.selectParts(
      concept.elements,
      concept.displayName || this.displayName(concept.name),
      options,
    );
  }

  selectParts(ids, requestedLabel = "", options = {}) {
    const uniqueIds = [...new Set(ids)].filter((id) => this.parts.some((part) => part.id === id));
    if (!uniqueIds.length) return;
    this.selectedIds = uniqueIds;
    this.isolated = Boolean(options.isolate);
    this.setThroatEmphasis(Boolean(options.throat));
    this.updateSelectionTexture();
    const selected = uniqueIds
      .map((id) => this.parts.find((part) => part.id === id))
      .filter(Boolean)
      .map((part) => this.displayPart(part));
    const names = [...new Set(selected.map((part) => part.displayName).filter(Boolean))];
    this.callbacks.onSelect?.({
      sex: this.sex,
      source: SOURCE[this.sex],
      label: requestedLabel || names[0] || "解剖结构",
      names,
      parts: selected,
      systems: [...new Set(selected.map((part) => part.systemLabel))],
      isolated: this.isolated,
    });
    if (options.focus) this.focusSelection();
  }

  showContext() {
    this.isolated = false;
    this.setThroatEmphasis(false);
    this.updateVisibility();
    this.fitCamera();
  }

  focusSelection() {
    if (!this.selectedIds.length) return;
    const box = new THREE.Box3();
    this.selectedIds.forEach((id) => {
      const index = this.parts.findIndex((part) => part.id === id);
      if (index >= 0) box.union(this.bounds[index]);
    });
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    this.modelCenter.copy(center);
    this.modelRadius = Math.max(0.05, box.getBoundingSphere(new THREE.Sphere()).radius);
    this.controls.target.copy(center);
    const distance = Math.max(0.28, Math.max(size.y, size.x * 1.3, size.z) / (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2))) * 1.55);
    const direction = new THREE.Vector3(0.42, 0.05, 1).normalize();
    this.camera.position.copy(center).addScaledVector(direction, distance);
    this.defaultDistance = distance;
    this.zoom = 1;
    this.camera.zoom = 1;
    this.viewOffsetX = 0;
    this.viewOffsetY = 0;
    this.applyViewProjection();
    this.callbacks.onZoom?.(1);
    this.controls.update();
    this.dirty = true;
  }

  findPartAt(x, y, allowSurface = true) {
    if (!this.ready) return -1;
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2(
      (x / this.canvas.clientWidth) * 2 - 1,
      -(y / this.canvas.clientHeight) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, this.camera);
    let nearest = Infinity;
    let found = -1;
    const hasInternal = this.parts.some(
      (part, index) => part.system !== "integumentary" && this.stateData[index * 4 + 3] > 0.5,
    );
    this.pickers.forEach((picker, index) => {
      if (!picker || this.stateData[index * 4 + 3] < 0.5) return;
      if (!allowSurface && hasInternal && this.parts[index].system === "integumentary") return;
      if (!raycaster.ray.intersectBox(this.bounds[index], new THREE.Vector3())) return;
      const hit = raycaster.intersectObject(picker, false)[0];
      if (hit && hit.distance < nearest) {
        nearest = hit.distance;
        found = index;
      }
    });
    return found;
  }

  pickAt(x, y) {
    const index = this.findPartAt(x, y, false);
    if (index < 0) return;
    const part = this.parts[index];
    this.selectParts([part.id], this.displayName(part.name));
  }

  selectBox(startX, startY, endX, endY) {
    if (!this.ready) return;
    const left = Math.min(startX, endX);
    const right = Math.max(startX, endX);
    const top = Math.min(startY, endY);
    const bottom = Math.max(startY, endY);
    const hits = [];
    const corner = new THREE.Vector3();
    const hasInternal = this.parts.some(
      (part, index) => part.system !== "integumentary" && this.stateData[index * 4 + 3] > 0.5,
    );
    this.parts.forEach((part, index) => {
      if (this.stateData[index * 4 + 3] < 0.5) return;
      if (this.depth > 0.05 && hasInternal && part.system === "integumentary") return;
      const bounds = this.bounds[index];
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;
      let visibleCorners = 0;
      for (let bits = 0; bits < 8; bits += 1) {
        corner.set(
          bits & 1 ? bounds.max.x : bounds.min.x,
          bits & 2 ? bounds.max.y : bounds.min.y,
          bits & 4 ? bounds.max.z : bounds.min.z,
        ).project(this.camera);
        if (corner.z < -1 || corner.z > 1) continue;
        visibleCorners += 1;
        const x = (corner.x + 1) * this.canvas.clientWidth / 2;
        const y = (1 - corner.y) * this.canvas.clientHeight / 2;
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
      if (visibleCorners && maxX >= left && minX <= right && maxY >= top && minY <= bottom) {
        hits.push(part.id);
      }
    });
    if (!hits.length) {
      this.callbacks.onSelectionEmpty?.();
      return;
    }
    hits.sort((a, b) => {
      const left = this.parts.find((part) => part.id === a);
      const right = this.parts.find((part) => part.id === b);
      return (
        (SYSTEM_PRIORITY[left?.system] ?? 99) -
          (SYSTEM_PRIORITY[right?.system] ?? 99) ||
        String(left?.name).localeCompare(String(right?.name), "zh-CN")
      );
    });
    this.selectParts(hits.slice(0, 120), "自定义框选区域");
  }

  refreshTheme() {
    const light = document.documentElement.dataset.theme === "light";
    const background = new THREE.Color(light ? 0xeaf4f8 : 0x020a17);
    this.renderer.setClearColor(background, 1);
    this.scene.background = background;
    this.scene.fog.color.copy(background);
    this.atmosphere.material.color.set(light ? 0x168aa3 : 0x58d9ff);
    this.pointClouds.forEach((cloud) => {
      if (cloud.material?.uniforms?.pointColor) {
        cloud.material.uniforms.pointColor.value.set(
          light
            ? 0x1686a1
            : (this.sex === "female" ? 0x1f7f98 : 0x56cbe4),
        );
      } else {
        cloud.material.color.set(light ? 0x148aa3 : 0x90f8ff);
      }
      if (cloud.userData?.breast && cloud.material?.uniforms?.pointColor) {
        cloud.material.uniforms.pointColor.value.set(
          light ? 0xb6577d : 0xd1789f,
        );
      }
      cloud.material.blending = THREE.NormalBlending;
      cloud.material.needsUpdate = true;
    });
    this.dirty = true;
  }

  resize() {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (!width || !height) return;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, width < 700 ? 1.5 : 2));
    this.renderer.setSize(width, height, false);
    this.composer.setSize(width, height);
    this.camera.aspect = width / height;
    this.applyViewProjection();
    this.dirty = true;
  }

  animate(time = performance.now()) {
    if (this.disposed) return;
    this.animationFrame = requestAnimationFrame((next) => this.animate(next));
    const delta = Math.min((time - this.lastFrame) / 1000, 0.04);
    this.lastFrame = time;
    if (this.atmosphere) this.atmosphere.rotation.y += delta * 0.018;
    this.controls.update();
    if (this.dirty) {
      this.composer.render();
      this.dirty = false;
    }
  }

  destroy() {
    this.disposed = true;
    this.abortController?.abort();
    cancelAnimationFrame(this.animationFrame);
    if (this.hoverTimer) cancelAnimationFrame(this.hoverTimer);
    this.resizeObserver.disconnect();
    this.clearAtlas();
    this.atmosphere.geometry.dispose();
    this.atmosphere.material.dispose();
    this.controls.dispose();
    this.composer.dispose();
    this.renderer.dispose();
  }
}

export { SYSTEM_META };
