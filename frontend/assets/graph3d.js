function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/* Graph explorer and custom 3D renderer */
export class Graph3D {
  constructor(canvas, data, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.options = {
      compact: false,
      interactive: true,
      ...options,
    };
    this.onSelect = options.onSelect || null;
    this.playing = true;
    this.zoom = 1;
    this.fit = { scale: 1, offsetX: 0, offsetY: 0 };
    this.yaw = -0.24;
    this.pitch = 0.14;
    this.selectedId = null;
    this.pointer = { down: false, x: 0, y: 0, moved: 0 };
    this.frameId = null;
    this.lastTime = performance.now();
    this.nodes = [];
    this.edges = [];
    this.width = 0;
    this.height = 0;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    this.update(data);
    this.resize();
    this.bindEvents();
    this.animate = this.animate.bind(this);
    this.frameId = requestAnimationFrame(this.animate);
  }

  hash(text = "") {
    let value = 2166136261;
    for (let index = 0; index < text.length; index++) {
      value ^= text.charCodeAt(index);
      value = Math.imul(value, 16777619);
    }
    return Math.abs(value);
  }

  update(data) {
    const previous = new Map(this.nodes.map((node) => [node.id, node]));
    this.nodes = (data?.nodes || []).map((node, index) => {
      const old = previous.get(node.id);
      const seed = this.hash(node.id || `${node.name}-${index}`);
      const angle = (seed % 360) * Math.PI / 180;
      const elevation = ((seed >> 8) % 180 - 90) * Math.PI / 180;
      const radius = 175 + ((seed >> 16) % 190);
      return {
        ...node,
        x: old?.x ?? Math.cos(elevation) * Math.cos(angle) * radius,
        y: old?.y ?? Math.sin(elevation) * radius,
        z: old?.z ?? Math.cos(elevation) * Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        vz: 0,
        radius:
          node.level === 0
            ? 9.5
            : node.level === 1
              ? 5.2
              : node.level === 2
                ? 3.9
                : ["Disease", "Drug"].includes(node.type)
                  ? 6
                  : 3.8,
      };
    });
    this.edges = (data?.edges || []).filter((edge) => {
      return this.nodes.some((node) => node.id === edge.source) && this.nodes.some((node) => node.id === edge.target);
    });
    const degrees = new Map(this.nodes.map((node) => [node.id, 0]));
    for (const edge of this.edges) {
      degrees.set(edge.source, (degrees.get(edge.source) || 0) + 1);
      degrees.set(edge.target, (degrees.get(edge.target) || 0) + 1);
    }
    for (const node of this.nodes) node.degree = degrees.get(node.id) || 0;
    this.layoutNodes();
  }

