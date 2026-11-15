import {
  $,
  $$,
  state,
  icon,
  escapeHtml,
  api,
  toast,
} from "../ui-core.js?v=20261106-29";


export async function renderLifestyle(isCurrent = () => true) {
  const data = await api("/api/lifestyle/plan", {
    method: "POST",
    body: JSON.stringify({
      symptoms: state.lifestyleSymptoms || "",
      dietary_preferences: state.lifestylePreferences || "",
    }),
  });
  if (!isCurrent()) return;
  drawLifestyle(data, isCurrent);
}


function drawLifestyle(data, isCurrent) {
  const risk = {
    low: ["低风险", "jade"],
    medium: ["需观察", "amber"],
    high: ["优先就医", "red"],
    emergency: ["急症警示", "red"],
  }[data.basis?.risk_level] || ["低风险", "jade"];
  const diet = data.diet || {};
  const movement = data.movement || {};
  $("#view-stack").innerHTML = `
    <div class="page-enter lifestyle-page">
      <div class="page-heading">
        <div class="page-heading-copy">
          <span>日常健康指导</span>
          <h1>健康生活建议</h1>
          <p>结合健康档案、近期体征和当前不适，生成可执行的饮食与活动参考。</p>
        </div>
        <span class="tag ${risk[1]}">${icon("shield")} ${risk[0]}</span>
      </div>

      <section class="card lifestyle-input-card">
        <div class="lifestyle-input-copy">
          <span class="eyebrow"><span></span> 个性化调整方案</span>
          <h3>今天哪里不舒服，或者想重点改善什么？</h3>
          <p>例如：肩颈酸痛、嗓子不适、最近睡眠不足。没有不适也可以直接生成日常方案。</p>
        </div>
        <form id="lifestyle-form" class="lifestyle-form">
          <div class="modal-field">
            <label>当前描述</label>
            <textarea name="symptoms" maxlength="1000" placeholder="例如：最近伏案久，肩颈酸痛，右手不麻">${escapeHtml(state.lifestyleSymptoms || "")}</textarea>
          </div>
          <div class="modal-field">
            <label>饮食偏好或忌口（可选）</label>
            <input name="dietary_preferences" maxlength="300" value="${escapeHtml(state.lifestylePreferences || "")}" placeholder="例如：不吃海鲜、希望少油、素食" />
          </div>
          <div class="lifestyle-quick-row">
            ${["肩颈酸痛", "嗓子不适", "睡眠不足", "最近血压偏高"].map((item) => `<button type="button" data-lifestyle-quick="${item}">+ ${item}</button>`).join("")}
            <button type="submit" class="primary-button">${icon("sparkles")} ${state.lifestyleGenerated ? "重新生成" : "生成"}</button>
          </div>
        </form>
      </section>

      ${data.safety?.length ? `
        <section class="lifestyle-safety-strip">
          <span>${icon("alert")}</span>
          <div><strong>使用前请留意</strong>${data.safety.map((note) => `<p>${escapeHtml(note)}</p>`).join("")}</div>
        </section>` : ""}

      <div class="lifestyle-grid">
        <section class="card lifestyle-diet-card">
          <div class="card-header">
            <div><h2 class="card-title">${escapeHtml(diet.title || "一日三餐参考")}</h2><p class="card-subtitle">不计算疾病治疗餐，使用生活化份量，便于执行和替换。</p></div>
            <span class="tag jade">${icon("heart")} 日常饮食</span>
          </div>
          <div class="diet-focus-note">
            <strong>${escapeHtml(diet.focus_title || "本方案重点")}</strong>
            <p>${escapeHtml(diet.focus_note || "")}</p>
          </div>
          <div class="lifestyle-principles">
            ${(diet.principles || []).map((item) => `
              <div><i></i><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.detail)}</p></div>`).join("")}
          </div>
          <div class="meal-plan">
            ${(diet.meals || []).map((meal, index) => `
              <article class="meal-card">
                <div class="meal-index">${String(index + 1).padStart(2, "0")}</div>
                <div class="meal-copy">
                  <h4>${escapeHtml(meal.name)}</h4>
                  <dl>
                    <div><dt>主食</dt><dd>${escapeHtml(meal.staple)}</dd></div>
                    <div><dt>蛋白质</dt><dd>${escapeHtml(meal.protein)}</dd></div>
                    <div><dt>蔬菜</dt><dd>${escapeHtml(meal.vegetable)}</dd></div>
                    <div><dt>搭配</dt><dd>${escapeHtml(meal.extra)}</dd></div>
                  </dl>
                </div>
              </article>`).join("")}
          </div>
          <div class="lifestyle-less">
            <strong>建议减少</strong>
            <div>${(diet.less_foods || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>
          </div>
          <p class="lifestyle-allergy-note">${escapeHtml(diet.allergy_note || "")}</p>
        </section>

        <section class="card lifestyle-movement-card">
          <div class="card-header">
            <div><h2 class="card-title">${escapeHtml(movement.title || "日常活动")}</h2><p class="card-subtitle">${escapeHtml(movement.focus || "低强度活动")}</p></div>
            <span class="tag ${data.basis?.risk_level === "low" ? "jade" : "amber"}">${icon("activity")} 分步进行</span>
          </div>
          <p class="movement-intro">${escapeHtml(movement.message || "")}</p>
          <div class="movement-list">
            ${(movement.items || []).map((item) => `
              <article class="movement-card">
                <span>${icon("activity")}</span>
                <div><h4>${escapeHtml(item.name)}</h4><strong>${escapeHtml(item.dose)}</strong><p>${escapeHtml(item.detail)}</p></div>
              </article>`).join("") || `<div class="evidence-empty">${icon("shield")} 当前不适场景下暂不提供动作训练。</div>`}
          </div>
          <div class="movement-stop">
            <strong>${icon("alert")} 出现以下情况立即停止</strong>
            <div>${(movement.stop_signals || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>
          </div>
        </section>
      </div>

      <section class="lifestyle-footnote">
        <div>
          <strong>本次方案依据</strong>
          <p>当前描述：${escapeHtml(data.basis?.symptoms || "未提供")} · 风险：${escapeHtml(data.basis?.risk_title || "")}</p>
        </div>
        <div class="lifestyle-sources">
          ${(data.sources || []).map((source) => `<span>${escapeHtml(source)}</span>`).join("")}
        </div>
        <p>${escapeHtml(data.disclaimer || "")}</p>
      </section>
    </div>`;

  $("#lifestyle-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    state.lifestyleSymptoms = String(form.get("symptoms") || "").trim();
    state.lifestylePreferences = String(form.get("dietary_preferences") || "").trim();
    const button = event.target.querySelector("button[type=submit]");
    const wasGenerated = state.lifestyleGenerated;
    state.lifestyleGenerated = true;
    button.disabled = true;
    button.innerHTML = `${icon("sparkles")} 正在生成…`;
    renderLifestyle(isCurrent)
      .then(() => toast("生活建议已更新"))
      .catch((error) => {
        state.lifestyleGenerated = wasGenerated;
        toast(error.message, "error");
        button.disabled = false;
        button.innerHTML = `${icon("sparkles")} ${state.lifestyleGenerated ? "重新生成" : "生成"}`;
      });
  });
  $$("[data-lifestyle-quick]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = $("#lifestyle-form textarea[name=symptoms]");
      const value = button.dataset.lifestyleQuick;
      input.value = input.value
        ? `${input.value.replace(/[，。,\s]+$/, "")}，${value}`
        : value;
      input.focus();
    });
  });
}
