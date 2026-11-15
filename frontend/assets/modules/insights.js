import { icon, escapeHtml, clamp } from "../ui-core.js?v=20261106-29";
export function lineChart(values, labels = [], options = {}) {
  const width = 700;
  const height = options.height || 185;
  const padX = 20;
  const padTop = 16;
  const padBottom = 25;
  const clean = values.length ? values.map(Number) : [0];
  const secondary = (options.secondary || []).map(Number);
  const allValues = [...clean, ...secondary];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const span = max - min || 1;
  const low = min - span * 0.24;
  const high = max + span * 0.24;
  const point = (value, index) => {
    const x = padX + (index / Math.max(clean.length - 1, 1)) * (width - padX * 2);
    const y = padTop + ((high - value) / (high - low)) * (height - padTop - padBottom);
    return [x, y];
  };
  const points = clean.map(point);
  const secondaryPoints = secondary.map((value, index) => point(value, index));
  const path = points.map(([x, y], index) => `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const secondaryPath = secondaryPoints.map(([x, y], index) => `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const areaPath = `${path} L${points.at(-1)[0]},${height - padBottom} L${points[0][0]},${height - padBottom} Z`;
  const grid = [0, 1, 2, 3].map((index) => {
    const y = padTop + index * ((height - padTop - padBottom) / 3);
    return `<line class="chart-grid-line" x1="${padX}" x2="${width - padX}" y1="${y}" y2="${y}" />`;
  }).join("");
  const xLabels = labels.map((label, index) => {
    if (labels.length > 8 && index % 2) return "";
    const [x] = point(clean[Math.min(index, clean.length - 1)], index);
    return `<text class="chart-axis-label" x="${x}" y="${height - 5}" text-anchor="middle">${escapeHtml(label)}</text>`;
  }).join("");
  const dots = points.map(([x, y], index) => `
    ${index === points.length - 1 ? `<circle class="chart-tooltip-dot" cx="${x}" cy="${y}" r="9"/>` : ""}
    <circle class="chart-point" cx="${x}" cy="${y}" r="2.5"><title>${clean[index]}</title></circle>
  `).join("");
  return `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="健康趋势折线图">
      <defs>
        <linearGradient id="chart-area-${Math.random().toString(36).slice(2)}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${options.color || "#68e0b1"}" stop-opacity=".15"/>
          <stop offset="100%" stop-color="${options.color || "#68e0b1"}" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${grid}
      <path d="${areaPath}" fill="${options.color || "#68e0b1"}" opacity=".045"/>
      ${secondaryPath ? `<path class="chart-line secondary" d="${secondaryPath}"/>` : ""}
      <path class="chart-line" d="${path}"/>
      ${dots}
      ${xLabels}
    </svg>`;
}


export function metricCard(iconName, label, value, unit, foot, tone) {
  return `
    <article class="card metric-card" data-go-dashboard-health role="button" tabindex="0" aria-label="查看${label}趋势">
      <div class="metric-top">
        <span class="metric-icon">${icon(iconName)}</span>
        <span class="metric-label">${label}</span>
      </div>
      <div class="metric-value"><strong>${escapeHtml(value)}</strong><span>${unit}</span></div>
      <div class="metric-foot"><span class="${tone}">${escapeHtml(foot)}</span><span>↗</span></div>
    </article>`;
}


export function signalRow(label, value, display) {
  return `
    <div class="signal-row">
      <span>${label}</span>
      <div class="signal-bar"><i style="--value:${clamp(value, 0, 100)}%"></i></div>
      <strong>${escapeHtml(display)}</strong>
    </div>`;
}


export function vitalSignalScore(latest) {
  let score = 100;
  if (latest.systolic && (latest.systolic < 90 || latest.systolic > 140)) score -= 25;
  if (latest.heart_rate && (latest.heart_rate < 50 || latest.heart_rate > 100)) score -= 25;
  if (latest.spo2 && latest.spo2 < 95) score -= 30;
  return score;
}


export function vitalItem(label, value, unit, note) {
  return `<div class="vital-item"><span>${label}</span><strong>${escapeHtml(value)}<small>${unit}</small></strong><em>${escapeHtml(note)}</em></div>`;
}


export function profileItem(label, value) {
  return `<div class="profile-item"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`;
}


export function chartMetricValues(records, metric) {
  if (metric === "bp") {
    return records.filter((record) => record.systolic).map((record) => record.systolic);
  }
  return records.filter((record) => record[metric] != null).map((record) => Number(record[metric]));
}


export function ageFromBirthDate(value) {
  if (!value) return null;
  const birth = new Date(value);
  if (Number.isNaN(birth.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  if (now.getMonth() < birth.getMonth() || (now.getMonth() === birth.getMonth() && now.getDate() < birth.getDate())) age--;
  return age;
}


export function formatCompact(number) {
  if (!number) return "0";
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(1)}M`;
  if (number >= 10_000) return `${Math.round(number / 1000)}K`;
  return Number(number).toLocaleString("zh-CN");
}


export function labelChinese(label) {
  const map = {
    SymptomAndSign: "症状体征",
    Drug: "药品",
    Ingredients: "成分",
    Disease: "疾病",
    Cause: "病因",
    Precautions: "注意事项",
    AdverseReactions: "不良反应",
    Symptom: "症状",
    Check: "检查",
    Department: "科室",
  };
  return map[label] || label;
}

