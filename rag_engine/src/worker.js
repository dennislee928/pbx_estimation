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

// Maps a constraint phrase (zh/en) to the canonical transport tokens that must
// be excluded. Tokens are matched against a row's medium/protocols/standards/
// description so "不可以用乙太網路" drops every ethernet/IP option, etc.
const TRANSPORT_EXCLUSIONS = [
  { keys: ["乙太網路線", "網路線", "ethernet cable", "ethernet wire", "rj45", "rj-45", "lan cable"], tokens: ["ethernet_wire", "ethernet", "rj45", "lan"] },
  { keys: ["乙太網路", "ethernet", "ip網路", "ip network", "區域網路"], tokens: ["ethernet", "ethernet_ip", "ethernet_wire", "serial_ethernet", "lan"] },
  { keys: ["類比電話線", "傳統電話線", "電話線", "類比線路", "analog phone", "analogue phone", "analog line", "pstn line", "copper line", "pots"], tokens: ["analog", "analogue", "pstn", "pots", "fxs", "fxo", "tdm", "copper", "phone_line"] },
  { keys: ["pstn", "傳統電話網路", "public switched"], tokens: ["pstn", "pots", "tdm", "analog"] },
  { keys: ["wifi", "wi-fi", "無線網路", "無線區域網路", "wlan"], tokens: ["wifi", "wifi_direct", "wlan", "802.11"] },
  { keys: ["蜂巢", "行動網路", "cellular", "lte", "5g", "4g", "nb-iot", "lte-m", "sim卡"], tokens: ["cellular", "cellular_ip", "cellular_lpwans", "cellular_esim", "private_cellular", "cellular_broadcast", "lte", "5g", "nb-iot"] },
  { keys: ["衛星", "satellite"], tokens: ["satellite", "satellite_navigation"] },
  { keys: ["序列", "serial", "rs-232", "rs232", "rs-485", "rs485"], tokens: ["serial_wire", "serial_ethernet", "rs-232", "rs-485", "modbus"] },
  { keys: ["藍牙", "bluetooth", "ble"], tokens: ["bluetooth", "ble", "radio_802_15_4"] },
  { keys: ["紅外線", "infrared"], tokens: ["infrared", "optical_signal"] },
];

// Phrase fragments that signal a *negation* in the scene text. If one appears
// within a short window before a transport keyword, that transport is excluded.
const NEGATION_MARKERS = [
  "不可以用", "不可以", "不能用", "不能", "不可", "不使用", "不要用", "不要", "不得", "禁用", "禁止", "避免", "排除", "無法使用", "沒有",
  "cannot use", "can not use", "can't use", "cannot", "can't", "without", "no ", "not ", "avoid", "exclude", "excluding", "ban", "prohibit", "must not", "don't use", "do not use",
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

// Parse negative transport constraints out of the scene text. Returns the set
// of canonical transport tokens the user said NOT to use, plus the human-
// readable constraint phrases for surfacing in the response evidence.
function parseExclusions(scene) {
  const text = normalizeText(scene);
  const tokens = new Set();
  const phrases = new Set();
  for (const group of TRANSPORT_EXCLUSIONS) {
    for (const key of group.keys) {
      const needle = normalizeText(key);
      let from = 0;
      let idx = text.indexOf(needle, from);
      while (idx !== -1) {
        // Look back a small window for a negation marker. CJK has no spaces,
        // so a 12-char window covers "不可以用乙太網路" style phrasing.
        const windowStart = Math.max(0, idx - 12);
        const before = text.slice(windowStart, idx);
        if (NEGATION_MARKERS.some((marker) => before.includes(normalizeText(marker)))) {
          group.tokens.forEach((token) => tokens.add(token));
          phrases.add(key);
          break;
        }
        from = idx + needle.length;
        idx = text.indexOf(needle, from);
      }
    }
  }
  return { tokens: [...tokens], phrases: [...phrases] };
}

// True if a catalog row relies on an excluded transport. Checks the structured
// transport fields first, then falls back to description text.
function isExcludedRow(row, exclusionTokens) {
  if (!exclusionTokens.length) return false;
  const transportText = normalizeText([
    row.medium,
    row.protocols,
    row.standards,
    row.category,
    row.description,
  ].join(" "));
  return exclusionTokens.some((token) => transportText.includes(normalizeText(token)));
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

function rankRows(scene, rows, kind, exclusionTokens = []) {
  return rows
    .filter((row) => !isExcludedRow(row, exclusionTokens))
    .map((row) => ({ row, score: scoreRow(scene, row) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || normalizeText(a.row.name).localeCompare(normalizeText(b.row.name)))
    .slice(0, TOP_K)
    .map((item, index) => ({
      name: item.row.name,
      rank: index + 1,
      score: Math.round(item.score),
      reason: makeReason(scene, item.row, kind),
      resource_url: item.row.resource_url || "",
    }));
}

function rankDocuments(scene, documents, exclusionTokens = []) {
  return documents
    .filter((document) => !isExcludedRow({ description: document.content, name: document.name }, exclusionTokens))
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
  const altNames = alternatives.slice(0, 3).map((item) => item.name).join(", ") || "no strong alternative match";
  const solNames = solutions.slice(0, 3).map((item) => item.name).join(", ") || "no strong solution match";
  return `For "${scene}", prioritize alternatives: ${altNames}. Pair with solutions: ${solNames}. Ranking is based on retrieved protocol, use-case, industry, security, latency, and cost evidence from the submitted catalog.`;
}

function buildAiPrompt(scene, alternatives, solutions, exclusions = { phrases: [] }) {
  const context = {
    scene,
    excluded_constraints: exclusions.phrases,
    alternatives: alternatives.slice(0, 5),
    solutions: solutions.slice(0, 5),
  };
  return [
    "You are ranking PBX/UCaaS and PSTN replacement options for a deployment scene.",
    "Use only the retrieved JSON context. Do not invent products.",
    "The context has already removed any option that uses an excluded transport.",
    "NEVER recommend or mention any transport listed in excluded_constraints; if a candidate would require one, drop it.",
    "Return one concise paragraph in Traditional Chinese if the scene contains Chinese, otherwise English.",
    JSON.stringify(context),
  ].join("\n");
}

async function aiRecommendation(env, scene, alternatives, solutions, exclusions = { phrases: [] }) {
  if (!env?.AI || String(env.USE_WORKERS_AI || "true") === "false") {
    return deterministicRecommendation(scene, alternatives, solutions);
  }
  try {
    const result = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
      messages: [
        { role: "system", content: "You are a concise cloud RAG recommender." },
        { role: "user", content: buildAiPrompt(scene, alternatives, solutions, exclusions) },
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
  const exclusions = parseExclusions(scene);
  const alternatives = rankRows(scene, alternativesInput, "alternative", exclusions.tokens);
  const solutions = rankRows(scene, solutionsInput, "solution", exclusions.tokens);
  const documents = rankDocuments(scene, documentsInput, exclusions.tokens);
  const recommendation = await aiRecommendation(env, scene, alternatives, solutions, exclusions);
  return {
    recommendation,
    alternatives,
    solutions,
    documents,
    evidence: {
      scene,
      excluded_constraints: exclusions.phrases,
      excluded_transport_tokens: exclusions.tokens,
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
