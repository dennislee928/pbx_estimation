import test from "node:test";
import assert from "node:assert/strict";
import { handleRagRequest } from "../src/worker.js";

const alternatives = [
  {
    name: "MQTT (MQTT-SN)",
    category: "web",
    medium: "ethernet_ip",
    protocols: "MQTT; MQTT-SN",
    use_case: "IoT edge device command/control, sensor telemetry, distributed relay triggering across many devices",
    industry_fit: "Smart building; Facilities; Hospitality; Retail",
    security: "TLS 1.2/1.3",
    cost_model: "Very Low; platform/broker plus usage",
  },
  {
    name: "Dry Contact / Relay Closure",
    category: "non_web",
    medium: "electrical_contact",
    protocols: "GPIO; Relay",
    use_case: "Door release, paging amplifier trigger, siren activation",
    industry_fit: "Smart building; Facilities; Hospitality; Retail",
    security: "Physical security only",
    cost_model: "Very Low",
  },
];

const solutions = [
  {
    name: "Twilio Programmable Voice",
    vendor: "Twilio",
    tags: "cpaas, api, voice",
    description: "Programmable voice API platform for building calling and event workflows.",
    industry_fit: "Contact center; Retail",
    cost_band: "Usage-based: per minute/API event",
  },
  {
    name: "Grandstream UCM Series",
    vendor: "Grandstream",
    tags: "ip_pbx, appliance, sip, fxs",
    description: "IP PBX appliance for SMB voice and facility deployments.",
    industry_fit: "SMB; Hospitality; Retail",
    cost_band: "Medium",
  },
];

test("ranks matching alternatives and solutions", async () => {
  const result = await handleRagRequest({
    scene: "hotel door relay low cost",
    alternatives,
    solutions,
    crawler_seed_context: {
      known_solution_count: 156,
      known_country_region_count: 42,
      known_alternative_count: 106,
      known_vendor_count: 126,
    },
  }, { USE_WORKERS_AI: "false" });

  assert.equal(result.alternatives[0].name, "Dry Contact / Relay Closure");
  assert.ok(result.alternatives[0].suitability_percent >= 55);
  assert.equal(result.alternatives[0].cost, "Very Low");
  assert.ok(result.alternatives[0].risk_level);
  assert.ok(Array.isArray(result.alternatives[0].pros));
  assert.ok(Array.isArray(result.alternatives[0].cons));
  assert.equal(result.alternatives[0].transport_label, "乾接點 / 繼電器（實體有線）");
  assert.equal(result.alternatives[0].primary_bearer, "electrical_contact");
  assert.ok(result.solutions.some((item) => item.name === "Grandstream UCM Series"));
  assert.ok(result.solutions.every((item) => item.transport_label));
  assert.ok(result.rag_response_table.some((item) => item.type === "alternative" && item.name === "Dry Contact / Relay Closure"));
  assert.ok(result.tables.alternatives.every((item) => item.label));
  assert.equal(result.evidence.crawler_seed_counts.known_solution_count, 156);
  assert.match(result.recommendation, /hotel door relay low cost/);
  assert.match(result.recommendation, /fit/);
});

test("excludes ethernet/IP transports when the scene forbids them", async () => {
  const result = await handleRagRequest({
    scene: "我有30台edge device跟5000台terminal device，不可以用乙太網路/乙太網路線/傳統類比電話線，對edge device下開關網路的命令",
    alternatives,
    solutions,
  }, { USE_WORKERS_AI: "false" });

  // No ethernet_ip alternative may survive the exclusion filter.
  assert.equal(result.alternatives.some((item) => item.name === "MQTT (MQTT-SN)"), false);
  // The dry-contact (electrical) option is still allowed.
  assert.equal(result.alternatives.some((item) => item.name === "Dry Contact / Relay Closure"), true);
  assert.equal(result.alternatives.find((item) => item.name === "Dry Contact / Relay Closure").transport_label, "乾接點 / 繼電器（實體有線）");
  // The constraint is reported back in the evidence.
  assert.ok(result.evidence.excluded_transport_tokens.includes("ethernet_ip"));
  assert.ok(result.evidence.excluded_constraints.length > 0);
});

test("falls back to deterministic prose if the LLM names an excluded product", async () => {
  // Mock Workers AI that hallucinates an excluded ethernet_ip option.
  const env = {
    USE_WORKERS_AI: "true",
    AI: {
      async run() {
        return { response: "建議使用 MQTT (MQTT-SN) 透過乙太網路傳輸。" };
      },
    },
  };
  const result = await handleRagRequest({
    scene: "不可以用乙太網路，對 edge device 下開關命令",
    alternatives,
    solutions,
  }, env);
  // The hallucinated excluded product must not appear in the recommendation.
  assert.equal(/MQTT \(MQTT-SN\)/.test(result.recommendation), false);
  // And no ethernet_ip alternative is returned.
  assert.equal(result.alternatives.some((item) => item.name === "MQTT (MQTT-SN)"), false);
});

