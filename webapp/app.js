/* 科技公司预测系统 — 实战版前端(投资看板 + 自训练控制台) */
"use strict";

const $view = document.getElementById("view");
const api = (path, opts) => {
  opts = { cache: "no-store", ...(opts || {}) };   // 状态接口永远实时,绕过一切浏览器缓存
  if (opts.method && opts.method !== "GET") {
    opts.headers = { ...(opts.headers || {}), "X-Dashboard": "1" };
  }
  return fetch(path, opts).then(r => {
  if (!r.ok) return r.text().then(t => { let d = t; try { d = JSON.parse(t).detail || t; } catch {} throw new Error(`${r.status} ${String(d).slice(0, 300)}`); });
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
  });
};
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const del = path => api(path, { method: "DELETE" });
const apiHref = path => {
  const prefix = typeof globalThis.__FORECAST_API_PREFIX === "string"
    ? globalThis.__FORECAST_API_PREFIX.replace(/\/$/, "")
    : "";
  return prefix && path.startsWith("/api/") ? `${prefix}${path.slice(4)}` : path;
};

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
const JOB_TYPE_LABEL = { live_forecast: ["accent", "推理·实时预测"], training_case: ["warning", "训练·单案例"], training_round: ["warning", "训练·整轮"], plan_round: ["muted", "规划·排任务"], suggest_watch: ["muted", "助理·选股推荐"] };
const TRAINING_TYPES = new Set(["training_case", "training_round", "plan_round"]);
const jobTypeChip = t => statusChip(...(JOB_TYPE_LABEL[t] || ["muted", t]));
const jobTarget = j => { const p = j.params || {}; return p.security || p.entity || p.round_id || p.hint || (j.type === "suggest_watch" ? "推荐关注" : ""); };
const ACTION_BADGE = { buy: ["good", "买入"], hold: ["accent", "持有"], watch: ["muted", "观察"], avoid: ["critical", "回避"] };
const actionChip = a => a ? statusChip(...(ACTION_BADGE[String(a).toLowerCase()] || ["muted", a])) : statusChip("muted", "未评级");

/* ---------- metric label dictionary (raw snake_case never reaches the eye) ---------- */
const METRIC_LABELS = {
  revenue_yoy_pct: "营收增速", gross_margin_pct: "毛利率", non_gaap_gross_margin_pct: "非GAAP毛利率",
  operating_income_M: "经营利润", non_gaap_operating_income: "非GAAP经营利润", gaap_operating_income: "GAAP经营利润",
  operating_margin_pct: "经营利率", non_gaap_operating_margin_pct: "非GAAP经营利率", revenue_yoy_pct_base: "营收增速(基准)",
  non_gaap_operating_margin_pct_base: "非GAAP经营利率(基准)", net_income_M: "净利润", diluted_eps: "摊薄EPS",
  non_gaap_eps: "非GAAP EPS", gaap_eps: "GAAP EPS", non_gaap_eps_bear: "非GAAP EPS(悲观)", non_gaap_eps_base: "非GAAP EPS(基准)",
  non_gaap_eps_bull: "非GAAP EPS(乐观)", fcf: "自由现金流", fcf_M: "自由现金流", fcf_base: "自由现金流(基准)",
  fcf_margin_pct: "FCF利率", capex_M: "资本开支", capex: "资本开支", diluted_shares_M: "摊薄股数",
  data_center_revenue: "数据中心收入", comm_other_revenue: "通信及其他收入", data_center_pct: "数据中心占比",
  revenue_regime_break: "断裂尾收入", custom_silicon_revenue_base: "定制硅收入(基准)",
  custom_silicon_revenue_bear: "定制硅收入(悲观)", custom_silicon_revenue_bull: "定制硅收入(乐观)",
  normalized_value_low: "正常化价值(低)", normalized_value_high: "正常化价值(高)",
  implied_fy28_revenue_minimum: "隐含FY28收入下限", implied_fy28_growth_minimum_pct: "隐含FY28增速下限",
  implied_terminal_fcf_at_25x: "25x隐含终值FCF", ev_revenue_fy27: "EV/FY27收入", current_price: "现价",
};
const metricLabel = k => METRIC_LABELS[k] || k.replace(/_M$|_pct$/g, "").replace(/_/g, " ");
const metricValue = (k, v) => {
  if (typeof v !== "number") return esc(v);
  if (/_pct($|_)/.test(k) || /pct$/.test(k)) return v.toFixed(1) + "%";
  if (/eps/.test(k) || k === "current_price") return "$" + v.toFixed(2);
  return v.toLocaleString("en-US");
};

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
    document.getElementById("chip-method").innerHTML = `方法 <span class="mono">${esc(timeline.branch || "?")}@${esc((timeline.head || "").slice(0, 7))}</span>`;
    const refresh = document.getElementById("chip-refresh");
    if (status.bridge && status.bridge.online === false) {
      refresh.innerHTML = statusChip("critical", "同步桥离线");
    } else if (status.bridge?.online) {
      refresh.textContent = "同步于 " + fmtTime(status.generated_at || status.bridge.last_seen_at || status.bridge.heartbeat_at);
    } else {
      refresh.textContent = "刷新于 " + new Date().toLocaleTimeString("zh-CN", { hour12: false });
    }
  } catch { document.getElementById("chip-refresh").textContent = "后端不可达"; }
}

/* ================= 投资看板 ================= */
const expanded = new Set();          // securities whose detail panel is open
const detailCache = new Map();       // case detail cache
let quotesCache = {};                // live quotes, merged in after first paint
let pfRows = [];                     // last /api/portfolio payload
let pfSort = "upside";               // upside | rating | dist
let pfFilter = "all";                // all | buy | hold | watch | avoid
let sugData = null;                  // /api/watch-suggestions payload
let sugTimer = null;                 // poll timer while a suggestion job runs
const DEFAULT_ENGINE_SPECS = [
  { engine: "claude", available: true, note: "", models: [] },
  { engine: "codex", available: true, note: "", models: [] },
];
const visibleEngines = list => {
  const source = Array.isArray(list) ? list : [];
  const policy = Array.isArray(globalThis.__FORECAST_ENGINE_POLICY)
    ? new Set(globalThis.__FORECAST_ENGINE_POLICY)
    : null;
  return policy ? source.filter(item => policy.has(item.engine)) : source;
};
let engineList = [];                 // /api/engines payload
let pfEngine = (() => {
  try { return JSON.parse(localStorage.getItem("enginePrefs") || "{}").last || "claude"; }
  catch { return "claude"; }
})();
if (!visibleEngines(DEFAULT_ENGINE_SPECS).some(item => item.engine === pfEngine)) {
  pfEngine = (visibleEngines(DEFAULT_ENGINE_SPECS)[0] || {}).engine || "codex";
}

/* ---------- 引擎选择:发起动作时弹两步菜单(引擎 → 型号+强度) ---------- */
const ENGINE_BLURB = {
  claude: "Claude Code · 本仓库方法树",
  codex: "Codex CLI · 项目同源方法树",
};
let _engMenuClose = null;

function engPrefs() {
  try { return JSON.parse(localStorage.getItem("enginePrefs") || "{}"); } catch { return {}; }
}
function saveEngPref(engine, model, effort) {
  const p = engPrefs();
  p.last = engine;
  p[engine] = { model, effort };
  localStorage.setItem("enginePrefs", JSON.stringify(p));
  pfEngine = engine;
}

function closeEngineMenu() {
  const box = document.getElementById("engine-menu");
  if (box) box.remove();
  if (_engMenuClose) { document.removeEventListener("mousedown", _engMenuClose, true); document.removeEventListener("keydown", _engMenuClose, true); _engMenuClose = null; }
}

