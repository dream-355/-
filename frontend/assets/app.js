import { Graph3D } from "./graph3d.js?v=20261106-29";
import {
  $,
  $$,
  state,
  icon,
  hydrateIcons,
  escapeHtml,
  formatMarkdown,
  api,
  toast,
  formatDate,
  formatTime,
  relativeDate,
  greeting,
  clamp,
  debounce,
  loadAppSettings,
  openSettingsModal,
  openSystemStatus,
  openFeedbackModal,
  openHealthPassport,
  sendHealthReport,
  compressImageFile,
  setChatImage,
  setTriageImage,
  closeModal,
  bindModalClose,
  scoreRing,
  toggleTheme,
} from "./ui-core.js?v=20261106-29";
import { installDeps } from "./modules/deps.js";
import { reviewChip, reviewSummary } from "./modules/review.js";
import { lineChart, metricCard, signalRow, vitalSignalScore, vitalItem, profileItem, chartMetricValues, ageFromBirthDate, formatCompact, labelChinese } from "./modules/insights.js";
import { renderKnowledge, knowledgeResultList, bindKnowledgeEvents, bindKnowledgeResultEvents, searchKnowledge } from "./modules/knowledge.js";
import { renderGraph, graphSearchSuggestions, runGraphSearch, showGraphNode } from "./modules/graph-view.js";
import { openGraphInspector, inspectGraphNode, commitInspectorHistory, updateInspectorHistoryControls, navigateInspectorHistory, renderInspectorFacts } from "./modules/inspector.js";
import { openRecordModal, modalInput, openProfileModal } from "./modules/records.js";
import { renderLifestyle } from "./modules/lifestyle.js?v=20261106-29";
import { openBodyMap } from "./modules/body-map.js?v=20261106-29";

const initialQuery = new URLSearchParams(location.search);
let pendingInitialView = ["dashboard", "chat", "health", "triage", "graph", "knowledge", "lifestyle"].includes(
  initialQuery.get("view")
)
  ? initialQuery.get("view")
  : "dashboard";
let pendingConversationId = initialQuery.get("conversation");
let navigationEntries = [];
let navigationIndex = -1;
let renderSequence = 0;

function statusFromTrace(trace) {
  const level = trace?.triage?.level || "low";
  return {
    low: ["低风险", "jade"],
    medium: ["需观察", "amber"],
    high: ["需尽快就医", "red"],
    emergency: ["急症警示", "red"],
  }[level] || ["低风险", "jade"];
}

function displayEvidenceId(value) {
  const match = String(value || "").match(/^E(\d+)$/i);
  return match ? `证据${match[1]}` : String(value || "");
}

function displayToolName(value) {
  return {
    "medical_graph.hybrid_search": "医疗知识图谱混合检索",
    "medical_graph.expand_relationship": "展开图谱关系",
    "medical_graph.filter_by_intent": "按问题类型筛选证据",
    "llm.generate_with_citations": "生成引用回答",
    "llm.stream_completion": "智能模型流式生成",
    "reviewer.medical_quality_check": "医学质量复核",
  }[value] || value || "医疗工具";
}

function displayConversationTitle(value) {
  const title = String(value || "").trim();
  return title.replace(/[\s\p{P}\p{S}]/gu, "") ? title : "待补充症状的健康咨询";
}

async function loadSystemStatus() {
  try {
    state.system = await api("/api/health");
    const status = $("#model-status");
    if (status) {
      status.textContent = state.system.deepseek_configured ? "已配置" : "演示引擎";
    }
    const graphStatus = $("#sidebar-graph-status");
    if (graphStatus) {
      graphStatus.textContent = state.system.neo4j.online
        ? `在线 · ${state.system.neo4j.latency_ms} 毫秒`
        : "等待连接";
    }
  } catch {
    // Status is explanatory only; the app remains usable.
  }
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isRegister = mode === "register";
  $(".auth-name-field").hidden = !isRegister;
  $("#auth-name").required = isRegister;
  $("#auth-title").textContent = isRegister ? "创建你的健康空间" : "登录你的健康空间";
  $("#auth-subtitle").textContent = isRegister
    ? "保存对话与健康记录，获得连续、个性化的健康支持。"
    : "你的连续健康记忆，从一次对话开始。";
  $("#auth-submit span:first-child").textContent = isRegister ? "创建并进入" : "进入健康空间";
  $("#auth-switch-copy").textContent = isRegister ? "已有账户？" : "还没有账户？";
  $("#auth-switch").textContent = isRegister ? "返回登录" : "创建账户";
  $("#auth-error").textContent = "";
}

function showAuth() {
  $("#auth-screen").hidden = false;
  $("#app-shell").hidden = true;
  state.user = null;
}

function showApp(user, initialView = "dashboard") {
  state.user = user;
  $("#auth-screen").hidden = true;
  $("#app-shell").hidden = false;
  const initial = userAvatarInitial(user.name);
  $("#sidebar-avatar").textContent = initial;
  $("#top-avatar").textContent = initial;
  $("#sidebar-user-name").textContent = user.name || "健康用户";
  const targetView = pendingInitialView || initialView;
  if (pendingConversationId) {
    state.activeConversationId = pendingConversationId;
    pendingConversationId = null;
  }
  pendingInitialView = "dashboard";
  renderView(targetView, { recordHistory: false });
  initializeNavigationTimeline();
  loadConversations().catch(() => {});
}

function userAvatarInitial(name) {
  return Array.from((name || "你").trim())[0] || "你";
}

async function initAuth() {
  setAuthMode("login");
  $("#auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("#auth-submit");
    const errorBox = $("#auth-error");
    errorBox.textContent = "";
    button.disabled = true;
    try {
      const payload = {
        email: $("#auth-email").value.trim(),
        password: $("#auth-password").value,
      };
      let result;
      const isRegistration = state.authMode === "register";
      if (isRegistration) {
        result = await api("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({
            ...payload,
            name: $("#auth-name").value.trim(),
          }),
        });
      } else {
        result = await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      loadSystemStatus();
      showApp(result.user);
      if (isRegistration && result.registration_email) {
        toast(
          result.registration_email.message,
          result.registration_email.status === "sent" ? "success" : "error",
          6500,
        );
      }
    } catch (error) {
      errorBox.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });

  $("#auth-switch").addEventListener("click", () => {
    setAuthMode(state.authMode === "login" ? "register" : "login");
  });
  $("#forgot-password").addEventListener("click", () => {
    openPasswordReset($("#auth-email").value.trim());
  });
  $("#demo-login").addEventListener("click", async () => {
    const button = $("#demo-login");
    button.disabled = true;
    try {
      const result = await api("/api/auth/demo", { method: "POST" });
      loadSystemStatus();
      showApp(result.user);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });
  $("#password-toggle").addEventListener("click", () => {
    const input = $("#auth-password");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    $("#password-toggle").textContent = show ? "隐藏" : "显示";
  });
}

function openPasswordReset(prefillEmail = "") {
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card password-reset-modal" role="dialog" aria-modal="true" aria-labelledby="password-reset-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 安全找回账号</span><h2 class="modal-title" id="password-reset-title">找回登录密码</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">输入注册邮箱，我们会发送 6 位验证码。验证码 10 分钟内有效，仅可使用一次。</p>
      <form id="password-reset-request-form">
        <div class="modal-field">
          <label>注册邮箱</label>
          <input name="email" type="email" required maxlength="120" value="${escapeHtml(prefillEmail)}" placeholder="name@example.com" />
        </div>
        <p class="form-error" id="password-reset-error" role="alert"></p>
        <div class="modal-actions">
          <button type="button" class="ghost-button" data-close-modal>取消</button>
          <button type="submit" class="primary-button">${icon("mail")} 发送验证码</button>
        </div>
      </form>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#password-reset-request-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = String(new FormData(event.target).get("email") || "").trim();
    const button = event.target.querySelector("button[type=submit]");
    const errorBox = $("#password-reset-error");
    errorBox.textContent = "";
    button.disabled = true;
    try {
      const result = await api("/api/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      renderPasswordResetConfirm(email, result.expires_in_minutes || 10);
    } catch (error) {
      errorBox.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

function renderPasswordResetConfirm(email, expiresInMinutes) {
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card password-reset-modal" role="dialog" aria-modal="true" aria-labelledby="password-reset-confirm-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 验证邮箱</span><h2 class="modal-title" id="password-reset-confirm-title">设置新密码</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">验证码已发送至 ${escapeHtml(email)}，${Number(expiresInMinutes)} 分钟内有效。若邮箱不存在，系统不会泄露账号状态。</p>
      <form id="password-reset-confirm-form">
        <div class="modal-field">
          <label>邮箱验证码</label>
          <div class="reset-code-row">
            <input name="code" type="text" required minlength="6" maxlength="6" inputmode="numeric" autocomplete="one-time-code" placeholder="6 位验证码" />
            <button type="button" class="ghost-button" id="resend-reset-code">重新发送</button>
          </div>
        </div>
        <div class="form-grid-2">
          <div class="modal-field"><label>新密码</label><input name="new_password" type="password" required minlength="8" maxlength="72" placeholder="至少 8 位" /></div>
          <div class="modal-field"><label>确认新密码</label><input name="confirm_password" type="password" required minlength="8" maxlength="72" placeholder="再输入一次" /></div>
        </div>
        <p class="form-error" id="password-reset-confirm-error" role="alert"></p>
        <div class="modal-actions">
          <button type="button" class="ghost-button" id="change-reset-email">更换邮箱</button>
          <button type="submit" class="primary-button">${icon("lock")} 重置密码</button>
        </div>
      </form>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#change-reset-email").addEventListener("click", () => openPasswordReset(email));
  $("#resend-reset-code").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await api("/api/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      toast("新的验证码已发送，请检查邮箱");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });
  $("#password-reset-confirm-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const code = String(form.get("code") || "").trim();
    const newPassword = String(form.get("new_password") || "");
    const confirmPassword = String(form.get("confirm_password") || "");
    const errorBox = $("#password-reset-confirm-error");
    errorBox.textContent = "";
    if (!/^\d{6}$/.test(code)) {
      errorBox.textContent = "请输入 6 位数字验证码";
      return;
    }
    if (newPassword !== confirmPassword) {
      errorBox.textContent = "两次输入的新密码不一致";
      return;
    }
    const button = event.target.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await api("/api/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ email, code, new_password: newPassword }),
      });
      closeModal();
      setAuthMode("login");
      $("#auth-email").value = email;
      $("#auth-password").value = "";
      $("#auth-error").textContent = "";
      toast("密码已重置，请使用新密码登录");
    } catch (error) {
      errorBox.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

async function bootstrap() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/assets/sw.js?v=20261106-29").catch(() => {});
    });
  }
  loadAppSettings();
  hydrateIcons();
  await initAuth();
  loadSystemStatus();
  bindGlobalEvents();
  showAuth();
}

function bindGlobalEvents() {
  $$("[data-view]").forEach((button) => {
    button.addEventListener("click", () => renderView(button.dataset.view));
  });
  $("#new-chat-side").addEventListener("click", startNewChat);
  $("#navigation-back").addEventListener("click", navigateBack);
  $$("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", toggleTheme);
  });
  try {
    state.sidebarSpaceOpen = localStorage.getItem("zhiheng.sidebarSpaceOpen") === "1";
  } catch {
    state.sidebarSpaceOpen = false;
  }
  $("#sidebar-space-toggle")?.addEventListener("click", () => {
    state.sidebarSpaceOpen = !state.sidebarSpaceOpen;
    if (!state.sidebarSpaceOpen) {
      state.sidebarManage = false;
      state.sidebarSelected.clear();
    }
    try {
      localStorage.setItem("zhiheng.sidebarSpaceOpen", state.sidebarSpaceOpen ? "1" : "0");
    } catch {
      /* storage may be unavailable */
    }
    renderSidebarHistory();
  });
  $("#sidebar-manage")?.addEventListener("click", () => {
    state.sidebarManage = !state.sidebarManage;
    state.sidebarSelected.clear();
    renderSidebarHistory();
  });
  $("#settings-button").addEventListener("click", () => {
    $("#user-menu").hidden = true;
    openSettingsModal();
  });
  $("#feedback-button").addEventListener("click", () => {
    $("#user-menu").hidden = true;
    openFeedbackModal();
  });
  $("#top-avatar").addEventListener("click", () => renderView("health"));
  $("#user-menu-button").addEventListener("click", (event) => {
    event.stopPropagation();
    $("#user-menu").hidden = !$("#user-menu").hidden;
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".sidebar-user")) $("#user-menu").hidden = true;
  });
  $("#logout-button").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    location.reload();
  });
  $("#mobile-menu").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  $("#command-search").addEventListener("click", openPalette);
  $("#notification-button")?.addEventListener("click", openSystemStatus);
  $("[data-close-palette]").addEventListener("click", closePalette);
  $("#palette-input").addEventListener(
    "input",
    debounce((event) => searchPalette(event.target.value), 220)
  );
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openPalette();
    }
    if (event.key === "Escape") {
      closePalette();
      closeModal();
    }
    if (event.altKey && event.key === "ArrowLeft") {
      event.preventDefault();
      navigateBack();
    }
  });
}

