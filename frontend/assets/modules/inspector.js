import { $, $$, state, icon, hydrateIcons, escapeHtml, api, toast, closeModal, bindModalClose } from "../ui-core.js?v=20261106-29";
import { Graph3D } from "../graph3d.js?v=20261106-29";
import { deps } from "./deps.js";
export function openGraphInspector(graphData, focusNode = null) {
  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];
  if (!nodes.length) {
    toast("当前没有可查看的图谱数据");
    return;
  }
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="graph-inspector-modal" role="dialog" aria-modal="true" aria-labelledby="graph-inspector-title">
      <header class="graph-inspector-head">
        <div>
          <span class="eyebrow"><span></span> 交互式知识图谱</span>
          <h2 class="modal-title" id="graph-inspector-title">医疗知识关系图谱</h2>
          <p class="modal-subtitle">拖拽旋转、滚轮缩放、点击任意实体展开真实 Neo4j 关系。</p>
        </div>
        <div class="inspector-history-nav">
          <button id="inspector-back" type="button" title="返回上一步" disabled>${icon("arrowLeft")}<span>上一步</span></button>
          <button id="inspector-forward" type="button" title="下一步" disabled><span>下一步</span>${icon("arrowRight")}</button>
          <span class="inspector-breadcrumb" id="inspector-breadcrumb">当前：一级核心实体</span>
          <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
        </div>
      </header>
      <div class="graph-inspector-body">
        <div class="inspector-canvas-wrap">
          <canvas id="inspector-graph-canvas"></canvas>
          <div class="inspector-level-legend">
            <span class="level-one"><i></i><b>一级</b><em>当前分析核心</em></span>
            <span class="level-two"><i></i><b>二级</b><em>直接相关实体</em></span>
            <span class="level-three"><i></i><b>三级</b><em>延伸关联线索</em></span>
          </div>
          <div class="inspector-controls">
            <button id="inspector-zoom-in" type="button" title="放大">${icon("zoomIn")}</button>
            <button id="inspector-zoom-out" type="button" title="缩小">${icon("zoomOut")}</button>
            <button id="inspector-play" type="button" title="暂停旋转">${icon("pause")}</button>
            <button id="inspector-reset" type="button" title="重新居中">${icon("refresh")}</button>
          </div>
          <div class="inspector-legend">
            <span>节点越大越接近核心，亮度越高代表关系越直接</span>
          </div>
        </div>
        <aside class="inspector-detail">
          <div class="inspector-selected-label">当前实体</div>
          <h3 id="inspector-node-name">点击节点查看</h3>
          <p id="inspector-node-type">${nodes.length} 个节点 · ${edges.length} 条关系</p>
          <div class="inspector-stat-row">
            <div><strong>${nodes.length}</strong><span>实体</span></div>
            <div><strong>${edges.length}</strong><span>关系</span></div>
          </div>
          <div class="inspector-facts-head"><span>直接关系</span><small id="inspector-fact-count">点击实体后载入</small></div>
          <div class="inspector-facts" id="inspector-graph-facts">
            <div class="evidence-empty">选择左侧任意实体，查看它在医疗知识图谱中的关系。</div>
          </div>
          <button class="ghost-button" id="inspector-focus-chat" style="width:100%;margin-top:14px">
            ${icon("message")} 基于该实体继续咨询
          </button>
        </aside>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  const canvas = $("#inspector-graph-canvas");
  state.inspectorGraph?.destroy();
  state.inspectorGraph = new Graph3D(canvas, { nodes, edges }, {
    interactive: true,
    onSelect: (node) => inspectGraphNode(node, {
      nodes: state.inspectorGraph?.nodes || nodes,
      edges: state.inspectorGraph?.edges || edges,
    }),
  });
  state.inspectorGraph.playing = false;
  $("#inspector-zoom-in").addEventListener("click", () => state.inspectorGraph?.setZoom(1));
  $("#inspector-zoom-out").addEventListener("click", () => state.inspectorGraph?.setZoom(-1));
  $("#inspector-reset").addEventListener("click", () => state.inspectorGraph?.resetView());
  $("#inspector-play").addEventListener("click", () => {
    if (!state.inspectorGraph) return;
    const playing = state.inspectorGraph.togglePlay();
    $("#inspector-play").innerHTML = icon(playing ? "pause" : "play");
  });
  $("#inspector-back").addEventListener("click", () => navigateInspectorHistory(-1));
  $("#inspector-forward").addEventListener("click", () => navigateInspectorHistory(1));
  let rootNode = focusNode;
  if (!rootNode) {
    const degree = new Map(nodes.map((node) => [node.id, 0]));
    edges.forEach((edge) => {
      degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
      degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
    });
    rootNode = [...nodes].sort((a, b) => (degree.get(b.id) || 0) - (degree.get(a.id) || 0))[0];
  }
  if (rootNode) {
    state.inspectorGraph.select(rootNode.id);
    inspectGraphNode(rootNode, { nodes, edges }, { replaceHistory: true });
  }
  $("#inspector-focus-chat").addEventListener("click", () => {
    const name = $("#inspector-node-name")?.textContent;
    closeModal();
    state.activeConversationId = null;
    state.activeConversation = null;
    Promise.resolve(deps.renderView?.("chat")).then(() => {
      const input = $("#chat-input");
      if (input && name && name !== "点击节点查看") {
        input.value = `请结合知识图谱，解释“${name}”及相关健康注意事项。`;
        input.focus();
      }
    });
  });
}


