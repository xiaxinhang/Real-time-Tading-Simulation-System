let ws = null;
let apiBase = localStorage.getItem("apiBase") || "http://127.0.0.1:8000";

const el = (id) => document.getElementById(id);
const pretty = (v) => JSON.stringify(v, null, 2);

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
    el("healthResult").textContent = pretty(await r.json());
  } catch (err) {
    el("healthResult").textContent = String(err);
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
    el("orderResult").textContent = pretty(data);
  } catch (err) {
    el("orderResult").textContent = String(err);
  }
};

el("loadPortfolio").onclick = async () => {
  const userId = el("userId").value.trim();
  try {
    const r = await fetch(`${apiBase}/api/user/${userId}/portfolio`);
    el("portfolioResult").textContent = pretty(await r.json());
  } catch (err) {
    el("portfolioResult").textContent = String(err);
  }
};

el("loadUserAnalysis").onclick = async () => {
  const userId = el("userId").value.trim();
  try {
    const r = await fetch(`${apiBase}/api/user/${userId}/analysis`);
    el("userAnalysisResult").textContent = pretty(await r.json());
  } catch (err) {
    el("userAnalysisResult").textContent = String(err);
  }
};

el("loadMarketAnalysis").onclick = async () => {
  try {
    const r = await fetch(`${apiBase}/api/market/analysis`);
    el("marketAnalysisResult").textContent = pretty(await r.json());
  } catch (err) {
    el("marketAnalysisResult").textContent = String(err);
  }
};