  bindEvents() {
    if (!this.options.interactive) return;
    this.canvas.addEventListener("pointerdown", (event) => {
      this.pointer.down = true;
      this.pointer.x = event.clientX;
      this.pointer.y = event.clientY;
      this.pointer.moved = 0;
      this.canvas.setPointerCapture(event.pointerId);
    });
    this.canvas.addEventListener("pointermove", (event) => {
      if (!this.pointer.down) return;
      const dx = event.clientX - this.pointer.x;
      const dy = event.clientY - this.pointer.y;
      this.yaw += dx * 0.005;
      this.pitch += dy * 0.004;
      this.pitch = clamp(this.pitch, -1.25, 1.25);
      this.pointer.x = event.clientX;
      this.pointer.y = event.clientY;
      this.pointer.moved += Math.abs(dx) + Math.abs(dy);
    });
    this.canvas.addEventListener("pointerup", (event) => {
      this.pointer.down = false;
      if (this.pointer.moved < 8) this.pickNode(event);
    });
    this.canvas.addEventListener("pointercancel", () => {
      this.pointer.down = false;
    });
    this.canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      this.zoom = clamp(this.zoom * (event.deltaY > 0 ? 0.93 : 1.07), 0.38, 2.1);
    }, { passive: false });
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.width = Math.max(rect.width, 1);
    this.height = Math.max(rect.height, 1);
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = Math.floor(this.width * this.dpr);
    this.canvas.height = Math.floor(this.height * this.dpr);
  }

  projectRaw(node) {
    const cosYaw = Math.cos(this.yaw);
    const sinYaw = Math.sin(this.yaw);
    const cosPitch = Math.cos(this.pitch);
    const sinPitch = Math.sin(this.pitch);
    const x1 = node.x * cosYaw - node.z * sinYaw;
    const z1 = node.x * sinYaw + node.z * cosYaw;
    const y2 = node.y * cosPitch - z1 * sinPitch;
    const z2 = node.y * sinPitch + z1 * cosPitch;
    const depth = 720;
    const perspective = depth / (depth - z2);
    return {
      x: x1 * perspective,
      y: y2 * perspective,
      scale: perspective,
      depth: z2,
    };
  }

  updateFitTransform() {
    if (!this.nodes.length || this.width < 2 || this.height < 2) return;
    const points = this.nodes.map((node) => this.projectRaw(node));
    const xs = points.map((point) => point.x);
    const ys = points.map((point) => point.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const spanX = Math.max(maxX - minX, 1);
    const spanY = Math.max(maxY - minY, 1);
    const padding = this.options.compact ? 18 : Math.max(34, Math.min(this.width, this.height) * 0.075);
    const fitScale = Math.min(
      Math.max(this.width - padding * 2, 1) / spanX,
      Math.max(this.height - padding * 2, 1) / spanY,
    );
    const effectiveScale = clamp(fitScale * this.zoom, 0.08, 8);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    this.fit = {
      scale: effectiveScale,
      offsetX: this.width / 2 - centerX * effectiveScale,
      offsetY: this.height / 2 - centerY * effectiveScale,
    };
  }

  layoutNodes() {
    if (!this.nodes.length) return;
    const hasLevels = this.nodes.some((node) => Number.isInteger(node.level));
    if (hasLevels) {
      const placeRing = (items, radius, depthOffset = 0) => {
        items.forEach((node, index) => {
          const angle = (index / Math.max(items.length, 1)) * Math.PI * 2 - Math.PI / 2;
          node.x = Math.cos(angle) * radius;
          node.y = Math.sin(angle) * radius;
          node.z = depthOffset + Math.sin(angle * 3 + index) * 34;
          node.vx = 0;
          node.vy = 0;
          node.vz = 0;
        });
      };
      const roots = this.nodes.filter((node) => node.level === 0);
      const direct = this.nodes.filter((node) => node.level === 1);
      const outer = this.nodes.filter((node) => !Number.isInteger(node.level) || node.level >= 2);
      roots.forEach((node, index) => {
        node.x = index * 24;
        node.y = index * 18;
        node.z = 0;
      });
      placeRing(direct, 158, 0);
      placeRing(outer, 318, 12);
      return;
    }
    const sorted = [...this.nodes].sort(
      (a, b) => b.degree - a.degree || String(a.name).localeCompare(String(b.name), "zh-CN"),
    );
    const innerCount = sorted.length > 16 ? Math.min(8, Math.ceil(Math.sqrt(sorted.length))) : 0;
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    sorted.forEach((node, index) => {
      const inCore = index < innerCount;
      const shellIndex = inCore ? index : index - innerCount;
      const shellCount = Math.max(inCore ? innerCount : sorted.length - innerCount, 1);
      const vertical = 1 - 2 * ((shellIndex + 0.5) / shellCount);
      const ringRadius = Math.sqrt(Math.max(1 - vertical * vertical, 0));
      const angle = goldenAngle * shellIndex;
      const radius = inCore ? 108 : 238 + (shellIndex % 3) * 42;
      node.x = Math.cos(angle) * ringRadius * radius;
      node.y = vertical * radius;
      node.z = Math.sin(angle) * ringRadius * radius;
      node.vx = 0;
      node.vy = 0;
      node.vz = 0;
    });
  }

  project(node) {
    const point = this.projectRaw(node);
    return {
      ...point,
      x: point.x * this.fit.scale + this.fit.offsetX,
      y: point.y * this.fit.scale + this.fit.offsetY,
      scale: point.scale * this.fit.scale,
    };
  }

  simulate(delta) {
    if (!this.playing || this.nodes.length > 150) return;
    const step = clamp(delta / 16.67, 0.25, 2);
    const nodes = this.nodes;
    for (let index = 0; index < nodes.length; index++) {
      const a = nodes[index];
      for (let other = index + 1; other < nodes.length; other++) {
        const b = nodes[other];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dz = b.z - a.z;
        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
        const force = 780 / (distance * distance);
        a.vx -= dx / distance * force;
        a.vy -= dy / distance * force;
        a.vz -= dz / distance * force;
        b.vx += dx / distance * force;
        b.vy += dy / distance * force;
        b.vz += dz / distance * force;
      }
      a.vx += -a.x * 0.00028;
      a.vy += -a.y * 0.00028;
      a.vz += -a.z * 0.00028;
    }
    const byId = new Map(nodes.map((node) => [node.id, node]));
    for (const edge of this.edges) {
      const a = byId.get(edge.source);
      const b = byId.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dz = b.z - a.z;
      const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
      const force = (distance - 116) * 0.00018;
      a.vx += dx * force;
      a.vy += dy * force;
      a.vz += dz * force;
      b.vx -= dx * force;
      b.vy -= dy * force;
      b.vz -= dz * force;
    }
    for (const node of nodes) {
      node.vx *= 0.9;
      node.vy *= 0.9;
      node.vz *= 0.9;
      node.x += node.vx * step;
      node.y += node.vy * step;
      node.z += node.vz * step;
    }
  }

  draw() {
    const ctx = this.ctx;
    const lightTheme = document.documentElement.dataset.theme === "light";
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);
    if (!this.nodes.length) {
      ctx.fillStyle = lightTheme
        ? "rgba(51, 94, 78, .62)"
        : "rgba(120, 155, 142, .55)";
      ctx.font = '10px "PingFang SC", sans-serif';
      ctx.textAlign = "center";
      ctx.fillText("正在载入知识图谱…", this.width / 2, this.height / 2);
      return;
    }
    this.updateFitTransform();
    const projected = new Map(this.nodes.map((node) => [node.id, this.project(node)]));
    const sortedEdges = [...this.edges].sort((a, b) => {
      const depthA = (projected.get(a.source)?.depth || 0) + (projected.get(a.target)?.depth || 0);
      const depthB = (projected.get(b.source)?.depth || 0) + (projected.get(b.target)?.depth || 0);
      return depthA - depthB;
    });
    for (const edge of sortedEdges) {
      const a = projected.get(edge.source);
      const b = projected.get(edge.target);
      if (!a || !b) continue;
      const active = edge.source === this.selectedId || edge.target === this.selectedId;
      const level = edge.level || 1;
      const alpha = active
        ? 0.68
        : level >= 2
          ? clamp(0.055 + (a.depth + b.depth + 240) / 3200, 0.045, 0.12)
          : clamp(0.16 + (a.depth + b.depth + 240) / 1900, 0.12, 0.36);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = active
        ? lightTheme
          ? `rgba(20, 132, 92, ${alpha})`
          : `rgba(104,224,177,${alpha})`
        : lightTheme
          ? `rgba(70, 119, 101, ${alpha})`
          : `rgba(103,160,140,${alpha})`;
      ctx.lineWidth = active ? 1.1 : level >= 2 ? 0.5 : 0.8;
      ctx.stroke();
    }

    const sortedNodes = [...this.nodes].sort((a, b) => (projected.get(a.id)?.depth || 0) - (projected.get(b.id)?.depth || 0));
    for (const node of sortedNodes) {
      const point = projected.get(node.id);
      if (!point) continue;
      const selected = node.id === this.selectedId;
      const isDisease = node.type === "Disease";
      const isDrug = node.type === "Drug";
      const isRoot = node.level === 0;
      const level = node.level;
      const color = lightTheme
        ? selected || isRoot
          ? "#9a6c20"
          : level === 1
            ? "#17956a"
            : level === 2
              ? "#68847a"
              : isDisease
                ? "#16865e"
                : isDrug
                  ? "#2d7d91"
                  : "#6b8078"
        : selected || isRoot
          ? "#f4dba2"
          : level === 1
            ? "#79e6b8"
            : level === 2
              ? "#568a7a"
              : isDisease
                ? "#68e0b1"
                : isDrug
                  ? "#7fc7dc"
                  : "#a5b9af";
      const radius = Math.max(2.2, node.radius * point.scale * (selected ? 1.35 : 1));
      const levelAlpha = isRoot || selected ? 1 : level === 1 ? 0.94 : level === 2 ? 0.58 : 1;
      const alpha = clamp((point.depth + 320) / 580, 0.28, 1) * levelAlpha;
      if (selected || isRoot || (level === 1 && (isDisease || isDrug))) {
        const glow = ctx.createRadialGradient(point.x, point.y, 0, point.x, point.y, radius * 5);
        glow.addColorStop(0, `${color}55`);
        glow.addColorStop(1, `${color}00`);
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius * 5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.globalAlpha = alpha;
      ctx.fill();
      ctx.strokeStyle = lightTheme
        ? "rgba(255,255,255,.88)"
        : "rgba(235,255,247,.65)";
      ctx.lineWidth = selected ? 1.2 : 0.45;
      ctx.stroke();
      ctx.globalAlpha = 1;
      const showLabel = !this.options.compact;
      if (!this.options.compact && showLabel) {
        const label = node.name.length > 10 ? `${node.name.slice(0, 9)}…` : node.name;
        const centerX = this.width / 2;
        const centerY = this.height / 2;
        const radialX = point.x - centerX;
        const radialY = point.y - centerY;
        const radialLength = Math.hypot(radialX, radialY) || 1;
        let labelX = point.x;
        let labelY = point.y - radius - 7;
        let labelAlign = "center";
        if (node.level !== 0 && !selected) {
          labelX = point.x + (radialX / radialLength) * (radius + 5);
          labelY = point.y + (radialY / radialLength) * (radius + 5) + 3;
          labelAlign = radialX >= 0 ? "left" : "right";
        }
        ctx.font = `${selected || isRoot ? "600" : "400"} ${selected || isRoot ? 10.5 : level === 2 ? 7.2 : 8.5}px "PingFang SC", sans-serif`;
        ctx.fillStyle = lightTheme
          ? selected || isRoot
            ? "#7e5a20"
            : level === 2
              ? "rgba(77,105,92,.72)"
              : "#24473b"
          : selected || isRoot
            ? "#f5e6bb"
            : level === 2
              ? "rgba(162,190,179,.62)"
              : "rgba(222,241,232,.9)";
        ctx.textAlign = labelAlign;
        ctx.shadowColor = lightTheme ? "rgba(255,255,255,.9)" : "rgba(0,0,0,.8)";
        ctx.shadowBlur = lightTheme ? 3 : 5;
        ctx.fillText(label, labelX, labelY);
        ctx.shadowBlur = 0;
      }
    }
  }

  animate(now) {
    const delta = now - this.lastTime;
    this.lastTime = now;
    if (this.playing && !this.pointer.down) {
      this.yaw += Math.min(delta, 32) * 0.00006;
    }
    this.draw();
    this.frameId = requestAnimationFrame(this.animate);
  }

  pickNode(event) {
    const rect = this.canvas.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    let closest = null;
    let bestDistance = 18;
    for (const node of this.nodes) {
      const point = this.project(node);
      const distance = Math.hypot(point.x - clickX, point.y - clickY);
      if (distance < bestDistance) {
        closest = node;
        bestDistance = distance;
      }
    }
    if (closest) {
      this.select(closest.id);
      this.onSelect?.(closest);
    }
  }

  select(id) {
    this.selectedId = id;
  }

  setZoom(direction) {
    this.zoom = clamp(this.zoom * (direction > 0 ? 1.18 : 0.85), 0.38, 2.1);
  }

  resetView() {
    this.yaw = -0.24;
    this.pitch = 0.14;
    this.zoom = this.options.compact ? 0.7 : 1;
  }

  togglePlay() {
    this.playing = !this.playing;
    return this.playing;
  }

  destroy() {
    cancelAnimationFrame(this.frameId);
    this.resizeObserver.disconnect();
  }
}

