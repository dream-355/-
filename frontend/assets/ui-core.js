export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export const state = {
  user: null,
  view: "dashboard",
  authMode: "login",
  dashboard: null,
  conversations: [],
  activeConversationId: null,
  activeConversation: null,
  graphOverview: null,
  graphInstance: null,
  evidenceGraph: null,
  chartMetric: "bp",
  healthData: null,
  triageResult: null,
  knowledgeResults: null,
  system: null,
  sending: false,
  composerCollapsed: false,
  inspectorGraph: null,
  inspectorHistory: { entries: [], index: -1 },
  inspectorCurrentNode: null,
  chatImage: null,
  triageImage: null,
  uiSize: "standard",
  sidebarManage: false,
  sidebarSelected: new Set(),
  sidebarSpaceOpen: false,
  theme: "dark",
  lifestyleSymptoms: "",
  lifestylePreferences: "",
  lifestyleGenerated: false,
};

export const ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  message: '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 9h8M8 13h5"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8z"/>',
  scan: '<path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
  graph: '<circle cx="5" cy="12" r="2.5"/><circle cx="18" cy="5" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m7.4 11 8.2-4.8M7.4 13l8.2 4.8M18 7.5v9"/>',
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 5.5v16M8 7h8M8 11h6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  more: '<circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  logout: '<path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
  sparkles: '<path d="m12 3 1.4 4.1L18 8.5l-4.6 1.4L12 14l-1.4-4.1L6 8.5l4.6-1.4zM5 15l.8 2.2L8 18l-2.2.8L5 21l-.8-2.2L2 18l2.2-.8zM19 14l.6 1.4L21 16l-1.4.6L19 18l-.6-1.4L17 16l1.4-.6z"/>',
  activity: '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
  blood: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/><path d="M9 15a3 3 0 0 0 3 3"/>',
  moon: '<path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/>',
  oxygen: '<circle cx="12" cy="12" r="8"/><path d="M8 12h8M12 8v8"/><path d="M4.5 9C2.8 7 2.8 4.7 4 3.4c2 .3 3.3 2 3 4.3M19.5 9c1.7-2 1.7-4.3.5-5.6-2 .3-3.3 2-3 4.3"/>',
  footprint: '<path d="M8.5 3.5c2.3.6 3.2 3 2.8 5.7-.2 1.9-1.1 3.2-1.6 5.1-.5 2 0 3.4-1.7 3.6-1.8.2-2.4-1.8-2.2-3.7.2-2.2 1-3.3 1-5.4-.1-2.4.3-5.8 1.7-5.3zM17 11c1.9.5 2.7 2.2 2.3 4.2-.2 1.3-.8 2.2-1.2 3.4-.3 1.2 0 2.2-1.4 2.4-1.4.1-1.8-1.1-1.7-2.3.1-1.5.8-2.1.8-3.4 0-1.7.3-4.6 1.2-4.3z"/>',
  send: '<path d="m22 2-7 20-4-9-9-4zM22 2 11 13"/>',
  attachment: '<path d="m20.5 11.5-8.8 8.8a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  filter: '<path d="M4 5h16M7 12h10M10 19h4"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18"/>',
  edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>',
  close: '<path d="m5 5 14 14M19 5 5 19"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="8.5" cy="9" r="1.5"/><path d="m4 17 5-5 3 3 2-2 6 6"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.09A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3v-4h.09A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.09A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.14.38.36.72.65 1 .3.28.68.42 1.1.4H21v4h-.09A1.7 1.7 0 0 0 19.4 15z"/>',
  zoomIn: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M10.5 7.5v6M7.5 10.5h6"/>',
  zoomOut: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M7.5 10.5h6"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 9A7 7 0 0 1 18.4 7M17.9 15A7 7 0 0 1 5.6 17"/>',
  pause: '<path d="M9 5v14M15 5v14"/>',
  play: '<path d="m8 5 11 7-11 7z"/>',
  alert: '<path d="m12 3 10 18H2z"/><path d="M12 9v5M12 18h.01"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/>',
  chevron: '<path d="m8 10 4 4 4-4"/>',
  arrowLeft: '<path d="M19 12H5M10 7l-5 5 5 5"/>',
  arrowRight: '<path d="M5 12h14M14 7l5 5-5 5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  shield: '<path d="M12 3 4 6v5c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V6z"/><path d="m9 12 2 2 4-4"/>',
  stethoscope: '<path d="M6 3v6a4 4 0 0 0 8 0V3M4 3h4M12 3h4M10 13v2a5 5 0 0 0 10 0v-2"/><circle cx="20" cy="11" r="1.5"/>',
};

