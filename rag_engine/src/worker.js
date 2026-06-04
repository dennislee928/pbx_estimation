const MAX_ALTERNATIVES = 160;
const MAX_SOLUTIONS = 240;
const MAX_DOCUMENTS = 80;
const TOP_K = 8;
const TEXT_ASSET_EXTENSIONS = [".md", ".txt", ".csv", ".json", ".jsonl", ".html"];

const FIELD_WEIGHTS = {
  name: 7,
  vendor: 5,
  category: 3,
  medium: 4,
  protocols: 5,
  lifecycle_assigned: 3,
  tags: 4,
  description: 3,
  use_case: 7,
  industry_fit: 5,
  typical_customers: 3,
  reliability: 2,
  security: 3,
  latency: 3,
  cost_model: 3,
  cost_band: 3,
  recommended_devices: 2,
  recommended_terminals: 2,
  pros: 2,
  cons: 1,
};

const SCENE_EXPANSIONS = [
  {
    keys: ["door", "lock", "access", "hotel", "門", "門禁", "飯店", "開門"],
    terms: ["door", "lock", "access", "relay", "dry contact", "osdp", "wiegand", "building", "hospitality", "hotel"],
  },
  {
    keys: ["alarm", "siren", "security", "警報", "保全", "告警"],
    terms: ["alarm", "siren", "security", "contact id", "sia", "cap", "relay", "monitoring"],
  },
  {
    keys: ["factory", "plc", "scada", "industrial", "工廠", "產線", "plc"],
    terms: ["plc", "scada", "modbus", "opc", "profinet", "ethercat", "industrial", "automation"],
  },
  {
    keys: ["remote", "rural", "farm", "cellular", "遠端", "農場", "偏遠"],
    terms: ["lorawan", "cellular", "nb-iot", "lte-m", "satellite", "esim", "remote", "agriculture"],
  },
  {
    keys: ["audit", "queue", "retry", "稽核", "重送", "佇列"],
    terms: ["amqp", "rabbitmq", "kafka", "redis", "nats", "webhook", "audit", "retry", "queue", "durable"],
  },
  {
    keys: ["teams", "ucaas", "cloud", "call", "客服", "雲端", "電話"],
    terms: ["cloud", "ucaas", "cpaas", "api", "voice", "sip", "contact center", "teams"],
  },
];

const CORS_HEADERS = {
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Max-Age": "86400",
};

function jsonResponse(body, status = 200, env = {}, request = undefined) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders(env, request),
    },
  });
}

function corsHeaders(env = {}, request = undefined) {
  const configured = String(env.ALLOWED_ORIGINS || "*");
  const origin = request?.headers?.get("Origin") || "";
  const allowOrigin = configured === "*" || configured.split(",").map((item) => item.trim()).includes(origin)
    ? (configured === "*" ? "*" : origin)
    : configured.split(",")[0].trim();
  return {
    ...CORS_HEADERS,
    "Access-Control-Allow-Origin": allowOrigin || "*",
  };
}

function normalizeText(value) {
  if (Array.isArray(value)) return value.map(normalizeText).join(" ");
  if (value && typeof value === "object") return Object.values(value).map(normalizeText).join(" ");
  return String(value || "").toLowerCase();
}