function navigationSnapshot() {
  return {
    view: state.view,
    activeConversationId: state.activeConversationId,
    graphFocus: state.graphFocus || "",
  };
}

function initializeNavigationTimeline() {
  navigationEntries = [navigationSnapshot()];
  navigationIndex = 0;
  updateNavigationBackButton();
}

function commitNavigationSnapshot() {
  if (!state.user || !state.view) return;
  const snapshot = navigationSnapshot();
  const current = navigationEntries[navigationIndex];
  if (
    current &&
    current.view === snapshot.view &&
    current.activeConversationId === snapshot.activeConversationId &&
    current.graphFocus === snapshot.graphFocus
  ) {
    return;
  }
  navigationEntries = navigationEntries.slice(0, navigationIndex + 1);
  navigationEntries.push(snapshot);
  navigationIndex = navigationEntries.length - 1;
  updateNavigationBackButton();
}

function restoreNavigationSnapshot(snapshot) {
  state.activeConversationId = snapshot.activeConversationId || null;
  state.activeConversation = null;
  state.graphFocus = snapshot.graphFocus || "";
  renderView(snapshot.view || "dashboard", { recordHistory: false });
  updateNavigationBackButton();
}

function updateNavigationBackButton() {
  const button = $("#navigation-back");
  if (!button) return;
  const hasHistory = navigationIndex > 0;
  button.disabled = !hasHistory;
  button.title = hasHistory
    ? "返回上一步"
    : "没有上一步";
  button.innerHTML = icon("arrowLeft");
}

function navigateBack() {
  if (
    $("#inspector-back") &&
    !$("#inspector-back").disabled &&
    state.inspectorHistory.index > 0
  ) {
    navigateInspectorHistory(-1);
    return;
  }
  if (navigationIndex <= 0) return;
  navigationIndex -= 1;
  restoreNavigationSnapshot(navigationEntries[navigationIndex]);
}

async function renderView(view, options = {}) {
  if (!state.user) return;
  const renderToken = ++renderSequence;
  const available = ["dashboard", "chat", "health", "triage", "graph", "knowledge", "lifestyle"];
  if (!available.includes(view)) view = "dashboard";
  state.view = view;
  state.graphInstance?.destroy();
  state.graphInstance = null;
  state.evidenceGraph?.destroy();
  state.evidenceGraph = null;
  $("#sidebar").classList.remove("open");
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  const titles = {
    dashboard: "健康总览",
    chat: "健康咨询",
    health: "健康档案",
    triage: "智能检测",
    graph: "医疗知识图谱",
    knowledge: "医学知识库",
    lifestyle: "健康生活",
  };
  $("#page-title").textContent = titles[view];
  $("#view-stack").innerHTML = `
    <div class="loading-screen">
      <div class="medical-loader"><span></span><span></span><span></span><i></i></div>
      <p>正在建立可信健康上下文…</p>
    </div>`;
  try {
    if (view === "dashboard") await renderDashboard(renderToken);
    if (view === "chat") await renderChat(renderToken);
    if (view === "health") await renderHealth(renderToken);
    if (view === "triage") await renderTriage(renderToken);
    if (view === "graph") await renderGraph(() => renderToken === renderSequence && state.view === "graph");
    if (view === "knowledge") await renderKnowledge(() => renderToken === renderSequence && state.view === "knowledge");
    if (view === "lifestyle") await renderLifestyle(() => renderToken === renderSequence && state.view === "lifestyle");
  } catch (error) {
    if (renderToken !== renderSequence) return;
    if (error.status === 401) {
      showAuth();
      return;
    }
    $("#view-stack").innerHTML = `
      <div class="loading-screen">
        <p>${escapeHtml(error.message)}</p>
        <button class="ghost-button" onclick="location.reload()">重新加载</button>
      </div>`;
  }
  if (renderToken !== renderSequence) return;
  hydrateIcons($("#view-stack"));
  if (options.recordHistory !== false) commitNavigationSnapshot();
}

