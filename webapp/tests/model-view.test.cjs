const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const APP = path.resolve(__dirname, "..", "app.js");


test("v2 model view renders causal profit line, value creation, valuation and monitoring", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView({
    version: "v2",
    main_line: {
      name: "AI capacity ramp",
      carrier_node_ids: ["AI shipments", "AI ASP"],
      target_node_ids: ["operating profit", "free cash flow"],
      lineage: ["qualification", "yield", "revenue", "operating profit"],
      falsification_ids: ["qualification_slip"],
      competitor_response_node_ids: ["new_supply"],
    },
    value_creation: {
      wacc: 0.10,
      periods: [{
        period: "FY2028",
        normalized_nopat: 18,
        average_invested_capital: 85.5,
        average_roic: 0.20,
        incremental_roic: 0.18,
        reinvestment_rate: 0.40,
        fundamental_growth: 0.072,
      }],
      fade: {
        terminal_roic: 0.14,
        years_to_fade: 8,
        competitive_response: "Competitor supply compresses the price-cost spread.",
        schedule: [{
          period: "Terminal",
          average_roic: 0.14,
          incremental_roic: 0.14,
          reinvestment_rate: 0.21,
          fundamental_growth: 0.03,
          erosion_or_renewal_event: "Qualified supply narrows excess returns.",
        }],
      },
    },
    valuation: {
      dcf: { enterprise_value: 1000 },
      residual_income: { equity_value: 930 },
      enterprise_to_equity: { equity_value: 910 },
      per_share: { value_per_share: 9.10 },
      reconciliation: { difference_pct: 0.022, explanation: "Different fade timing." },
      terminal: { wacc: 0.10, growth_rate: 0.03, terminal_roic: 0.14 },
    },
    market_implied_expectations: {
      named_driver: "AI ASP",
      implied_driver_value: 42,
      model_driver_value: 50,
      unit: "USD/unit",
    },
    monitoring: {
      indicators: [{ name: "qualification", trigger: "slips by two quarters" }],
    },
  }, {});

  for (const expected of [
    "利润 / FCF",
    "AI capacity ramp",
    "AI shipments",
    "operating profit",
    "价值创造",
    "ROIC",
    "规范化 NOPAT",
    "平均投入资本",
    "再投资率",
    "基本面增长",
    "竞争衰减",
    "Qualified supply narrows excess returns.",
    "DCF",
    "Residual Income",
    "市场反向隐含",
    "AI ASP",
    "证伪与监测",
    "qualification_slip",
  ]) assert.match(html, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));

  assert.doesNotMatch(html, /机制权重|mech-track/);
});


test("snapshot-native v2 fields render when backend model_view is absent", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView(null, {
    driver_tree: {
      main_line: "subscriber retention",
      thesis_carriers: ["paid members", "ARPU"],
      target_node_ids: ["free cash flow"],
      falsification_ids: ["churn_break"],
      competitor_response_node_ids: ["price_response"],
    },
    investment_case: { variant_view: "Churn stays below the market-implied level." },
    value_creation: { roic: 0.16, reinvestment_rate: 0.25, fundamental_growth: 0.04 },
    valuation: { dcf: { enterprise_value: 500 }, residual_income: { equity_value: 430 } },
    market_implied_expectations: { named_driver: "churn", implied_driver_value: 0.08 },
    monitoring: ["monthly churn"],
  });
  assert.match(html, /subscriber retention/);
  assert.match(html, /paid members/);
  assert.match(html, /Churn stays below/);
  assert.match(html, /monthly churn/);
});