export function icon(name, className = "icon") {
  return `<svg class="${className}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
}

export function hydrateIcons(root = document) {
  $$("[data-icon]", root).forEach((element) => {
    element.innerHTML = icon(element.dataset.icon);
  });
}

export function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatMarkdown(text = "") {
  const escaped = escapeHtml(text);
  const lines = escaped.split("\n");
  const output = [];
  let inList = false;
  for (const raw of lines) {
    let line = raw.trimEnd();
    const listMatch = line.match(/^\s*[-*]\s+(.+)/);
    if (listMatch) {
      if (!inList) {
        output.push("<ul>");
        inList = true;
      }
      output.push(`<li>${inlineMarkdown(listMatch[1])}</li>`);
      continue;
    }
    if (inList) {
      output.push("</ul>");
      inList = false;
    }
    if (!line.trim()) continue;
    if (line.startsWith("&gt; ")) {
      output.push(`<blockquote>${inlineMarkdown(line.slice(5))}</blockquote>`);
    } else if (/^#{1,3}\s/.test(line)) {
      output.push(`<p><strong>${inlineMarkdown(line.replace(/^#{1,3}\s+/, ""))}</strong></p>`);
    } else {
      output.push(`<p>${inlineMarkdown(line)}</p>`);
    }
  }
  if (inList) output.push("</ul>");
  return output.join("");
}

export function inlineMarkdown(line) {
  return line
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, '<code class="inline-code">$1</code>')
    .replace(/\[(E\d+)\]/g, '<button class="citation-ref" type="button" data-citation="$1">[$1]</button>');
}