test("excludes analog/TDM solutions even on truncated/partial phrasing (類比電話)", async () => {
  const legacy = [
    { name: "Nortel BCM / CS1000", vendor: "Avaya", tags: "tdm, digital, fxs", description: "Legacy TDM PBX." },
    { name: "emnify IoT eSIM", vendor: "emnify", tags: "iot, esim, api, cellular", description: "Cellular IoT connectivity." },
  ];
  const result = await handleRagRequest({
    // Note: truncated like the UI ("傳統類比電話", no 線) and a forbidden ethernet too.
    scene: "5000 edge devices 不可以用乙太網路/傳統類比電話 下命令",
    alternatives,
    solutions: legacy,
  }, { USE_WORKERS_AI: "false" });
  assert.ok(result.evidence.excluded_transport_tokens.includes("analog"));
  assert.equal(result.solutions.some((s) => s.name === "Nortel BCM / CS1000"), false);
  // The cellular IoT solution is still allowed.
  assert.equal(result.solutions.some((s) => s.name === "emnify IoT eSIM"), true);
});

test("does not exclude transports that are merely mentioned positively", async () => {
  const result = await handleRagRequest({
    scene: "use ethernet IP for hotel door relay low cost",
    alternatives,
    solutions,
  }, { USE_WORKERS_AI: "false" });
  assert.equal(result.evidence.excluded_transport_tokens.length, 0);
});

test("keeps API capability separate from an eSIM wireless bearer", async () => {
  const esim = [{
    name: "1NCE IoT eSIM",
    tags: "iot, esim, api, cellular",
    description: "IoT cellular connectivity and eSIM fleet management.",
    primary_bearer: "cellular_esim",
    bearer_family: "cellular",
    link_mode: "wireless",
    network_type: "ip",
    bearers: ["cellular_esim"],
    control_interfaces: ["api"],
    api_capable: true,
    hybrid: false,
    transport_schema_version: 2,
    transport_label_en: "Cellular / eSIM (wireless)",
    transport_label_zh: "蜂巢 / eSIM（無線）",
    capability_labels_en: ["API management"],
    capability_labels_zh: ["API 管理"],
  }];
  const result = await handleRagRequest({ scene: "IoT eSIM API device fleet", alternatives: [], solutions: esim }, { USE_WORKERS_AI: "false" });
  assert.equal(result.solutions[0].link_mode, "wireless");
  assert.equal(result.solutions[0].transport_label, "蜂巢 / eSIM（無線）");
  assert.deepEqual(result.solutions[0].control_interfaces, ["api"]);
});

test("empty scene returns empty ranks", async () => {
  const result = await handleRagRequest({ scene: "", alternatives, solutions }, { USE_WORKERS_AI: "false" });
  assert.deepEqual(result.alternatives, []);
  assert.deepEqual(result.solutions, []);
});

test("loads catalog and documents from bucket context", async () => {
  const objects = new Map([
    ["latest/rag_engine/dist/rag_assets_manifest.json", {
      asset_count: 4,
      assets: [
        {
          path: "reports/global_research_report_zh.md",
          key: "latest/reports/global_research_report_zh.md",
          content_type: "text/markdown",
          sha256: "abc",
        },
      ],
    }],
    ["latest/frontend/data/awesome_list.json", alternatives],
    ["latest/frontend/data/solution_registry.json", solutions],
    ["latest/frontend/data/crawler_seed_context.json", {
      known_solution_count: 156,
      known_country_region_count: 42,
      known_alternative_count: 106,
      known_vendor_count: 126,
    }],
    ["latest/reports/global_research_report_zh.md", "hotel door relay dry contact hospitality evidence"],
  ]);
  const env = {
    USE_WORKERS_AI: "false",
    RAG_ASSET_PREFIX: "latest",
    RAG_ASSETS: {
      async get(key) {
        const value = objects.get(key);
        if (value === undefined) return null;
        return {
          async json() {
            return value;
          },
          async text() {
            return typeof value === "string" ? value : JSON.stringify(value);
          },
        };
      },
    },
  };

  const result = await handleRagRequest({ scene: "hotel door relay" }, env);
  assert.equal(result.alternatives[0].name, "Dry Contact / Relay Closure");
  assert.equal(result.documents[0].name, "reports/global_research_report_zh.md");
  assert.equal(result.evidence.asset_manifest_count, 4);
  assert.equal(result.evidence.crawler_seed_counts.known_vendor_count, 126);
});

test("resolves an immutable catalog snapshot through latest-pointer.json", async () => {
  const objects = new Map([
    ["latest-pointer.json", { asset_prefix: "snapshots/run-42", catalog_snapshot_id: "run-42" }],
    ["snapshots/run-42/rag_engine/dist/rag_assets_manifest.json", { transport_schema_version: 2, catalog_snapshot_id: "run-42", asset_count: 2, assets: [] }],
    ["snapshots/run-42/frontend/data/awesome_list.json", alternatives],
    ["snapshots/run-42/frontend/data/solution_registry.json", solutions],
    ["snapshots/run-42/frontend/data/crawler_seed_context.json", {}],
  ]);
  const env = {
    USE_WORKERS_AI: "false",
    RAG_ASSET_PREFIX: "latest",
    RAG_ASSETS: {
      async get(key) {
        const value = objects.get(key);
        if (value === undefined) return null;
        return { async json() { return value; }, async text() { return JSON.stringify(value); } };
      },
    },
  };
  const result = await handleRagRequest({ scene: "hotel door relay" }, env);
  assert.equal(result.evidence.catalog_snapshot_id, "run-42");
  assert.equal(result.evidence.transport_schema_version, 2);
});
