/* 科技公司预测系统 — 实战版前端(投资看板 + 自训练控制台) */
"use strict";

const $view = document.getElementById("view");
const api = (path, opts) => {
  if (opts && opts.method && opts.method !== "GET") {
    opts.headers = { ...(opts.headers || {}), "X-Dashboard": "1" };
  }
  return fetch(path, opts).then(r => {
  if (!r.ok) return r.text().then(t => { let d = t; try { d = JSON.parse(t).detail || t; } catch (e) {} throw new Error(`${r.status} ${String(d).slice(0, 300)}`); });
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
  });
};
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const del = path => api(path, { method: "DELETE" });

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (v, d = 1) => v == null ? "—" : (v * 100).toFixed(d) + "%";
const num = (v, d = 2) => v == null || v === "" || isNaN(Number(v)) ? "—" : Number(v).toFixed(d);
const money = v => v == null || isNaN(Number(v)) ? "—" : "$" + Number(v).toFixed(2);
const fmtTime = t => {
  if (!t) return "—";
  const d = typeof t === "number" ? new Date(t * 1000) : new Date(t);
  return isNaN(d) ? esc(t) : d.toLocaleString("zh-CN", { hour12: false });
};
const fmtDate = t => { const s = fmtTime(t); return s === "—" ? s : s.split(" ")[0].replace(/\//g, "-"); };

const STATUS_STYLE = { good: "var(--good)", warning: "var(--warning)", serious: "var(--serious)", critical: "var(--critical)", accent: "var(--accent)", muted: "var(--baseline)" };
const statusChip = (kind, label) => `<span class="status"><span class="dot" style="background:${STATUS_STYLE[kind] || STATUS_STYLE.muted}"></span>${esc(label)}</span>`;
const JOB_STATUS = {
  running: ["accent", "运行中"], running_detached: ["warning", "运行中(脱管)"],
  finished: ["good", "已完成"], failed: ["critical", "失败"],
  stopped: ["serious", "已停止"], interrupted: ["serious", "已中断"],
};
const jobChip = s => statusChip(...(JOB_STATUS[s] || ["muted", s || "未知"]));
const ACTION_BADGE = { buy: ["good", "买入"], hold: ["accent", "持有"], watch: ["muted", "观察"], avoid: ["critical", "回避"] };
const actionChip = a => a ? statusChip(...(ACTION_BADGE[String(a).toLowerCase()] || ["muted", a])) : statusChip("muted", "未评级");

/* ---------- minimal markdown renderer ---------- */
function mdRender(src) {
  const inline = t => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\*([^*]+)\*/g, "<i>$1</i>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a class="plain" href="$2" target="_blank" rel="noopener">$1</a>');
  const lines = String(src || "").split(/\r?\n/);
  const out = [];
  let list = null, code = false, table = null;
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  const closeTable = () => { if (table) { out.push("</tbody></table>"); table = null; } };
  for (const raw of lines) {
    if (code) { if (/^```/.test(raw)) { out.push("</code></pre>"); code = false; } else out.push(esc(raw)); continue; }
    if (/^```/.test(raw)) { closeList(); closeTable(); out.push("<pre><code>"); code = true; continue; }
    if (/^\|.*\|\s*$/.test(raw)) {
      const cells = raw.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      if (cells.every(c => /^:?-{2,}:?$/.test(c))) continue;
      if (!table) { closeList(); out.push("<table><tbody>"); table = "th"; }
      const tag = table; table = "td";
      out.push("<tr>" + cells.map(c => `<${tag}>${inline(c)}</${tag}>`).join("") + "</tr>");
      continue;
    }
    closeTable();
    let m;
    if ((m = raw.match(/^(#{1,4})\s+(.*)$/))) { closeList(); out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); }
    else if (/^\s*[-*]\s+/.test(raw)) { if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; } out.push(`<li>${inline(raw.replace(/^\s*[-*]\s+/, ""))}</li>`); }
    else if (/^\s*\d+\.\s+/.test(raw)) { if (list !== "ol") { closeList(); out.push("<ol>"); list = "ol"; } out.push(`<li>${inline(raw.replace(/^\s*\d+\.\s+/, ""))}</li>`); }
    else if (/^\s*(---+|\*\*\*+)\s*$/.test(raw)) { closeList(); out.push("<hr>"); }
    else if (raw.trim() === "") closeList();
    else { closeList(); out.push(`<p>${inline(raw)}</p>`); }
  }
  closeList(); closeTable(); if (code) out.push("</code></pre>");
  return `<div class="md">${out.join("\n")}</div>`;
}

/* ---------- header ---------- */
async function refreshHeader() {
  try {
    const [status, timeline] = await Promise.all([api("/api/status"), api("/api/method/timeline")]);
    const paused = (status.control || {}).auto_training === "pause";
    document.getElementById("chip-control").innerHTML = statusChip(paused ? "warning" : "good", paused ? "自动优化:已暂停" : "自动优化:运行");
    document.getElementById("chip-method").innerHTML = `方法版本 <span class="mono">${esc(timeline.branch || "?")}@${esc((timeline.head || "").slice(0, 7))}</span>`;
    document.getElementById("chip-refresh").textContent = "刷新于 " + new Date().toLocaleTimeString("zh-CN", { hour12: false });
  } catch (e) { document.getElementById("chip-refresh").textContent = "后端不可达"; }
}

/* ================= 投资看板 ================= */
const expanded = new Set();          // securities whose detail row is open
const detailCache = new Map();       // case detail cache

function upsideCell(quotePrice, valuation) {
  const price = quotePrice ?? valuation?.current_price;
  const base = valuation?.fair_value?.base;
  if (price == null || base == null || !Number(price)) return "—";
  const up = base / price - 1;
  const cls = up >= 0 ? "up-good" : "up-bad";
  return `<span class="${cls}">${up >= 0 ? "+" : ""}${(up * 100).toFixed(1)}%</span>`;
}

async function viewPortfolio() {
  const rows = await api("/api/portfolio");
  const symbols = rows.map(r => r.security).filter(Boolean);
  const quotes = {};  // filled in asynchronously after first paint (cold Yahoo fetches can take seconds)

  let html = `
  <div class="card">
    <div class="form-row" style="margin-bottom:0">
      <div class="field"><label>公司名</label><input id="w-entity" placeholder="Micron Technology"></div>
      <div class="field"><label>代码</label><input id="w-sec" placeholder="MU" style="min-width:90px"></div>
      <div class="field"><label>备注(可选)</label><input id="w-note" placeholder="存储周期"></div>
      <button class="btn btn-primary" id="w-add">加入关注</button>
      <span id="w-msg" class="formmsg"></span>
    </div>
  </div>`;

  if (!rows.length) {
    html += `<div class="empty"><b>关注列表为空。</b><br>先把要研究的公司加进来,然后点「跑预测」——完成后这一行会出现当前股价、AI 目标价和建议买入价。</div>`;
    $view.innerHTML = html; bindPortfolio(rows); return;
  }

  html += `<div class="card tablecard"><table class="grid ptable"><thead><tr>
    <th>公司</th><th class="num">当前股价</th><th>当前估值</th><th class="num">AI 目标价</th><th class="num">建议买入价</th>
    <th class="num">空间</th><th>评级</th><th></th>
  </tr></thead><tbody>`;
  for (const r of rows) {
    const q = quotes[r.security] || {};
    const v = r.valuation || null;
    const livePrice = q.price ?? null;
    const priceCell = livePrice != null
      ? `${money(livePrice)} <span class="cellnote">实时</span>`
      : v?.current_price != null ? `${money(v.current_price)} <span class="cellnote">${esc((v.price_as_of || "").slice(0, 10) || "研究时点")}</span>` : "—";
    const latest = r.latest_live || r.latest;
    html += `<tr class="rowlink prow" data-sec="${esc(r.security)}">
      <td><b>${esc(r.entity)}</b> <span class="mono cellnote">${esc(r.security)}</span>
        <div class="cellnote">${r.note ? esc(r.note) + " · " : ""}${latest ? "最新预测 " + fmtDate(latest.last_activity) : "未跑过"}${r.job_running ? " · " : ""}</div>${r.job_running ? statusChip("accent", "运行中") : ""}</td>
      <td class="num">${priceCell}</td>
      <td>${esc(v?.current_valuation_note || "—")}</td>
      <td class="num"><b>${money(v?.fair_value?.base)}</b></td>
      <td class="num">${money(v?.recommended_buy_price)}</td>
      <td class="num">${upsideCell(livePrice, v)}</td>
      <td>${actionChip(v?.action)}</td>
      <td class="actcell">
        <button class="btn btn-sm" data-run="${esc(r.security)}" data-entity="${esc(r.entity)}" ${r.job_running ? "disabled" : ""}>跑预测</button>
        <button class="btn btn-sm btn-danger" data-unwatch="${esc(r.security)}">移除</button>
      </td>
    </tr>
    <tr class="drow" data-drow="${esc(r.security)}" style="display:${expanded.has(r.security) ? "" : "none"}"><td colspan="8"><div class="dwrap" id="d-${esc(r.security)}">${expanded.has(r.security) ? "加载中…" : ""}</div></td></tr>`;
  }
  html += `</tbody></table></div>
  <div class="notice">折叠行 = 结论;点击行展开 = 理由(预测明细、情景、机制、运行记录、完整报告、模型下载)。实时价源自 Yahoo(可在 backend/config.json 配代理),取不到时回退为研究时点价格。</div>`;
  $view.innerHTML = html;
  bindPortfolio(rows);
  for (const sec of expanded) renderDetail(sec, rows);
  if (symbols.length) {
    api("/api/quotes?symbols=" + encodeURIComponent(symbols.join(","))).then(q => {
      for (const r of rows) {
        const quote = q[r.security];
        if (!quote || quote.price == null) continue;
        const cell = $view.querySelector(`.prow[data-sec="${CSS.escape(r.security)}"] td:nth-child(2)`);
        if (cell) cell.innerHTML = `${money(quote.price)} <span class="cellnote">实时</span>`;
        const up = $view.querySelector(`.prow[data-sec="${CSS.escape(r.security)}"] td:nth-child(6)`);
        if (up) up.innerHTML = upsideCell(quote.price, r.valuation);
      }
    }).catch(() => {});
  }
}

function bindPortfolio(rows) {
  const msg = document.getElementById("w-msg");
  document.getElementById("w-add").onclick = async () => {
    try {
      await post("/api/watchlist", { entity: document.getElementById("w-entity").value, security: document.getElementById("w-sec").value, note: document.getElementById("w-note").value });
      viewPortfolio();
    } catch (e) { msg.textContent = e.message; }
  };
  $view.querySelectorAll("[data-run]").forEach(b => b.onclick = async ev => {
    ev.stopPropagation();
    b.disabled = true; b.textContent = "启动中…";
    try { await post("/api/jobs", { type: "live_forecast", engine: "claude", params: { entity: b.dataset.entity, security: b.dataset.run } }); viewPortfolio(); }
    catch (e) { alert("启动失败:" + e.message); viewPortfolio(); }
  });
  $view.querySelectorAll("[data-unwatch]").forEach(b => b.onclick = async ev => {
    ev.stopPropagation();
    if (!confirm(`把 ${b.dataset.unwatch} 移出关注列表?(不删除已有预测记录)`)) return;
    await del(`/api/watchlist/${encodeURIComponent(b.dataset.unwatch)}`); expanded.delete(b.dataset.unwatch); viewPortfolio();
  });
  $view.querySelectorAll(".prow").forEach(tr => tr.onclick = () => {
    const sec = tr.dataset.sec;
    const drow = $view.querySelector(`[data-drow="${CSS.escape(sec)}"]`);
    if (expanded.has(sec)) { expanded.delete(sec); drow.style.display = "none"; }
    else { expanded.add(sec); drow.style.display = ""; document.getElementById("d-" + sec).textContent = "加载中…"; renderDetail(sec, rows); }
  });
}

async function renderDetail(sec, rows) {
  const box = document.getElementById("d-" + sec);
  if (!box) return;
  const row = rows.find(r => r.security === sec);
  if (!row) { box.textContent = "无数据"; return; }
  const primary = row.latest_live || row.latest;
  let html = "";
  const v = row.valuation;
  if (v && (v.one_line_thesis || v.fair_value)) {
    html += `<div class="verdict">
      <div class="verdict-main">${actionChip(v.action)} <b>${esc(v.one_line_thesis || "")}</b></div>
      <div class="verdict-fv">情景公允价:悲观 ${money(v.fair_value?.bear)} · 基准 <b>${money(v.fair_value?.base)}</b> · 乐观 ${money(v.fair_value?.bull)} · 建议买入 ≤ ${money(v.recommended_buy_price)}</div>
    </div>`;
  }
  if (!primary) {
    html += `<div class="empty" style="margin:10px 0">这家公司还没跑过预测。点上面的「跑预测」发起一次(约几十分钟,完成后自动出现在这里)。</div>`;
    box.innerHTML = html; return;
  }
  try {
    const key = primary.round_id + "/" + primary.case_id;
    let detail = detailCache.get(key);
    if (!detail) { detail = await api(`/api/cases/${encodeURIComponent(primary.round_id)}/${encodeURIComponent(primary.case_id)}`); detailCache.set(key, detail); }
    const snap = detail.forecast_snapshot || {};
    const outputs = snap.outputs || {};
    const periods = [["year_1", "FY+1"], ["year_2", "FY+2"], ["year_3_distribution", "FY+3"]];
    const rowsHtml = periods.map(([k, label]) => {
      const o = outputs[k] || {};
      if (!Object.keys(o).length) return "";
      return `<tr><td>${label}</td>
        <td class="num">${num(o.revenue_point ?? o.revenue)}</td>
        <td class="num">${num(o.revenue_low)} ~ ${num(o.revenue_high)}</td>
        <td class="num">${num(o.profit_point ?? o.net_income ?? o.profit)}</td>
        <td class="num">${num(o.profit_low)} ~ ${num(o.profit_high)}</td></tr>`;
    }).join("");
    if (rowsHtml) {
      html += `<div class="dsec"><h3>预测输出(${esc(primary.run_mode === "live_forecast" ? "实时" : "训练")} · as_of ${esc((primary.as_of || "").slice(0, 10))} · 方法 ${esc((primary.method_commit || "").slice(0, 7))})</h3>
        <table class="grid"><thead><tr><th>期</th><th class="num">收入点值</th><th class="num">收入区间</th><th class="num">利润点值</th><th class="num">利润区间</th></tr></thead><tbody>${rowsHtml}</tbody></table></div>`;
    }
    const probs = Object.entries(snap.scenario_probabilities || {});
    if (probs.length) {
      const segColors = ["var(--cat-1)", "var(--cat-2)", "var(--cat-3)", "var(--cat-4)"];
      html += `<div class="dsec"><h3>情景概率</h3><div class="segbar">` +
        probs.map(([k, p], i) => `<div class="seg" style="flex:${Number(p) || 0.001};background:${segColors[i % 4]}" title="${esc(k)} ${pct(p, 0)}"></div>`).join("") +
        `</div><div class="seglegend">` +
        probs.map(([k, p], i) => `<span class="status"><span class="dot" style="background:${segColors[i % 4]}"></span>${esc(k)} ${pct(p, 0)}</span>`).join("") + `</div></div>`;
    }
    const weights = Object.entries(snap.mechanism_weights || {});
    if (weights.length) html += `<div class="dsec"><h3>机制权重</h3>${weights.map(([k, w]) => `<span class="chip">${esc(k)} ${pct(w, 0)}</span>`).join(" ")}</div>`;
    if (detail.metrics) {
      const m = detail.metrics;
      html += `<div class="dsec"><h3>对照真值(训练案例)</h3><span class="chip">收入MAPE ${pct(m.revenue_mape)}</span> <span class="chip">利润率误差 ${num(m.profit_margin_mae_pp, 1)}pp</span> <span class="chip">区间覆盖 ${pct(m.revenue_coverage, 0)}</span></div>`;
    }
    if (row.cases.length) {
      html += `<div class="dsec"><h3>运行记录(${row.cases.length})</h3><table class="grid"><thead><tr><th>轮次</th><th>as_of</th><th>模式</th><th>封存</th><th>校验</th><th>时间</th><th></th></tr></thead><tbody>`;
      for (const c of row.cases) {
        html += `<tr><td>${esc(c.round_id)}</td><td class="mono">${esc((c.as_of || "").slice(0, 10))}</td><td>${esc(c.run_mode || "—")}</td>
          <td>${c.sealed ? statusChip("good", "已封存") : statusChip("muted", "未封存")}</td>
          <td>${c.delivery_passed == null ? "—" : c.delivery_passed ? statusChip("good", "通过") : statusChip("critical", "未过")}</td>
          <td class="mono cellnote">${fmtDate(c.last_activity)}</td>
          <td>${c.has_model ? `<a class="plain" href="/api/cases/${encodeURIComponent(c.round_id)}/${encodeURIComponent(c.case_id)}/model" onclick="event.stopPropagation()">模型</a> ` : ""}<button class="btn btn-sm btn-danger" data-delcase="${esc(c.round_id)}|${esc(c.case_id)}">删除</button></td></tr>`;
      }
      html += `</tbody></table></div>`;
    }
    try {
      const hist = await api(`/api/history/${encodeURIComponent(sec)}`);
      const withVal = hist.filter(h => h.valuation);
      if (withVal.length) {
        html += `<div class="dsec"><h3>版本对比(方法演进对这家公司结论的影响)</h3>
          <table class="grid"><thead><tr><th>运行日期</th><th>方法版本</th><th>as_of</th><th class="num">目标价</th><th class="num">建议买入</th><th>评级</th><th class="num">FY+1 收入</th><th>论点</th></tr></thead><tbody>` +
          withVal.map(h => `<tr><td class="mono cellnote">${fmtDate(h.last_activity)}</td>
            <td class="mono">${esc((h.method_commit || "—").slice(0, 7))}</td>
            <td class="mono cellnote">${esc((h.as_of || "").slice(0, 10))}</td>
            <td class="num">${money(h.valuation?.fair_value?.base)}</td>
            <td class="num">${money(h.valuation?.recommended_buy_price)}</td>
            <td>${actionChip(h.valuation?.action)}</td>
            <td class="num">${num(h.fy1_revenue_point)}</td>
            <td class="cellnote">${esc(h.valuation?.one_line_thesis || "")}</td></tr>`).join("") +
          `</tbody></table></div>`;
      }
    } catch (e) {}
    if (primary.has_report) {
      const report = await api(`/api/cases/${encodeURIComponent(primary.round_id)}/${encodeURIComponent(primary.case_id)}/report`);
      html += `<div class="dsec"><h3>完整理由(研究报告)</h3>${mdRender(report)}</div>`;
    }
  } catch (e) { html += `<div class="notice">明细加载失败:${esc(e.message)}</div>`; }
  box.innerHTML = html;
  box.querySelectorAll("[data-delcase]").forEach(b => b.onclick = async ev => {
    ev.stopPropagation();
    const [r, c] = b.dataset.delcase.split("|");
    if (!confirm(`删除运行记录 ${c}(移入回收站 training-runs/_trash,可手动恢复)?`)) return;
    try { await del(`/api/cases/${encodeURIComponent(r)}/${encodeURIComponent(c)}`); }
    catch (e) { alert("删除失败:" + e.message); }
    detailCache.clear(); viewPortfolio();
  });
}

/* ================= 自训练 ================= */
let logTimer = null;
const plan = { a: [], b: [] };       // planner state persists across re-renders

function nextRoundId(rounds) {
  let n = 0;
  for (const r of rounds) { const m = r.round_id.match(/^round-(\d+)$/); if (m) n = Math.max(n, +m[1]); }
  return "round-" + (n + 1);
}

async function viewTraining() {
  clearInterval(logTimer);
  const [status, roundsData, waves, jobsList, engines] = await Promise.all([
    api("/api/status"), api("/api/rounds"), api("/api/curriculum"), api("/api/jobs"), api("/api/engines")]);
  const paused = (status.control || {}).auto_training === "pause";
  const usedKeys = new Set(roundsData.flatMap(r => r.cases.map(c => c.case_id)));
  const engineOpts = engines.map(e => `<option value="${esc(e.engine)}" ${e.available ? "" : "disabled"}>${esc(e.engine)}${e.available ? "" : "(待接入)"}</option>`).join("");

  const groupEditor = (key, label, items) => `
    <div class="planbox"><b>${label}</b>(${items.length}/2)
      <table class="grid">${items.map((it, i) => `<tr><td>${esc(it.entity)} <span class="mono cellnote">${esc(it.security)}</span></td><td class="mono">${esc(it.as_of)}</td><td><button class="btn btn-sm" data-rmplan="${key}|${i}">去掉</button></td></tr>`).join("") || "<tr><td class='cellnote'>从课程表点「填入」或手动添加</td></tr>"}</table>
      <div class="form-row" style="margin:6px 0 0">
        <div class="field"><input placeholder="公司" id="p-${key}-e" style="min-width:110px"></div>
        <div class="field"><input placeholder="代码" id="p-${key}-s" style="min-width:70px"></div>
        <div class="field"><input placeholder="as_of 如 2020-01-31" id="p-${key}-d" style="min-width:130px"></div>
        <button class="btn btn-sm" data-addplan="${key}">添加</button>
      </div>
    </div>`;

  let html = `
  <div class="card">
    <h2>自动优化控制</h2>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
      ${statusChip(paused ? "warning" : "good", paused ? "已暂停" : "运行中")}
      <button class="btn ${paused ? "btn-primary" : "btn-danger"}" id="btn-toggle">${paused ? "恢复自动优化" : "暂停自动优化"}</button>
      <span class="cellnote">${(status.running_jobs || []).length} 个任务在跑 · 开关写入 training-runs/control.json,训练会话每个案例前读取</span>
    </div>
  </div>

  <div class="card">
    <h2>轮次计划(一轮 4 只:2 训练 + 2 验证)</h2>
    <div class="card-sub">从下方课程表按 pair 填入,或手动编辑;保存后可一键启动整轮,也可以让 agent 自动安排下一轮。</div>
    <div class="form-row"><div class="field"><label>轮次 ID</label><input id="plan-id" value="${esc(nextRoundId(roundsData))}" style="min-width:120px"></div>
      <div class="field"><label>引擎</label><select id="plan-engine">${engineOpts}</select></div></div>
    <div class="planrow">${groupEditor("a", "A组 · 训练", plan.a)}${groupEditor("b", "B组 · 验证(未触碰)", plan.b)}</div>
    <div class="form-row" style="margin-top:10px">
      <button class="btn btn-primary" id="plan-save">保存计划</button>
      <button class="btn" id="plan-launch">启动整轮训练</button>
      <button class="btn" id="plan-agent">让 agent 安排下一轮</button>
      <span id="plan-msg" class="formmsg"></span>
    </div>
  </div>

  <div class="card"><h2>训练课程表(agent 预排任务)</h2>
    <div class="card-sub">来自 skill 内置课程:按阶段(wave)组织的 开发/留出 配对;灰色 = 已在某轮跑过。点「填入」把 pair 加进上面的计划(开发→A组,留出→B组)。</div>`;
  for (const wave of waves) {
    html += `<h3 class="wavehead">第 ${esc(wave.wave)} 阶段</h3><div class="pairgrid">`;
    for (const pair of wave.pairs) {
      html += `<div class="paircard"><div class="pairhead"><b>${esc(pair.pair_id)}</b><button class="btn btn-sm" data-fill='${esc(JSON.stringify(pair.cases.map(c => ({ entity: c.company, security: c.security, as_of: c.proposed_as_of, role: c.role }))))}'>填入计划</button></div>`;
      for (const c of pair.cases) {
        const used = usedKeys.has(c.case_key);
        html += `<div class="pcase ${used ? "pcase-used" : ""}">
          <b>${esc(c.company)}</b> <span class="mono cellnote">${esc(c.security)}</span> · <span class="mono cellnote">${esc(c.proposed_as_of)}</span>
          ${statusChip(c.role === "development" ? "accent" : c.role === "untouched_holdout" ? "warning" : "muted",
                        c.role === "development" ? "训练" : c.role === "untouched_holdout" ? "验证" : "回归(不入轮)")}${used ? " " + statusChip("muted", "已用过") : ""}
          <div class="cellnote">${esc(c.mechanism || "")}</div></div>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
  }
  html += `</div>

  <div class="card"><h2>轮次记录</h2>`;
  if (!roundsData.length) html += `<div class="empty">还没有轮次。</div>`;
  else {
    for (const r of roundsData) {
      const meta = r.round || {};
      const isLive = r.round_id === "live";
      const groupLine = g => (g || []).map(x => `${esc(x.entity || x.case_id)} <span class="mono cellnote">${esc(x.security || "")}@${esc((x.as_of || "").slice(0, 10))}</span>`).join(" · ");
      html += `<div class="roundrow"><div class="pairhead"><b>${esc(isLive ? "live(实时预测)" : r.round_id)}</b>
        <span>${isLive ? statusChip("accent", "实时区") : statusChip(meta.status === "pushed" ? "good" : meta.status === "abandoned" ? "serious" : "accent", meta.status || "无计划文件")}
        ${!isLive && meta.status === "planned" ? `<button class="btn btn-sm" data-loadplan="${esc(r.round_id)}">载入编辑</button><button class="btn btn-sm btn-primary" data-launchround="${esc(r.round_id)}">启动</button>` : ""}
        ${!isLive ? `<button class="btn btn-sm btn-danger" data-delround="${esc(r.round_id)}">删除</button>` : ""}</span></div>
        ${meta.group_a ? `<div class="cellnote">A组·训练:${groupLine(meta.group_a)}</div>` : ""}
        ${meta.group_b ? `<div class="cellnote">B组·验证:${groupLine(meta.group_b)}</div>` : ""}
        ${meta.notes ? `<div class="cellnote">${esc(meta.notes)}</div>` : ""}`;
      if (r.cases.length) {
        html += `<table class="grid"><tbody>` + r.cases.map(c => `<tr><td>${esc(c.entity || c.case_id)}</td><td class="mono">${esc((c.as_of || "").slice(0, 10))}</td><td>${esc(c.case_role || "—")}</td>
          <td>${c.sealed ? statusChip("good", "已封存") : statusChip("muted", "未封存")}</td>
          <td>${c.metrics ? `MAPE ${pct(c.metrics.revenue_mape)}` : "—"}</td>
          <td><button class="btn btn-sm btn-danger" data-delcase2="${esc(c.round_id)}|${esc(c.case_id)}">删除</button></td></tr>`).join("") + `</tbody></table>`;
      } else html += `<div class="cellnote">计划中,尚无案例工件。</div>`;
      html += `</div>`;
    }
  }
  html += `</div>

  <div class="card"><h2>任务</h2>`;
  if (!jobsList.length) html += `<div class="empty">还没有任务记录。</div>`;
  else {
    html += `<table class="grid"><thead><tr><th>任务</th><th>类型</th><th>引擎</th><th>状态</th><th>开始</th><th></th></tr></thead><tbody>`;
    for (const j of jobsList) {
      const running = ["running", "running_detached"].includes(j.status);
      html += `<tr><td class="mono">${esc(j.id)}</td><td>${esc(j.type)}</td><td>${esc(j.engine)}</td><td>${jobChip(j.status)}</td>
        <td class="mono cellnote">${fmtTime(j.started_at)}</td>
        <td><button class="btn btn-sm" data-log="${esc(j.id)}">日志</button>
        ${running ? `<button class="btn btn-sm btn-danger" data-stop="${esc(j.id)}">停止</button>` : `<button class="btn btn-sm" data-deljob="${esc(j.id)}">删记录</button>`}</td></tr>`;
    }
    html += `</tbody></table>`;
  }
  html += `<div id="logbox" style="display:none;margin-top:12px"><div class="card-sub" id="logtitle"></div><pre class="log" id="logpre"></pre></div></div>`;

  $view.innerHTML = html;
  bindTraining(paused);
}

function bindTraining(paused) {
  const msg = document.getElementById("plan-msg");
  document.getElementById("btn-toggle").onclick = async () => {
    await post("/api/control", { auto_training: paused ? "run" : "pause", note: "dashboard 手动切换" });
    refreshHeader(); viewTraining();
  };
  $view.querySelectorAll("[data-fill]").forEach(b => b.onclick = () => {
    for (const c of JSON.parse(b.dataset.fill)) {
      const target = c.role === "development" ? plan.a : c.role === "untouched_holdout" ? plan.b : null;
      if (!target) continue;               // locked_regression etc. never enter a round plan
      if (target.length >= 2) continue;    // 2+2 shape is fixed
      if (!target.some(x => x.security === c.security && x.as_of === c.as_of)) target.push({ entity: c.entity, security: c.security, as_of: c.as_of });
    }
    viewTraining();
  });
  $view.querySelectorAll("[data-rmplan]").forEach(b => b.onclick = () => {
    const [key, i] = b.dataset.rmplan.split("|"); plan[key].splice(+i, 1); viewTraining();
  });
  $view.querySelectorAll("[data-addplan]").forEach(b => b.onclick = () => {
    const key = b.dataset.addplan;
    const entity = document.getElementById(`p-${key}-e`).value.trim();
    const security = document.getElementById(`p-${key}-s`).value.trim();
    const as_of = document.getElementById(`p-${key}-d`).value.trim();
    if (!entity || !as_of) { msg.textContent = "公司和 as_of 必填"; return; }
    if (plan[key].length >= 2) { msg.textContent = "每组固定 2 只(2+2)"; return; }
    plan[key].push({ entity, security: security || entity, as_of }); viewTraining();
  });
  document.getElementById("plan-save").onclick = async () => {
    if (plan.a.length !== 2 || plan.b.length !== 2) { msg.textContent = `一轮固定 4 只:训练 2 + 验证 2(当前 ${plan.a.length}+${plan.b.length})`; return; }
    try {
      await post("/api/rounds", { round_id: document.getElementById("plan-id").value.trim(), group_a: plan.a, group_b: plan.b, notes: "dashboard 计划" });
      msg.textContent = "计划已保存"; viewTraining();
    } catch (e) { msg.textContent = e.message; }
  };
  document.getElementById("plan-launch").onclick = async () => {
    const rid = document.getElementById("plan-id").value.trim();
    if (!confirm(`启动整轮训练 ${rid}?agent 会依次跑 A组训练→B组验证→按结果换组或发布,耗时数小时。`)) return;
    try {
      if (plan.a.length && plan.b.length) await post("/api/rounds", { round_id: rid, group_a: plan.a, group_b: plan.b, notes: "dashboard 计划" });
      const rec = await post("/api/jobs", { type: "training_round", engine: document.getElementById("plan-engine").value, params: { round_id: rid } });
      msg.textContent = `整轮任务已启动 ${rec.id}`; viewTraining();
    } catch (e) { msg.textContent = e.message; }
  };
  document.getElementById("plan-agent").onclick = async () => {
    try {
      const rec = await post("/api/jobs", { type: "plan_round", engine: document.getElementById("plan-engine").value, params: {} });
      msg.textContent = `已让 agent 规划下一轮(任务 ${rec.id},完成后轮次记录里会出现新计划)`; viewTraining();
    } catch (e) { msg.textContent = e.message; }
  };
  const guarded = fn => async (...args) => { try { await fn(...args); } catch (e) { alert("操作失败:" + e.message); } finally { detailCache.clear(); viewTraining(); } };
  $view.querySelectorAll("[data-loadplan]").forEach(b => b.onclick = guarded(async () => {
    const rounds = await api("/api/rounds");
    const meta = (rounds.find(r => r.round_id === b.dataset.loadplan) || {}).round || {};
    plan.a = (meta.group_a || []).map(x => ({ entity: x.entity, security: x.security, as_of: x.as_of }));
    plan.b = (meta.group_b || []).map(x => ({ entity: x.entity, security: x.security, as_of: x.as_of }));
    setTimeout(() => { const el = document.getElementById("plan-id"); if (el) el.value = b.dataset.loadplan; }, 60);
  }));
  $view.querySelectorAll("[data-launchround]").forEach(b => b.onclick = guarded(async () => {
    if (!confirm(`启动整轮训练 ${b.dataset.launchround}?耗时数小时。`)) return;
    await post("/api/jobs", { type: "training_round", engine: document.getElementById("plan-engine").value, params: { round_id: b.dataset.launchround } });
  }));
  $view.querySelectorAll("[data-delround]").forEach(b => b.onclick = guarded(async () => {
    if (!confirm(`删除整轮 ${b.dataset.delround}(连同其案例移入回收站)?`)) return;
    await del(`/api/rounds/${encodeURIComponent(b.dataset.delround)}`);
  }));
  $view.querySelectorAll("[data-delcase2]").forEach(b => b.onclick = guarded(async () => {
    const [r, c] = b.dataset.delcase2.split("|");
    if (!confirm(`删除案例 ${c}(移入回收站)?`)) return;
    await del(`/api/cases/${encodeURIComponent(r)}/${encodeURIComponent(c)}`);
  }));
  $view.querySelectorAll("[data-stop]").forEach(b => b.onclick = guarded(async () => {
    if (!confirm(`停止任务 ${b.dataset.stop}?运行中的研究会被终止。`)) return;
    await api(`/api/jobs/${b.dataset.stop}/stop`, { method: "POST" });
  }));
  $view.querySelectorAll("[data-deljob]").forEach(b => b.onclick = guarded(async () => {
    if (!confirm("删除该任务记录和日志?(移入 jobs/_trash)")) return;
    await del(`/api/jobs/${b.dataset.deljob}`);
  }));
  $view.querySelectorAll("[data-log]").forEach(b => b.onclick = () => {
    const id = b.dataset.log;
    document.getElementById("logbox").style.display = "";
    document.getElementById("logtitle").textContent = "任务日志 " + id + "(每 3 秒刷新)";
    const load = async () => { try { document.getElementById("logpre").textContent = await api(`/api/jobs/${id}/log?tail=300`); } catch (e) {} };
    clearInterval(logTimer); load(); logTimer = setInterval(load, 3000);
  });
}

/* ================= 方法 ================= */
const LOOP_SVG = `
<svg viewBox="0 0 1080 300" width="100%" style="min-width:900px" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="自训练闭环流程图">
  <defs><marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#52514e"/></marker></defs>
  <style>.box{fill:#fcfcfb;stroke:#c3c2b7}.bt{font:600 13px system-ui;fill:#0b0b0b}.bs{font:11.5px system-ui;fill:#52514e}.edge{stroke:#52514e;stroke-width:1.6;fill:none;marker-end:url(#arr)}.lbl{font:11.5px system-ui;fill:#52514e}</style>
  <rect class="box" x="10" y="40" width="150" height="58" rx="8"/><text class="bt" x="85" y="64" text-anchor="middle">选公司组(2+2)</text><text class="bs" x="85" y="82" text-anchor="middle">2只训练 + 2只验证</text>
  <rect class="box" x="200" y="40" width="150" height="58" rx="8"/><text class="bt" x="275" y="64" text-anchor="middle">时间沙盒研究</text><text class="bs" x="275" y="82" text-anchor="middle">只用 ≤ as_of 的资料</text>
  <rect class="box" x="390" y="40" width="115" height="58" rx="8"/><text class="bt" x="447" y="64" text-anchor="middle">封存预测</text><text class="bs" x="447" y="82" text-anchor="middle">哈希定格</text>
  <rect class="box" x="545" y="40" width="130" height="58" rx="8"/><text class="bt" x="610" y="64" text-anchor="middle">揭真值·打分</text><text class="bs" x="610" y="82" text-anchor="middle">封存之后才允许</text>
  <rect class="box" x="715" y="40" width="150" height="58" rx="8"/><text class="bt" x="790" y="64" text-anchor="middle">机制级误差归因</text><text class="bs" x="790" y="82" text-anchor="middle">改规则,不调数字</text>
  <rect class="box" x="905" y="40" width="150" height="58" rx="8"/><text class="bt" x="980" y="64" text-anchor="middle">2只验证股复核</text><text class="bs" x="980" y="82" text-anchor="middle">没大问题 → 发布</text>
  <line class="edge" x1="160" y1="69" x2="196" y2="69"/><line class="edge" x1="350" y1="69" x2="386" y2="69"/>
  <line class="edge" x1="505" y1="69" x2="541" y2="69"/><line class="edge" x1="675" y1="69" x2="711" y2="69"/>
  <line class="edge" x1="865" y1="69" x2="901" y2="69"/>
  <rect class="box" x="290" y="200" width="210" height="58" rx="8"/><text class="bt" x="395" y="224" text-anchor="middle">换组交叉(左脚踩右脚)</text><text class="bs" x="395" y="242" text-anchor="middle">B转训练,A回验,比一致性</text>
  <rect class="box" x="560" y="200" width="190" height="58" rx="8"/><text class="bt" x="655" y="224" text-anchor="middle">git 发布 / 回退</text><text class="bs" x="655" y="242" text-anchor="middle">通过 push;失败 revert 换新组</text>
  <path class="edge" d="M 980 98 C 980 170 530 229 504 229"/><text class="lbl" x="775" y="150">验证不佳 ↓</text>
  <line class="edge" x1="500" y1="229" x2="556" y2="229"/>
  <path class="edge" d="M 655 200 C 655 130 120 130 88 102"/><text class="lbl" x="300" y="135">发布新方法版本,进入下一轮 ↺</text>
</svg>`;

async function viewMethod() {
  const [timeline, skills] = await Promise.all([api("/api/method/timeline"), api("/api/method/skills")]);
  let html = `
    <div class="card">
      <h2>自训练闭环</h2>
      <div class="idea-row">
        <div class="idea"><b>时间沙盒</b><span>历史训练只用截止日前公开的资料,模型记忆不算证据。</span></div>
        <div class="idea"><b>先封存,后见真值</b><span>预测在看真实结果前哈希封存,打分只对封存版本进行。</span></div>
        <div class="idea"><b>改机制,不调数字</b><span>误差归因到经济机制,修可泛化的规则,不是把 20% 改成 10%。</span></div>
        <div class="idea"><b>2+2 换组交叉</b><span>一轮 4 只:2 只训练、2 只未触碰验证;失败则两组互换再验,仍不一致就放弃换新组。</span></div>
      </div>
      <div class="loopwrap">${LOOP_SVG}</div>
    </div>
    <div class="card"><h2>两个技能的分工</h2><table class="grid"><tbody>` +
    skills.map(s => `<tr><td style="min-width:220px"><b class="mono">${esc(s.name)}</b></td><td>${esc(s.description)}</td></tr>`).join("") +
    `</tbody></table></div>
    <div class="card"><h2>方法演进时间线</h2>
      <div class="card-sub">方法版本 = git 提交。当前 <span class="mono">${esc(timeline.branch)}@${esc((timeline.head || "").slice(0, 7))}</span> · 远程 ${esc(timeline.remote || "—")}</div>
      <ul class="timeline">` + timeline.commits.map(c => `
      <li><div class="tl-head"><span class="tl-date">${esc((c.date || "").replace("T", " ").slice(0, 16))}</span>
        <span class="mono" style="color:var(--muted)">${esc(c.short)}</span>
        <span class="tl-subject">${esc(c.subject)}</span></div>
        ${c.body ? `<div class="tl-body">${esc(c.body)}</div>` : ""}</li>`).join("") + `</ul></div>`;
  $view.innerHTML = html;
}

/* ---------- router ---------- */
async function route() {
  clearInterval(logTimer);
  const hash = location.hash || "#/portfolio";
  const parts = hash.slice(2).split("/").map(decodeURIComponent);
  document.querySelectorAll(".tabs a").forEach(a => a.classList.toggle("active", a.dataset.tab === parts[0]));
  $view.innerHTML = `<div class="empty">加载中…</div>`;
  try {
    if (parts[0] === "training") await viewTraining();
    else if (parts[0] === "method") await viewMethod();
    else await viewPortfolio();
  } catch (e) {
    $view.innerHTML = `<div class="empty"><b>加载失败。</b><br><span class="mono">${esc(e.message)}</span></div>`;
  }
}

window.addEventListener("hashchange", route);
route();
refreshHeader();
setInterval(refreshHeader, 5000);
