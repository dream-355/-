import { $, $$, state, icon, hydrateIcons, escapeHtml, api, toast, clamp } from "../ui-core.js?v=20261106-29";
import { formatCompact, labelChinese } from "./insights.js";
import { deps } from "./deps.js";

const POPULAR_TERMS = [
  "高血压",
  "头晕",
  "糖尿病",
  "偏头痛",
  "哮喘",
  "贫血",
  "冠心病",
  "失眠",
  "咳嗽",
  "颈椎病",
  "腰椎间盘突出",
  "痛风",
  "湿疹",
  "焦虑",
  "甲状腺结节",
  "高血脂",
  "脂肪肝",
  "胃食管反流",
  "便秘",
  "腹泻",
  "骨质疏松",
  "过敏性鼻炎",
  "尿路感染",
];
const POPULAR_TERM_WINDOW = 7;
let popularTermOffset = 0;
let popularTermTimer = null;


function popularTermsMarkup() {
  const terms = Array.from(
    { length: POPULAR_TERM_WINDOW },
    (_, index) => POPULAR_TERMS[(popularTermOffset + index) % POPULAR_TERMS.length],
  );
  return `
    ${[...new Set(terms)].map((term) => `<button type="button" data-popular-term="${term}">${term}</button>`).join("")}
    <button type="button" class="popular-terms-refresh" id="knowledge-refresh-terms">
      ${icon("refresh")} 换一组
    </button>`;
}
export async function renderKnowledge(isCurrent = () => true) {
  const [overview, initial] = await Promise.all([
    api("/api/graph/overview"),
    api("/api/graph/search?q=高血压&limit=10"),
  ]);
  if (!isCurrent()) return;
  state.graphOverview = overview;
  state.knowledgeResults = initial.results || [];
  const labels = (overview.labels || []).slice(0, 10);
  const stats = overview.stats || {};
  const vector = overview.vector_index || {};

  $("#view-stack").innerHTML = `
    <div class="page-enter">
      <section class="knowledge-hero">
        <div class="eyebrow"><span></span> Neo4j 医疗知识图谱</div>
        <h1>可信医学知识，一触即达</h1>
        <p>在 ${formatCompact(stats.nodes)} 个医疗实体与 ${formatCompact(stats.relationships)} 条关系中进行关键词与向量混合检索。</p>
        <div class="knowledge-search">
          ${icon("search")}
          <input id="knowledge-search-input" placeholder="搜索疾病、症状、药品或检查… 例如：偏头痛" />
          <button id="knowledge-search-button">检索证据</button>
        </div>
        <div class="popular-terms" id="knowledge-popular-terms">
          ${popularTermsMarkup()}
        </div>
      </section>

      <div class="knowledge-body">
        <section class="card knowledge-results-card">
          <div class="card-header">
            <div><h3 class="card-title">知识检索结果</h3><p class="card-subtitle" id="knowledge-result-title">与“高血压”相关的图谱实体</p></div>
            <span class="tag jade" id="knowledge-result-count">${state.knowledgeResults.length} 个实体</span>
          </div>
          <div class="search-result-list" id="knowledge-result-list">${knowledgeResultList(state.knowledgeResults)}</div>
        </section>

        <aside class="knowledge-side-stack" style="display:flex;flex-direction:column;gap:16px">
          <section class="card knowledge-side-card">
            <div class="card-header"><div><h3 class="card-title">实体类型分布</h3><p class="card-subtitle">来自当前 Neo4j 图谱</p></div></div>
            <div class="category-cloud">
              ${labels.map((item) => `<button class="category-tag" data-category="${escapeHtml(item.label)}">${escapeHtml(labelChinese(item.label))}<strong>${formatCompact(item.count)}</strong></button>`).join("")}
            </div>
          </section>
          <section class="card knowledge-side-card">
            <div class="card-header"><div><h3 class="card-title">知识来源与保障</h3><p class="card-subtitle">回答不是无来源生成</p></div></div>
            <div class="source-list">
              <div class="source-item"><i></i><div><strong>Neo4j 本机医疗图谱</strong><small>${formatCompact(stats.nodes)} 节点 / ${formatCompact(stats.relationships)} 关系</small></div></div>
              <div class="source-item"><i></i><div><strong>本地字符向量召回</strong><small>${vector.ready ? `${formatCompact(vector.entities)} 个已索引实体 · ${vector.dimensions} 维` : "索引尚未就绪"}</small></div></div>
              <div class="source-item"><i></i><div><strong>DeepSeek 证据约束生成</strong><small>严格提示词限定模型只能依据检索结果回答</small></div></div>
              <div class="source-item"><i></i><div><strong>急症安全规则</strong><small>独立于大模型识别红旗症状，优先保证安全</small></div></div>
              <div class="source-item"><i></i><div><strong>可追溯证据链</strong><small>每次回答展示命中的实体与关系类型</small></div></div>
            </div>
          </section>
        </aside>
      </div>
    </div>`;
  bindKnowledgeEvents();
}


