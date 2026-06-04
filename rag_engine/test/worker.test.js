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

test("empty scene returns empty ranks", async () => {
  const result = await handleRagRequest({ scene: "", alternatives, solutions }, { USE_WORKERS_AI: "false" });
  assert.deepEqual(result.alternatives, []);
  assert.deepEqual(result.solutions, []);
});