function openEngineMenu(anchor, title, onPick) {
  closeEngineMenu();
  const list = visibleEngines(engineList.length ? engineList : DEFAULT_ENGINE_SPECS);
  const prefs = engPrefs();
  const box = document.createElement("div");
  box.id = "engine-menu";
  box.className = "engmenu";
  document.body.appendChild(box);

  const place = () => {
    const r = anchor.getBoundingClientRect();
    box.style.left = Math.max(8, Math.min(r.right - box.offsetWidth, window.innerWidth - box.offsetWidth - 8)) + "px";
    box.style.top = (r.bottom + 6 + box.offsetHeight > window.innerHeight ? Math.max(8, r.top - box.offsetHeight - 6) : r.bottom + 6) + "px";
  };

  const stepEngine = () => {
    box.innerHTML = `<div class="engmenu-h">${esc(title)}</div>` + list.map(e => `
      <button class="engmenu-i" data-pick="${esc(e.engine)}" ${e.available ? "" : "disabled"}>
        <span class="engmenu-n">${esc(e.engine)}${e.engine === (prefs.last || pfEngine) && e.available ? `<span class="engmenu-tag">上次</span>` : ""}</span>
        <span class="engmenu-d">${esc(e.available ? (ENGINE_BLURB[e.engine] || "") : (e.note || "未接入"))}</span>
      </button>`).join("");
    box.querySelectorAll("[data-pick]").forEach(b => b.onclick = ev => { ev.stopPropagation(); stepModel(b.dataset.pick); });
    place();
  };

  const stepModel = engineName => {
    const spec = list.find(e => e.engine === engineName) || {};
    const models = spec.models || [];
    const saved = prefs[engineName] || {};
    let model = models.some(m => m.id === saved.model) ? saved.model : (spec.default_model || (models[0] || {}).id || "");
    const effortOf = mid => {
      const m = models.find(x => x.id === mid) || {};
      const efforts = m.efforts || [];
      const want = saved.model === mid && saved.effort ? saved.effort : (m.default_effort || "");
      return efforts.includes(want) ? want : (m.default_effort || efforts[0] || "");
    };
    let effort = effortOf(model);
    const render = () => {
      const m = models.find(x => x.id === model) || {};
      box.innerHTML = `
        <div class="engmenu-h"><button class="engmenu-back" data-back>‹</button>${esc(title)} · <b>${esc(engineName)}</b></div>
        ${models.length ? `<div class="engmenu-sec">型号</div>` + models.map(x => `
          <button class="engmenu-i engmenu-model ${x.id === model ? "sel" : ""}" data-model="${esc(x.id)}">
            <span class="engmenu-n">${esc(x.id)}${x.id === (spec.default_model || "") ? `<span class="engmenu-tag">默认</span>` : ""}</span>
            <span class="engmenu-d">${esc(x.label || "")}</span>
          </button>`).join("") : `<div class="engmenu-d" style="padding:6px 9px">该引擎未登记型号,用其默认配置。</div>`}
        ${(m.efforts || []).length ? `<div class="engmenu-sec">推理强度</div>
          <div class="engmenu-efforts">${m.efforts.map(e => `<button class="tbtn ${e === effort ? "active" : ""}" data-effort="${esc(e)}">${esc(e)}</button>`).join("")}</div>` : ""}
        <div class="engmenu-foot"><button class="btn btn-primary btn-sm" data-go>启动</button></div>`;
      box.querySelector("[data-back]").onclick = ev => { ev.stopPropagation(); stepEngine(); };
      box.querySelectorAll("[data-model]").forEach(b => b.onclick = ev => { ev.stopPropagation(); model = b.dataset.model; effort = effortOf(model); render(); });
      box.querySelectorAll("[data-effort]").forEach(b => b.onclick = ev => { ev.stopPropagation(); effort = b.dataset.effort; render(); });
      box.querySelector("[data-go]").onclick = ev => {
        ev.stopPropagation();
        saveEngPref(engineName, model, effort);
        closeEngineMenu();
        onPick(engineName, model, effort);
      };
      place();
    };
    render();
  };

  stepEngine();
  _engMenuClose = ev => {
    if (ev.type === "keydown" && ev.key !== "Escape") return;
    if (ev.type === "mousedown" && (box.contains(ev.target) || anchor.contains(ev.target))) return;
    closeEngineMenu();
  };
  setTimeout(() => { document.addEventListener("mousedown", _engMenuClose, true); document.addEventListener("keydown", _engMenuClose, true); }, 0);
}

const RATE_META = {
  buy:   { label: "买入", color: "var(--gain)",     bg: "rgba(11,122,67,.10)" },
  hold:  { label: "持有", color: "var(--accent)",   bg: "rgba(37,99,201,.10)" },
  watch: { label: "观察", color: "var(--gold)",     bg: "rgba(181,130,42,.12)" },
  avoid: { label: "回避", color: "var(--critical)", bg: "rgba(197,55,47,.10)" },
};
const rateMeta = a => RATE_META[String(a || "").toLowerCase()] || { label: "未评级", color: "var(--baseline)", bg: "#f0f0ec" };
const RATE_RANK = { buy: 0, hold: 1, watch: 2, avoid: 3 };

function enrichRow(r) {
  const v = r.valuation || {};
  const q = quotesCache[r.security] || {};
  const price = q.price ?? v.current_price ?? null;
  const live = q.price != null;
  const fv = v.fair_value || {};
  const base = fv.base ?? null, bear = fv.bear ?? null, bull = fv.bull ?? null;
  const buy = v.recommended_buy_price ?? null;
  const u = price && base != null ? base / price - 1 : null;
  const d = price && buy ? price / buy - 1 : null;
  let distKey = null, distLabel = "";
  if (d != null) {
    if (d <= 0) { distKey = "at"; distLabel = "已到买入价"; }
    else if (d <= 0.05) { distKey = "near"; distLabel = "接近买点 +" + (d * 100).toFixed(1) + "%"; }
    else { distKey = "above"; distLabel = "高于买点 +" + (d * 100).toFixed(1) + "%"; }
  }
  return { r, v, price, live, base, bear, bull, buy, u, d, distKey, distLabel, action: String(v.action || "").toLowerCase() };
}

function valbarHtml(e) {
  if (e.price == null || e.base == null || e.bear == null || e.bull == null) return "";
  const lo = Math.min(e.bear, e.buy ?? e.bear, e.price), hi = Math.max(e.bull, e.price);
  const pad = (hi - lo) * 0.08 || 1, dmin = lo - pad, span = hi + pad - dmin;
  const P = x => ((x - dmin) / span) * 100;
  const L = x => Math.max(4, Math.min(96, x));   // 标签钳制,避免溢出条外
  const up = e.u != null && e.u >= 0;
  const pB = P(e.base), pP = P(e.price);
  return `<div class="valwrap"><div class="valbar">
      <div class="vb-price" style="left:${L(pP).toFixed(2)}%">现 ${money(e.price)}</div>
      <div class="vb-track"></div>
      <div class="vb-range" style="left:${P(e.bear).toFixed(2)}%;width:${(P(e.bull) - P(e.bear)).toFixed(2)}%"></div>
      <div class="vb-conn ${up ? "vb-up" : "vb-down"}" style="left:${Math.min(pB, pP).toFixed(2)}%;width:${Math.abs(pB - pP).toFixed(2)}%"></div>
      <div class="vb-base" style="left:${pB.toFixed(2)}%"></div>
      <div class="vb-now" style="left:${pP.toFixed(2)}%"></div>
      ${e.buy != null ? `<div class="vb-buy" style="left:${L(P(e.buy)).toFixed(2)}%">▲ 买 ${money(e.buy)}</div>` : ""}
    </div>
    <div class="vb-scale"><span class="vb-lo">悲观 ${money(e.bear)}</span><span class="vb-basetxt" style="left:${L(pB).toFixed(2)}%">基准 ${money(e.base)}</span><span class="vb-hi">乐观 ${money(e.bull)}</span></div></div>`;
}

function summaryHtml(es) {
  const ups = es.filter(e => e.u != null);
  const avgU = ups.length ? ups.reduce((s, e) => s + e.u, 0) / ups.length : null;
  const atBuy = es.filter(e => e.distKey === "at").length;
  const withD = es.filter(e => e.d != null).sort((a, b) => a.d - b.d);
  const closest = withD[0];
  const counts = {};
  es.forEach(e => { const k = RATE_META[e.action] ? e.action : "none"; counts[k] = (counts[k] || 0) + 1; });
  const distDefs = [["buy", "买入", "var(--gain)"], ["hold", "持有", "var(--accent)"], ["watch", "观察", "var(--gold)"], ["avoid", "回避", "var(--critical)"], ["none", "未评级", "var(--baseline)"]];
  const dist = distDefs.filter(([k]) => counts[k]);
  const attn = es.filter(e => e.distKey === "at" || e.distKey === "near" || e.action === "buy" || (e.u != null && e.u <= -0.15));
  const attnRow = e => `<div class="attn-row"><b>${esc(e.r.security)}</b><span class="attn-metric" style="color:${e.u != null && e.u >= 0 ? "var(--gain)" : "var(--loss)"}">${e.u == null ? "—" : (e.u >= 0 ? "+" : "") + (e.u * 100).toFixed(1) + "%"}</span><span class="cellnote">${e.distKey === "at" ? "已到买点" : e.distKey === "near" ? "接近买点" : e.action === "buy" ? "评级买入" : "现价高于基准"}</span></div>`;
  return `<div class="sumrow">
    <div class="sumcell"><div class="s-label">关注公司</div><div class="s-value">${es.length}</div></div>
    <div class="sumcell"><div class="s-label">平均上涨空间</div><div class="s-value" style="color:${avgU == null ? "inherit" : avgU >= 0 ? "var(--gain)" : "var(--loss)"}">${avgU == null ? "—" : (avgU >= 0 ? "+" : "") + (avgU * 100).toFixed(1) + "%"}</div></div>
    <div class="sumcell"><div class="s-label">已到买入价</div><div class="s-inline"><span class="s-value">${atBuy}</span>${closest ? `<span class="cellnote">最接近 <b style="color:var(--ink)">${esc(closest.r.security)} ${closest.distKey === "at" ? "已到价" : "+" + (closest.d * 100).toFixed(1) + "%"}</b></span>` : ""}</div></div>
    <div class="sumcell"><div class="s-label">评级分布</div>
      <div class="distbar">${dist.map(([k, , c]) => `<div class="distseg" style="flex:${counts[k]};background:${c}"></div>`).join("")}</div>
      <div class="distlegend">${dist.map(([k, l, c]) => `<span class="status"><span class="dot" style="background:${c}"></span>${l} ${counts[k]}</span>`).join("")}</div></div>
    <div class="sumcell"><div class="s-label">需关注 · ${attn.length}</div>${attn.length ? attn.slice(0, 3).map(attnRow).join("") : `<div class="cellnote">暂无到价/超估标的</div>`}</div>
  </div>`;
}

