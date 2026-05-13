let ws = null;
let apiBase = localStorage.getItem("apiBase") || "http://127.0.0.1:8000";

const el = (id) => document.getElementById(id);
const money = (v) => Number(v || 0).toLocaleString("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const num = (v) => Number(v || 0).toLocaleString("zh-CN");
const pct = (v) => `${Number(v || 0).toFixed(2)}%`;
const time = (v) => (v ? new Date(v).toLocaleString() : "-");

function setError(targetId, message) {
  el(targetId).innerHTML = `<div class="notice bad">${message}</div>`;
}

function metric(label, value, tone = "") {
  return `<div class="metric ${tone}">
    <span>${label}</span>
    <strong>${value}</strong>
  </div>`;
}

function renderKeyValues(targetId, title, rows) {
  el(targetId).innerHTML = `
    <div class="result-header">${title}</div>
    <div class="kv-list">
      ${rows.map(([k, v]) => `<div><span>${k}</span><strong>${v}</strong></div>`).join("")}
    </div>
  `;
}

function setAccountTab(activeId) {
  ["loadPortfolio", "loadUserAnalysis", "loadMarketAnalysis"].forEach((id) => {
    el(id).classList.toggle("active", id === activeId);
  });
}

const apiBaseInput = el("apiBase");
apiBaseInput.value = apiBase;

el("saveBase").onclick = () => {
  apiBase = apiBaseInput.value.trim().replace(/\/$/, "");
  localStorage.setItem("apiBase", apiBase);
  alert("已保存 API Base");
};

el("checkHealth").onclick = async () => {
  try {
    const r = await fetch(`${apiBase}/health`);
    const data = await r.json();
    el("healthResult").innerHTML = `
      <span class="dot ${data.status === "ok" ? "ok" : "bad"}"></span>
      后端状态：${data.status === "ok" ? "运行中" : "异常"}
    `;
  } catch (err) {
    setError("healthResult", String(err));
  }
};

function renderMarketRows(data) {
  const tbody = el("marketTable");
  tbody.innerHTML = "";
  for (const item of data) {
    const tr = document.createElement("tr");
    const changePct = (Number(item.change) * 100).toFixed(3);
    tr.innerHTML = `
      <td>${item.symbol}</td>
      <td>${item.price}</td>
      <td style="color:${item.change >= 0 ? "#0b8f5a" : "#c23c3c"}">${changePct}%</td>
      <td>${item.volume}</td>
      <td>${new Date(item.ts).toLocaleTimeString()}</td>
    `;
    tbody.appendChild(tr);
  }
}

el("connectWs").onclick = () => {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  const wsUrl = apiBase.replace("http://", "ws://").replace("https://", "wss://") + "/ws/market";
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    el("wsStatus").textContent = "已连接";
    el("wsStatus").className = "ok";
  };

  ws.onclose = () => {
    el("wsStatus").textContent = "已断开";
    el("wsStatus").className = "bad";
  };

  ws.onerror = () => {
    el("wsStatus").textContent = "连接异常";
    el("wsStatus").className = "bad";
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "snapshot" && Array.isArray(msg.data)) {
        renderMarketRows(msg.data);
      }
    } catch {
      // ignore non-json payloads
    }
  };
};

el("disconnectWs").onclick = () => {
  if (ws) ws.close();
};

