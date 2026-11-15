import { $, state, icon, escapeHtml, api, toast, closeModal, bindModalClose, compressImageFile } from "../ui-core.js?v=20261106-29";
import { deps } from "./deps.js";
export function openRecordModal() {
  let importedFromImage = false;
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="record-modal-title">
      <h2 class="modal-title" id="record-modal-title">记录一次健康体征</h2>
      <p class="modal-subtitle">连续数据比单次读数更有价值。缺失项可以留空。</p>
      <form id="record-form">
        <section class="record-import-panel">
          <div class="record-import-head">
            <span class="record-import-icon">${icon("image")}</span>
            <div>
              <strong>从智能手表读数导入</strong>
              <small>上传 App 截图或拍下手表读数，识别后请核对再保存。</small>
            </div>
          </div>
          <div class="record-import-actions">
            <button type="button" class="ghost-button" id="record-image-pick">${icon("image")} 上传截图</button>
            <button type="button" class="ghost-button" id="record-camera-pick">${icon("scan")} 拍照识别</button>
            <span>支持 JPG、PNG、WebP</span>
          </div>
          <input id="record-image-input" type="file" accept="image/jpeg,image/png,image/webp" hidden />
          <input id="record-camera-input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden />
          <div class="record-image-state" id="record-image-state" hidden></div>
        </section>
        <div class="form-grid-2">
          ${modalInput("systolic", "收缩压（毫米汞柱）", "number", "118")}
          ${modalInput("diastolic", "舒张压（毫米汞柱）", "number", "76")}
          ${modalInput("heart_rate", "静息心率（次/分）", "number", "72")}
          ${modalInput("glucose", "血糖 (mmol/L)", "number", "5.4", "0.1")}
          ${modalInput("spo2", "血氧 (%)", "number", "98")}
          ${modalInput("sleep_hours", "睡眠时长 (小时)", "number", "7.5", "0.1")}
          ${modalInput("weight_kg", "体重（千克）", "number", "52.0", "0.1")}
          ${modalInput("steps", "步数", "number", "8000")}
        </div>
        <div class="modal-field">
          <label>备注</label>
          <input name="note" placeholder="例如：晨起、运动后、服药后" maxlength="500" />
        </div>
        <div class="modal-actions">
          <button type="button" class="ghost-button" data-close-modal>取消</button>
          <button type="submit" class="primary-button">保存记录</button>
        </div>
      </form>
    </section>`;
  bindModalClose();
  const imageInput = $("#record-image-input");
  const cameraInput = $("#record-camera-input");
  $("#record-image-pick").addEventListener("click", () => imageInput.click());
  $("#record-camera-pick").addEventListener("click", () => cameraInput.click());
  imageInput.addEventListener("change", () => handleRecordImage(imageInput.files?.[0]));
  cameraInput.addEventListener("change", () => handleRecordImage(cameraInput.files?.[0]));

  async function handleRecordImage(file) {
    if (!file) return;
    const stateBox = $("#record-image-state");
    const uploadButton = $("#record-image-pick");
    const cameraButton = $("#record-camera-pick");
    stateBox.hidden = false;
    stateBox.className = "record-image-state analyzing";
    stateBox.innerHTML = `<span class="record-import-spinner"></span><div><strong>正在识别画面中的健康数据…</strong><small>图片仅用于本次识别，不会保存。</small></div>`;
    uploadButton.disabled = true;
    cameraButton.disabled = true;
    try {
      const image = await compressImageFile(file);
      stateBox.innerHTML = `<img src="${image.dataUrl}" alt="待识别健康读数截图"/><span class="record-import-spinner"></span><div><strong>正在读取读数…</strong><small>${escapeHtml(image.name)}</small></div>`;
      const result = await api("/api/vision/health-metrics", {
        method: "POST",
        body: JSON.stringify({ image_data: image.dataUrl }),
      });
      const metrics = result.metrics || {};
      const form = $("#record-form");
      const filled = [];
      const preserved = [];
      for (const [key, value] of Object.entries(metrics)) {
        const input = form.elements.namedItem(key);
        if (!input) continue;
        if (input.value !== "" && Number(input.value) !== Number(value)) {
          preserved.push(key);
          continue;
        }
        input.value = value;
        input.classList.add("record-recognized");
        filled.push(key);
      }
      if (filled.length) importedFromImage = true;
      if (!filled.length) {
        stateBox.className = "record-image-state empty";
        stateBox.innerHTML = `<img src="${image.dataUrl}" alt="已上传健康读数截图"/><div><strong>没有识别到可填写的数值</strong><small>请换一张更清晰、无反光的截图，或手动填写。</small></div>`;
        toast("未识别到健康数据，请尝试更清晰的截图", "error");
        return;
      }
      const confidenceLabels = { high: "较清晰", medium: "需留意", low: "低清晰度" };
      const notes = (result.notes || []).map((note) => `<li>${escapeHtml(note)}</li>`).join("");
      stateBox.className = "record-image-state success";
      stateBox.innerHTML = `
        <img src="${image.dataUrl}" alt="已识别健康读数截图"/>
        <div>
          <strong>已识别 ${filled.length} 项数据，请核对</strong>
          <small>识别把握：${escapeHtml(confidenceLabels[result.confidence] || "需留意")}${preserved.length ? ` · ${preserved.length} 项已有内容未覆盖` : ""}</small>
          ${notes ? `<ul>${notes}</ul>` : ""}
        </div>`;
      toast(`已识别 ${filled.length} 项健康数据，请核对后保存`);
    } catch (error) {
      stateBox.className = "record-image-state error";
      stateBox.innerHTML = `<div><strong>图片识别失败</strong><small>${escapeHtml(error.message)}</small></div>`;
      toast(error.message, "error", 5000);
    } finally {
      uploadButton.disabled = false;
      cameraButton.disabled = false;
      imageInput.value = "";
      cameraInput.value = "";
    }
  }

  $("#record-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      source: importedFromImage ? "智能设备截图" : "manual",
      note: form.get("note") || "",
    };
    for (const [key, value] of form.entries()) {
      if (key !== "note" && value !== "") payload[key] = Number(value);
    }
    try {
      await api("/api/health/records", { method: "POST", body: JSON.stringify(payload) });
      closeModal();
      toast("健康记录已保存，趋势已重新分析");
      if (state.view === "health") deps.renderHealth?.();
      if (state.view === "dashboard") deps.renderDashboard?.();
    } catch (error) {
      toast(error.message, "error");
    }
  });
}


export function modalInput(name, label, type = "text", placeholder = "", step = "1") {
  return `<div class="modal-field"><label>${label}</label><input name="${name}" type="${type}" placeholder="${placeholder}" ${type === "number" ? `step="${step}"` : ""} /></div>`;
}


export function openProfileModal() {
  const profile = state.healthData?.profile || state.user?.profile || {};
  $("#modal-root").innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭"></button>
    <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="profile-modal-title">
      <h2 class="modal-title" id="profile-modal-title">个人健康档案</h2>
      <p class="modal-subtitle">这些信息会用于过敏、特殊人群和个性化风险提醒。</p>
      <form id="profile-form">
        <div class="form-grid-2">
          <div class="modal-field"><label>性别</label><select name="gender"><option value="">未填写</option><option value="女" ${profile.gender === "女" ? "selected" : ""}>女</option><option value="男" ${profile.gender === "男" ? "selected" : ""}>男</option><option value="其他" ${profile.gender === "其他" ? "selected" : ""}>其他</option></select></div>
          <div class="modal-field"><label>出生日期</label><input type="date" name="birth_date" value="${escapeHtml(profile.birth_date || "")}" /></div>
          <div class="modal-field"><label>血型</label><select name="blood_type"><option value="">未填写</option>${["A","B","AB","O"].map((type) => `<option value="${type}" ${profile.blood_type === type ? "selected" : ""}>${type} 型</option>`).join("")}</select></div>
          <div class="modal-field"><label>身高（厘米）</label><input type="number" name="height_cm" value="${profile.height_cm || ""}" step="0.1" /></div>
        </div>
        <div class="modal-field"><label>过敏史（用逗号分隔）</label><input name="allergies" value="${escapeHtml((profile.allergies || []).join("，"))}" /></div>
        <div class="modal-field"><label>基础疾病</label><input name="conditions" value="${escapeHtml((profile.conditions || []).join("，"))}" /></div>
        <div class="modal-field"><label>长期用药</label><input name="medications" value="${escapeHtml((profile.medications || []).join("，"))}" /></div>
        <div class="modal-field"><label>家族史</label><input name="family_history" value="${escapeHtml((profile.family_history || []).join("，"))}" /></div>
        <div class="modal-actions">
          <button type="button" class="ghost-button" data-close-modal>取消</button>
          <button type="submit" class="primary-button">保存档案</button>
        </div>
      </form>
    </section>`;
  bindModalClose();
  $("#profile-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const split = (value) => String(value || "").split(/[，,、]/).map((item) => item.trim()).filter(Boolean);
    const payload = {
      gender: form.get("gender") || "",
      birth_date: form.get("birth_date") || "",
      blood_type: form.get("blood_type") || "",
      height_cm: form.get("height_cm") ? Number(form.get("height_cm")) : null,
      allergies: split(form.get("allergies")),
      conditions: split(form.get("conditions")),
      medications: split(form.get("medications")),
      family_history: split(form.get("family_history")),
    };
    try {
      const result = await api("/api/health/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      state.user.profile = result.profile;
      closeModal();
      toast("个人健康档案已更新");
    deps.renderHealth?.();
    } catch (error) {
      toast(error.message, "error");
    }
  });
}