/* Dashboard */
async function renderDashboard(renderToken = renderSequence) {
  const data = await api("/api/dashboard");
  if (renderToken !== renderSequence || state.view !== "dashboard") return;
  state.dashboard = data;
  const overview = data.overview || {};
  const latest = overview.latest || {};
  const records = data.recent_records || [];
  const bp = latest.systolic && latest.diastolic ? `${latest.systolic}/${latest.diastolic}` : "—";
  const conversations = data.conversations || [];
  const chartLabels = [...records].reverse().map((record) => formatDate(record.measured_at));
  const systolic = [...records].reverse().map((record) => record.systolic || 0);
  const diastolic = [...records].reverse().map((record) => record.diastolic || 0);
  const sleep = [...records].reverse().map((record) => record.sleep_hours || 0);
  const heart = [...records].reverse().map((record) => record.heart_rate || 0);
  const trendValues = state.chartMetric === "sleep" ? sleep : heart;

  $("#view-stack").innerHTML = `
    <div class="page-enter">
      <div class="page-heading">
        <div class="page-heading-copy">
          <span>个人健康管理中心</span>
          <h1>${greeting()}，${escapeHtml(state.user.name)}<span style="color:var(--jade)">。</span></h1>
          <p>${new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date())} · 你的健康信号已完成今日分析</p>
        </div>
        <div class="heading-actions">
          <button class="ghost-button" data-open-record>${icon("plus")} 记录体征</button>
          <button class="small-button" data-go-dashboard-health>${icon("activity")} 查看趋势</button>
        </div>
      </div>

      <section class="hero-banner">
        <div class="hero-content">
          <div class="hero-kicker"><i class="live-dot"></i> 智能健康简报 · 今日洞察已更新</div>
          <h2>${escapeHtml(overview.headline || "健康信号整体平稳")}，我们继续<br/>把你的身体变化读懂。</h2>
          <p>${escapeHtml(overview.insight || "基于最近 7 天的生命体征、睡眠与对话记录，持续建立个人健康基线。")}</p>
          <div class="hero-actions">
            <button class="primary-button" data-view-button="chat">${icon("sparkles")} 询问智能健康助手 <span class="arrow">↗</span></button>
            <button class="ghost-button" data-view-button="triage">${icon("scan")} 智能症状检测</button>
          </div>
        </div>
        <div class="hero-visual">
          <div class="orb-pulse"></div>
          <div class="orb-pulse"></div>
          <div class="health-orb"></div>
        </div>
      </section>

      <section class="metric-grid">
        ${metricCard("health", "健康评分", overview.score ?? "—", "/ 100", overview.status || "等待数据", overview.score >= 85 ? "delta-up" : "delta-warn")}
        ${metricCard("blood", "血压", bp, "毫米汞柱", latest.systolic ? "处于个人基线范围" : "尚未记录", latest.systolic && latest.systolic > 139 ? "delta-warn" : "delta-up")}
        ${metricCard("moon", "昨夜睡眠", latest.sleep_hours ?? "—", "小时", latest.sleep_hours && latest.sleep_hours < 7 ? "略低于目标" : "睡眠节律良好", latest.sleep_hours && latest.sleep_hours < 7 ? "delta-warn" : "delta-up")}
        ${metricCard("heart", "静息心率", latest.heart_rate ?? "—", "次/分", latest.heart_rate ? "心肺节律稳定" : "等待设备数据", "delta-up")}
      </section>

      <section class="dashboard-grid">
        <article class="card trend-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">身体信号趋势</h3>
              <p class="card-subtitle">数据来自最近 ${records.length} 次健康记录 · 自动识别偏离</p>
            </div>
            <div class="period-tabs">
              <button class="${state.chartMetric === "bp" ? "active" : ""}" data-dashboard-chart="bp">血压</button>
              <button class="${state.chartMetric === "sleep" ? "active" : ""}" data-dashboard-chart="sleep">睡眠</button>
            </div>
          </div>
          <div class="chart-summary">
            <div class="chart-number">
              ${state.chartMetric === "sleep"
                ? `<strong>${sleep.length ? (sleep.reduce((a, b) => a + b, 0) / sleep.length).toFixed(1) : "—"}</strong><span>小时</span><small>近 7 天平均睡眠</small>`
                : `<strong>${bp}</strong><span>毫米汞柱</span><small>最近一次测量 · ${formatTime(latest.measured_at)}</small>`}
            </div>
            <div class="legend-inline"><span><i></i>${state.chartMetric === "sleep" ? "睡眠时长" : "收缩压"}</span><span><i></i>${state.chartMetric === "sleep" ? "目标下限" : "舒张压"}</span></div>
          </div>
          <div class="line-chart">
            ${lineChart(
              trendValues.length ? trendValues : [0, 0, 0],
              chartLabels,
              state.chartMetric === "bp" ? { secondary: diastolic } : {},
            )}
          </div>
        </article>

        <article class="card insight-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">智能健康解读</h3>
              <p class="card-subtitle">基于个人基线的连续观察</p>
            </div>
            <span class="ai-chip">${icon("sparkles")} 智能洞察</span>
          </div>
          <div class="insight-main">
            ${scoreRing(overview.score ?? 0)}
            <div class="insight-copy">
              <strong>${escapeHtml(overview.status || "等待数据")}</strong>
              <p>${escapeHtml(overview.insight || "记录健康数据后，智能助手会开始识别你的个人趋势。")}</p>
            </div>
          </div>
          <div class="signal-list">
            ${signalRow("生命体征", vitalSignalScore(latest), latest.systolic ? "稳定" : "待记录")}
            ${signalRow("睡眠质量", latest.sleep_hours ? clamp(latest.sleep_hours / 8 * 100, 20, 100) : 0, latest.sleep_hours ? `${latest.sleep_hours}h` : "待记录")}
            ${signalRow("活动水平", latest.steps ? clamp(latest.steps / 10000 * 100, 15, 100) : 0, latest.steps ? `${Math.round(latest.steps / 1000)}k 步` : "待记录")}
          </div>
          ${(data.longitudinal || []).length ? `
            <div class="longitudinal-list">
              <span class="longitudinal-label">纵向关联洞察</span>
              ${data.longitudinal.map((item) => `
                <div class="longitudinal-item ${item.severity}">
                  <i></i>
                  <div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.detail)}</p></div>
                </div>`).join("")}
            </div>` : ""}
          <button class="insight-action" data-view-button="health">查看完整体检趋势 ${icon("arrow")}</button>
        </article>
      </section>

      <section class="bottom-grid">
        <article class="card conversation-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">最近健康对话</h3>
              <p class="card-subtitle">上下文和健康结论已自动保存</p>
            </div>
            <button class="text-button" data-all-conversations>查看全部 ${icon("arrow")}</button>
          </div>
          <div class="recent-list">
            ${conversations.length ? conversations.map(conversationRow).join("") : `
              <div class="evidence-empty">还没有对话。向智能助手描述你的健康问题，系统会记住完整上下文。</div>
            `}
          </div>
        </article>
        <article class="card timeline-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">今日健康轨迹</h3>
              <p class="card-subtitle">来自设备、记录与智能分析</p>
            </div>
            <span class="tag jade"><span class="status-dot"></span>实时</span>
          </div>
          <div class="timeline">
            <div class="timeline-item">
              <div class="timeline-time">${formatTime(latest.measured_at) || "08:32"}</div>
              <div class="timeline-copy">最近一次体征同步</div>
              <div class="timeline-note">${bp !== "—" ? `血压 ${bp} 毫米汞柱 · 心率 ${latest.heart_rate || "—"} 次/分` : "等待健康设备同步"}</div>
            </div>
            <div class="timeline-item">
              <div class="timeline-time">07:15</div>
              <div class="timeline-copy">智能助手完成夜间健康复盘</div>
              <div class="timeline-note">${latest.sleep_hours ? `识别睡眠 ${latest.sleep_hours} 小时，节律${latest.sleep_hours >= 7 ? "良好" : "需关注"}` : "尚无睡眠数据"}</div>
            </div>
            <div class="timeline-item">
              <div class="timeline-time">昨日 22:40</div>
              <div class="timeline-copy">个人健康基线更新</div>
              <div class="timeline-note">已结合 ${data.graph?.nodes ? `${Math.round(data.graph.nodes / 1000)}k+` : "14 万+"} 医疗实体进行上下文校准</div>
            </div>
          </div>
        </article>
      </section>
    </div>`;

  $$("[data-view-button]", $("#view-stack")).forEach((button) => {
    button.addEventListener("click", () => renderView(button.dataset.viewButton));
  });
  $$("[data-open-record]", $("#view-stack")).forEach((button) => button.addEventListener("click", openRecordModal));
  $$("[data-go-dashboard-health]", $("#view-stack")).forEach((button) => {
    button.addEventListener("click", () => renderView("health"));
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        renderView("health");
      }
    });
  });
  $$("[data-all-conversations]", $("#view-stack")).forEach((button) => button.addEventListener("click", () => renderView("chat")));
  $$("[data-dashboard-chart]", $("#view-stack")).forEach((button) => {
    button.addEventListener("click", () => {
      state.chartMetric = button.dataset.dashboardChart;
      renderDashboard(++renderSequence);
    });
  });
  $$("[data-conversation-id]", $("#view-stack")).forEach((row) => {
    row.addEventListener("click", () => openConversation(row.dataset.conversationId));
  });
}