async function viewPortfolio() {
  pfRows = await api("/api/portfolio");
  paintPortfolio();
  api("/api/engines").then(e => {
    engineList = visibleEngines(e);
    paintPortfolio();
  }).catch(() => {});
  api("/api/watch-suggestions").then(s => { sugData = s; paintPortfolio(); }).catch(() => {});
  const symbols = pfRows.map(r => r.security).filter(Boolean);
  if (symbols.length) {
    api("/api/quotes?symbols=" + encodeURIComponent(symbols.join(","))).then(q => {
      quotesCache = { ...quotesCache, ...q };
      if ((location.hash || "#/portfolio").includes("portfolio")) paintPortfolio();
    }).catch(() => {});
  }
}

function paintPortfolio() {
  const rows = pfRows;
  const keep = id => { const el = document.getElementById(id); return el ? el.value : ""; };
  const saved = { e: keep("w-entity"), s: keep("w-sec"), n: keep("w-note"), h: keep("sug-hint") };
  const es = rows.map(enrichRow);

  let html = "";
  if (rows.length) html += summaryHtml(es);

  html += `<div class="card">
    <div class="form-row" style="margin-bottom:0">
      <div class="field acwrap"><label>公司名(输入 2 个字母自动补全)</label><input id="w-entity" placeholder="lam → Lam Research" autocomplete="off"><div class="acbox" id="ac-box" style="display:none"></div></div>
      <div class="field"><label>代码</label><input id="w-sec" placeholder="MU" style="min-width:90px"></div>
      <div class="field"><label>备注(可选)</label><input id="w-note" placeholder="存储周期"></div>
      <button class="btn btn-primary" id="w-add">加入关注</button>
      <span id="w-msg" class="formmsg"></span>
    </div>
  </div>`;
  html += suggestCardHtml();

  if (!rows.length) {
    html += `<div class="empty"><b>关注列表为空。</b><br>先把要研究的公司加进来,然后点「跑预测」——完成后这里会出现当前股价、AI 目标价和建议买入价。</div>`;
    $view.innerHTML = html; bindPortfolio(); return;
  }

  const sortDefs = [["upside", "空间"], ["rating", "评级"], ["dist", "到价距离"]];
  const present = [...new Set(es.map(e => e.action).filter(a => RATE_META[a]))];
  const filterDefs = [["all", "全部"], ...present.map(a => [a, RATE_META[a].label])];
  if (pfFilter !== "all" && !present.includes(pfFilter)) pfFilter = "all";
  let visible = es.filter(e => pfFilter === "all" || e.action === pfFilter);
  visible = visible.slice().sort((a, b) =>
    pfSort === "rating" ? (RATE_RANK[a.action] ?? 9) - (RATE_RANK[b.action] ?? 9)
    : pfSort === "dist" ? (a.d ?? 9e9) - (b.d ?? 9e9)
    : (b.u ?? -9e9) - (a.u ?? -9e9));

  html += `<div class="toolbar">
    <div class="tgroup"><span class="tlabel">排序</span>${sortDefs.map(([k, l]) => `<button class="tbtn ${pfSort === k ? "active" : ""}" data-sort="${k}">${l}</button>`).join("")}</div>
    <div class="tsep"></div>
    <div class="tgroup"><span class="tlabel">筛选</span>${filterDefs.map(([k, l]) => `<button class="tbtn ${pfFilter === k ? "active" : ""}" data-filter="${k}">${l}</button>`).join("")}</div>
    <div class="tspacer"></div>
    <span class="cellnote">${es.some(e => e.live) ? "实时价 · Yahoo" : "价格为研究时点,实时价加载中…"}</span>
  </div>`;

  for (const e of visible) {
    const r = e.r, rm = rateMeta(e.action);
    const latest = r.latest_live || r.latest;
    const isOpen = expanded.has(r.security);
    html += `<div class="pcard" data-sec="${esc(r.security)}">
      <div class="pchead" data-toggle="${esc(r.security)}">
        <div><div class="pc-name"><b>${esc(r.entity)}</b><span class="sec">${esc(r.security)}</span>${r.job_running ? statusChip("accent", "推理中") : ""}</div>
          <div class="pc-sub">${r.note ? esc(r.note) + " · " : ""}${latest ? "预测 " + fmtDate(latest.last_activity) + (latest.method_commit ? " · 方法 " + esc(String(latest.method_commit).slice(0, 7)) : "") : "未跑过"}</div></div>
        <div><div class="pc-price">${e.price != null ? money(e.price) : "—"}${e.live ? ` <span class="cellnote">实时</span>` : e.price != null ? ` <span class="cellnote">${esc((e.v.price_as_of || "").slice(0, 10) || "研究时点")}</span>` : ""}</div>
          ${e.distKey ? `<div class="pc-dist ${e.distKey}">${esc(e.distLabel)}</div>` : ""}</div>
        <div class="pc-rating"><span class="ratepill" style="background:${rm.bg};color:${rm.color}"><span class="dot" style="background:${rm.color}"></span>${rm.label}</span></div>
        <div class="pc-up"><span class="v" style="color:${e.u == null ? "var(--muted)" : e.u >= 0 ? "var(--gain)" : "var(--loss)"}">${e.u == null ? "—" : (e.u >= 0 ? "+" : "") + (e.u * 100).toFixed(1) + "%"}</span><div class="l">上涨空间</div></div>
        <div class="pc-target"><span class="v">${money(e.base)}</span><div class="l">目标价</div></div>
        <div class="pc-act">${r.job_running
          ? `<button class="btn btn-sm" data-viewlog="${esc(r.job_id || "")}">日志</button> <button class="btn btn-sm btn-danger" data-canceljob="${esc(r.job_id || "")}" data-sec="${esc(r.security)}">取消</button>`
          : `<button class="btn btn-sm" data-run="${esc(r.security)}" data-entity="${esc(r.entity)}">跑预测</button>`}
          <button class="btn btn-sm" data-versions="${esc(r.security)}" data-entity="${esc(r.entity)}" title="版本管理:选择看板显示哪一版 / 删除坏版本">版本</button>
          <button class="btn btn-sm btn-danger" data-unwatch="${esc(r.security)}" title="移出关注列表(历史版本保留在数据库)">移除</button></div>
        <div class="chev ${isOpen ? "open" : ""}">›</div>
      </div>
      ${valbarHtml(e)}
      ${isOpen ? `<div class="pcbody"><div class="dwrap" id="d-${esc(r.security)}">加载中…</div></div>` : ""}
    </div>`;
  }
  html += `<div class="notice">折叠看结论 · 展开看理由(论点、预测输出、情景概率、机制权重、运行记录、版本对比、完整报告)。估值区间条:黑标 = 现价,蓝标 = AI 目标价(基准情景),金标 = 建议买入价,蓝底 = 悲观↔乐观区间。实时价源自 Yahoo,取不到时回退研究时点价格。</div>`;
  $view.innerHTML = html;
  if (saved.e || saved.s || saved.n) { document.getElementById("w-entity").value = saved.e; document.getElementById("w-sec").value = saved.s; document.getElementById("w-note").value = saved.n; }
  if (saved.h) { const el = document.getElementById("sug-hint"); if (el) el.value = saved.h; }
  closeEngineMenu();   // 重绘会换掉锚点节点,菜单不能留在旧位置
  bindPortfolio();
  for (const sec of expanded) renderDetail(sec, pfRows);
}

function suggestCardHtml() {
  const watched = new Set(pfRows.map(r => String(r.security || "").toUpperCase()));
  const s = sugData || {};
  const list = s.suggestions || [];
  const rows = list.map((it, i) => {
    const sec = String(it.security || "").toUpperCase();
    return `<div class="sugrow"><b>${esc(it.entity || "")}</b><span class="mono cellnote">${esc(sec)}</span>
      <span class="cellnote" style="flex:1">${esc(it.note || "")}</span>
      ${watched.has(sec) ? statusChip("good", "已在关注") : `<button class="btn btn-sm" data-sugadd="${i}">加入关注</button>`}</div>`;
  }).join("");
  return `<div class="card"><h2>AI 推荐关注</h2>
    <div class="card-sub">让 agent 结合方法机制覆盖面和当前关注列表推荐候选,你来挑。可给方向提示,如「光模块」「存储上游」。</div>
    <div class="form-row" style="margin-bottom:${list.length ? "10px" : "0"}">
      <div class="field"><label>方向提示(可选)</label><input id="sug-hint" placeholder="留空 = 自动按机制覆盖推荐"></div>
      <button class="btn" id="sug-run" ${sugTimer ? "disabled" : ""}>${sugTimer ? "生成中…" : "让 AI 推荐一批"}</button>
      ${list.length ? `<button class="btn btn-sm" id="sug-clear">清空</button>` : ""}
      <span id="sug-msg" class="formmsg">${sugTimer ? "生成中,约 1~3 分钟,完成后自动出现" : ""}</span>
    </div>
    ${rows}
    ${s.generated_at ? `<div class="cellnote" style="margin-top:8px">生成于 ${fmtTime(s.generated_at)}${s.hint ? " · 提示:" + esc(s.hint) : ""}</div>` : ""}
  </div>`;
}