test("backend adapter model_view wrapper renders methods, causal chain and falsification", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView({
    contract_version: "2.0",
    legacy: false,
    main_line: {
      id: "ai-price-duration",
      carrier_node_ids: ["ai_asp"],
      target_node_ids: ["profit"],
      thesis_carriers: ["AI ASP"],
      profit_causal_chain: {
        nodes: [{ id: "ai_asp" }, { id: "ai_revenue" }, { id: "profit" }],
        equations: [{ id: "eq_revenue" }, { id: "eq_profit" }],
      },
      competitor_response_node_ids: ["competitive_supply"],
    },
    investment_case: { variant_view: "Price duration is longer than implied." },
    value_creation: { periods: [{ period: "FY2028", roic: 0.20, reinvestment_rate: 0.40, fundamental_growth: 0.08 }] },
    valuation: {
      summary: { fair_value: { base: 9.1 } },
      methods: {
        dcf: { enterprise_value: 1000 },
        residual_income: { equity_value: 930 },
        per_share: { value_per_share: 9.1 },
      },
    },
    market_implied_expectations: { named_driver: "AI ASP", implied_driver_value: 42 },
    monitoring: { driver_ids: ["ai_asp"] },
    falsification: { ids: ["asp_break"], triggers: ["ASP below 42"] },
  }, {});
  for (const expected of ["ai-price-duration", "ai_revenue", "eq_profit", "1,000", "930", "9.1", "asp_break", "ASP below 42"]) {
    assert.match(html, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("monitoring rows expose series frequency threshold and breach action", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView({
    contract_version: "2.0",
    legacy: false,
    monitoring: { drivers: [{
      driver_id: "ai_asp",
      series: "Contract ASP",
      current_value: 48,
      model_value: 50,
      unit: "USD/unit",
      model_cell_or_formula: "Drivers!F18",
      monitor_type: "continuous",
      frequency: "quarterly",
      next_expected_at: "2026-09-30",
      milestone_date: "2026-10-15",
      trigger_operator: "below",
      trigger_value: 42,
      action_if_breached: "re-underwrite price path",
      owner: "analyst",
    }] },
  }, {});
  assert.match(html, /ai_asp \/ Contract ASP/);
  assert.match(html, /频率: quarterly/);
  assert.match(html, /当前: 48 USD\/unit/);
  assert.match(html, /模型: 50 USD\/unit/);
  assert.match(html, /单元格: Drivers!F18/);
  assert.match(html, /下次: 2026-09-30/);
  assert.match(html, /里程碑: 2026-10-15/);
  assert.match(html, /触发: below 42 USD\/unit/);
  assert.match(html, /动作: re-underwrite price path/);
  assert.match(html, /负责人: analyst/);
});


test("legacy weights are names-only compatibility metadata, never a reasoning chart", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView(null, {
    mechanism_weights: { "capacity-ramp": 0.75, "orders-backlog": 0.25 },
  });
  assert.match(html, /历史拆分元数据/);
  assert.match(html, /仅用于兼容旧快照/);
  assert.match(html, /capacity-ramp/);
  assert.match(html, /orders-backlog/);
  assert.doesNotMatch(html, /机制权重|75%|25%|mech-track|mech-fill/);
});


test("backend legacy adapter exposes component names without numeric weights", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView({
    contract_version: "legacy-v1",
    mode: "legacy_decomposition",
    legacy: true,
    main_line: { carrier_node_ids: [], target_node_ids: [], thesis_carriers: [] },
    investment_case: { one_line_thesis: "Legacy thesis" },
    value_creation: {},
    valuation: { summary: { fair_value: { base: 100 } }, methods: {} },
    market_implied_expectations: { implied_revenue: 100 },
    legacy_decomposition: {
      label: "legacy decomposition metadata",
      components: ["capacity-utilization-yield", "orders-backlog-recognition"],
      company_lenses: ["lens-equipment-process-control"],
    },
  }, {});
  assert.match(html, /capacity-utilization-yield/);
  assert.match(html, /orders-backlog-recognition/);
  assert.doesNotMatch(html, /75%|25%|0\.75|0\.25/);
});


test("model-view text is escaped", () => {
  const { renderForecastModelView } = require(APP);
  const html = renderForecastModelView({
    version: "v2",
    main_line: {
      name: '<img src=x onerror="alert(1)">',
      carrier_node_ids: ["units"],
      target_node_ids: ["profit"],
      falsification_ids: ["break"],
      competitor_response_node_ids: ["response"],
    },
  }, {});
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
});


test("v10 reference-scenario valuation renders the reference value, not a bear/base/bull range", () => {
  const { referenceValuationHtml } = require(APP);
  const v = {
    current_price: 194.94,
    price_currency: "USD",
    valuation_note: "Reference DCF only; alternatives are explicit but intentionally unvalued.",
    fair_value: { bear: null, base: null, bull: null },
    reference_scenario_id: "reference_ai_ramp",
    reference_fair_value: 85.8339068124985,
    fair_value_by_scenario_id: { reference_ai_ramp: 85.8339068124985 },
    not_valued_scenario_ids: [
      "qualification_and_competitive_delay",
      "broader_program_acceleration",
    ],
    market_implied: {
      observed_price: 194.94,
      named_driver: "FY2031 revenue at reference FCF margin",
      implied_driver_value: 71233.23251373842,
      model_driver_value: 27000,
      unit: "USD_millions",
    },
    action: "watch",
    one_line_thesis: "Operating upside is substantial.",
  };
  const html = referenceValuationHtml(v, 194.94);

  // No synthesized scenario range: the bear ("悲观") framing must be absent.
  assert.doesNotMatch(html, /悲观/);
  // Reference framing and the deliberately-unvalued line are present.
  assert.match(html, /参考情景/);
  assert.match(html, /刻意未估值/);
  // Reference fair value and the humanized scenario id (underscores -> spaces).
  assert.match(html, /\$85\.83/);
  assert.match(html, /reference ai ramp/);
  // Market-implied gap: named driver, implied vs model value, unit.
  assert.match(html, /FY2031 revenue at reference FCF margin/);
  assert.match(html, /71,233/);
  assert.match(html, /27,000/);
  assert.match(html, /USD_millions/);
  // The unvalued scenarios are listed in human-readable form.
  assert.match(html, /qualification and competitive delay/);
});


test("method pipeline is rendered from the canonical skill map", () => {
  const source = fs.readFileSync(APP, "utf8");
  for (const oldText of ["9+1 机制模块", "8 行业透镜", "机制权重"]) {
    assert.doesNotMatch(source, new RegExp(oldText.replace(/[+]/g, "\\+")));
  }
  assert.match(source, /skillMap\.stages\.map/);
  assert.match(source, /当前证据持续进入直到发布冻结/);
  assert.doesNotMatch(source, /const PIPE_SVG/);
});