function conversationRow(conversation) {
  const risk = {
    low: ["低风险", "jade"],
    medium: ["需观察", "amber"],
    high: ["高风险", "red"],
    emergency: ["急症", "red"],
  }[conversation.risk_level] || ["健康咨询", ""];
  return `
    <div class="recent-conversation" data-conversation-id="${escapeHtml(conversation.id)}">
      <span class="conversation-icon">${icon("message")}</span>
      <div class="recent-copy">
        <div class="recent-question">${escapeHtml(displayConversationTitle(conversation.title))}</div>
        <div class="recent-preview">${escapeHtml((conversation.last_message || "开始新的健康对话").replace(/[#*>`]/g, ""))}</div>
      </div>
      <div class="recent-meta"><span class="tag ${risk[1]}">${risk[0]}</span><div style="margin-top:6px">${relativeDate(conversation.updated_at)}</div></div>
    </div>`;
}

/* Chat */
function startNewChat() {
  state.activeConversationId = null;
  state.activeConversation = null;
  renderView("chat");
}

async function openConversation(id) {
  if (
    state.view === "chat" &&
    state.activeConversationId === id
  ) {
    return;
  }
  state.activeConversationId = id;
  state.activeConversation = null;
  renderView("chat");
}

async function loadConversations() {
  const data = await api("/api/conversations");
  state.conversations = data.conversations || [];
  const existing = new Set(state.conversations.map((item) => item.id));
  [...state.sidebarSelected].forEach((id) => {
    if (!existing.has(id)) state.sidebarSelected.delete(id);
  });
  renderSidebarHistory();
}

const CONVERSATION_CATEGORIES = [
  {
    name: "耳鼻喉科",
    short: "耳",
    keywords: ["耳", "鼻", "咽喉", "喉咙", "扁桃体", "听力", "耳鸣", "鼻炎", "鼻塞", "声音嘶哑"],
  },
  {
    name: "外科",
    short: "外",
    keywords: ["外伤", "伤口", "手术", "阑尾", "疝", "肿块", "包块", "出血", "缝合", "腹腔镜"],
  },
  {
    name: "皮肤科",
    short: "皮",
    keywords: ["皮肤", "皮疹", "瘙痒", "湿疹", "荨麻疹", "痘", "斑", "脱发"],
  },
  {
    name: "妇产科",
    short: "妇",
    keywords: ["月经", "经期", "痛经", "孕", "妇科", "盆腔", "白带", "卵巢", "子宫"],
  },
  {
    name: "儿科",
    short: "儿",
    keywords: ["儿童", "宝宝", "婴儿", "小儿", "孩子", "幼儿"],
  },
  {
    name: "骨科",
    short: "骨",
    keywords: ["骨折", "关节", "颈椎", "腰椎", "腰痛", "膝盖", "扭伤", "骨痛"],
  },
  {
    name: "口腔科",
    short: "口",
    keywords: ["牙", "口腔", "牙龈", "智齿", "口臭"],
  },
  {
    name: "内科",
    short: "内",
    keywords: [
      "头晕", "头痛", "发热", "发烧", "咳嗽", "胸闷", "胸痛", "心悸", "血压",
      "血糖", "贫血", "血红蛋白", "胃", "肝", "肾", "甲状腺", "呼吸", "消化",
      "乏力", "失眠", "恶心", "呕吐", "腹痛", "腹泻", "糖尿病", "高血压",
    ],
  },
];

function classifyConversation(conversation) {
  // The category must come from the user's consultation topic. Assistant
  // answers often mention several specialties and would create false groups.
  const text = conversation.title || "";
  const matched = CONVERSATION_CATEGORIES.find((category) =>
    category.keywords.some((keyword) => text.includes(keyword))
  );
  return matched || { name: "内科", short: "内" };
}

function renderSidebarHistory() {
  const container = $("#sidebar-history");
  if (!container) return;
  const open = Boolean(state.sidebarSpaceOpen);
  const totalCount = state.conversations.length;
  $("#sidebar")?.classList.toggle("space-expanded", open);
  $("#sidebar-space-head")?.classList.toggle("is-open", open);
  $("#sidebar-space-toggle")?.setAttribute("aria-expanded", open ? "true" : "false");
  const spaceToggle = $("#sidebar-space-toggle");
  if (spaceToggle) {
    spaceToggle.title = open ? "收起我的空间" : "展开并查看全部对话";
  }
  const countNode = $("#sidebar-space-count");
  if (countNode) countNode.textContent = String(totalCount);
  const manageNode = $("#sidebar-manage");
  if (manageNode) manageNode.hidden = !open;
  $("#sidebar-manage")?.classList.toggle("active", state.sidebarManage);
  container.classList.toggle("is-collapsed", !open);
  if (!open) {
    container.innerHTML = "";
    return;
  }
  if (!state.conversations.length) {
    container.innerHTML = `<div class="sidebar-history-empty">暂无对话记录<br/>开始咨询后会自动归类</div>`;
    return;
  }
  const grouped = new Map();
  for (const conversation of state.conversations) {
    const category = classifyConversation(conversation);
    if (!grouped.has(category.name)) grouped.set(category.name, { category, items: [] });
    grouped.get(category.name).items.push(conversation);
  }
  const categoryOrder = ["内科", "外科", "耳鼻喉科", "皮肤科", "妇产科", "儿科", "骨科", "口腔科"];
  const groups = [...grouped.values()].sort(
    (a, b) => categoryOrder.indexOf(a.category.name) - categoryOrder.indexOf(b.category.name)
  );
  const total = totalCount;
  const selectedCount = state.sidebarSelected.size;
  const allSelected = selectedCount === total;
  const bulkBar = state.sidebarManage ? `
    <div class="sidebar-bulk">
      <span>已选 <b>${selectedCount}</b> / ${total}</span>
      <button type="button" class="sidebar-bulk-all" data-select-all>
        ${allSelected ? "取消全选" : "全选"}
      </button>
      <button type="button" class="sidebar-bulk-delete" data-delete-selected ${selectedCount ? "" : "disabled"}>
        ${icon("trash")} 删除
      </button>
    </div>` : "";
  container.innerHTML = bulkBar + groups.map(({ category, items }) => `
    <section class="sidebar-category">
      <div class="sidebar-category-head">
        <span class="sidebar-category-mark">${escapeHtml(category.short)}</span>
        <strong>${escapeHtml(category.name)}</strong>
        <small>${items.length}</small>
      </div>
      ${items.map((conversation) => {
        const selected = state.sidebarSelected.has(conversation.id);
        const active = conversation.id === state.activeConversationId;
        return `
          <div class="sidebar-row${selected ? " selected" : ""}${active ? " active" : ""}">
            ${state.sidebarManage ? `
              <button type="button" class="sidebar-check${selected ? " on" : ""}" data-select-conversation="${escapeHtml(conversation.id)}" aria-pressed="${selected ? "true" : "false"}" title="${selected ? "取消选择" : "选择这段对话"}">
                ${icon("check")}
              </button>` : ""}
            <button type="button" class="sidebar-conversation${active ? " active" : ""}" data-sidebar-conversation="${escapeHtml(conversation.id)}" title="${escapeHtml(displayConversationTitle(conversation.title))}">
              <i></i><span>${escapeHtml(displayConversationTitle(conversation.title))}</span>
            </button>
            ${state.sidebarManage ? "" : `
              <button type="button" class="sidebar-delete" data-delete-conversation="${escapeHtml(conversation.id)}" title="删除这段对话" aria-label="删除这段对话">
                ${icon("trash")}
              </button>`}
          </div>`;
      }).join("")}
    </section>
  `).join("");
  $$("[data-sidebar-conversation]", container).forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.sidebarConversation;
      if (state.sidebarManage) {
        toggleSidebarSelection(id);
        return;
      }
      openConversation(id);
    });
  });
  $$("[data-select-conversation]", container).forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleSidebarSelection(button.dataset.selectConversation);
    });
  });
  $$("[data-delete-conversation]", container).forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteSidebarConversation(button.dataset.deleteConversation);
    });
  });
  $("[data-select-all]", container)?.addEventListener("click", () => {
    if (state.sidebarSelected.size === state.conversations.length) {
      state.sidebarSelected.clear();
    } else {
      state.conversations.forEach((conversation) => state.sidebarSelected.add(conversation.id));
    }
    renderSidebarHistory();
  });
  $("[data-delete-selected]", container)?.addEventListener("click", deleteSidebarSelection);
}

function toggleSidebarSelection(id) {
  if (!id) return;
  if (state.sidebarSelected.has(id)) state.sidebarSelected.delete(id);
  else state.sidebarSelected.add(id);
  renderSidebarHistory();
}

async function deleteSidebarConversation(id) {
  if (!id) return;
  if (!confirm("删除这段对话及全部上下文？此操作不可恢复。")) return;
  try {
    await api(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
    state.sidebarSelected.delete(id);
    if (state.activeConversationId === id) {
      state.activeConversationId = null;
      state.activeConversation = null;
      state.sidebarManage = false;
    }
    await loadConversations();
    if (state.view === "chat") await renderChat();
    toast("对话已删除");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteSidebarSelection() {
  const ids = [...state.sidebarSelected];
  if (!ids.length) return;
  if (!confirm(`删除选中的 ${ids.length} 段对话及全部上下文？此操作不可恢复。`)) return;
  let removed = 0;
  const failed = [];
  for (const id of ids) {
    try {
      await api(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
      removed += 1;
      if (state.activeConversationId === id) {
        state.activeConversationId = null;
        state.activeConversation = null;
      }
    } catch (error) {
      failed.push(id);
    }
  }
  state.sidebarSelected.clear();
  if (!failed.length) state.sidebarManage = false;
  await loadConversations();
  if (state.view === "chat") await renderChat();
  if (removed) toast(`已删除 ${removed} 段对话`);
  if (failed.length) toast(`${failed.length} 段对话删除失败，请重试`, "error");
}

async function loadActiveConversation() {
  if (!state.activeConversationId) {
    state.activeConversation = null;
    return;
  }
  const data = await api(`/api/conversations/${encodeURIComponent(state.activeConversationId)}`);
  state.activeConversation = data.conversation;
}

async function renderChat(renderToken = renderSequence) {
  state.evidenceGraph?.destroy();
  state.evidenceGraph = null;
  await loadConversations();
  if (state.activeConversationId) await loadActiveConversation();
  if (renderToken !== renderSequence || state.view !== "chat") return;
  const conversation = state.activeConversation;
  const messages = conversation?.messages || [];
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
  const trace = lastAssistant?.trace || {};
  const title = displayConversationTitle(conversation?.title || "新的健康咨询");
  const hasMessages = messages.length > 0;

  $("#view-stack").innerHTML = `
    <div class="chat-page page-enter">
      <div class="chat-workspace">
        <section class="chat-main">
          <header class="chat-head">
            <div class="chat-title">
              <h1>${escapeHtml(title)}</h1>
              <p><i class="live-dot"></i> 已载入个人档案与图谱上下文 · 对话自动保存</p>
            </div>
            <div class="chat-head-actions">
              <select class="history-select" id="conversation-select" aria-label="切换历史会话">
                <option value="">＋ 新对话</option>
                ${state.conversations.map((item) => `
                  <option value="${escapeHtml(item.id)}" ${item.id === state.activeConversationId ? "selected" : ""}>
                    ${escapeHtml(displayConversationTitle(item.title))}
                  </option>`).join("")}
              </select>
              <button class="icon-button" id="chat-new-button" aria-label="新建对话">${icon("plus")}</button>
              <button class="icon-button" id="toggle-composer" aria-label="收起或展开输入框" title="收起/展开输入框">${icon("chevron")}</button>
              ${conversation ? `<button class="icon-button" id="delete-conversation" aria-label="删除对话">${icon("trash")}</button>` : ""}
            </div>
          </header>

          <div class="messages" id="chat-messages">
            ${hasMessages ? messages.map((message, index) => messageBubble(message, index)).join("") : chatWelcome()}
            ${state.sending ? typingMessage() : ""}
          </div>

          <div class="chat-composer-wrap ${state.composerCollapsed ? "is-collapsed" : ""}" id="composer-wrap">
            <button class="composer-reveal" id="composer-reveal" type="button">
              ${icon("message")} 继续对话 <span>展开输入框</span>
            </button>
            <div class="chat-composer">
              <div class="chat-image-preview" id="chat-image-preview" ${state.chatImage ? "" : "hidden"}>
                ${state.chatImage ? `<img src="${state.chatImage.dataUrl}" alt="待发送图片预览"/><div><strong>${escapeHtml(state.chatImage.name)}</strong><small>将使用视觉模型分析，图片不保存</small></div><button type="button" id="remove-chat-image" aria-label="移除图片">${icon("close")}</button>` : ""}
              </div>
              <textarea id="chat-input" rows="2" maxlength="4000" placeholder="描述你的症状、检查结果，或继续追问…"></textarea>
              <input id="chat-image-input" type="file" accept="image/jpeg,image/png,image/webp" hidden />
              <div class="composer-footer">
                <div class="composer-tools">
                  <button class="composer-tool" id="composer-image" type="button">${icon("image")} 图片</button>
                  <button class="composer-tool" id="composer-body-map" type="button">${icon("user")} 人体定位</button>
                </div>
                <div class="composer-actions">
                  <button class="composer-collapse" id="composer-hide" type="button" title="收起输入框">${icon("chevron")}</button>
                  <button class="send-button" id="send-message" aria-label="发送消息" ${state.sending ? "disabled" : ""}>${icon("send")}</button>
                </div>
              </div>
            </div>
            <p class="composer-hint">智能助手可能出错，请核对信息。紧急情况请立即拨打 120。</p>
          </div>
        </section>

        <aside class="chat-evidence">
          <header class="evidence-head">
            <div><strong>证据链</strong><span>${trace.evidence_count ? `${trace.evidence_count} 条图谱关系已检索` : "等待本轮检索"}</span></div>
            <span class="evidence-live"><i class="live-dot"></i> 实时</span>
          </header>
          <div class="evidence-scroll">
            <div class="evidence-graph-card">
              <canvas id="evidence-graph-canvas"></canvas>
              <span class="graph-overlay-label">医疗知识图谱检索</span>
              <button class="graph-expand-button" id="expand-evidence-graph" type="button" title="放大并交互查看知识图谱">${icon("scan")} <span>查看图谱</span></button>
            </div>
            ${tracePanel(trace)}
          </div>
        </aside>
      </div>
    </div>`;

  bindChatEvents();
  if (trace.graph?.nodes?.length) {
    const canvas = $("#evidence-graph-canvas");
    if (canvas) {
      state.evidenceGraph = new Graph3D(canvas, trace.graph, {
        compact: true,
        interactive: true,
        onSelect: (node) => openGraphInspector(trace.graph, node),
      });
    }
    $("#expand-evidence-graph").addEventListener("click", () => {
      openGraphInspector(trace.graph);
    });
  } else {
    $("#expand-evidence-graph")?.addEventListener("click", () => {
      toast("发送一条健康问题后即可查看关联图谱");
    });
  }
}

function chatWelcome() {
  const suggestions = [
    ["症状理解", "最近起床时总是头晕，可能和什么有关？"],
    ["用药安全", "服用感冒药时，需要注意哪些常见风险？"],
    ["检查解读", "体检报告显示血红蛋白偏低，应该关注什么？"],
    ["健康管理", "结合我的档案，帮我制定一周睡眠改善计划。"],
  ];
  return `
    <section class="chat-welcome">
      <div class="welcome-symbol"><span>衡</span></div>
      <h2>今天，身体想告诉你什么？</h2>
      <p>我会先理解症状，再从 14 万级医疗知识图谱中检索证据，并结合你的健康档案给出安全、可解释的建议。</p>
      <div class="suggestion-grid">
        ${suggestions.map(([type, text]) => `
          <button class="suggestion-card" data-suggestion="${escapeHtml(text)}">
            <span>${type}</span><strong>${text}</strong>
          </button>`).join("")}
      </div>
    </section>`;
}

function messageBubble(message, index = null) {
  const isUser = message.role === "user";
  const trace = message.trace || {};
  const citations = isUser ? [] : trace.citations || [];
  const displayContent = isUser
    ? message.content
    : String(message.content || "")
        .replace(/\n?\s*\*\*引用依据\*\*[\s\S]*$/m, "")
        .replace(/\[E\d+\]/g, "")
        .trim();
  const modeLabels = {
    deepseek: "DeepSeek · 证据约束生成",
    "deepseek-vision": "DeepSeek 视觉模型 · 图像与图谱联合分析",
    "grounded-demo": "Neo4j · 本地证据引擎",
    "grounded-fallback": "图谱证据 · 模型降级保护",
    "input-guidance": "本地输入引导",
  };
  return `
    <div class="message-row ${isUser ? "user" : "assistant"}" ${index === null ? "" : `data-message-index="${index}"`}>
      ${isUser ? "" : `<span class="message-avatar">衡</span>`}
      <div class="message-content">
        <div class="message-label">
          <strong>${isUser ? escapeHtml(state.user?.name || "我") : "知衡健康"}</strong>
          <span>${formatTime(message.created_at)}</span>
        </div>
        <div class="message-bubble">${formatMarkdown(displayContent)}</div>
        ${!isUser && citations.length ? `
          <details class="message-citations">
            <summary>${icon("book")} 引用依据 <span>${citations.length} 条</span></summary>
            <div class="message-citation-list">
              ${citations.map((citation) => `
                <button class="citation-item" type="button" data-citation="${escapeHtml(citation.id)}">
              <b>[${escapeHtml(displayEvidenceId(citation.id))}]</b>
                  <span>${escapeHtml(citation.subject)} — ${escapeHtml(citation.predicate)} → ${escapeHtml(citation.object)}</span>
                </button>`).join("")}
            </div>
          </details>` : ""}
        ${!isUser ? `
          <div class="message-source">
            <span class="dot"></span>${modeLabels[trace.source_mode] || "健康知识助手"}
            ${trace.evidence_count ? `· ${trace.evidence_count} 条证据` : ""}
            ${trace.triage ? `· ${statusFromTrace(trace)[0]}` : ""}
            ${trace.has_image ? `· 图片分析` : ""}
            ${trace.review ? reviewChip(trace.review) : ""}
          </div>` : ""}
      </div>
    </div>`;
}

function typingMessage() {
  return `
    <div class="message-row assistant">
      <span class="message-avatar">衡</span>
      <div class="message-content">
        <div class="message-label"><strong>知衡健康</strong><span>正在分析</span></div>
        <div class="message-bubble">
          <div class="thinking-pipeline">
            <span class="active">${icon("search")} 识别医疗意图</span>
            <span>${icon("graph")} 混合召回与关系过滤</span>
            <span>${icon("shield")} 校验安全与引用</span>
          </div>
        </div>
      </div>
    </div>`;
}

function tracePanel(trace) {
  const entities = trace.entities || [];
  const risk = trace.triage || {};
  const citations = (trace.citations || []).slice(0, 8);
  if (!entities.length && !risk.level) {
    return `
      <div class="evidence-empty">
        ${icon("graph")}<br/>
        发送健康问题后，这里会展示命中的医疗实体、Neo4j 关系与分诊依据。
      </div>`;
  }
  const riskColor = { low: "jade", medium: "amber", high: "red", emergency: "red" }[risk.level] || "jade";
  return `
    <section class="evidence-section">
      <div class="evidence-section-title"><span>图谱命中实体</span><span>${entities.length} ENTITIES</span></div>
      <div class="entity-chips">
        ${entities.map((entity) => `
          <span class="entity-chip"><i></i>${escapeHtml(entity.name)}<small style="color:#687d74">${escapeHtml(labelChinese(entity.type_label || entity.type))} · ${entity.match_type === "hybrid" ? "混合" : entity.match_type === "vector" ? "语义" : "关键词"}</small></span>
        `).join("")}
      </div>
    </section>
    <section class="evidence-section">
      <div class="risk-mini"><span>规则分诊</span><strong style="color:var(--${riskColor})">${escapeHtml(risk.title || "未评估")}</strong></div>
    </section>
    ${trace.retrieval ? `
      <section class="evidence-section">
        <div class="risk-mini"><span>混合检索</span><strong>${trace.retrieval.vector_index?.ready ? "关键词 + 向量召回" : "关键词召回"} · ${trace.retrieval.evidence_quality === "high" ? "证据充分" : trace.retrieval.evidence_quality === "medium" ? "证据有限" : "证据不足"}</strong></div>
      </section>` : ""}
    ${trace.tool_calls?.length ? `
      <details class="evidence-details">
        <summary>${icon("activity")} 工具调用记录 <span>${trace.tool_calls.length} 步</span></summary>
        ${trace.tool_calls.map((call) => `
          <div class="tool-call-row">
          <i></i><div><strong>${escapeHtml(displayToolName(call.name))}</strong><small>${escapeHtml(call.status === "success" ? "成功" : call.status || "完成")}${call.result_count !== undefined ? ` · ${call.result_count} 条` : ""}${call.duration_ms ? ` · ${call.duration_ms} 毫秒` : ""}</small></div>
          </div>`).join("")}
      </details>` : ""}
    ${trace.review ? `
      <section class="evidence-section">
        <div class="evidence-section-title"><span>智能医学复核</span><span>${trace.review.llm_used ? "模型与规则" : "规则校验"}</span></div>
        <div class="review-panel">
          ${reviewChip(trace.review)}
          <p class="review-note">${escapeHtml(reviewSummary(trace.review))}</p>
          ${(trace.review.issues || []).length ? `
            <div class="review-issues">
              ${trace.review.issues.slice(0, 6).map((issue) => `
                <div class="review-issue ${issue.severity === "high" ? "high" : ""}"><i></i>${escapeHtml(issue.message)}</div>`).join("")}
            </div>` : ""}
        </div>
      </section>` : ""}
    ${citations.length ? `
      <section class="evidence-section">
        <div class="evidence-section-title"><span>可引用证据</span><span>${trace.retrieval?.filtered_fact_count || citations.length} FILTERED</span></div>
        ${citations.map((citation) => `
          <button class="evidence-fact citation-row" type="button" data-citation="${escapeHtml(citation.id)}">
            <b>[${escapeHtml(citation.id)}]</b>
            <strong>${escapeHtml(citation.subject)}</strong>
            <span>— ${escapeHtml(citation.predicate)} →</span>
            <strong>${escapeHtml(citation.object)}</strong>
          </button>`).join("")}
      </section>` : ""}
    ${risk.red_flags?.length ? `
      <section class="evidence-section">
        <div class="evidence-section-title"><span>急症警示</span><span>危险信号</span></div>
        ${risk.red_flags.map((item) => `<div class="red-flag-item"><i></i>${escapeHtml(item)}</div>`).join("")}
      </section>` : ""}`;
}

function getLatestTrace() {
  const messages = state.activeConversation?.messages || [];
  return [...messages].reverse().find((message) => message.role === "assistant")?.trace || {};
}

function openCitationModal(citation) {
  if (!citation) {
    toast("当前回答没有可展开的图谱引用", "error");
    return;
  }
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card citation-modal" role="dialog" aria-modal="true" aria-labelledby="citation-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 可追溯证据</span><h2 class="modal-title" id="citation-title">引用 [${escapeHtml(displayEvidenceId(citation.id))}]</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">下面是本轮检索中真实返回的 Neo4j 关系，不是模型自行补充的来源。</p>
      <div class="citation-detail">
        <div class="citation-entity"><span>${escapeHtml(citation.subject_type || "实体")}</span><strong>${escapeHtml(citation.subject)}</strong></div>
        <div class="citation-relation">${icon("arrow")}<span>${escapeHtml(citation.predicate)}</span></div>
        <div class="citation-entity"><span>${escapeHtml(citation.object_type || "实体")}</span><strong>${escapeHtml(citation.object)}</strong></div>
      </div>
      <div class="citation-source"><strong>来源</strong><span>${escapeHtml(citation.source || "Neo4j 医疗知识图谱")}</span></div>
      <div class="modal-actions">
        <button class="ghost-button" data-close-modal>关闭</button>
        <button class="primary-button" id="open-citation-graph" type="button">${icon("graph")} 在图谱中查看</button>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#open-citation-graph").addEventListener("click", () => {
    closeModal();
    state.graphFocus = citation.subject;
    renderView("graph");
  });
}

function bindMessageActions() {
  const latestTrace = getLatestTrace();
  $$(".citation-ref, .citation-item").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const row = button.closest("[data-message-index]");
      const index = row ? Number(row.dataset.messageIndex) : -1;
      const trace = index >= 0
        ? state.activeConversation?.messages?.[index]?.trace || {}
        : latestTrace;
      const citation = (trace.citations || []).find((item) => item.id === button.dataset.citation);
      openCitationModal(citation);
    });
  });
  $$(".citation-row").forEach((button) => {
    button.addEventListener("click", () => {
      const citation = (latestTrace.citations || []).find((item) => item.id === button.dataset.citation);
      openCitationModal(citation);
    });
  });
}

function bindChatEvents() {
  const input = $("#chat-input");
  const send = () => sendChatMessage();
  $("#send-message").addEventListener("click", send);
  $("#composer-image").addEventListener("click", () => $("#chat-image-input").click());
  $("#composer-body-map").addEventListener("click", () => {
    openBodyMap((region) => {
      const existing = input.value.trim();
      input.value = existing ? `${existing} ${region.prompt}` : region.prompt;
      input.dispatchEvent(new Event("input"));
      input.focus();
      toast(`已带入${region.label}，可继续补充疼痛性质和持续时间`);
    });
  });
  $("#chat-image-input").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setChatImage(await compressImageFile(file));
      toast("图片已添加，可补充描述后发送");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      event.target.value = "";
    }
  });
  $("#remove-chat-image")?.addEventListener("click", () => setChatImage(null));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
  });
  $$(".suggestion-card").forEach((card) => {
    card.addEventListener("click", () => {
      input.value = card.dataset.suggestion;
      input.focus();
    });
  });
  $("#conversation-select").addEventListener("change", (event) => {
    const id = event.target.value;
    if (id) openConversation(id);
    else startNewChat();
  });
  $("#chat-new-button").addEventListener("click", startNewChat);
  const setComposerCollapsed = (collapsed) => {
    state.composerCollapsed = collapsed;
    $("#composer-wrap")?.classList.toggle("is-collapsed", collapsed);
    if (!collapsed) setTimeout(() => $("#chat-input")?.focus(), 30);
  };
  $("#toggle-composer").addEventListener("click", () => setComposerCollapsed(!state.composerCollapsed));
  $("#composer-hide").addEventListener("click", () => setComposerCollapsed(true));
  $("#composer-reveal").addEventListener("click", () => setComposerCollapsed(false));
  $("#delete-conversation")?.addEventListener("click", async () => {
    if (!state.activeConversationId) return;
    if (!confirm("删除这段对话及其全部上下文？此操作不可恢复。")) return;
    try {
      await api(`/api/conversations/${encodeURIComponent(state.activeConversationId)}`, { method: "DELETE" });
      toast("对话已删除");
      startNewChat();
    } catch (error) {
      toast(error.message, "error");
    }
  });
  requestAnimationFrame(() => {
    const messages = $("#chat-messages");
    if (messages) messages.scrollTop = messages.scrollHeight;
  });
  const lastAssistant = [...(state.activeConversation?.messages || [])]
    .reverse()
    .find((message) => message.role === "assistant");
  if (lastAssistant) {
    const live = $("#sr-live");
    if (live) live.textContent = "新回答：" + lastAssistant.content.replace(/[#*>`]/g, "").slice(0, 90);
  }
  bindMessageActions();
}