/* ---------- 通用右侧抽屉(日志 / 版本管理 共用) ---------- */
let drawerTimer = null;

function closeDrawer() {
  clearInterval(drawerTimer); drawerTimer = null;
  ["drawer-ov", "drawer"].forEach(id => { const el = document.getElementById(id); if (el) el.remove(); });
}

function openDrawer(titleHtml, bodyHtml) {
  closeDrawer();
  const ov = document.createElement("div"); ov.id = "drawer-ov"; ov.className = "drawer-ov";
  const dr = document.createElement("div"); dr.id = "drawer"; dr.className = "drawer";
  dr.innerHTML = `<div class="drawer-h"><div class="drawer-t">${titleHtml}</div><button class="btn btn-sm" id="drawer-x">关闭 Esc</button></div><div class="drawer-b">${bodyHtml}</div>`;
  document.body.append(ov, dr);
  requestAnimationFrame(() => { ov.classList.add("on"); dr.classList.add("on"); });
  ov.onclick = closeDrawer;
  dr.querySelector("#drawer-x").onclick = closeDrawer;
  const onEsc = ev => { if (ev.key === "Escape") { closeDrawer(); document.removeEventListener("keydown", onEsc); } };
  document.addEventListener("keydown", onEsc);
  return dr;
}

/* 日志抽屉:任何页面都能开,3 秒轮询,运行中可直接停止 */
function openLogDrawer(jobId) {
  if (!jobId) { alert("找不到任务 ID"); return; }
  openDrawer(`任务日志 · <span class="mono">${esc(jobId)}</span>`,
    `<div id="log-meta" class="cellnote" style="margin-bottom:8px">加载中…</div><pre class="log drawer-log" id="drawer-log"></pre>`);
  const load = async () => {
    try {
      const [rec, log] = await Promise.all([api(`/api/jobs/${jobId}`), api(`/api/jobs/${jobId}/log?tail=500`)]);
      const meta = document.getElementById("log-meta"), pre = document.getElementById("drawer-log");
      if (!meta || !pre) return;
      const isRunning = ["running", "running_detached"].includes(rec.status);
      meta.innerHTML = `${jobTypeChip(rec.type)} ${jobChip(rec.status)} <span class="mono">${esc(rec.engine)}${rec.params && rec.params.model ? " · " + esc(rec.params.model) : ""}${rec.params && rec.params.effort ? " · " + esc(rec.params.effort) : ""}</span> <span class="cellnote">${elapsed(rec.started_at, rec.ended_at)}</span> ${isRunning ? `<button class="btn btn-sm btn-danger" id="drawer-stop">停止任务</button>` : ""}`;
      const stick = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 40;
      pre.textContent = log || "(暂无日志)";
      if (stick) pre.scrollTop = pre.scrollHeight;
      const stop = document.getElementById("drawer-stop");
      if (stop) stop.onclick = async () => { if (!confirm("停止该任务?")) return; try { await api(`/api/jobs/${jobId}/stop`, { method: "POST" }); } catch {} load(); };
      if (!isRunning) { clearInterval(drawerTimer); drawerTimer = null; }
    } catch (e) {
      const meta = document.getElementById("log-meta"), pre = document.getElementById("drawer-log");
      if (meta) meta.textContent = "日志暂不可用";
      if (pre) pre.textContent = e && e.message ? e.message : "安全日志尚未同步";
    }
  };
  load();
  drawerTimer = setInterval(load, 3000);
}

/* 版本管理抽屉:单选 = 看板显示哪版;删除/恢复;固定后可恢复自动 */
function openVersionDrawer(sec, entity) {
  openDrawer(`${esc(entity || sec)} <span class="mono cellnote">${esc(sec)}</span> · 版本管理`, `<div id="ver-body">加载中…</div>`);
  const load = async () => {
    let hist = [];
    try { hist = await api(`/api/history/${encodeURIComponent(sec)}`); } catch {}
    const box = document.getElementById("ver-body");
    if (!box) return;
    if (!hist.length) { box.innerHTML = `<div class="empty">还没有入库版本——跑一次预测后这里会出现。</div>`; return; }
    const pinned = hist.find(h => h.is_active && !h.deleted);
    const effective = pinned || hist.find(h => h.has_valuation && !h.deleted) || null;
    box.innerHTML = `<div class="cellnote" style="margin-bottom:10px">选中的版本就是投资看板显示的结论。默认自动跟随最新有估值版本;手动选中后固定不动。删除是软删除,可恢复;数据在 backend/state/forecast.db,工作区被覆盖也不丢。</div>` +
      hist.map(h => {
        const val = h.valuation || {}, fv = val.fair_value || {};
        const isEff = effective && effective.id === h.id;
        return `<div class="vercard ${h.deleted ? "ver-del" : ""} ${isEff ? "ver-eff" : ""}">
          <div class="ver-pick">${h.deleted || !h.has_valuation ? "" : `<input type="radio" name="verpick" ${isEff ? "checked" : ""} data-actrun="${h.id}" title="设为看板显示版本">`}</div>
          <div class="ver-main">
            <div><b class="mono" style="font-size:14px">${money(fv.base)}</b> ${h.has_valuation ? actionChip(val.action) : statusChip("muted", "无估值")}
              ${isEff ? statusChip("good", pinned ? "当前显示 · 手动固定" : "当前显示 · 自动") : ""} ${h.deleted ? statusChip("critical", "已删除") : ""}</div>
            <div class="cellnote">买入 ≤ ${money(val.recommended_buy_price)} · 方法 <span class="mono">${esc((h.method_commit || "—").slice(0, 7))}</span> · ${esc(h.engine || "—")}${h.model ? " · " + esc(h.model) : ""}${h.effort ? " · " + esc(h.effort) : ""}</div>
            <div class="cellnote mono">${fmtTime(h.captured_at)} · as_of ${esc((h.as_of || "").slice(0, 10))} · ${esc(h.case_id || "")}</div>
          </div>
          <div class="ver-ops">${h.deleted ? `<button class="btn btn-sm" data-resrun="${h.id}">恢复</button>` : `<button class="btn btn-sm btn-danger" data-delrun="${h.id}">删除</button>`}</div>
        </div>`;
      }).join("") +
      (pinned ? `<button class="btn btn-sm" id="ver-auto" style="margin-top:10px">恢复自动(总是显示最新版)</button>` : "");
    const act = fn => async () => {
      try { await fn(); } catch (e) { if (e.message !== "cancelled") alert("操作失败:" + e.message); }
      detailCache.clear(); load(); viewPortfolio();
    };
    box.querySelectorAll("[data-actrun]").forEach(r => r.onchange = act(() => api(`/api/runs/${r.dataset.actrun}/activate`, { method: "POST" })));
    box.querySelectorAll("[data-delrun]").forEach(b => b.onclick = act(async () => {
      if (!confirm("删除该版本?(软删除,可恢复)")) throw new Error("cancelled");
      await api(`/api/runs/${b.dataset.delrun}`, { method: "DELETE" });
    }));
    box.querySelectorAll("[data-resrun]").forEach(b => b.onclick = act(() => api(`/api/runs/${b.dataset.resrun}/restore`, { method: "POST" })));
    const auto = document.getElementById("ver-auto");
    if (auto) auto.onclick = act(() => api(`/api/history/${encodeURIComponent(sec)}/auto`, { method: "POST" }));
  };
  load();
}

function bindAutocomplete() {
  const input = document.getElementById("w-entity");
  const box = document.getElementById("ac-box");
  if (!input || !box) return;
  let timer = null;
  input.oninput = () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { box.style.display = "none"; return; }
    timer = setTimeout(async () => {
      // 重绘可能替换过节点(行情/推荐到达时),回调里实时取当前节点
      const liveBox = () => document.getElementById("ac-box");
      const liveInput = () => document.getElementById("w-entity");
      try {
        const items = await api("/api/symbol-search?q=" + encodeURIComponent(q));
        const bx = liveBox(), inp = liveInput();
        if (!bx || !inp) return;
        if (!Array.isArray(items) || !items.length || inp.value.trim() !== q) { bx.style.display = "none"; return; }
        bx.innerHTML = items.map(i => `<div class="ac-item" data-n="${esc(i.name)}" data-s="${esc(i.symbol)}"><b>${esc(i.name)}</b> <span class="mono cellnote">${esc(i.symbol)}</span> <span class="cellnote">${esc(i.exchange)}</span></div>`).join("");
        bx.style.display = "";
        bx.querySelectorAll(".ac-item").forEach(el => el.onmousedown = ev => {
          ev.preventDefault();
          liveInput().value = el.dataset.n;
          document.getElementById("w-sec").value = el.dataset.s;
          liveBox().style.display = "none";
        });
      } catch { const bx = liveBox(); if (bx) bx.style.display = "none"; }
    }, 250);
  };
  input.onblur = () => setTimeout(() => { box.style.display = "none"; }, 150);
}