export function knowledgeResultList(results) {
  if (!results?.length) return `<div class="knowledge-empty">没有找到匹配实体，请尝试更完整的医疗名称。</div>`;
  const maxScore = Math.max(...results.map((result) => Number(result.score) || 1), 1);
  return results.map((result) => `
    <button class="search-result" style="width:100%;text-align:left" data-knowledge-entity="${escapeHtml(encodeURIComponent(JSON.stringify(result)))}">
      <span class="result-type-icon">${escapeHtml((result.type_label || result.type || "知").slice(0, 1))}</span>
      <div><strong>${escapeHtml(result.name)}</strong><small>${escapeHtml(result.type_label || result.type)} · ${result.match_type === "hybrid" ? "关键词 + 向量混合召回" : result.match_type === "vector" ? "向量语义召回" : "关键词召回"}</small></div>
      <div>
        <div class="score-meter" style="--score:${clamp(Number(result.score) / maxScore * 100, 12, 100)}%"><i></i></div>
        <small style="text-align:right;margin-top:5px;color:#587068">${Number(result.score).toFixed(1)}</small>
      </div>
      <span style="color:#627970">${icon("arrow")}</span>
    </button>`).join("");
}


export function bindKnowledgeEvents() {
  const search = () => searchKnowledge($("#knowledge-search-input").value.trim());
  $("#knowledge-search-button").addEventListener("click", search);
  $("#knowledge-search-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") search();
  });
  bindPopularTerms(search);
  resetPopularTermRotation(search);
  $$("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      $("#knowledge-search-input").value = button.dataset.category;
      search();
    });
  });
  bindKnowledgeResultEvents();
}


function bindPopularTerms(search) {
  const container = $("#knowledge-popular-terms");
  if (!container) return;
  $$("[data-popular-term]", container).forEach((button) => {
    button.addEventListener("click", () => {
      $("#knowledge-search-input").value = button.dataset.popularTerm;
      search();
    });
  });
  $("#knowledge-refresh-terms")?.addEventListener("click", () => {
    showNextPopularTerms();
    bindPopularTerms(search);
    resetPopularTermRotation(search);
  });
  hydrateIcons(container);
}


function showNextPopularTerms() {
  popularTermOffset = (popularTermOffset + 3) % POPULAR_TERMS.length;
  const container = $("#knowledge-popular-terms");
  if (container) container.innerHTML = popularTermsMarkup();
}


function resetPopularTermRotation(search) {
  if (popularTermTimer) clearInterval(popularTermTimer);
  popularTermTimer = setInterval(() => {
    if (state.view !== "knowledge" || !$("#knowledge-popular-terms")) {
      clearInterval(popularTermTimer);
      popularTermTimer = null;
      return;
    }
    showNextPopularTerms();
    bindPopularTerms(search);
  }, 5500);
}


export function bindKnowledgeResultEvents() {
  $$("[data-knowledge-entity]").forEach((button) => {
    button.addEventListener("click", () => {
      const entity = JSON.parse(decodeURIComponent(button.dataset.knowledgeEntity));
      state.graphFocus = entity.name;
    deps.renderView?.("graph");
    });
  });
}


export async function searchKnowledge(query) {
  if (!query) {
    $("#knowledge-search-input").focus();
    return;
  }
  const button = $("#knowledge-search-button");
  button.disabled = true;
  button.textContent = "检索中…";
  try {
    const data = await api(`/api/graph/search?q=${encodeURIComponent(query)}&limit=12`);
    state.knowledgeResults = data.results || [];
    $("#knowledge-result-title").textContent = `与“${query}”相关的图谱实体`;
    $("#knowledge-result-count").textContent = `${state.knowledgeResults.length} 个实体`;
    $("#knowledge-result-list").innerHTML = knowledgeResultList(state.knowledgeResults);
    hydrateIcons($("#knowledge-result-list"));
    bindKnowledgeResultEvents();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "检索证据";
  }
}