async function sendChatMessage() {
  if (state.sending) return;
  const input = $("#chat-input");
  const typedMessage = input?.value.trim() || "";
  const image = state.chatImage;
  const message = typedMessage || (image ? "请分析这张图片中可见的健康相关信息。" : "");
  if (!message) {
    input?.focus();
    return;
  }
  state.sending = true;
  input.value = "";
  input.disabled = true;
  const messagesElement = $("#chat-messages");
  const welcome = $(".chat-welcome", messagesElement);
  welcome?.remove();
  messagesElement.insertAdjacentHTML("beforeend", messageBubble({
    role: "user",
    content: image ? `[图片] ${typedMessage || "请分析图片"}` : message,
    created_at: new Date().toISOString(),
  }));
  messagesElement.insertAdjacentHTML("beforeend", typingMessage());
  messagesElement.scrollTop = messagesElement.scrollHeight;
  try {
    const payload = {
      conversation_id: state.activeConversationId,
      message,
      image_data: image?.dataUrl || null,
    };
    const streamed = await streamAnswer(payload, messagesElement);
    let result = streamed;
    if (!result) {
      result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    setChatImage(null);
    state.activeConversationId = result.conversation_id;
    await loadActiveConversation();
    state.sending = false;
    await renderChat();
  } catch (error) {
    state.sending = false;
    input.disabled = false;
    $$(".typing-bubble, .streaming-message").forEach((node) => {
      node.closest(".message-row")?.remove();
    });
    toast(error.message, "error");
    if (error.status === 401) showAuth();
  }
}

async function streamAnswer(payload, messagesElement) {
  const typingRow = $(".typing-bubble")?.closest(".message-row");
  if (!window.fetch || !window.TextDecoder) return null;
  let response;
  try {
    response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
  } catch {
    return null;
  }
  if (!response.ok || !response.body) return null;

  const bubble = document.createElement("div");
  bubble.className = "message-row assistant streaming-message";
  bubble.innerHTML = `
    <span class="message-avatar">衡</span>
    <div class="message-content">
      <div class="message-label"><strong>知衡健康</strong><span>正在生成回答</span></div>
      <div class="message-bubble"><span class="stream-cursor"></span></div>
    </div>`;
  typingRow?.remove();
  messagesElement.appendChild(bubble);
  const content = $(".message-bubble", bubble);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let raw = "";
  let text = "";
  let conversationId = null;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    raw += decoder.decode(value, { stream: true });
    const frames = raw.split("\n\n");
    raw = frames.pop() || "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      let parsed;
      try {
        parsed = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (parsed.token) {
        text += parsed.token;
        content.innerHTML = formatMarkdown(text) + '<span class="stream-cursor"></span>';
        messagesElement.scrollTop = messagesElement.scrollHeight;
      }
      if (parsed.revision) {
        text = parsed.revision;
        content.innerHTML = formatMarkdown(text) + '<span class="stream-cursor"></span>';
        messagesElement.scrollTop = messagesElement.scrollHeight;
      }
      if (parsed.done) conversationId = parsed.conversation_id;
    }
  }
  content.innerHTML = formatMarkdown(text);
  if (!text.trim() || !conversationId) {
    bubble.remove();
    return null;
  }
  return { conversation_id: conversationId };
}