export async function api(path, options = {}) {
  const config = {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  };
  const response = await fetch(path, config);
  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) {
    const error = new Error(data.detail || `请求失败 (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}

export function toast(message, type = "success", duration = 3500) {
  const stack = $("#toast-stack");
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.innerHTML = `<i></i><p>${escapeHtml(message)}</p><button aria-label="关闭">${icon("close")}</button>`;
  element.querySelector("button").addEventListener("click", () => element.remove());
  stack.appendChild(element);
  if (duration) setTimeout(() => element.remove(), duration);
}

export function formatDate(value, options = {}) {
  if (!value) return "刚刚";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "刚刚";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    ...options,
  }).format(date);
}

export function formatTime(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function relativeDate(value) {
  if (!value) return "";
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  if (diff < 60_000) return "刚刚";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`;
  return formatDate(value);
}

export function greeting() {
  const hour = new Date().getHours();
  if (hour < 6) return "夜深了";
  if (hour < 11) return "早上好";
  if (hour < 14) return "中午好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function debounce(fn, delay = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

const UI_SCALE = {
  small: 0.92,
  standard: 1,
  large: 1.12,
  xlarge: 1.22,
};

export function loadAppSettings() {
  try {
    state.uiSize = localStorage.getItem("zhiheng_ui_size") || "standard";
    state.theme = localStorage.getItem("zhiheng_theme") === "light" ? "light" : "dark";
  } catch {
    state.uiSize = "standard";
    state.theme = "dark";
  }
  applyUiSize(state.uiSize);
  applyTheme(state.theme);
}

export function applyUiSize(size) {
  state.uiSize = Object.hasOwn(UI_SCALE, size) ? size : "standard";
  document.body.dataset.uiSize = state.uiSize;
  document.documentElement.dataset.fontSize = state.uiSize;
  $$("[data-font-size]").forEach((item) => {
    item.classList.toggle("active", item.dataset.fontSize === state.uiSize);
  });
  try {
    localStorage.setItem("zhiheng_ui_size", state.uiSize);
  } catch {
    // Preferences remain active for this page even when storage is blocked.
  }
}

export function applyTheme(theme) {
  state.theme = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.style.colorScheme = state.theme;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) {
    themeColor.setAttribute(
      "content",
      state.theme === "light" ? "#f3f7f2" : "#07110f",
    );
  }
  $$("[data-theme-toggle]").forEach((button) => {
    button.innerHTML = icon(state.theme === "dark" ? "sun" : "moon");
    const label = state.theme === "dark" ? "切换到亮色模式" : "切换到暗色模式";
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
  });
  $$("[data-theme-choice]").forEach((button) => {
    const active = button.dataset.themeChoice === state.theme;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
  try {
    localStorage.setItem("zhiheng_theme", state.theme);
  } catch {
    // The selected theme still applies to the current page.
  }
}

export function toggleTheme() {
  applyTheme(state.theme === "dark" ? "light" : "dark");
}

export function openSettingsModal() {
  const sizes = [
    ["small", "小", "适合更多内容"],
    ["standard", "标准", "默认观感"],
    ["large", "大", "更易阅读"],
    ["xlarge", "特大", "演示投影"],
  ];
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 显示设置</span><h2 class="modal-title" id="settings-title">显示设置</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">字号调整会立即生效，并保存在当前浏览器。</p>
      <div class="settings-group">
        <label class="settings-label">界面主题</label>
        <div class="theme-options">
          <button type="button" class="theme-option ${state.theme === "dark" ? "active" : ""}" data-theme-choice="dark" aria-pressed="${state.theme === "dark"}">
            <span>${icon("moon")}</span>
            <div><strong>暗色模式</strong><small>深绿背景，适合夜间与投影</small></div>
          </button>
          <button type="button" class="theme-option ${state.theme === "light" ? "active" : ""}" data-theme-choice="light" aria-pressed="${state.theme === "light"}">
            <span>${icon("sun")}</span>
            <div><strong>亮色模式</strong><small>浅色背景，更明亮清晰</small></div>
          </button>
        </div>
      </div>
      <div class="settings-group">
        <label class="settings-label">界面字号</label>
        <div class="font-size-options">
          ${sizes.map(([value, label, hint]) => `
            <button type="button" class="font-size-option ${state.uiSize === value ? "active" : ""}" data-font-size="${value}">
              <strong style="font-size:${value === "small" ? 12 : value === "standard" ? 14 : value === "large" ? 16 : 18}px">${label}</strong>
              <small>${hint}</small>
            </button>`).join("")}
        </div>
        <div class="settings-preview">
          <strong>健康问题，应回答得清楚。</strong>
          <p>这是字号预览。调整后页面中的导航、对话、表单和报告会同步变化。</p>
        </div>
      </div>
      <div class="settings-group account-settings-group">
        <label class="settings-label">账号与安全</label>
        <div class="account-summary">
          <div>
            <strong id="account-email-value">${escapeHtml(state.user?.email || "未登录")}</strong>
            <small>密码以加盐哈希保存，系统无法显示原文；可凭当前密码重设。</small>
          </div>
          <button class="ghost-button" id="open-account-editor" type="button">
            ${icon("lock")} 修改账号密码
          </button>
        </div>
      </div>
      <div class="modal-actions">
        <button class="ghost-button" id="reset-display-settings" type="button">恢复默认</button>
        <button class="primary-button" data-close-modal type="button">完成</button>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $$("[data-theme-choice]").forEach((button) => {
    button.addEventListener("click", () => applyTheme(button.dataset.themeChoice));
  });
  $$("[data-font-size]").forEach((button) => {
    button.addEventListener("click", () => {
      applyUiSize(button.dataset.fontSize);
      $$("[data-font-size]").forEach((item) => item.classList.toggle("active", item === button));
    });
  });
  $("#reset-display-settings").addEventListener("click", () => {
    applyUiSize("standard");
    applyTheme("dark");
    $$("[data-font-size]").forEach((item) => item.classList.toggle("active", item.dataset.fontSize === "standard"));
  });
  $("#open-account-editor").addEventListener("click", openAccountEditor);
}

export function openAccountEditor() {
  const email = state.user?.email || "";
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="account-editor-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 账号安全</span><h2 class="modal-title" id="account-editor-title">修改账号密码</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">需验证当前密码。只改邮箱时新密码留空即可。</p>
      <form id="account-form" autocomplete="off">
        <div class="modal-field">
          <label>当前密码</label>
          <input name="current_password" type="password" required maxlength="72" placeholder="输入当前登录密码" />
        </div>
        <div class="modal-field">
          <label>新邮箱</label>
          <input name="new_email" type="email" maxlength="120" value="${escapeHtml(email)}" />
        </div>
        <div class="form-grid-2">
          <div class="modal-field"><label>新密码</label><input name="new_password" type="password" minlength="8" maxlength="72" placeholder="至少 8 位，可留空" /></div>
          <div class="modal-field"><label>确认新密码</label><input name="confirm_password" type="password" minlength="8" maxlength="72" placeholder="再输入一次" /></div>
        </div>
        <p class="form-error" id="account-error" role="alert"></p>
        <div class="modal-actions">
          <button type="button" class="ghost-button" data-close-modal>取消</button>
          <button type="submit" class="primary-button">保存修改</button>
        </div>
      </form>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#account-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const current = String(form.get("current_password") || "");
    const newEmail = String(form.get("new_email") || "").trim();
    const newPassword = String(form.get("new_password") || "");
    const confirmPassword = String(form.get("confirm_password") || "");
    const errorBox = $("#account-error");
    errorBox.textContent = "";
    if (newPassword && newPassword !== confirmPassword) {
      errorBox.textContent = "两次输入的新密码不一致";
      return;
    }
    if (!newPassword && newEmail === email) {
      errorBox.textContent = "邮箱和密码都没有变化";
      return;
    }
    const button = event.target.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const result = await api("/api/auth/account", {
        method: "PUT",
        body: JSON.stringify({
          current_password: current,
          new_email: newEmail || null,
          new_password: newPassword || null,
        }),
      });
      state.user = { ...state.user, ...result.user };
      closeModal();
      toast(newPassword ? "账号与密码已更新" : "账号邮箱已更新");
    } catch (error) {
      errorBox.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

export async function openSystemStatus() {
  let health = state.system;
  try {
    health = await api("/api/health");
    state.system = health;
  } catch {}
  const online = health?.neo4j?.online;
  const vector = health?.vector_index || {};
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card system-status-modal" role="dialog" aria-modal="true" aria-labelledby="system-status-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 实时服务状态</span><h2 class="modal-title" id="system-status-title">服务状态</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">这里展示当前真实的服务连接状态，不生成虚构通知。</p>
      <div class="system-status-list">
        <div class="system-status-row"><span class="status-orb ${online ? "online" : "offline"}"></span><div><strong>Neo4j 知识图谱</strong><small>${online ? `${health.neo4j.latency_ms} 毫秒 · 版本 ${health.neo4j.version}` : "连接异常"}</small></div><em>${online ? "在线" : "离线"}</em></div>
        <div class="system-status-row"><span class="status-orb ${health?.deepseek_configured ? "online" : "offline"}"></span><div><strong>DeepSeek 模型</strong><small>${escapeHtml(health?.model || "未配置")} · 图像模型 ${escapeHtml(health?.vision_model || "未配置")}</small></div><em>${health?.deepseek_configured ? "已配置" : "未配置"}</em></div>
        <div class="system-status-row"><span class="status-orb ${health?.email_configured ? "online" : "offline"}"></span><div><strong>邮件服务</strong><small>${health?.email_configured ? "注册通知、验证码与健康报告可发送" : "SMTP 尚未配置"}</small></div><em>${health?.email_configured ? "已配置" : "未配置"}</em></div>
        <div class="system-status-row"><span class="status-orb ${vector.ready ? "online" : "offline"}"></span><div><strong>本地向量召回</strong><small>${vector.ready ? `${vector.entities.toLocaleString("zh-CN")} 个实体 · ${vector.dimensions} 维` : "索引未就绪"}</small></div><em>${vector.ready ? "就绪" : "不可用"}</em></div>
        <div class="system-status-row"><span class="status-orb ${health?.mcp_tools ? "online" : "offline"}"></span><div><strong>MCP 医疗工具</strong><small>${health?.mcp_tools || 0} 个只读工具已注册</small></div><em>${health?.mcp_tools ? "就绪" : "不可用"}</em></div>
      </div>
      <div class="system-modal-actions">
        <button class="ghost-button" id="refresh-system-status">${icon("refresh")} 重新检查</button>
        <button class="ghost-button" data-view-modal="health">${icon("heart")} 查看健康档案</button>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#refresh-system-status").addEventListener("click", openSystemStatus);
  $("[data-view-modal]").addEventListener("click", (event) => {
    closeModal();
    renderView(event.currentTarget.dataset.viewModal);
  });
}

export function openFeedbackModal() {
  const scale = (key, label, hint) => `
    <div class="feedback-scale">
      <div><strong>${label}</strong><small>${hint}</small></div>
      <div class="scale-buttons" data-scale="${key}">
        ${[1, 2, 3, 4, 5].map((value) => `<button type="button" data-score="${value}">${value}</button>`).join("")}
      </div>
    </div>`;
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card feedback-modal" role="dialog" aria-modal="true" aria-labelledby="feedback-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 用户体验调研</span><h2 class="modal-title" id="feedback-title">真实体验反馈</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">反馈用于项目迭代和比赛中的真实用户体验记录，不收集诊断信息。</p>
      ${scale("rating", "整体体验", "1 很差，5 很好")}
      ${scale("ease", "操作容易度", "1 很难，5 很容易")}
      ${scale("useful", "健康帮助程度", "1 没用，5 很有帮助")}
      <div class="modal-field">
        <label>最希望继续改进的地方</label>
        <textarea name="feedback_comments" id="feedback-comments" maxlength="1000" placeholder="例如：检索结果、字号、健康档案……"></textarea>
      </div>
      <p class="form-error" id="feedback-error"></p>
      <div class="modal-actions">
        <button class="ghost-button" data-close-modal type="button">稍后填写</button>
        <button class="primary-button" id="submit-feedback" type="button">提交反馈</button>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  const scores = { rating: 0, ease: 0, useful: 0 };
  $$("[data-scale]", $("#modal-root")).forEach((group) => {
    $$("[data-score]", group).forEach((button) => {
      button.addEventListener("click", () => {
        scores[group.dataset.scale] = Number(button.dataset.score);
        $$("[data-score]", group).forEach((item) => item.classList.toggle("active", item === button));
      });
    });
  });
  $("#submit-feedback").addEventListener("click", async () => {
    if (!scores.rating || !scores.ease || !scores.useful) {
      $("#feedback-error").textContent = "请先完成三个评分项";
      return;
    }
    const button = $("#submit-feedback");
    button.disabled = true;
    try {
      const result = await api("/api/feedback", {
        method: "POST",
        body: JSON.stringify({
          rating: scores.rating,
          ease_score: scores.ease,
          usefulness_score: scores.useful,
          comments: $("#feedback-comments").value.trim(),
        }),
      });
      toast(`反馈已记录：当前平均体验 ${result.summary.rating} / 5`);
      closeModal();
    } catch (error) {
      $("#feedback-error").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

export async function openHealthPassport() {
  let passport;
  try {
    passport = await api("/api/health/passport");
  } catch (error) {
    toast(error.message, "error");
    return;
  }
  const profile = passport.profile || {};
  const overview = passport.overview || {};
  const latest = overview.latest || {};
  const timeline = (passport.timeline || []).slice(0, 12);
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card passport-modal" role="dialog" aria-modal="true" aria-labelledby="passport-title">
      <div class="settings-head">
        <div><span class="eyebrow"><span></span> 个人健康证据</span><h2 class="modal-title" id="passport-title">健康证据护照</h2></div>
        <button class="icon-button" data-close-modal aria-label="关闭">${icon("close")}</button>
      </div>
      <p class="modal-subtitle">${escapeHtml(passport.owner.name)} · 生成于 ${formatDate(passport.generated_at, { year: "numeric" })} ${formatTime(passport.generated_at)}</p>
      <div class="passport-summary">
        ${scoreRing(overview.score || 0)}
        <div><span>当前健康概览</span><h3>${escapeHtml(overview.status || "等待数据")}</h3><p>${escapeHtml(overview.insight || "")}</p></div>
      </div>
      <div class="passport-metrics">
        <div><span>血压</span><strong>${latest.systolic ? `${latest.systolic}/${latest.diastolic}` : "—"}</strong><small>毫米汞柱</small></div>
        <div><span>睡眠</span><strong>${latest.sleep_hours ?? "—"}</strong><small>小时</small></div>
        <div><span>心率</span><strong>${latest.heart_rate ?? "—"}</strong><small>次/分</small></div>
      </div>
      <section class="passport-section">
        <h4>健康关键词</h4>
        <div class="result-tags">
          ${(profile.conditions || []).map((item) => `<span class="result-tag">${escapeHtml(item)}</span>`).join("")}
          ${(profile.allergies || []).map((item) => `<span class="result-tag alert">过敏：${escapeHtml(item)}</span>`).join("")}
          ${!(profile.conditions?.length || profile.allergies?.length) ? `<span class="result-tag">暂无基础病或过敏记录</span>` : ""}
        </div>
      </section>
      <section class="passport-section">
        <h4>健康事件时间轴</h4>
        <div class="passport-timeline">
          ${timeline.map((event) => `
            <div class="passport-event">
              <i class="${escapeHtml(event.risk || "low")}"></i>
              <div><strong>${escapeHtml(event.title)}</strong><p>${escapeHtml(event.description)}</p><small>${formatDate(event.occurred_at, { year: "numeric" })} · ${escapeHtml(event.source || "")}</small></div>
            </div>`).join("")}
        </div>
      </section>
      <p class="passport-disclaimer">${escapeHtml(passport.disclaimer)}</p>
      <div class="modal-actions">
        <button class="ghost-button" id="copy-passport" type="button">${icon("download")} 复制摘要</button>
        <button class="ghost-button" id="email-passport" type="button">${icon("mail")} 发送到邮箱</button>
        <button class="primary-button" id="print-passport" type="button">${icon("download")} 打印 / 保存 PDF</button>
      </div>
    </section>`;
  hydrateIcons($("#modal-root"));
  bindModalClose();
  $("#email-passport").addEventListener("click", (event) => {
    sendHealthReport("passport", event.currentTarget);
  });
  $("#copy-passport").addEventListener("click", async () => {
    const text = [
      `健康证据护照 - ${passport.owner.name}`,
      `健康状态：${overview.status || "等待数据"}，评分 ${overview.score || 0}`,
      `基础疾病：${(profile.conditions || []).join("、") || "无记录"}`,
      `过敏史：${(profile.allergies || []).join("、") || "无记录"}`,
      `最近体征：血压 ${latest.systolic || "—"}/${latest.diastolic || "—"}，心率 ${latest.heart_rate || "—"}，睡眠 ${latest.sleep_hours || "—"} 小时`,
      `免责声明：${passport.disclaimer}`,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast("健康摘要已复制");
    } catch {
      toast("浏览器未允许复制，请使用打印功能", "error");
    }
  });
  $("#print-passport").addEventListener("click", () => {
    const printWindow = window.open("", "_blank", "width=900,height=760");
    if (!printWindow) {
      toast("浏览器阻止了打印窗口，请允许弹出窗口", "error");
      return;
    }
    printWindow.document.write(passportPrintHtml(passport));
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 400);
  });
}

export async function sendHealthReport(reportType, button) {
  const originalHtml = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `${icon("mail")} 正在发送…`;
  try {
    const result = await api("/api/email/health-report", {
      method: "POST",
      body: JSON.stringify({ report_type: reportType }),
    });
    toast(`报告已发送至 ${result.recipient}`);
  } catch (error) {
    toast(error.message, "error", 5500);
  } finally {
    button.disabled = false;
    button.innerHTML = originalHtml;
    hydrateIcons(button);
  }
}

export function passportPrintHtml(passport) {
  const condition = (items) => (items || []).map(escapeHtml).join("、") || "无记录";
  const events = (passport.timeline || []).slice(0, 20).map((event) => `
    <li><strong>${escapeHtml(event.title)}</strong><br>${escapeHtml(event.description)}
    <small>${formatDate(event.occurred_at, { year: "numeric" })} · ${escapeHtml(event.source || "")}</small></li>`).join("");
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
    <title>健康证据护照 - ${escapeHtml(passport.owner.name)}</title>
    <style>body{font-family:"Microsoft YaHei",sans-serif;color:#17372d;max-width:760px;margin:36px auto;line-height:1.7}h1{font-size:26px}h2{font-size:17px;border-top:1px solid #c9dbd3;padding-top:16px}li{margin:8px 0}small{color:#637b72}.meta{color:#637b72}.notice{margin-top:24px;padding:12px;background:#f1f7f4;font-size:12px}</style></head>
    <body><h1>知衡健康 · 健康证据护照</h1><p class="meta">${escapeHtml(passport.owner.name)} · ${formatDate(passport.generated_at, { year: "numeric" })}</p>
    <h2>健康概况</h2><p><b>${escapeHtml(passport.overview.status || "等待数据")}</b> · 健康评分 ${passport.overview.score || 0} / 100</p><p>${escapeHtml(passport.overview.insight || "")}</p>
    <h2>健康档案</h2><p>基础疾病：${condition(passport.profile.conditions)}</p><p>过敏史：${condition(passport.profile.allergies)}</p><p>长期用药：${condition(passport.profile.medications)}</p>
    <h2>近期健康事件</h2><ul>${events || "<li>暂无记录</li>"}</ul>
    <h2>近期咨询</h2><ul>${(passport.recent_consultations || []).map((item) => `<li>${escapeHtml(item.title)}</li>`).join("") || "<li>暂无记录</li>"}</ul>
    <p class="notice">${escapeHtml(passport.disclaimer)}</p></body></html>`;
}

export function compressImageFile(file) {
  return new Promise((resolve, reject) => {
    if (!file || !file.type.startsWith("image/")) {
      reject(new Error("请选择图片文件"));
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      reject(new Error("图片不能超过 12 MB"));
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("读取图片失败"));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("图片格式无法识别"));
      image.onload = () => {
        const maxSide = 1400;
        const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve({
          dataUrl: canvas.toDataURL("image/jpeg", 0.82),
          name: file.name,
        });
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

export function setChatImage(image) {
  state.chatImage = image;
  const preview = $("#chat-image-preview");
  if (!preview) return;
  preview.hidden = !image;
  preview.innerHTML = image
    ? `<img src="${image.dataUrl}" alt="待发送图片预览"/><div><strong>${escapeHtml(image.name)}</strong><small>将使用视觉模型分析，图片不保存</small></div><button type="button" id="remove-chat-image" aria-label="移除图片">${icon("close")}</button>`
    : "";
  $("#remove-chat-image")?.addEventListener("click", () => setChatImage(null));
}

export function setTriageImage(image) {
  state.triageImage = image;
  const preview = $("#triage-image-preview");
  if (!preview) return;
  preview.hidden = !image;
  preview.innerHTML = image
    ? `<img src="${image.dataUrl}" alt="待分析图片预览"/><div><strong>${escapeHtml(image.name)}</strong><small>图片只在当前分析请求中使用</small></div><button type="button" id="remove-triage-image" aria-label="移除图片">${icon("close")}</button>`
    : "";
  $("#remove-triage-image")?.addEventListener("click", () => setTriageImage(null));
}

export function closeModal() {
  state.inspectorGraph?.destroy();
  state.inspectorGraph = null;
  state.inspectorCurrentNode = null;
  state.inspectorHistory = { entries: [], index: -1 };
  const root = $("#modal-root");
  if (root) root.innerHTML = "";
}

export function bindModalClose() {
  $$("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", closeModal);
  });
  const dialog = $("#modal-root [role=dialog]");
  if (!dialog) return;
  const focusable = () =>
    $$(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      dialog
    ).filter((element) => element.offsetParent !== null);
  const first = focusable()[0];
  if (first) requestAnimationFrame(() => first.focus());
  dialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const items = focusable();
    if (!items.length) return;
    const firstItem = items[0];
    const lastItem = items[items.length - 1];
    if (event.shiftKey && document.activeElement === firstItem) {
      event.preventDefault();
      lastItem.focus();
    } else if (!event.shiftKey && document.activeElement === lastItem) {
      event.preventDefault();
      firstItem.focus();
    }
  });
}

export function scoreRing(score, label = "健康评分") {
  return `
    <div class="score-ring" style="--score:${clamp(Number(score), 0, 100)}">
      <div><strong>${score}</strong><small>${label}</small></div>
    </div>`;
}