export async function inspectGraphNode(node, localGraph = null, options = {}) {
  const nameElement = $("#inspector-node-name");
  if (!nameElement) return;
  nameElement.textContent = node.name;
  $("#inspector-node-type").textContent = `${node.type_label || node.type || "医疗实体"} · 正在加载直接关系`;
  renderInspectorFacts(node, localGraph);
  try {
    const detail = await api(`/api/graph/node/${encodeURIComponent(node.id)}?depth=2`);
    if (!state.inspectorGraph || !$("#inspector-node-name")) return;
    if (detail.center) {
      $("#inspector-node-type").textContent = `${node.type_label || node.type || detail.center.type} · Neo4j 实时关系`;
      state.inspectorGraph.update(detail);
      state.inspectorGraph.select(node.id);
      renderInspectorFacts(node, detail);
      const stats = $$(".inspector-stat-row strong");
      if (stats.length === 2) {
        stats[0].textContent = detail.nodes.length;
        stats[1].textContent = detail.edges.length;
      }
      commitInspectorHistory(node, detail, Boolean(options.replaceHistory));
    }
  } catch (error) {
    $("#inspector-node-type").textContent = `${node.type_label || node.type || "医疗实体"} · 本地关系`;
  }
}


export function commitInspectorHistory(node, graphData, replaceHistory = false) {
  const history = state.inspectorHistory;
  const entry = { node, data: graphData };
  const current = history.entries[history.index];
  if (replaceHistory || history.index < 0) {
    history.entries = [entry];
    history.index = 0;
  } else if (current?.node.id === node.id) {
    history.entries[history.index] = entry;
  } else {
    history.entries = history.entries.slice(0, history.index + 1);
    history.entries.push(entry);
    history.index = history.entries.length - 1;
  }
  state.inspectorCurrentNode = node;
  updateInspectorHistoryControls();
}


export function updateInspectorHistoryControls() {
  const history = state.inspectorHistory;
  const back = $("#inspector-back");
  const forward = $("#inspector-forward");
  const breadcrumb = $("#inspector-breadcrumb");
  if (!back || !forward || !breadcrumb) return;
  back.disabled = history.index <= 0;
  forward.disabled = history.index >= history.entries.length - 1;
  const path = history.entries
    .slice(Math.max(0, history.index - 2), history.index + 1)
    .map((entry) => {
      const level = entry.node.level === 1 ? "二级" : entry.node.level === 2 ? "三级" : "一级";
      return `${level} ${entry.node.name}`;
    });
  breadcrumb.textContent = path.length ? `路径：${path.join(" → ")}` : "当前：一级核心实体";
  breadcrumb.title = history.entries.map((entry) => entry.node.name).join(" → ");
}


export function navigateInspectorHistory(direction) {
  const history = state.inspectorHistory;
  const targetIndex = history.index + direction;
  if (targetIndex < 0 || targetIndex >= history.entries.length || !state.inspectorGraph) return;
  history.index = targetIndex;
  const entry = history.entries[targetIndex];
  state.inspectorCurrentNode = entry.node;
  state.inspectorGraph.update(entry.data);
  state.inspectorGraph.select(entry.node.id);
  $("#inspector-node-name").textContent = entry.node.name;
  $("#inspector-node-type").textContent = `${entry.node.type_label || entry.node.type || entry.data.center?.type || "医疗实体"} · 浏览历史`;
  renderInspectorFacts(entry.node, entry.data);
  const stats = $$(".inspector-stat-row strong");
  if (stats.length === 2) {
    stats[0].textContent = entry.data.nodes.length;
    stats[1].textContent = entry.data.edges.length;
  }
  updateInspectorHistoryControls();
}


export function renderInspectorFacts(node, graphData) {
  const container = $("#inspector-graph-facts");
  if (!container) return;
  if (graphData?.facts?.length) {
    const seen = new Set();
    const facts = graphData.facts.filter((fact) => {
      const key = `${fact.predicate}|${fact.object}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 16);
    container.innerHTML = facts.map((fact) => `
      <div class="inspector-fact">
        <span>${escapeHtml(fact.predicate)}</span>
        <strong>${escapeHtml(fact.object)}</strong>
      </div>`).join("");
    $("#inspector-fact-count").textContent = `${facts.length} 条`;
    return;
  }
  const nodes = new Map((graphData?.nodes || []).map((item) => [item.id, item]));
  const facts = (graphData?.edges || [])
    .filter((edge) => edge.source === node.id)
    .slice(0, 16);
  container.innerHTML = facts.length
    ? facts.map((edge) => `
        <div class="inspector-fact">
          <span>${escapeHtml(edge.label || edge.type)}</span>
          <strong>${escapeHtml(nodes.get(edge.target)?.name || "相关实体")}</strong>
        </div>`).join("")
    : `<div class="evidence-empty">该实体暂未返回可展示的直接关系。</div>`;
  $("#inspector-fact-count").textContent = `${facts.length} 条`;
}