async function openVisitSummary() {
  let data;
  try {
    data = await api("/api/health/summary");
  } catch (error) {
    toast(error.message, "error");
    return;
  }
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card visit-summary-modal" role="dialog" aria-modal="true" aria-labelledby="visit-summary-title">
      <div class="settings-head no-print">
        <div><span class="eyebrow"><span></span> 就诊摘要</span><h2 class="modal-title" id="visit-summary-title">就诊前健康摘要</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle no-print">由你的记录自动整理，用于就诊沟通，可直接打印或出示给医生。</p>
      <pre class="visit-summary-body">${escapeHtml(data.summary)}</pre>
      <div class="modal-actions no-print">
        <button class="ghost-button" data-close-modal>关闭</button>
        <button class="ghost-button" id="copy-visit-summary">${icon("download")} 复制文本</button>
        <button class="ghost-button" id="email-visit-summary">${icon("mail")} 发送到邮箱</button>
        <button class="primary-button" id="print-visit-summary">${icon("download")} 打印</button>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#print-visit-summary").addEventListener("click", () => window.print());
  $("#email-visit-summary").addEventListener("click", (event) => {
    sendHealthReport("visit_summary", event.currentTarget);
  });
  $("#copy-visit-summary").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(data.summary);
      toast("摘要已复制");
    } catch {
      toast("浏览器不允许复制，请手动选择文本", "error");
    }
  });
}

