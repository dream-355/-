import { icon, escapeHtml } from "../ui-core.js?v=20261106-29";
export function reviewChip(review) {
  const verdict = review.verdict || "pass";
  const labels = {
    pass: "智能复核通过",
    revised: "智能复核已修正",
    warn: "智能复核提示",
  };
  const detail = review.issue_count
    ? `title="${escapeHtml(`发现 ${review.issue_count} 处问题，已处理 ${(review.applied_fixes || []).length} 项`)}"`
    : `title="规则与证据一致性检查通过"`;
  return `<span class="review-chip ${escapeHtml(verdict)}" ${detail}>${icon("shield")} ${labels[verdict] || labels.pass}</span>`;
}


export function reviewSummary(review) {
  const reviewer = review.llm_used ? "规则引擎 + 大模型复核" : "规则引擎复核";
  if (review.verdict === "pass") {
    return `${reviewer}未发现问题：无确定诊断、无药物剂量、声明与急症提示齐全。`;
  }
  const fixes = (review.applied_fixes || []).join("；");
  const high = review.high_issue_count || 0;
  if (review.verdict === "warn") {
    return `${reviewer}发现 ${high} 项高风险问题，已提示用户以医生判断为准。`;
  }
  return `${reviewer}发现 ${review.issue_count || 0} 处问题，已自动处理：${fixes || "保持原文并标记风险"}。`;
}