function tokenize(value) {
  return normalizeText(value)
    .replace(/[^\p{L}\p{N}+#.-]+/gu, " ")
    .split(/\s+/)
    .filter((token) => token.length >= 2);
}

function expandedQuery(scene) {
  const base = tokenize(scene);
  const text = normalizeText(scene);
  const extra = [];
  for (const expansion of SCENE_EXPANSIONS) {
    if (expansion.keys.some((key) => text.includes(normalizeText(key)))) {
      extra.push(...expansion.terms);
    }
  }
  return [...new Set([...base, ...tokenize(extra.join(" "))])];
}

function asRows(value, maxRows) {
  return Array.isArray(value) ? value.filter((row) => row && typeof row === "object").slice(0, maxRows) : [];
}

function assetPrefix(env = {}) {
  return String(env.RAG_ASSET_PREFIX || "latest").replace(/^\/+|\/+$/g, "");
}

async function readJsonAsset(env, key) {
  if (!env?.RAG_ASSETS) return undefined;
  const object = await env.RAG_ASSETS.get(key);
  if (!object) return undefined;
  return object.json();
}

async function readTextAsset(env, key, maxChars = 8000) {
  if (!env?.RAG_ASSETS) return "";
  const object = await env.RAG_ASSETS.get(key);
  if (!object) return "";
  const text = await object.text();
  return text.slice(0, maxChars);
}

async function loadBucketContext(env) {
  const prefix = assetPrefix(env);
  const manifest = await readJsonAsset(env, `${prefix}/rag_engine/dist/rag_assets_manifest.json`);
  const alternatives = await readJsonAsset(env, `${prefix}/frontend/data/awesome_list.json`);
  const solutions = await readJsonAsset(env, `${prefix}/frontend/data/solution_registry.json`);
  const crawlerSeed = await readJsonAsset(env, `${prefix}/frontend/data/crawler_seed_context.json`);
  const documents = [];

  for (const asset of manifest?.assets || []) {
    if (documents.length >= MAX_DOCUMENTS) break;
    const path = String(asset.path || "");
    if (!TEXT_ASSET_EXTENSIONS.some((extension) => path.endsWith(extension))) continue;
    if (!path.startsWith("reports/") && !path.startsWith("data/processed/")) continue;
    const content = await readTextAsset(env, asset.key);
    if (content) {
      documents.push({
        name: path,
        path,
        key: asset.key,
        content,
        content_type: asset.content_type,
        sha256: asset.sha256,
      });
    }
  }
  return { manifest, alternatives, solutions, crawlerSeed, documents };
}

function weightedText(row) {
  return Object.entries(FIELD_WEIGHTS)
    .map(([field, weight]) => normalizeText(row[field]).repeat(weight))
    .join(" ");
}

function scoreRow(scene, row) {
  const queryTerms = expandedQuery(scene);
  if (!queryTerms.length) return 0;
  const text = weightedText(row);
  let score = 0;
  for (const term of queryTerms) {
    if (text.includes(term)) score += 8 + Math.min(12, term.length);
    if (normalizeText(row.name).includes(term)) score += 14;
    if (normalizeText(row.use_case).includes(term)) score += 12;
    if (normalizeText(row.industry_fit).includes(term)) score += 10;
    if (normalizeText(row.protocols).includes(term)) score += 10;
  }
  const sceneText = normalizeText(scene);
  if (/low|cheap|cost|便宜|低成本/.test(sceneText) && /low|very low|低|usage|subscription/.test(text)) score += 18;
  if (/secure|security|tls|encrypt|安全|加密/.test(sceneText) && /tls|aes|mtls|oauth|secure|encryption|加密/.test(text)) score += 18;
  if (/fast|latency|real.?time|即時|低延遲/.test(sceneText) && /<\s?(1|5|10|50|100)ms|real-time|low latency/i.test(text)) score += 18;
  if (/audit|稽核/.test(sceneText) && /queue|retry|log|audit|durable|acknowledgement|dead-letter/.test(text)) score += 18;
  return score;
}

function splitList(value) {
  if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean);
  return String(value || "").split(";").map((item) => item.trim()).filter(Boolean);
}

function suitabilityPercent(score, rank) {
  return Math.max(35, Math.min(98, Math.round(42 + score * 0.75 - (rank - 1) * 4)));
}

function riskProfile(row) {
  const text = normalizeText(row);
  const risks = [];
  let level = "Low";
  if (/physical security only|none natively|no native encryption|no identity/.test(text)) {
    risks.push("Requires physical security, gateway authentication, or compensating controls.");
    level = "Medium";
  }
  if (/high|very high|scada|private 5g|satellite|iec 61850|engineering/.test(text)) {
    risks.push("Higher deployment complexity or specialist engineering may be required.");
    level = "High";
  }
  if (/subscription|usage|carrier|roaming|message\/device/.test(text)) {
    risks.push("Recurring service fees or provider coverage constraints may apply.");
    if (level === "Low") level = "Medium";
  }
  if (/rf|radio|wifi|cellular|satellite|licensed spectrum|interference/.test(text)) {
    risks.push("Wireless coverage, interference, or regulatory constraints must be validated on site.");
    if (level === "Low") level = "Medium";
  }
  if (!risks.length) risks.push("Main risk is validating local device compatibility and operational monitoring.");
  return { level, reasons: risks.slice(0, 3) };
}

function recommendationSummary(scene, row, kind, suitability, risk) {
  const name = row.name || row.vendor || "option";
  const cost = row.cost_model || row.cost_band || row.cost || "not specified";
  const fit = row.industry_fit || row.typical_customers || "general deployments";
  const useCase = row.use_case || row.description || "the requested scene";
  return `${name} is a ${suitability}% fit for "${scene}" because it maps to ${useCase}. Cost profile: ${cost}. Best fit: ${fit}. Risk level: ${risk.level}.`;
}

function enrichRankedItem(scene, row, score, rank, kind) {
  const risk = riskProfile(row);
  const suitability = suitabilityPercent(score, rank);
  const pros = splitList(row.pros).slice(0, 4);
  const cons = splitList(row.cons).slice(0, 4);
  return {
    name: row.name,
    rank,
    score: Math.round(score),
    suitability_percent: suitability,
    cost: row.cost_model || row.cost_band || row.cost || "",
    risk_level: risk.level,
    risk_reasons: risk.reasons,
    pros: pros.length ? pros : ["Matches retrieved catalog evidence for the requested scene."],
    cons: cons.length ? cons : ["Requires validation against local device support, integration path, and operations."],
    reason: makeReason(scene, row, kind),
    recommendation: recommendationSummary(scene, row, kind, suitability, risk),
    resource_url: row.resource_url || "",
  };
}

function rankRows(scene, rows, kind) {
  return rows
    .map((row) => ({ row, score: scoreRow(scene, row) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || normalizeText(a.row.name).localeCompare(normalizeText(b.row.name)))
    .slice(0, TOP_K)
    .map((item, index) => enrichRankedItem(scene, item.row, item.score, index + 1, kind));
}

function rankDocuments(scene, documents) {
  return documents
    .map((document) => ({
      document,
      score: scoreRow(scene, {
        name: document.name,
        description: document.content,
        use_case: document.content,
        industry_fit: document.content,
        protocols: document.content,
      }),
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || normalizeText(a.document.name).localeCompare(normalizeText(b.document.name)))
    .slice(0, TOP_K)
    .map((item, index) => ({
      name: item.document.name,
      rank: index + 1,
      score: Math.round(item.score),
      key: item.document.key,
      reason: `Retrieved supporting report/data asset for "${scene}" from ${item.document.path}.`,
      excerpt: item.document.content.replace(/\s+/g, " ").slice(0, 260),
    }));
}

function makeReason(scene, row, kind) {
  const parts = [];
  if (row.use_case) parts.push(`use case: ${row.use_case}`);
  if (row.industry_fit) parts.push(`industry fit: ${row.industry_fit}`);
  if (row.protocols) parts.push(`protocols: ${row.protocols}`);
  if (row.security) parts.push(`security: ${row.security}`);
  if (row.cost_model || row.cost_band) parts.push(`cost: ${row.cost_model || row.cost_band}`);
  if (!parts.length && row.description) parts.push(row.description);
  const prefix = kind === "solution" ? "Matches the solution scene" : "Matches the alternative control path";
  return `${prefix} "${scene}" via ${parts.slice(0, 3).join("; ")}.`;
}

function deterministicRecommendation(scene, alternatives, solutions) {
  const topAlt = alternatives[0];
  const topSolution = solutions[0];
  if (!topAlt && !topSolution) return `No strong match found for "${scene}". Add more scene detail such as site type, device count, latency, cost, and security needs.`;
  const altText = topAlt ? `${topAlt.name} (${topAlt.suitability_percent}% fit, ${topAlt.risk_level} risk, cost: ${topAlt.cost || "not specified"})` : "no strong alternative match";
  const solText = topSolution ? `${topSolution.name} (${topSolution.suitability_percent}% fit, ${topSolution.risk_level} risk, cost: ${topSolution.cost || "not specified"})` : "no strong solution match";
  return `For "${scene}", recommended path: ${altText}. Pair with: ${solText}. Review the ranked pros, cons, cost profile, suitability percentage, and risk reasons before deployment.`;
}

function buildAiPrompt(scene, alternatives, solutions) {
  const context = {
    scene,
    alternatives: alternatives.slice(0, 5),
    solutions: solutions.slice(0, 5),
  };
  return [
    "You are ranking PBX/UCaaS and PSTN replacement options for a deployment scene.",
    "Use only the retrieved JSON context. Do not invent products.",
    "Return one concise paragraph in Traditional Chinese if the scene contains Chinese, otherwise English.",
    JSON.stringify(context),
  ].join("\n");
}

async function aiRecommendation(env, scene, alternatives, solutions) {
  if (!env?.AI || String(env.USE_WORKERS_AI || "true") === "false") {
    return deterministicRecommendation(scene, alternatives, solutions);
  }
  try {
    const result = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
      messages: [
        { role: "system", content: "You are a concise cloud RAG recommender." },
        { role: "user", content: buildAiPrompt(scene, alternatives, solutions) },
      ],
      max_tokens: 180,
    });
    return result?.response || result?.result?.response || deterministicRecommendation(scene, alternatives, solutions);
  } catch (error) {
    return `${deterministicRecommendation(scene, alternatives, solutions)} Workers AI fallback reason: ${error.message}`;
  }
}

export async function handleRagRequest(payload, env = {}) {
  const scene = String(payload?.scene || "").trim();
  if (!scene) {
    return {
      recommendation: "Enter a scene before requesting cloud RAG prioritization.",
      alternatives: [],
      solutions: [],
    };
  }
  const bucketContext = await loadBucketContext(env);
  const alternativesInput = asRows(payload.alternatives, MAX_ALTERNATIVES).length
    ? asRows(payload.alternatives, MAX_ALTERNATIVES)
    : asRows(bucketContext.alternatives, MAX_ALTERNATIVES);
  const solutionsInput = asRows(payload.solutions, MAX_SOLUTIONS).length
    ? asRows(payload.solutions, MAX_SOLUTIONS)
    : asRows(bucketContext.solutions, MAX_SOLUTIONS);
  const documentsInput = asRows(payload.documents, MAX_DOCUMENTS).length
    ? asRows(payload.documents, MAX_DOCUMENTS)
    : asRows(bucketContext.documents, MAX_DOCUMENTS);
  const crawlerSeed = payload?.crawler_seed_context || bucketContext.crawlerSeed || {};
  const alternatives = rankRows(scene, alternativesInput, "alternative");
  const solutions = rankRows(scene, solutionsInput, "solution");
  const documents = rankDocuments(scene, documentsInput);
  const recommendation = await aiRecommendation(env, scene, alternatives, solutions);
  return {
    recommendation,
    alternatives,
    solutions,
    documents,
    evidence: {
      scene,
      alternatives_considered: alternativesInput.length,
      solutions_considered: solutionsInput.length,
      documents_considered: documentsInput.length,
      asset_manifest_count: bucketContext.manifest?.asset_count,
      crawler_seed_counts: {
        known_solution_count: crawlerSeed.known_solution_count,
        known_country_region_count: crawlerSeed.known_country_region_count,
        known_alternative_count: crawlerSeed.known_alternative_count,
        known_vendor_count: crawlerSeed.known_vendor_count,
      },
    },
  };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(env, request) });
    }

    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return jsonResponse({ ok: true, service: "pbx-rag-engine" }, 200, env, request);
    }

    if (request.method === "GET" && url.pathname === "/assets/manifest") {
      const manifest = await readJsonAsset(env, `${assetPrefix(env)}/rag_engine/dist/rag_assets_manifest.json`);
      return jsonResponse(manifest || { assets: [], asset_count: 0 }, 200, env, request);
    }

    if (request.method !== "POST") {
      return jsonResponse({ error: "Use POST / with a JSON body." }, 405, env, request);
    }

    try {
      const payload = await request.json();
      const body = await handleRagRequest(payload, env);
      return jsonResponse(body, 200, env, request);
    } catch (error) {
      return jsonResponse({ error: error.message || String(error) }, 400, env, request);
    }
  },
};