/* Health records */
async function renderHealth(renderToken = renderSequence) {
  const [recordsData, profileData, timelineData] = await Promise.all([
    api("/api/health/records?limit=30"),
    api("/api/health/profile"),
    api("/api/health/timeline?limit=12"),
  ]);
  if (renderToken !== renderSequence || state.view !== "health") return;
  state.healthData = {
    ...recordsData,
    profile: profileData.profile,
    timeline: timelineData.events || [],
  };
  const records = recordsData.records || [];
  const overview = recordsData.overview || {};
  const latest = overview.latest || {};
  const profile = profileData.profile || {};
  const metric = state.chartMetric === "bp" ? "bp" : state.chartMetric;
  const reversed = [...records].reverse();
  const labels = reversed.map((record) => formatDate(record.measured_at));
  const values = chartMetricValues(reversed, metric);
  const metricMeta = {
    bp: ["收缩压", "毫米汞柱", "systolic"],
    heart_rate: ["心率", "次/分", "heart_rate"],
    sleep_hours: ["睡眠", "小时", "sleep_hours"],
    glucose: ["血糖", "mmol/L", "glucose"],
    weight_kg: ["体重", "千克", "weight_kg"],
  }[metric] || ["收缩压", "毫米汞柱", "systolic"];
  const displayName = profile.gender === "女" ? "女士" : profile.gender === "男" ? "先生" : "";
  const age = ageFromBirthDate(profile.birth_date);

  $("#view-stack").innerHTML = `
    <div class="page-enter">
      <div class="page-heading">
        <div class="page-heading-copy">
          <span>连续健康档案</span>
          <h1>健康档案</h1>
          <p>理解长期变化，而不只是记住一次测量。</p>
        </div>
        <div class="heading-actions">
          <button class="ghost-button" id="open-passport-button">${icon("book")} 健康证据护照</button>
          <button class="ghost-button" id="open-summary-button">${icon("download")} 就诊摘要</button>
          <button class="ghost-button" id="edit-profile-button">${icon("edit")} 编辑档案</button>
          <button class="primary-button" style="height:35px;padding:0 14px;font-size:9px" data-open-record>${icon("plus")} 添加记录</button>
        </div>
      </div>

      <div class="health-layout">
        <div class="health-main-stack">
          <section class="card vitals-overview">
            <div class="health-score-block">
              ${scoreRing(overview.score ?? 0)}
              <span>${escapeHtml(overview.status || "等待数据")}</span>
              <p>基于最近 7 天个人趋势</p>
            </div>
            <div class="vitals-list">
              ${vitalItem("血压", latest.systolic ? `${latest.systolic}/${latest.diastolic}` : "—", "毫米汞柱", latest.systolic >= 90 && latest.systolic <= 140 ? "处于参考范围" : "建议复测")}
              ${vitalItem("静息心率", latest.heart_rate ?? "—", "次/分", latest.heart_rate && latest.heart_rate <= 100 ? "节律平稳" : "等待数据")}
              ${vitalItem("空腹血糖", latest.glucose ?? "—", "mmol/L", latest.glucose && latest.glucose >= 3.9 && latest.glucose <= 6.1 ? "处于参考范围" : "结合测量时间判断")}
              ${vitalItem("血氧", latest.spo2 ?? "—", "%", latest.spo2 >= 95 ? "氧合良好" : "建议复测")}
            </div>
          </section>

          <section class="card full-trend-card">
            <div class="card-header">
              <div><h3 class="card-title">连续指标趋势</h3><p class="card-subtitle">自动识别个人基线偏离，避免单次读数误判</p></div>
              <span class="tag jade"><span class="status-dot"></span>${records.length} 条记录</span>
            </div>
            <div class="chart-tabs-row" style="margin-top:18px">
              <div class="metric-tabs">
                ${[
                  ["bp", "血压"],
                  ["heart_rate", "心率"],
                  ["sleep_hours", "睡眠"],
                  ["glucose", "血糖"],
                  ["weight_kg", "体重"],
                ].map(([key, label]) => `<button class="metric-tab ${metric === key ? "active" : ""}" data-metric-tab="${key}">${label}</button>`).join("")}
              </div>
              <span class="tag">${metricMeta[1]}</span>
            </div>
            <div class="line-chart">
              ${lineChart(values.length > 1 ? values : [0, 0], labels)}
            </div>
          </section>

          <section class="card records-card">
            <div class="card-header">
              <div><h3 class="card-title">最近健康记录</h3><p class="card-subtitle">设备同步与手动录入统一管理</p></div>
              <button class="small-button" data-open-record>${icon("plus")} 新增</button>
            </div>
            ${records.length ? `
              <div style="overflow-x:auto">
                <table class="record-table">
                  <thead><tr><th>日期</th><th>血压</th><th>心率</th><th>血糖</th><th>睡眠</th><th>来源</th></tr></thead>
                  <tbody>
                    ${records.slice(0, 10).map((record) => `
                      <tr>
                        <td>${formatDate(record.measured_at, { year: "numeric" })} ${formatTime(record.measured_at)}</td>
                        <td class="${record.systolic >= 90 && record.systolic <= 140 ? "value-good" : "value-warn"}">${record.systolic ? `${record.systolic}/${record.diastolic}` : "—"}</td>
                        <td>${record.heart_rate || "—"}</td>
                        <td>${record.glucose ?? "—"}</td>
                        <td>${record.sleep_hours ?? "—"}</td>
                        <td><span class="tag">${escapeHtml(record.source || "手动")}</span></td>
                      </tr>`).join("")}
                  </tbody>
                </table>
              </div>` : `<div class="knowledge-empty">还没有健康记录，添加第一条数据开始建立个人基线。</div>`}
          </section>
        </div>

        <aside class="health-side-stack">
          <section class="card profile-card">
            <div class="profile-hero">
              <span class="avatar">${escapeHtml(userAvatarInitial(state.user.name || "我"))}</span>
              <div><h3>${escapeHtml(state.user.name)}${displayName}</h3><p>${age ? `${age} 岁 · ` : ""}${escapeHtml(profile.blood_type || "血型未填")} 型血 · 个人健康档案</p></div>
            </div>
            <div class="profile-items">
              ${profileItem("过敏史", profile.allergies?.join("、") || "无记录")}
              ${profileItem("基础疾病", profile.conditions?.join("、") || "无记录")}
              ${profileItem("长期用药", profile.medications?.join("、") || "无记录")}
              ${profileItem("家族史", profile.family_history?.join("、") || "无记录")}
              ${profileItem("身高", profile.height_cm ? `${profile.height_cm} 厘米` : "未记录")}
            </div>
          </section>

          <section class="card health-alert-card">
            <span class="alert-icon">${icon("sparkles")}</span>
            <strong>智能连续健康洞察</strong>
            <p>${escapeHtml(overview.insight || "完善档案与连续记录后，智能助手可以识别更适合你的健康趋势。")}</p>
            <button class="ghost-button" style="margin-top:13px;width:100%" data-view-button="chat">${icon("message")} 带档案咨询</button>
          </section>

          <section class="card" style="padding:18px">
            <div class="card-header">
              <div><h3 class="card-title">连续健康时间轴</h3><p class="card-subtitle">体征、检测与咨询共同构成健康轨迹</p></div>
              <span class="tag jade">${state.healthData.timeline.length} 事件</span>
            </div>
            <div class="passport-timeline" style="margin-top:11px;max-height:220px">
              ${state.healthData.timeline.slice(0, 8).map((event) => `
                <div class="passport-event">
                  <i class="${escapeHtml(event.risk || "low")}"></i>
                  <div><strong>${escapeHtml(event.title)}</strong><p>${escapeHtml(event.description)}</p><small>${formatDate(event.occurred_at)} · ${escapeHtml(event.source || "")}</small></div>
                </div>`).join("") || `<div class="evidence-empty">暂无健康事件</div>`}
            </div>
          </section>

          <section class="card" style="padding:18px">
            <h3 class="card-title">数据隐私</h3>
            <div class="source-item" style="margin-top:12px">
              <i></i><div><strong>本地优先存储</strong><small>个人健康记录保存在本机 SQLite，不进入医疗知识图谱。</small></div>
            </div>
            <div class="source-item">
              <i></i><div><strong>最小化模型上下文</strong><small>仅发送本轮必要的档案字段，降低隐私暴露范围。</small></div>
            </div>
          </section>
        </aside>
      </div>
    </div>`;

  $$("[data-open-record]").forEach((button) => button.addEventListener("click", openRecordModal));
  $("#open-passport-button").addEventListener("click", openHealthPassport);
  $("#open-summary-button").addEventListener("click", openVisitSummary);
  $("#edit-profile-button").addEventListener("click", openProfileModal);
  $$("[data-metric-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.chartMetric = button.dataset.metricTab;
      renderHealth(++renderSequence);
    });
  });
  $$("[data-view-button]").forEach((button) => button.addEventListener("click", () => renderView(button.dataset.viewButton)));
}

/* Intelligent triage */
async function renderTriage() {
  const profile = state.healthData?.profile || state.user.profile || {};
  const age = ageFromBirthDate(profile.birth_date);
  $("#view-stack").innerHTML = `
    <div class="page-enter">
      <div class="page-heading">
        <div class="page-heading-copy">
          <span>临床信号识别</span>
          <h1>智能健康检测</h1>
          <p>识别症状、生命体征与红旗信号，给出清晰的就医优先级。</p>
        </div>
        <span class="tag jade">${icon("shield")} 规则 + 图谱双引擎</span>
      </div>
      <div class="triage-layout">
        <section class="card triage-form-card">
          <form id="triage-form">
            <div class="form-step">
              <span class="step-number">01</span>
              <div><h3>描述你正在经历的不适</h3><p>尽量包含症状、持续时间、诱因和伴随表现。</p></div>
            </div>
            <div class="symptom-input-shell">
              <textarea id="triage-symptoms" name="symptoms" maxlength="3000" placeholder="例如：今天早上起床时头晕，持续约十分钟，伴有轻微恶心。平时血压偏低，最近睡眠不足……"></textarea>
              <div class="symptom-input-foot">
                <span class="tag">0 / 3000</span>
              </div>
            </div>
            <input id="triage-image-input" type="file" accept="image/jpeg,image/png,image/webp" hidden />
            <div class="image-input-tools">
              <button type="button" class="ghost-button" id="triage-image-button">${icon("image")} 上传健康图片</button>
              <button type="button" class="ghost-button" id="analyze-triage-image" ${state.triageImage ? "" : "disabled"}>${icon("sparkles")} 分析图片</button>
              <span>支持皮肤、伤口、检查报告或药品包装图片</span>
            </div>
            <div class="chat-image-preview triage-image-preview" id="triage-image-preview" ${state.triageImage ? "" : "hidden"}>
              ${state.triageImage ? `<img src="${state.triageImage.dataUrl}" alt="待分析图片预览"/><div><strong>${escapeHtml(state.triageImage.name)}</strong><small>图片不保存，仅用于本次分析</small></div><button type="button" id="remove-triage-image" aria-label="移除图片">${icon("close")}</button>` : ""}
            </div>
            <div class="quick-symptoms">
              ${["头晕", "头痛", "胸闷", "心悸", "发热", "咳嗽", "腹痛", "乏力"].map((symptom) => `<button type="button" class="quick-symptom" data-quick-symptom="${symptom}">+ ${symptom}</button>`).join("")}
            </div>

            <div class="form-step">
              <span class="step-number">02</span>
              <div><h3>补充判断信息</h3><p>生命体征缺失时仍可检测，但补充数据会提高判断质量。</p></div>
            </div>
            <div class="triage-fields">
              <div class="compact-field"><label>年龄</label><input name="age" type="number" min="0" max="120" value="${age ?? ""}" placeholder="岁" /></div>
              <div class="compact-field"><label>持续天数</label><input name="duration_days" type="number" min="0" max="3650" placeholder="天" /></div>
              <div class="compact-field"><label>收缩压</label><input name="systolic" type="number" min="40" max="300" placeholder="毫米汞柱" /></div>
              <div class="compact-field"><label>舒张压</label><input name="diastolic" type="number" min="20" max="200" placeholder="毫米汞柱" /></div>
              <div class="compact-field"><label>心率</label><input name="heart_rate" type="number" min="20" max="250" placeholder="次/分" /></div>
              <div class="compact-field"><label>血氧</label><input name="spo2" type="number" min="50" max="100" placeholder="%" /></div>
            </div>
            <label class="checkbox-row"><input type="checkbox" name="pregnancy" /> 当前处于孕期或可能怀孕</label>
            <button type="submit" class="primary-button triage-submit">${icon("scan")} 开始智能检测</button>
            <p class="triage-disclaimer">系统不会提供确定诊断或处方。检测到急症信号时，请立即拨打 120。</p>
          </form>
        </section>
        <section class="card triage-result-card ${state.triageResult?.level || ""}" id="triage-result">
          ${triageResultPanel(state.triageResult)}
        </section>
      </div>
    </div>`;
  $("#triage-symptoms").addEventListener("input", (event) => {
    const tag = $(".symptom-input-foot .tag");
    if (tag) tag.textContent = `${event.target.value.length} / 3000`;
  });
  $("#triage-image-button").addEventListener("click", () => $("#triage-image-input").click());
  $("#triage-image-input").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setTriageImage(await compressImageFile(file));
      $("#analyze-triage-image").disabled = false;
      toast("健康图片已添加");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      event.target.value = "";
    }
  });
  $("#remove-triage-image")?.addEventListener("click", () => {
    setTriageImage(null);
    $("#analyze-triage-image").disabled = true;
  });
  $("#analyze-triage-image").addEventListener("click", analyzeTriageImage);
  $$("[data-quick-symptom]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = $("#triage-symptoms");
      input.value = input.value ? `${input.value.replace(/[，。,\s]+$/, "")}，${button.dataset.quickSymptom}` : button.dataset.quickSymptom;
      input.dispatchEvent(new Event("input"));
      input.focus();
    });
  });
  $("#triage-form").addEventListener("submit", runTriage);
}