function startSugPoll(prevGen) {
  clearInterval(sugTimer);
  let ticks = 0;
  sugTimer = setInterval(async () => {
    ticks++;
    if (ticks > 75) { clearInterval(sugTimer); sugTimer = null; return; }   // ~10 min cap
    try {
      const s = await api("/api/watch-suggestions");
      if (s.generated_at && s.generated_at !== prevGen) {
        clearInterval(sugTimer); sugTimer = null; sugData = s;
        if ((location.hash || "#/portfolio").includes("portfolio")) paintPortfolio();
      }
    } catch {}
  }, 8000);
}

function bindPortfolio() {
  const msg = document.getElementById("w-msg");
  document.getElementById("w-add").onclick = async () => {
    try {
      await post("/api/watchlist", { entity: document.getElementById("w-entity").value, security: document.getElementById("w-sec").value, note: document.getElementById("w-note").value });
      viewPortfolio();
    } catch (e) { msg.textContent = e.message; }
  };
  bindAutocomplete();
  const sugRun = document.getElementById("sug-run");
  if (sugRun) sugRun.onclick = async () => {
    const hint = (document.getElementById("sug-hint") || {}).value || "";
    openEngineMenu(sugRun, "AI 推荐关注", async (engine, model, effort) => {
      try {
        await post("/api/jobs", { type: "suggest_watch", engine, params: { hint: hint.trim(), model, effort } });
        startSugPoll((sugData || {}).generated_at || null);
        paintPortfolio();
      } catch (e) { const m = document.getElementById("sug-msg"); if (m) m.textContent = e.message; }
    });
  };
  const sugClear = document.getElementById("sug-clear");
  if (sugClear) sugClear.onclick = async () => {
    try { await del("/api/watch-suggestions"); sugData = null; paintPortfolio(); } catch {}
  };
  $view.querySelectorAll("[data-sugadd]").forEach(b => b.onclick = async () => {
    const it = ((sugData || {}).suggestions || [])[+b.dataset.sugadd];
    if (!it) return;
    try { await post("/api/watchlist", { entity: it.entity, security: it.security, note: (it.note || "").slice(0, 30) }); viewPortfolio(); }
    catch (e) { const m = document.getElementById("sug-msg"); if (m) m.textContent = e.message; }
  });
  $view.querySelectorAll("[data-sort]").forEach(b => b.onclick = () => { pfSort = b.dataset.sort; paintPortfolio(); });
  $view.querySelectorAll("[data-filter]").forEach(b => b.onclick = () => { pfFilter = b.dataset.filter; paintPortfolio(); });
  $view.querySelectorAll("[data-run]").forEach(b => b.onclick = ev => {
    ev.stopPropagation();
    openEngineMenu(b, `${b.dataset.run} 跑预测`, async (engine, model, effort) => {
      b.disabled = true; b.textContent = "启动中…";
      try { await post("/api/jobs", { type: "live_forecast", engine, params: { entity: b.dataset.entity, security: b.dataset.run, model, effort } }); viewPortfolio(); }
      catch (e) { alert("启动失败:" + e.message); viewPortfolio(); }
    });
  });
  $view.querySelectorAll("[data-viewlog]").forEach(b => b.onclick = ev => { ev.stopPropagation(); openLogDrawer(b.dataset.viewlog); });
  $view.querySelectorAll("[data-versions]").forEach(b => b.onclick = ev => { ev.stopPropagation(); openVersionDrawer(b.dataset.versions, b.dataset.entity); });
  $view.querySelectorAll("[data-canceljob]").forEach(b => b.onclick = async ev => {
    ev.stopPropagation();
    if (!b.dataset.canceljob) { alert("找不到任务 ID,请到「任务」页停止"); return; }
    if (!confirm(`取消 ${b.dataset.sec} 正在进行的推理?`)) return;
    try { await api(`/api/jobs/${b.dataset.canceljob}/stop`, { method: "POST" }); } catch (e) { alert("取消失败:" + e.message); }
    viewPortfolio();
  });
  $view.querySelectorAll("[data-unwatch]").forEach(b => b.onclick = async ev => {
    ev.stopPropagation();
    if (!confirm(`把 ${b.dataset.unwatch} 移出关注列表?(不删除已有预测记录)`)) return;
    await del(`/api/watchlist/${encodeURIComponent(b.dataset.unwatch)}`); expanded.delete(b.dataset.unwatch); viewPortfolio();
  });
  $view.querySelectorAll("[data-toggle]").forEach(el => el.onclick = () => {
    const sec = el.dataset.toggle;
    if (expanded.has(sec)) expanded.delete(sec); else expanded.add(sec);
    paintPortfolio();
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
    html += `<div class="verdict" style="border-left-color:${rateMeta(v.action).color}">
      <div class="verdict-main">${actionChip(v.action)} <b>${esc(v.one_line_thesis || "")}</b></div>
      <div class="verdict-fv">情景公允价:悲观 ${money(v.fair_value?.bear)} · 基准 <b>${money(v.fair_value?.base)}</b> · 乐观 ${money(v.fair_value?.bull)} · 建议买入 ≤ ${money(v.recommended_buy_price)}</div>
      ${v.current_valuation_note ? `<div class="verdict-fv" style="margin-top:4px">当前估值:${esc(v.current_valuation_note)}</div>` : ""}
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
    // 后端已把所有快照方言归一成标准结构:{revenue,profit,eps} x {point,low,high} + extras
    const normalized = detail.outputs_normalized || {};
    const periods = [["year_1", "FY+1"], ["year_2", "FY+2"], ["year_3_distribution", "FY+3"], ["long_term_normalized", "长期正常化"]];
    const fm = v => v == null ? "—" : Number(v).toLocaleString("en-US");
    const feps = v => v == null ? "—" : "$" + Number(v).toFixed(2);
    const range = (lo, hi, f) => (lo != null || hi != null) ? `${f(lo)} ~ ${f(hi)}` : "—";
    const rowsHtml = periods.map(([k, label]) => {
      const o = normalized[k];
      if (!o) return "";
      const r = o.revenue || {}, pr = o.profit || {}, e = o.eps || {};
      const extras = Object.entries(o.extras || {})
        .map(([key, v]) => `<div class="kv"><span class="kv-k">${esc(metricLabel(key))}</span><span class="kv-v">${metricValue(key, v)}</span></div>`).join("");
      const dv = pr.derived ? "≈" : "";
      return `<tr><td><b>${label}</b>${o.period ? `<div class="cellnote mono">${esc(o.period)}</div>` : ""}</td>
        <td class="num">${fm(r.point)}</td>
        <td class="num">${range(r.low, r.high, fm)}</td>
        <td class="num">${pr.point != null ? dv + fm(pr.point) : "—"}</td>
        <td class="num">${(pr.low != null || pr.high != null) ? dv + range(pr.low, pr.high, fm) : "—"}</td>
        <td class="num">${feps(e.point)}${e.low != null || e.high != null ? `<div class="cellnote">${feps(e.low)} ~ ${feps(e.high)}</div>` : ""}</td></tr>` +
        (extras ? `<tr class="kvrow"><td></td><td colspan="5"><div class="kvgrid">${extras}</div></td></tr>` : "");
    }).join("");
    if (rowsHtml) {
      const methodTag = primary.method_commit ? ` · 方法 ${esc(String(primary.method_commit).slice(0, 7))}` : "";
      html += `<div class="dsec"><h3>预测输出(${esc(primary.run_mode === "live_forecast" ? "实时" : "训练")} · as_of ${esc((primary.as_of || "").slice(0, 10))}${methodTag} · 金额单位:百万美元)</h3>
        <table class="grid"><thead><tr><th>期</th><th class="num">收入点值</th><th class="num">收入区间</th><th class="num">净利点值</th><th class="num">净利区间</th><th class="num">EPS(区间)</th></tr></thead><tbody>${rowsHtml}</tbody></table>
        <div class="cellnote">点值 = 基准情景 / 分布中位(p50);区间 = 悲观~乐观(FY+3 为 p10~p90)。净利为 GAAP 口径;带 ≈ 的净利由 EPS × 摊薄股数推算(快照未直接给出总额)。</div></div>`;
    }
    const probs = Object.entries(snap.scenario_probabilities || {});
    if (probs.length) {
      const segColor = (k, i) => ({ bear: "var(--loss)", base: "var(--accent)", bull: "var(--gain)" }[String(k).toLowerCase()]
        || ["var(--cat-1)", "var(--cat-3)", "var(--cat-4)", "var(--cat-2)"][i % 4]);
      html += `<div class="dsec"><h3>情景概率</h3><div class="segbar">` +
        probs.map(([k, p], i) => `<div class="seg" style="flex:${Number(p) || 0.001};background:${segColor(k, i)}" title="${esc(k)} ${pct(p, 0)}"></div>`).join("") +
        `</div><div class="seglegend">` +
        probs.map(([k, p], i) => `<span class="status"><span class="dot" style="background:${segColor(k, i)}"></span>${esc(k)} ${pct(p, 0)}</span>`).join("") + `</div></div>`;
    }
    const weights = Object.entries(snap.mechanism_weights || {});
    if (weights.length) {
      html += `<div class="dsec"><h3>机制权重</h3>` + weights.map(([k, w]) => `<div class="mech-row">
        <div class="mech-head"><span class="lb">${esc(k)}</span><span class="pc">${pct(w, 0)}</span></div>
        <div class="mech-track"><div class="mech-fill" style="width:${Math.min(100, (Number(w) || 0) * 100)}%"></div></div></div>`).join("") + `</div>`;
    }
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
          <td>${c.has_model ? `<a class="plain" href="${esc(apiHref(`/api/cases/${encodeURIComponent(c.round_id)}/${encodeURIComponent(c.case_id)}/model`))}" onclick="event.stopPropagation()">模型</a> ` : ""}<button class="btn btn-sm btn-danger" data-delcase="${esc(c.round_id)}|${esc(c.case_id)}">删除</button></td></tr>`;
      }
      html += `</tbody></table></div>`;
    }
    // 版本管理已提升为卡片头「版本」按钮的抽屉
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
  const [status, roundsData, waves, engines] = await Promise.all([
    api("/api/status"), api("/api/rounds"), api("/api/curriculum"), api("/api/engines")]);
  const paused = (status.control || {}).auto_training === "pause";
  const availableEngines = visibleEngines(engines);
  const usedKeys = new Set(roundsData.flatMap(r => r.cases.map(c => c.case_id)));
  const engineOpts = availableEngines.map(e => `<option value="${esc(e.engine)}" ${e.available ? "" : "disabled"}>${esc(e.engine)}${e.available ? "" : "(待接入)"}</option>`).join("");
  const modelOptsFor = name => {
    const spec = availableEngines.find(e => e.engine === name && e.available) || {};
    return `<option value="">默认</option>` + (spec.models || []).map(m => `<option value="${esc(m.id)}">${esc(m.id)}</option>`).join("");
  };
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
      <span class="cellnote">${(status.running_jobs || []).filter(j => TRAINING_TYPES.has(j.type)).length} 个训练任务在跑(推理任务见「<a class="plain" href="#/jobs">任务</a>」页)· 开关写入 training-runs/control.json,训练会话每个案例前读取</span>
    </div>
  </div>

  <div class="card">
    <h2>轮次计划(一轮 4 只:2 训练 + 2 验证)</h2>
    <div class="card-sub">从下方课程表按 pair 填入,或手动编辑;保存后可一键启动整轮,也可以让 agent 自动安排下一轮。</div>
    <div class="form-row"><div class="field"><label>轮次 ID</label><input id="plan-id" value="${esc(nextRoundId(roundsData))}" style="min-width:120px"></div>
      <div class="field"><label>引擎</label><select id="plan-engine">${engineOpts}</select></div>
      <div class="field"><label>型号(可选)</label><select id="plan-model" style="min-width:150px">${modelOptsFor((availableEngines.find(e => e.available) || {}).engine || "codex")}</select></div>
      <div class="field"><label>强度(可选)</label><select id="plan-effort" style="min-width:100px"><option value="">默认</option></select></div></div>
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
          <div class="cellnote">${esc(c.mechanism || "")}</div>
          ${c.role === "development" || c.role === "untouched_holdout" ? `<div class="fillbtns"><button class="btn btn-sm" data-fillone='${esc(JSON.stringify({ group: c.role === "development" ? "a" : "b", entity: c.company, security: c.security, as_of: c.proposed_as_of }))}'>${c.role === "development" ? "填入训练" : "填入验证"}</button></div>` : ""}</div>`;
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

  <div class="card"><h2>方法是否在进步</h2>
    <div class="card-sub">按方法版本(git 提交)聚合已对照真值的案例——skill 每优化一版,这里多一行。</div>
    <div id="progressbox">加载中…</div>
  </div>

`;

  $view.innerHTML = html;
  bindTraining(paused);
  api("/api/method/progress").then(prog => {
    const box = document.getElementById("progressbox");
    if (!box) return;
    if (!prog.length) { box.innerHTML = `<div class="cellnote">还没有已评分的案例——第一轮训练完成后,这里会出现按方法版本的误差趋势。</div>`; return; }
    box.innerHTML = `<table class="grid"><thead><tr><th>方法版本</th><th class="num">案例数</th><th class="num">平均收入MAPE</th><th class="num">平均利润率误差(pp)</th><th class="num">区间覆盖率</th></tr></thead><tbody>` +
      prog.map(r => `<tr><td class="mono">${esc(r.method_commit)}</td><td class="num">${r.cases}</td>
        <td class="num">${pct(r.avg_revenue_mape)}</td><td class="num">${num(r.avg_margin_mae_pp, 1)}</td>
        <td class="num">${pct(r.avg_revenue_coverage, 0)}</td></tr>`).join("") + `</tbody></table>`;
  }).catch(() => {
    const box = document.getElementById("progressbox");
    if (box) box.innerHTML = `<div class="cellnote">后端重启后可用(新端点待加载)。</div>`;
  });
}