el("placeOrder").onclick = async () => {
  const payload = {
    user_id: el("userId").value.trim(),
    symbol: el("symbol").value.trim().toUpperCase(),
    side: el("side").value,
    quantity: Number(el("qty").value),
  };

  try {
    const r = await fetch(`${apiBase}/api/order`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await r.json();
    if (!r.ok) {
      setError("orderResult", data.detail || "下单失败");
      return;
    }
    renderKeyValues("orderResult", "成交回报", [
      ["订单号", data.order_id],
      ["用户", data.user_id],
      ["标的", data.symbol],
      ["方向", data.side === "buy" ? "买入" : "卖出"],
      ["状态", data.status === "filled" ? "已成交" : data.status],
      ["成交价", money(data.fill_price)],
      ["数量", num(data.fill_qty)],
      ["成交额", money(data.notional)],
      ["时间", time(data.ts)],
    ]);
  } catch (err) {
    setError("orderResult", String(err));
  }
};

el("loadPortfolio").onclick = async () => {
  setAccountTab("loadPortfolio");
  const userId = el("userId").value.trim();
  try {
    const r = await fetch(`${apiBase}/api/user/${userId}/portfolio`);
    const data = await r.json();
    if (!r.ok) {
      setError("accountPanel", data.detail || "查询持仓失败");
      return;
    }
    const rows = (data.positions || []).map((p) => `
      <tr>
        <td>${p.symbol}</td>
        <td>${num(p.quantity)}</td>
        <td>${money(p.avg_price)}</td>
        <td>${money(p.market_price)}</td>
        <td class="${p.unrealized_pnl >= 0 ? "pos" : "neg"}">${money(p.unrealized_pnl)}</td>
      </tr>
    `).join("");

    el("accountPanel").innerHTML = `
      <div class="result-header">账户资产</div>
      <div class="metrics">
        ${metric("现金", money(data.cash))}
        ${metric("总权益", money(data.total_equity))}
        ${metric("已实现盈亏", money(data.realized_pnl), data.realized_pnl >= 0 ? "pos" : "neg")}
        ${metric("持仓数", num((data.positions || []).length))}
      </div>
      <table class="result-table">
        <thead><tr><th>标的</th><th>数量</th><th>成本价</th><th>现价</th><th>浮动盈亏</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5" class="muted">暂无持仓</td></tr>`}</tbody>
      </table>
    `;
  } catch (err) {
    setError("accountPanel", String(err));
  }
};

el("loadUserAnalysis").onclick = async () => {
  setAccountTab("loadUserAnalysis");
  const userId = el("userId").value.trim();
  try {
    const r = await fetch(`${apiBase}/api/user/${userId}/analysis`);
    const data = await r.json();
    if (!r.ok) {
      setError("accountPanel", data.detail || "查询用户分析失败");
      return;
    }
    const distRows = Object.entries(data.position_distribution || {}).map(([symbol, value]) => `
      <tr><td>${symbol}</td><td>${money(value)}</td></tr>
    `).join("");
    el("accountPanel").innerHTML = `
      <div class="result-header">用户交易分析</div>
      <div class="metrics">
        ${metric("交易次数", num(data.trade_count))}
        ${metric("胜率", pct(data.win_rate))}
        ${metric("已实现盈亏", money(data.realized_pnl), data.realized_pnl >= 0 ? "pos" : "neg")}
        ${metric("未实现盈亏", money(data.unrealized_pnl), data.unrealized_pnl >= 0 ? "pos" : "neg")}
        ${metric("总盈亏", money(data.total_pnl), data.total_pnl >= 0 ? "pos" : "neg")}
        ${metric("持仓市值", money(data.exposure_notional))}
      </div>
      <table class="result-table">
        <thead><tr><th>标的</th><th>持仓市值</th></tr></thead>
        <tbody>${distRows || `<tr><td colspan="2" class="muted">暂无仓位分布</td></tr>`}</tbody>
      </table>
    `;
  } catch (err) {
    setError("accountPanel", String(err));
  }
};

el("loadMarketAnalysis").onclick = async () => {
  setAccountTab("loadMarketAnalysis");
  try {
    const r = await fetch(`${apiBase}/api/market/analysis`);
    const data = await r.json();
    if (!r.ok) {
      setError("accountPanel", data.detail || "查询市场分析失败");
      return;
    }
    el("accountPanel").innerHTML = `
      <div class="result-header">市场概览</div>
      <div class="metrics">
        ${metric("标的数量", num(data.symbol_count))}
        ${metric("平均价格", money(data.avg_price))}
        ${metric("总成交量", num(data.total_volume))}
        ${metric("总成交额", money(data.total_notional))}
        ${metric("平均波动", pct(data.avg_abs_change_pct))}
        ${metric("20窗口波动率", money(data.volatility_20))}
      </div>
      <div class="small-note">更新时间：${time(data.ts)}</div>
    `;
  } catch (err) {
    setError("accountPanel", String(err));
  }
};

el("checkHealth").click();
el("loadPortfolio").click();