function triageResultPanel(result) {
  if (!result) {
    return `
      <div class="triage-result-empty">
        <div class="scan-art"></div>
        <h3>等待健康信号</h3>
        <p>完成左侧描述后，系统将从症状、生命体征和急症模式三个维度进行检测。</p>
      </div>`;
  }
  const colors = {
    low: "#68e0b1",
    medium: "#efc36b",
    high: "#ff9a77",
    emergency: "#ff806f",
  };
  const color = colors[result.level] || colors.low;
  const medication = result.medication_advice || {};
  return `
    <div class="risk-result-top">
      <div class="risk-gauge" style="--score:${result.score};--risk-color:${color}">
        <div style="text-align:center"><strong>${result.score}</strong><small>风险指数</small></div>
      </div>
      <div class="risk-result-copy">
        <span>${result.level === "emergency" ? "紧急信号" : result.level === "high" ? "优先处理" : result.level === "medium" ? "建议持续观察" : "低风险"}</span>
        <h2 style="color:${color}">${escapeHtml(result.title)}</h2>
        <p>${escapeHtml(result.subtitle)}</p>
      </div>
    </div>
    <div class="risk-action-box" style="border-color:${color}44">${escapeHtml(result.action)}</div>
    ${medication.possible_conditions?.length ? `
      <div class="result-section">
        <span>症状分析</span>
        <div class="possible-condition-list">
          ${medication.possible_conditions.map((item) => `
            <div class="possible-condition">
              <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.confidence)}</small></div>
              <p>${escapeHtml(item.note)}</p>
            </div>`).join("")}
        </div>
      </div>` : ""}
    ${result.red_flags?.length ? `
      <div class="result-section">
        <span>需要立即处理的信号</span>
        <div class="red-flag-list">${result.red_flags.map((flag) => `<div class="red-flag-item"><i></i>${escapeHtml(flag)}</div>`).join("")}</div>
      </div>` : ""}
    <div class="result-section">
      <span>已识别症状</span>
      <div class="result-tags">${result.symptoms?.length ? result.symptoms.map((item) => `<span class="result-tag">${escapeHtml(item)}</span>`).join("") : `<span class="result-tag">未命中标准症状词</span>`}</div>
    </div>
    <div class="result-section">
      <span>建议就诊科室</span>
      <div class="result-tags">${(result.departments || []).map((item) => `<span class="result-tag">${escapeHtml(item)}</span>`).join("")}</div>
    </div>
    ${result.graph_entities?.length ? `
      <div class="result-section">
        <span>知识图谱命中</span>
        <div class="result-tags">${result.graph_entities.slice(0, 6).map((entity) => `<span class="result-tag">${escapeHtml(entity.name)} · ${escapeHtml(entity.type_label || entity.type)}</span>`).join("")}</div>
      </div>` : ""}
    ${medication.title ? `
      <section class="medication-panel">
        <div class="medication-panel-head">
          <div><span>用药参考</span><h3>${escapeHtml(medication.title)}</h3></div>
          <span class="tag ${medication.available ? "jade" : "amber"}">${medication.available ? "非处方药" : "先咨询医生"}</span>
        </div>
        <p class="medication-intro">${escapeHtml(medication.message || "")}</p>
        ${medication.items?.length ? `
          <div class="medication-list">
            ${medication.items.map((item) => `
              <article class="medication-item">
                <div class="medication-item-top">
                  <div>
                    <span class="medication-category">${escapeHtml(item.category)}</span>
                    <h4>${escapeHtml(item.name)}</h4>
                    <small>${escapeHtml(item.spec)} · 通用名 ${escapeHtml(item.generic)}</small>
                  </div>
                  <div class="medication-price">
                    <strong>${escapeHtml(item.price)}</strong>
                    <span>${escapeHtml(item.price_label)}</span>
                  </div>
                </div>
                <p>${escapeHtml(item.reason)}</p>
                <div class="medication-caution">${escapeHtml(item.cautions)}</div>
                <div class="medication-item-foot">
                  <span>价格更新：${escapeHtml(item.price_updated_at)}</span>
                  <a href="${escapeHtml(item.search_url)}" target="_blank" rel="noopener noreferrer">查看实时价 ${icon("arrow")}</a>
                </div>
              </article>`).join("")}
          </div>` : ""}
        ${medication.safety_notes?.length ? `
          <ul class="medication-safety">
            ${medication.safety_notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
          </ul>` : ""}
        <p class="medication-price-note">${escapeHtml(medication.price_note || "")}</p>
      </section>` : ""}
    <p class="triage-disclaimer">${escapeHtml(result.disclaimer)}</p>`;
}

async function runTriage(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const symptoms = String(form.get("symptoms") || "").trim();
  if (symptoms.length < 2) {
    toast("请先描述你的不适", "error");
    $("#triage-symptoms").focus();
    return;
  }
  const button = $(".triage-submit");
  button.disabled = true;
  button.innerHTML = `${icon("activity")} 正在识别健康信号…`;
  const payload = { symptoms, pregnancy: form.get("pregnancy") === "on" };
  for (const key of ["age", "duration_days", "systolic", "diastolic", "heart_rate", "spo2"]) {
    if (form.get(key) !== "") payload[key] = Number(form.get(key));
  }
  try {
    const result = await api("/api/triage", { method: "POST", body: JSON.stringify(payload) });
    state.triageResult = result;
    const card = $("#triage-result");
    card.className = `card triage-result-card ${result.level}`;
    card.innerHTML = triageResultPanel(result);
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = `${icon("scan")} 重新检测`;
  }
}

async function analyzeTriageImage() {
  if (!state.triageImage) {
    toast("请先上传图片", "error");
    return;
  }
  const button = $("#analyze-triage-image");
  button.disabled = true;
  button.innerHTML = `${icon("activity")} 正在识别图像…`;
  try {
    const result = await api("/api/vision", {
      method: "POST",
      body: JSON.stringify({
        image_data: state.triageImage.dataUrl,
        question: $("#triage-symptoms")?.value.trim() || "",
      }),
    });
    $("#modal-root").innerHTML = `
      <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
      <section class="modal-card vision-result-modal" role="dialog" aria-modal="true" aria-labelledby="vision-result-title">
        <div class="settings-head">
          <div><span class="eyebrow"><span></span> 多模态分析</span><h2 class="modal-title" id="vision-result-title">图片信息识别</h2></div>
          <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
        </div>
        <p class="modal-subtitle">${escapeHtml(result.notice)}</p>
        <div class="vision-preview"><img src="${state.triageImage.dataUrl}" alt="已分析图片"/></div>
        <div class="vision-answer">${formatMarkdown(result.content)}</div>
        <div class="modal-actions">
          <button class="ghost-button" data-close-modal>关闭</button>
          <button class="primary-button" id="continue-with-image" type="button">${icon("message")} 结合图片继续咨询</button>
        </div>
      </section>`;
    hydrateIcons($("#modal-root"));
    bindModalClose();
    $("#continue-with-image").addEventListener("click", () => {
      state.chatImage = state.triageImage;
      closeModal();
      renderView("chat");
    });
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = `${icon("sparkles")} 分析图片`;
  }
}

/* Medical knowledge base */
/* Command palette */
function openPalette() {
  $("#command-palette").hidden = false;
  $("#palette-input").value = "";
  searchPalette("");
  setTimeout(() => $("#palette-input").focus(), 30);
}

function closePalette() {
  $("#command-palette").hidden = true;
}

async function searchPalette(query) {
  const container = $("#palette-results");
  const pages = [
    ["message", "chat", "开始一次健康咨询"],
    ["scan", "triage", "进行智能症状检测"],
    ["graph", "graph", "探索 3D 医疗知识图谱"],
    ["heart", "health", "查看健康档案"],
  ];
  if (!query) {
    container.innerHTML = `
      <p class="palette-label">快速前往</p>
      ${pages.map(([iconName, view, label]) => `<button data-palette-view="${view}"><span>${icon(iconName)}</span><span>${label}</span><kbd>↵</kbd></button>`).join("")}`;
    bindPaletteButtons();
    return;
  }
  try {
    const data = await api(`/api/graph/search?q=${encodeURIComponent(query)}&limit=6`);
    const results = data.results || [];
    container.innerHTML = `
      ${results.length ? `<p class="palette-label">知识实体</p>${results.map((result) => `<button data-palette-entity="${escapeHtml(encodeURIComponent(JSON.stringify(result)))}"><span>${icon("graph")}</span><span>${escapeHtml(result.name)}</span><small>${escapeHtml(result.type_label || result.type)}</small></button>`).join("")}` : ""}
      <p class="palette-label">页面</p>
      ${pages.filter((page) => page[2].includes(query)).map(([iconName, view, label]) => `<button data-palette-view="${view}"><span>${icon(iconName)}</span><span>${label}</span></button>`).join("")}`;
    bindPaletteButtons();
  } catch {
    container.innerHTML = `<p class="palette-label">搜索暂不可用</p>`;
  }
}

function bindPaletteButtons() {
  $$("[data-palette-view]").forEach((button) => {
    button.addEventListener("click", () => {
      closePalette();
      renderView(button.dataset.paletteView);
    });
  });
  $$("[data-palette-entity]").forEach((button) => {
    button.addEventListener("click", () => {
      const entity = JSON.parse(decodeURIComponent(button.dataset.paletteEntity));
      state.graphFocus = entity.name;
      closePalette();
      renderView("graph");
    });
  });
}


installDeps({
  renderView,
  renderChat,
  renderHealth,
  renderDashboard,
  openConversation,
  startNewChat,
  openRecordModal,
  openProfileModal,
  openGraphInspector,
  renderKnowledge,
  renderGraph,
  renderTriage,
  modalInput,
  knowledgeResultList,
  graphSearchSuggestions,
});

bootstrap();

