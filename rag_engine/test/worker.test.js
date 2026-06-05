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
  assert.ok(result.solutions.some((item) => item.name === "Grandstream UCM Series"));
  assert.equal(result.evidence.crawler_seed_counts.known_solution_count, 156);
  assert.match(result.recommendation, /hotel door relay low cost/);
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
  // The constraint is reported back in the evidence.
  assert.ok(result.evidence.excluded_transport_tokens.includes("ethernet_ip"));
  assert.ok(result.evidence.excluded_constraints.length > 0);
});

test("does not exclude transports that are merely mentioned positively", async () => {
  const result = await handleRagRequest({
    scene: "use ethernet IP for hotel door relay low cost",
    alternatives,
    solutions,
  }, { USE_WORKERS_AI: "false" });
  assert.equal(result.evidence.excluded_transport_tokens.length, 0);
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
