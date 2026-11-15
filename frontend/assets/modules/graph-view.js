import { $, $$, state, icon, hydrateIcons, escapeHtml, api, toast, debounce } from "../ui-core.js?v=20261106-29";
import { Graph3D } from "../graph3d.js?v=20261106-29";
import { formatCompact } from "./insights.js";
export async function renderGraph(isCurrent = () => true) {
  const data = await api("/api/graph/overview");
  if (!isCurrent()) return;
  state.graphOverview = data;
  const stats = data.stats || {};
  const labels = (data.labels || []).slice(0, 7);
  $("#view-stack").innerHTML = `
    <div class="graph-page page-enter">
      <div class="graph-workspace">
        <canvas class="graph-canvas" id="main-graph-canvas"></canvas>
        <section class="graph-top-panel">
          <div class="graph-heading">
            <h1>医疗知识图谱</h1>
            <p>在真实 Neo4j 关系网络中探索疾病、症状与治疗证据。</p>
          </div>
          <div class="graph-search" style="position:relative">
            ${icon("search")}
            <input id="graph-search-input" placeholder="搜索疾病、药品或症状…" value="${escapeHtml(state.graphFocus || "")}" />
            <button id="graph-search-button" aria-label="搜索">${icon("arrow")}</button>
            <div class="graph-search-results" id="graph-search-results" hidden></div>
          </div>
        </section>
        <aside class="graph-insight-panel">
          <h3>知识网络概览</h3>
          <p>当前项目复用本机现有医疗图谱</p>
          <div class="graph-stat-grid">
            <div class="graph-stat"><strong>${formatCompact(stats.nodes)}</strong><span>实体节点</span></div>
            <div class="graph-stat"><strong>${formatCompact(stats.relationships)}</strong><span>关系边</span></div>
            <div class="graph-stat"><strong>${stats.label_count || 38}</strong><span>实体类型</span></div>
            <div class="graph-stat"><strong>${data.graph?.nodes?.length || 0}</strong><span>当前可视</span></div>
          </div>
          <div class="graph-selected">
            <span>当前选择</span>
            <strong id="graph-selected-name">${escapeHtml(state.graphFocus || "全局知识网络")}</strong>
            <small id="graph-selected-type">点击节点查看关系</small>
          </div>
        </aside>
        <div class="graph-legend">
          <span><i class="legend-disease"></i>疾病</span>
          <span><i class="legend-drug"></i>药品</span>
          <span><i class="legend-other"></i>症状/其他</span>
          <span><i class="legend-selected"></i>当前节点</span>
        </div>
        <div class="graph-controls">
          <button id="graph-zoom-in" aria-label="放大">${icon("zoomIn")}</button>
          <button id="graph-zoom-out" aria-label="缩小">${icon("zoomOut")}</button>
          <button id="graph-play" aria-label="暂停动画">${icon("pause")}</button>
          <button id="graph-reset" aria-label="重置视角">${icon("refresh")}</button>
        </div>
        <span class="graph-hint">拖拽旋转 · 滚轮缩放 · 点击实体展开关系</span>
      </div>
    </div>`;

  hydrateIcons($("#view-stack"));
  const canvas = $("#main-graph-canvas");
  state.graphInstance = new Graph3D(canvas, data.graph, {
    onSelect: (node) => showGraphNode(node),
  });
  // The canvas can be measured before the new layout settles; repaint once
  // after the first frame so the graph is never left blank.
  requestAnimationFrame(() => {
    if (!state.graphInstance) return;
    state.graphInstance.resize();
    state.graphInstance.draw();
  });
  $("#graph-zoom-in").addEventListener("click", () => state.graphInstance.setZoom(1));
  $("#graph-zoom-out").addEventListener("click", () => state.graphInstance.setZoom(-1));
  $("#graph-reset").addEventListener("click", () => state.graphInstance.resetView());
  $("#graph-play").addEventListener("click", () => {
    const playing = state.graphInstance.togglePlay();
    $("#graph-play").innerHTML = icon(playing ? "pause" : "play");
  });
  $("#graph-search-input").addEventListener("input", debounce(async (event) => {
    const query = event.target.value.trim();
    if (query.length < 1) {
      $("#graph-search-results").hidden = true;
      return;
    }
    await graphSearchSuggestions(query);
  }, 260));
  $("#graph-search-button").addEventListener("click", () => runGraphSearch($("#graph-search-input").value.trim()));
  $("#graph-search-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") runGraphSearch(event.target.value.trim());
  });
  if (state.graphFocus) {
    runGraphSearch(state.graphFocus);
    state.graphFocus = null;
  }
}


export async function graphSearchSuggestions(query) {
  const container = $("#graph-search-results");
  if (!container) return;
  try {
    const data = await api(`/api/graph/search?q=${encodeURIComponent(query)}&limit=8`);
    const results = data.results || [];
    container.hidden = false;
    container.innerHTML = results.length
      ? results.map((entity) => `<button data-graph-result="${escapeHtml(encodeURIComponent(JSON.stringify(entity)))}"><span>${escapeHtml(entity.type_label || entity.type)}</span>${escapeHtml(entity.name)}</button>`).join("")
      : `<button><span>无结果</span>尝试输入完整疾病或药品名称</button>`;
    $$("[data-graph-result]", container).forEach((button) => {
      button.addEventListener("click", () => {
        const entity = JSON.parse(decodeURIComponent(button.dataset.graphResult));
        showGraphNode(entity);
        $("#graph-search-input").value = entity.name;
        container.hidden = true;
      });
    });
  } catch {
    container.hidden = true;
  }
}


export async function runGraphSearch(query) {
  if (!query || !state.graphInstance) return;
  try {
    const data = await api(`/api/graph/search?q=${encodeURIComponent(query)}&limit=1`);
    if (data.results?.length) await showGraphNode(data.results[0]);
    else toast("知识库中暂未找到该实体", "error");
  } catch (error) {
    toast(error.message, "error");
  }
}


export async function showGraphNode(node) {
  const nameElement = $("#graph-selected-name");
  const typeElement = $("#graph-selected-type");
  if (nameElement) nameElement.textContent = node.name;
  if (typeElement) typeElement.textContent = node.type_label || node.type || "医疗实体";
  state.graphInstance?.select(node.id);
  try {
    const detail = await api(`/api/graph/node/${encodeURIComponent(node.id)}?depth=2`);
    if (detail.center && state.graphInstance) {
      state.graphInstance.update(detail);
      state.graphInstance.select(detail.center.id);
      if (typeElement) typeElement.textContent = `${detail.center.type} · ${detail.facts.length} 条直接关系`;
    }
  } catch (error) {
    toast(error.message, "error");
  }
}