function bindTraining(paused) {
  const msg = document.getElementById("plan-msg");
  const engineSel = document.getElementById("plan-engine");
  const modelSel = document.getElementById("plan-model");
  const effortSel = document.getElementById("plan-effort");
  const planChoice = () => ({ engine: engineSel.value, model: modelSel ? modelSel.value : "", effort: effortSel ? effortSel.value : "" });
  if (engineSel && modelSel && effortSel) {
    const refill = async () => {
      const list = visibleEngines(await api("/api/engines").catch(() => []));
      const spec = list.find(e => e.engine === engineSel.value && e.available) || {};
      modelSel.innerHTML = `<option value="">默认</option>` + (spec.models || []).map(m => `<option value="${esc(m.id)}">${esc(m.id)}</option>`).join("");
      effortSel.innerHTML = `<option value="">默认</option>`;
      modelSel.onchange = () => {
        const m = (spec.models || []).find(x => x.id === modelSel.value) || {};
        effortSel.innerHTML = `<option value="">默认</option>` + (m.efforts || []).map(e => `<option value="${esc(e)}">${esc(e)}</option>`).join("");
      };
    };
    engineSel.onchange = refill;
    modelSel.onchange = () => {};
    refill();
  }
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
  $view.querySelectorAll("[data-fillone]").forEach(b => b.onclick = () => {
    const c = JSON.parse(b.dataset.fillone);
    const target = c.group === "a" ? plan.a : plan.b;
    if (target.length >= 2) { msg.textContent = "每组固定 2 只(2+2)"; return; }
    if (!target.some(x => x.security === c.security && x.as_of === c.as_of)) target.push({ entity: c.entity, security: c.security, as_of: c.as_of });
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
      const c = planChoice();
      const rec = await post("/api/jobs", { type: "training_round", engine: c.engine, params: { round_id: rid, model: c.model, effort: c.effort } });
      msg.textContent = `整轮任务已启动 ${rec.id}`; viewTraining();
    } catch (e) { msg.textContent = e.message; }
  };
  document.getElementById("plan-agent").onclick = async () => {
    try {
      const c = planChoice();
      const rec = await post("/api/jobs", { type: "plan_round", engine: c.engine, params: { model: c.model, effort: c.effort } });
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
    const c = planChoice();
    await post("/api/jobs", { type: "training_round", engine: c.engine, params: { round_id: b.dataset.launchround, model: c.model, effort: c.effort } });
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
}

/* ================= 任务看板 ================= */
let boardTimer = null;
const elapsed = (start, end) => {
  if (!start) return "—";
  const ms = (end ? new Date(end) : new Date()) - new Date(start);
  if (isNaN(ms) || ms < 0) return "—";
  const m = Math.floor(ms / 60000), h = Math.floor(m / 60);
  return h ? `${h}h${m % 60}m` : `${m}m${Math.floor(ms % 60000 / 1000)}s`;
};

async function viewJobs() {
  clearInterval(logTimer); clearInterval(boardTimer);
  const jobsList = await api("/api/jobs");
  const running = jobsList.filter(j => ["running", "running_detached"].includes(j.status));
  const totalCost = jobsList.reduce((s, j) => s + (Number(j.cost_usd) || 0), 0);
  let html = `
    <div class="tile-row">
      <div class="tile"><div class="t-label">运行中</div><div class="t-value">${running.length}</div>
        <div class="t-note">推理 ${running.filter(j => j.type === "live_forecast").length} · 训练 ${running.filter(j => TRAINING_TYPES.has(j.type)).length}</div></div>
      <div class="tile"><div class="t-label">历史任务</div><div class="t-value">${jobsList.length}</div></div>
      <div class="tile"><div class="t-label">推理 / 训练</div><div class="t-value">${jobsList.filter(j => j.type === "live_forecast").length} / ${jobsList.filter(j => TRAINING_TYPES.has(j.type)).length}</div></div>
      <div class="tile"><div class="t-label">总成本</div><div class="t-value">${totalCost ? "$" + totalCost.toFixed(2) : "—"}</div></div>
    </div>
    <div class="card"><h2>任务看板</h2>
      <div class="card-sub">推理任务从「投资看板」发起;训练任务从「自训练」发起;这里统一查看、看日志、停止、删记录。</div>`;
  if (!jobsList.length) html += `<div class="empty">还没有任务记录。</div>`;
  else {
    html += `<table class="grid"><thead><tr><th>类型</th><th>对象</th><th>状态</th><th>引擎</th><th>开始</th><th>耗时</th><th class="num">成本</th><th></th></tr></thead><tbody>`;
    for (const j of jobsList) {
      const isRunning = ["running", "running_detached"].includes(j.status);
      html += `<tr><td>${jobTypeChip(j.type)}</td><td><b>${esc(jobTarget(j))}</b><div class="mono cellnote">${esc(j.id)}</div></td>
        <td>${jobChip(j.status)}</td><td>${esc(j.engine)}${(j.params || {}).model ? `<div class="mono cellnote">${esc(j.params.model)}${j.params.effort ? " · " + esc(j.params.effort) : ""}</div>` : ""}</td>
        <td class="mono cellnote">${fmtTime(j.started_at)}</td>
        <td class="mono cellnote">${elapsed(j.started_at, j.ended_at)}</td>
        <td class="num cellnote">${j.cost_usd != null ? "$" + Number(j.cost_usd).toFixed(2) : "—"}</td>
        <td><button class="btn btn-sm" data-log="${esc(j.id)}">日志</button>
        ${isRunning ? `<button class="btn btn-sm btn-danger" data-stop="${esc(j.id)}">停止</button>` : `<button class="btn btn-sm" data-deljob="${esc(j.id)}">删记录</button>`}</td></tr>`;
    }
    html += `</tbody></table>`;
  }
  html += `<div id="logbox" style="display:none;margin-top:12px"><div class="card-sub" id="logtitle"></div><pre class="log" id="logpre"></pre></div></div>`;
  $view.innerHTML = html;

  const guarded = fn => async (...args) => { try { await fn(...args); } catch (e) { alert("操作失败:" + e.message); } finally { viewJobs(); } };
  $view.querySelectorAll("[data-stop]").forEach(b => b.onclick = guarded(async () => {
    if (!confirm(`停止任务 ${b.dataset.stop}?运行中的研究会被终止。`)) return;
    await api(`/api/jobs/${b.dataset.stop}/stop`, { method: "POST" });
  }));
  $view.querySelectorAll("[data-deljob]").forEach(b => b.onclick = guarded(async () => {
    if (!confirm("删除该任务记录和日志?(移入 jobs/_trash)")) return;
    await del(`/api/jobs/${b.dataset.deljob}`);
  }));
  $view.querySelectorAll("[data-log]").forEach(b => b.onclick = () => openLogDrawer(b.dataset.log));
  const wantLog = (window.__routeQuery || new URLSearchParams()).get("log");
  if (wantLog) openLogDrawer(wantLog);
  if (running.length && !document.getElementById("logbox").style.display) {
    boardTimer = setInterval(() => { if ((location.hash || "").includes("jobs") && document.getElementById("logbox").style.display === "none") viewJobs(); }, 15000);
  }
}

/* ================= 方法 ================= */
const LOOP_SVG = `
<svg viewBox="0 0 1160 322" width="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="自训练闭环流程图">
  <defs>
    <marker id="ar-n" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#8a8c92"/></marker>
    <marker id="ar-w" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#b5822a"/></marker>
    <marker id="ar-g" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#0b7a43"/></marker>
    <marker id="ar-b" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2563c9"/></marker>
  </defs>
  <style>
    .bd{fill:#f7f7f3;stroke:#eeeee9}
    .bd2{fill:rgba(37,99,201,.045);stroke:rgba(37,99,201,.13)}
    .bdl{font:500 10.5px 'IBM Plex Mono',monospace;fill:#8a8c92;letter-spacing:.12em}
    .bx{fill:#fff;stroke:#dedcd4;stroke-width:1}
    .no{font:500 9.5px 'IBM Plex Mono',monospace;fill:#c2c1b9;letter-spacing:.1em}
    .bt{font:600 13px 'IBM Plex Sans',system-ui,sans-serif;fill:#14161a}
    .bs{font:11px 'IBM Plex Sans',system-ui,sans-serif;fill:#8a8c92}
    .e{stroke:#8a8c92;stroke-width:1.5;fill:none;marker-end:url(#ar-n)}
    .ew{stroke:#b5822a;stroke-width:1.5;fill:none;marker-end:url(#ar-w)}
    .eg{stroke:#0b7a43;stroke-width:1.5;fill:none;marker-end:url(#ar-g)}
    .eb{stroke:#2563c9;stroke-width:1.5;fill:none;stroke-dasharray:5 3;marker-end:url(#ar-b)}
    .lw{font:600 11px 'IBM Plex Sans',system-ui,sans-serif;fill:#b5822a}
    .lg{font:600 11px 'IBM Plex Sans',system-ui,sans-serif;fill:#0b7a43}
    .lb{font:600 11px 'IBM Plex Sans',system-ui,sans-serif;fill:#2563c9}
    .note{font:10.5px 'IBM Plex Sans',system-ui,sans-serif;fill:#a8a79f}
  </style>

  <rect class="bd" x="0" y="40" width="578" height="112" rx="10"/>
  <text class="bdl" x="14" y="59">时间沙盒 · 只用 ≤ as_of 的信息</text>
  <rect class="bd2" x="582" y="40" width="578" height="112" rx="10"/>
  <text class="bdl" x="596" y="59">封存之后 · 揭真值、归因、复核</text>

  <rect class="bx" x="10" y="76" width="170" height="62" rx="7"/>
  <text class="no" x="24" y="94">01</text><text class="bt" x="95" y="107" text-anchor="middle">选公司组</text><text class="bs" x="95" y="125" text-anchor="middle">2 只训练 + 2 只验证</text>
  <rect class="bx" x="204" y="76" width="170" height="62" rx="7"/>
  <text class="no" x="218" y="94">02</text><text class="bt" x="289" y="107" text-anchor="middle">沙盒研究</text><text class="bs" x="289" y="125" text-anchor="middle">模型记忆不算证据</text>
  <rect class="bx" x="398" y="76" width="170" height="62" rx="7"/>
  <text class="no" x="412" y="94">03</text><text class="bt" x="483" y="107" text-anchor="middle">封存预测</text><text class="bs" x="483" y="125" text-anchor="middle">哈希定格,不可改</text>
  <rect class="bx" x="592" y="76" width="170" height="62" rx="7"/>
  <text class="no" x="606" y="94">04</text><text class="bt" x="677" y="107" text-anchor="middle">揭真值 · 打分</text><text class="bs" x="677" y="125" text-anchor="middle">MAPE / 误差 / 覆盖</text>
  <rect class="bx" x="786" y="76" width="170" height="62" rx="7"/>
  <text class="no" x="800" y="94">05</text><text class="bt" x="871" y="107" text-anchor="middle">机制级归因</text><text class="bs" x="871" y="125" text-anchor="middle">改规则,不调数字</text>
  <rect class="bx" x="980" y="76" width="170" height="62" rx="7"/>
  <text class="no" x="994" y="94">06</text><text class="bt" x="1065" y="107" text-anchor="middle">验证组复核</text><text class="bs" x="1065" y="125" text-anchor="middle">2 只未触碰的股</text>

  <line class="e" x1="180" y1="107" x2="198" y2="107"/>
  <line class="e" x1="374" y1="107" x2="392" y2="107"/>
  <line class="e" x1="568" y1="107" x2="586" y2="107"/>
  <line class="e" x1="762" y1="107" x2="780" y2="107"/>
  <line class="e" x1="956" y1="107" x2="974" y2="107"/>

  <rect class="bx" x="700" y="226" width="260" height="60" rx="7"/>
  <text class="bt" x="830" y="252" text-anchor="middle">换组交叉(左脚踩右脚)</text><text class="bs" x="830" y="270" text-anchor="middle">B 转训练,A 回验,比一致性</text>
  <rect class="bx" x="270" y="226" width="250" height="60" rx="7"/>
  <text class="bt" x="395" y="252" text-anchor="middle">git 发布 / 回退</text><text class="bs" x="395" y="270" text-anchor="middle">通过 push · 失败 revert</text>

  <path class="eg" d="M 1030 138 V 182 Q 1030 190 1022 190 H 403 Q 395 190 395 198 V 216"/>
  <text class="lg" x="620" y="179">没大问题 → 发布</text>

  <path class="ew" d="M 1100 138 V 248 Q 1100 256 1092 256 H 970"/>
  <text class="lw" x="1088" y="216" text-anchor="end">验证不佳</text>

  <line class="ew" x1="700" y1="256" x2="530" y2="256"/>
  <text class="note" x="830" y="302" text-anchor="middle">两组一致 → 发布;仍不一致 → 放弃,换一组新公司</text>

  <path class="eb" d="M 270 256 H 103 Q 95 256 95 248 V 148"/>
  <text class="lb" x="112" y="243">新方法版本 → 下一轮</text>
</svg>`;

const PIPE_SVG = `
<svg viewBox="0 0 1160 306" width="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="生产 skill 预测流水线">
  <defs><marker id="par" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#8a8c92"/></marker></defs>
  <style>
    .pbx{fill:#fff;stroke:#dedcd4}
    .pno{font:500 9.5px 'IBM Plex Mono',monospace;fill:#c2c1b9;letter-spacing:.1em}
    .pbt{font:600 12.5px 'IBM Plex Sans',system-ui,sans-serif;fill:#14161a}
    .pbs{font:10.5px 'IBM Plex Sans',system-ui,sans-serif;fill:#8a8c92}
    .pe{stroke:#8a8c92;stroke-width:1.5;fill:none;marker-end:url(#par)}
  </style>
  <rect class="pbx" x="10" y="30" width="212" height="66" rx="7"/><text class="pno" x="24" y="48">01</text>
  <text class="pbt" x="116" y="60" text-anchor="middle">范围与时间边界</text><text class="pbs" x="116" y="78" text-anchor="middle">公司口径 · 财历 · as_of 锁定</text>
  <rect class="pbx" x="246" y="30" width="212" height="66" rx="7"/><text class="pno" x="260" y="48">02</text>
  <text class="pbt" x="352" y="60" text-anchor="middle">点时点 Source Pack</text><text class="pbs" x="352" y="78" text-anchor="middle">E0–E4 分级证据 · 哈希留痕</text>
  <rect class="pbx" x="482" y="30" width="212" height="66" rx="7"/><text class="pno" x="496" y="48">03</text>
  <text class="pbt" x="588" y="60" text-anchor="middle">前瞻证据 SignalCards</text><text class="pbs" x="588" y="78" text-anchor="middle">≥6 信号 · ≥3 家族 · 独立源约束</text>
  <rect class="pbx" x="718" y="30" width="212" height="66" rx="7"/><text class="pno" x="732" y="48">04</text>
  <text class="pbt" x="824" y="60" text-anchor="middle">机制路由与建模</text><text class="pbs" x="824" y="78" text-anchor="middle">9+1 机制模块 × 8 行业透镜 · 权重</text>
  <rect class="pbx" x="954" y="30" width="196" height="66" rx="7"/><text class="pno" x="968" y="48">05</text>
  <text class="pbt" x="1052" y="60" text-anchor="middle">公式化三表模型</text><text class="pbs" x="1052" y="78" text-anchor="middle">model.xlsx · ≥30 公式驱动</text>
  <line class="pe" x1="222" y1="63" x2="242" y2="63"/><line class="pe" x1="458" y1="63" x2="478" y2="63"/>
  <line class="pe" x1="694" y1="63" x2="714" y2="63"/><line class="pe" x1="930" y1="63" x2="950" y2="63"/>
  <path class="pe" d="M 1052 96 V 130 Q 1052 138 1044 138 H 124 Q 116 138 116 146 V 178"/>
  <rect class="pbx" x="10" y="182" width="212" height="66" rx="7"/><text class="pno" x="24" y="200">06</text>
  <text class="pbt" x="116" y="212" text-anchor="middle">情景与分布输出</text><text class="pbs" x="116" y="230" text-anchor="middle">FY+1 点 · FY+2 情景 · FY+3 分位</text>
  <rect class="pbx" x="246" y="182" width="212" height="66" rx="7"/><text class="pno" x="260" y="200">07</text>
  <text class="pbt" x="352" y="212" text-anchor="middle">估值与买入纪律</text><text class="pbs" x="352" y="230" text-anchor="middle">DCF/倍数 · 市场隐含反推 · 买点</text>
  <rect class="pbx" x="482" y="182" width="212" height="66" rx="7"/><text class="pno" x="496" y="200">08</text>
  <text class="pbt" x="588" y="212" text-anchor="middle">独立红队</text><text class="pbs" x="588" y="230" text-anchor="middle">开放 P0/P1 不闭环 = 不许交付</text>
  <rect class="pbx" x="718" y="182" width="212" height="66" rx="7"/><text class="pno" x="732" y="200">09</text>
  <text class="pbt" x="824" y="212" text-anchor="middle">严格交付校验</text><text class="pbs" x="824" y="230" text-anchor="middle">validate_delivery --strict 全门槛</text>
  <rect class="pbx" x="954" y="182" width="196" height="66" rx="7"/><text class="pno" x="968" y="200">10</text>
  <text class="pbt" x="1052" y="212" text-anchor="middle">封存与入库</text><text class="pbs" x="1052" y="230" text-anchor="middle">快照哈希 · 版本入库 · 上看板</text>
  <line class="pe" x1="222" y1="215" x2="242" y2="215"/><line class="pe" x1="458" y1="215" x2="478" y2="215"/>
  <line class="pe" x1="694" y1="215" x2="714" y2="215"/><line class="pe" x1="930" y1="215" x2="950" y2="215"/>
</svg>`;

const SKILL_MODULES = {
  "机制模块(利润从哪来)": ["量·价·成本 unit-volume-price-cost", "产能利用率与良率 capacity-utilization-yield", "订阅与合同收入 recurring-contract-revenue", "订单积压与确认 orders-backlog-recognition", "项目分阶段转化 program-stage-conversion", "平台用量与渗透 platform-usage-adoption", "订户与内容经济 subscriber-content-economics", "离散会计事件 discrete-accounting-events", "口径与并表 perimeter-and-accounting", "合同/合资/资本 contracts-jv-capital", "DTA 估值准备(子模块)"],
  "行业透镜(公司属于哪种生意)": ["存储 memory-storage", "设备与过程控制 equipment-process-control", "代工封装材料 foundry-packaging-materials", "网络/光/定制硅 networking-optics-custom-silicon", "计算平台 compute-platforms", "云基础设施 cloud-infrastructure", "企业订阅软件 enterprise-recurring-software", "订阅内容平台 subscription-content-platform"],
  "治理与证据(不许胡说的部分)": ["核心工作流 core-forecast-workflow", "证据分级 core-source-and-evidence", "输出与估值契约 core-output-and-valuation", "前瞻证据校验 forward-evidence-validation", "研究充分性 research-completeness", "交付契约 full-company-delivery-contract", "模式路由与时间边界 mode-router"],
};

async function viewMethod() {
  const [timeline, skills, evolution, progress] = await Promise.all([
    api("/api/method/timeline"), api("/api/method/skills"),
    api("/api/method/evolution").catch(() => ({ versions: [] })),
    api("/api/method/progress").catch(() => [])]);
  const progByCommit = {};
  for (const r of progress) progByCommit[r.method_commit] = r;

  const moduleGroups = Object.entries(SKILL_MODULES).map(([group, items]) =>
    `<h3 class="wavehead">${group}</h3><div style="display:flex;flex-wrap:wrap;gap:6px">${items.map(m => `<span class="chip">${esc(m)}</span>`).join("")}</div>`).join("");

  let html = `
    <div class="card">
      <h2>生产 skill 完整逻辑(technology-company-profit-forecasting)</h2>
      <div class="card-sub">一次实时预测从 01 到 10 全流程走完才允许交付;任何一道门失败都会中止并留下失败记录。</div>
      <div class="loopwrap">${PIPE_SVG}</div>
      ${moduleGroups}
    </div>
    <div class="card">
      <h2>自训练闭环(technology-company-forecasting-trainer)</h2>
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
    <div class="card"><h2>方法演进脉络(每个版本优化了什么)</h2>
      <div class="card-sub">方法版本 = git 提交,当前 <span class="mono">${esc(timeline.branch)}@${esc((timeline.head || "").slice(0, 7))}</span> · 远程 ${esc(timeline.remote || "—")} · 绿点 = 当前版本;带训练成绩的版本标注验证结果。</div>
      <ul class="evo">` +
    evolution.versions.map((v, i) => {
      const prog = progByCommit[v.short];
      return `<li class="${i === 0 ? "evo-head" : ""}">
        <div class="evo-meta">
          <span class="evo-hash">${esc(v.short)}</span>
          <span class="evo-date">${esc((v.date || "").replace("T", " ").slice(0, 16))}</span>
          ${v.categories.map(c => `<span class="evo-cat c-${esc(c)}">${esc(c)}</span>`).join("")}
          ${prog ? `<span class="evo-metrics">验证 ${prog.cases} 案例 · MAPE ${pct(prog.avg_revenue_mape)}</span>` : ""}
        </div>
        <div class="evo-subject">${esc(v.subject)}</div>
        ${v.points.length ? `<ul class="evo-points">${v.points.map(pt => `<li>${esc(pt)}</li>`).join("")}</ul>`
          : v.body ? `<div class="evo-points" style="padding-left:0">${esc(v.body.split("\\n")[0].slice(0, 160))}</div>` : ""}
        <div class="evo-foot">${v.file_count} 文件 · +${v.adds} −${v.dels}${v.files.length ? " · " + esc(v.files.slice(0, 3).map(f => f.split("/").pop()).join(" · ")) + (v.file_count > 3 ? " …" : "") : ""}</div>
      </li>`;
    }).join("") + `</ul></div>`;
  $view.innerHTML = html;
}

/* ---------- router ---------- */
async function route() {
  clearInterval(logTimer); clearInterval(boardTimer);
  const hash = location.hash || "#/portfolio";
  const qIndex = hash.indexOf("?");
  window.__routeQuery = new URLSearchParams(qIndex === -1 ? "" : hash.slice(qIndex + 1));
  const parts = (qIndex === -1 ? hash : hash.slice(0, qIndex)).slice(2).split("/").map(decodeURIComponent);
  document.querySelectorAll(".tabs a").forEach(a => a.classList.toggle("active", a.dataset.tab === parts[0]));
  $view.innerHTML = `<div class="empty">加载中…</div>`;
  try {
    if (parts[0] === "training") await viewTraining();
    else if (parts[0] === "jobs") await viewJobs();
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
