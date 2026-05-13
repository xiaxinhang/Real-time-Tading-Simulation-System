export function formatMoney(value) {
  return Number(value || 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

export function formatPercent(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

export function formatTime(value) {
  return value ? new Date(value).toLocaleTimeString() : "-";
}
