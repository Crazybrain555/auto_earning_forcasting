/* 副本模式控件 — 仅本地仪表盘加载(不在 sync-console-assets 同步列表里,
   托管站点永远拿不到这个文件)。后端 /api/replica 的 mode 为 false 时什么都不渲染。
   默认收起成一枚"副本"小胶囊(颜色示意状态),点击展开;拉取中或出错时自动展开。 */
"use strict";

(() => {
  const FAST_MS = 2000;    // 拉取进行中
  const SLOW_MS = 60000;   // 平时刷新"数据截至"年龄
  const STALE_MS = 36 * 3600 * 1000;
  const COLLAPSE_KEY = "replica-bar-collapsed";
  const STYLE = `
    #replica-bar{position:fixed;right:16px;bottom:16px;z-index:900;display:flex;align-items:center;
      gap:10px;padding:8px 12px;border-radius:10px;font:500 12px/1.4 "IBM Plex Mono",ui-monospace,monospace;
      background:var(--panel,#faf9f6);color:var(--ink,#14161a);
      border:1px solid var(--line,#e7e7e2);box-shadow:0 6px 20px rgba(20,22,26,.12);max-width:min(92vw,460px)}
    #replica-bar.rb-min{padding:5px 6px;gap:0;box-shadow:0 3px 10px rgba(20,22,26,.10)}
    #replica-bar.rb-min .rb-text,#replica-bar.rb-min button{display:none}
    #replica-bar .rb-tag{padding:2px 7px;border:0;border-radius:999px;background:var(--accent,#2f6fde);
      color:#fff;font:inherit;font-weight:600;letter-spacing:.02em;white-space:nowrap;cursor:pointer;user-select:none}
    #replica-bar .rb-tag.rb-warn-bg{background:var(--warning,#9a6b00)}
    #replica-bar .rb-tag.rb-err-bg{background:var(--critical,#b3261e)}
    #replica-bar .rb-text{color:var(--soft,#4a4d54);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    #replica-bar .rb-text.rb-warn{color:var(--warning,#9a6b00)}
    #replica-bar .rb-text.rb-err{color:var(--critical,#b3261e);white-space:normal}
    #replica-bar button{cursor:pointer;border-radius:7px;padding:5px 11px;font:inherit;font-weight:600;
      color:#fff;background:var(--accent,#2f6fde);border:1px solid transparent;white-space:nowrap}
    #replica-bar button:disabled{opacity:.55;cursor:default}
  `;

  const el = (tag, cls) => { const n = document.createElement(tag); if (cls) n.className = cls; return n; };

  const scrub = message => {
    const shared = globalThis.__FORECAST_ACTION_FEEDBACK;
    return shared && shared.safeErrorMessage ? shared.safeErrorMessage(message) : String(message);
  };

  function ageText(iso) {
    if (!iso) return null;
    const ms = Date.now() - new Date(iso).getTime();
    if (!isFinite(ms)) return null;
    if (ms < 60000) return "刚刚";       // 含轻微时钟偏差的负值
    const mins = Math.floor(ms / 60000);
    if (mins < 60) return `${mins} 分钟前`;
    const hours = Math.floor(mins / 60);
    return hours < 48 ? `${hours} 小时前` : `${Math.floor(hours / 24)} 天前`;
  }

  const getStatus = () => fetch("/api/replica", { cache: "no-store" }).then(r => r.ok ? r.json() : null);

  function postPull() {
    return fetch("/api/replica/pull", { method: "POST", headers: { "X-Dashboard": "1" } })
      .then(async r => {
        const body = await r.json().catch(() => ({}));
        if (r.ok) return body;
        const error = new Error(body.detail || `HTTP ${r.status}`);
        error.status = r.status;
        throw error;
      });
  }

  let bar, tag, text, button;
  let timer = 0;
  let sawPulling = false;   // 本页面观察到过拉取,才允许完成后自动刷新一次
  let fetchFailures = 0;
  let lastState = null;
  let collapsed = localStorage.getItem(COLLAPSE_KEY) !== "0";   // 默认收起

  function ensureBar() {
    if (bar) return;
    const style = el("style");
    style.textContent = STYLE;
    document.head.append(style);
    bar = el("div"); bar.id = "replica-bar";
    tag = el("button", "rb-tag"); tag.type = "button"; tag.textContent = "副本";
    tag.title = "点击展开 / 收起";
    tag.setAttribute("aria-label", "副本状态栏:展开或收起");
    tag.onclick = () => {
      collapsed = !collapsed;
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
      if (lastState) render(lastState);
    };
    text = el("span", "rb-text");
    button = el("button"); button.type = "button"; button.textContent = "拉取最新";
    button.onclick = onPull;
    bar.append(tag, text, button);
    document.body.append(bar);
  }

  function render(state) {
    ensureBar();
    fetchFailures = 0;
    lastState = state;

    const broken = !state.pulling && !state.error && !state.snapshot;
    const created = state.snapshot && state.snapshot.created_at;
    const stale = created && (Date.now() - new Date(created).getTime()) > STALE_MS;

    // 拉取中/出错/清单不可读时强制展开;其余尊重用户的收起偏好
    const attention = state.pulling || Boolean(state.error) || broken;
    bar.classList.toggle("rb-min", collapsed && !attention);
    tag.className = "rb-tag" + (state.error || broken ? " rb-err-bg" : stale ? " rb-warn-bg" : "");

    if (state.pulling) {
      sawPulling = true;
      const elapsed = state.started_at ? Math.max(0, Math.round((Date.now() - new Date(state.started_at).getTime()) / 1000)) : null;
      text.className = "rb-text";
      text.textContent = elapsed == null ? "正在从生产拉取…" : `正在从生产拉取…已进行 ${elapsed} 秒(通常约 1 分钟)`;
      button.disabled = true;
      button.textContent = "拉取中";
      return;
    }

    if (sawPulling && state.finished_at && !state.error) {
      // 本页面看着这次拉取完成:刷新一次,让所有视图读新快照。
      // 刷新后 sawPulling 归零,不会形成刷新循环。
      location.reload();
      return;
    }

    button.disabled = false;
    button.textContent = "拉取最新";

    if (state.error) {
      text.className = "rb-text rb-err";
      text.textContent = `拉取失败：${scrub(state.error)}`;
      return;
    }

    if (broken) {
      text.className = "rb-text rb-err";
      text.textContent = "副本清单不可读——仪表盘可能读不到数据,请拉取或检查 replica/current";
      bar.title = "";
      return;
    }

    const age = ageText(created);
    text.className = stale ? "rb-text rb-warn" : "rb-text";
    text.textContent = age ? `数据截至 ${age}${stale ? " · 建议拉取" : ""}` : "数据时间未知";
    bar.title = `快照 ${state.snapshot.snapshot_id}\n生成于 ${created}\n生产代码 ${String(state.snapshot.root_commit || "").slice(0, 7)}`;
  }

  function schedule(ms) {
    clearTimeout(timer);
    timer = setTimeout(tick, ms);
  }

  async function tick() {
    let state = null;
    try {
      state = await getStatus();
    } catch {
      state = null;
    }
    if (state && state.mode) {
      render(state);
      schedule(state.pulling ? FAST_MS : SLOW_MS);
      return;
    }
    if (state && !state.mode) return;   // 非副本模式:不渲染,也不再轮询
    // 瞬时失败(比如后端正忙):不让轮询链断掉
    fetchFailures += 1;
    if (bar && sawPulling) {
      text.className = "rb-text rb-warn";
      text.textContent = `状态获取失败,重试中(${fetchFailures})…`;
    }
    schedule(Math.min(FAST_MS * fetchFailures, 15000));
  }

  async function onPull() {
    button.disabled = true;
    button.textContent = "拉取中";
    try {
      render(await postPull());
    } catch (error) {
      if (error.status === 409) {
        // 另一个标签页(或本页并发点击)已在拉取:跟着看进度即可
        sawPulling = true;
        render({ mode: true, pulling: true, started_at: null });
      } else {
        render({ mode: true, pulling: false, error: String(error.message || error), snapshot: null, finished_at: null });
      }
    }
    schedule(FAST_MS);
  }

  const boot = () => tick();
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", boot);
  else boot();
})();
