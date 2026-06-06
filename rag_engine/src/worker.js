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
  { keys: ["類比電話線", "傳統電話線", "傳統電話", "類比電話", "類比線路", "類比", "電話線", "市話", "analog phone", "analogue phone", "analog line", "analog", "analogue", "pstn line", "copper line", "pots", "landline"], tokens: ["analog", "analogue", "pstn", "pots", "fxs", "fxo", "tdm", "copper", "phone_line"] },
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

// Clause boundary: a negation's scope ends at the next sentence/clause break.
const CLAUSE_BOUNDARY = /[，,。.!！?？;；:：\n]/;
// How far forward a negation can reach when no boundary is hit first.
const NEGATION_FORWARD_WINDOW = 60;

// Parse negative transport constraints out of the scene text. Returns the set
// of canonical transport tokens the user said NOT to use, plus the human-
// readable constraint phrases for surfacing in the response evidence.
//
// A negation governs the whole following clause, so a *list* like
// "不可以用 乙太網路/乙太網路線/傳統類比電話線" excludes ALL three items — not just
// the one nearest the marker. We therefore scan forward from each negation
// marker to the next clause boundary and match every transport keyword inside.
function parseExclusions(scene) {
  const text = normalizeText(scene);
  const tokens = new Set();
  const phrases = new Set();

  for (const marker of NEGATION_MARKERS) {
    const needle = normalizeText(marker);
    let from = 0;
    let idx = text.indexOf(needle, from);
    while (idx !== -1) {
      const start = idx + needle.length;
      let end = start;
      while (
        end < text.length &&
        end - start < NEGATION_FORWARD_WINDOW &&
        !CLAUSE_BOUNDARY.test(text[end])
      ) {
        end += 1;
      }
      const clause = text.slice(start, end);
      for (const group of TRANSPORT_EXCLUSIONS) {
        for (const key of group.keys) {
          if (clause.includes(normalizeText(key))) {
            group.tokens.forEach((token) => tokens.add(token));
            phrases.add(key);
          }
        }
      }
      from = idx + needle.length;
      idx = text.indexOf(needle, from);
    }
  }
  return { tokens: [...tokens], phrases: [...phrases] };
}

// Solutions in solution_registry.json carry no explicit transport `medium`,
// only category `tags`. We classify those tags into:
//   - IP-platform tags: the solution fundamentally requires IP/ethernet to run
//     (cloud/SIP/UCaaS/PBX). Forbidden when ethernet is excluded.
//   - analog tags: the solution rides the legacy TDM/analog network. Forbidden
//     when analog/PSTN is excluded.
//   - bearer tags: device-side non-ethernet connectivity (eSIM/cellular/
//     satellite) that legitimately satisfies a "no ethernet" constraint and so
//     RESCUES an otherwise IP-leaning solution.
// "api"/"sms"/"voice" are deliberately neutral: every modern platform exposes an
// API, and an incidental SMS channel does not make a cloud platform ethernet-free.
const IP_PLATFORM_TAGS = new Set([
  "cloud", "ucaas", "cpaas", "hosted", "ip_pbx", "sip", "voip", "webrtc",
  "telco", "h323", "sbc", "wholesale", "workspace", "messaging",
]);
const ANALOG_TAGS = new Set(["tdm", "digital", "fxs", "fxo", "analog", "pots", "pstn"]);
const BEARER_TRANSPORT = { esim: "cellular", cellular: "cellular", satellite: "satellite" };
const TRANSPORT_LABELS = {
  network_api_wired: "網路 / API（有線）",
  non_network_physical: "非網路 / 實體媒介",
};
const NON_NETWORK_MEDIA = new Set([
  "electrical_contact",
  "dry_contact",
  "relay",
  "gpio",
  "optical_signal",
  "infrared",
  "acoustic",
  "audio",
  "mechanical",
  "pneumatic",
  "hydraulic",
  "visual_code",
  "qr",
  "magnetic",
]);

function tagSet(tags) {
  return new Set(normalizeText(tags).split(/[^a-z0-9_]+/).filter(Boolean));
}

function transportClassification(row) {
  const medium = normalizeText(row.medium);
  const categoryTokens = tagSet(row.category);
  const protocols = normalizeText(row.protocols);
  const tags = tagSet(row.tags);
  const text = normalizeText([row.name, row.medium, row.category, row.protocols, row.tags, row.description].join(" "));

  const isPhysical =
    categoryTokens.has("non_web") ||
    [...NON_NETWORK_MEDIA].some((token) => medium.includes(token) || protocols.includes(token) || text.includes(token)) ||
    /\b(contact|relay|gpio|dry contact|mechanical|pneumatic|hydraulic|optical|infrared|acoustic|qr|barcode)\b/.test(text);

  const isNetworkOrApi =
    categoryTokens.has("web") ||
    /api|http|https|sip|graphql|webhook|webrtc|mqtt|amqp|tcp|ip|json|cloud|ucaas|cpaas|voice|subscription|callback/.test(text) ||
    [...tags].some((tag) => IP_PLATFORM_TAGS.has(tag) || tag === "api");

  if (isPhysical && !isNetworkOrApi) {
    return {
      transport_type: "non_network_physical",
      transport_label: TRANSPORT_LABELS.non_network_physical,
    };
  }

  return {
    transport_type: "network_api_wired",
    transport_label: TRANSPORT_LABELS.network_api_wired,
  };
}

// True if a catalog row relies on an excluded transport.
// - Alternatives: authoritative explicit `medium`, then a text fallback.
// - Solutions: classified from tags. A solution is excluded when its only
//   transport family (IP platform and/or analog) is forbidden AND it has no
//   allowed device-side bearer (cellular/eSIM/satellite) to fall back on.
function isExcludedRow(row, exclusionTokens) {
  if (!exclusionTokens.length) return false;
  const hits = (text) => exclusionTokens.some((token) => normalizeText(text).includes(normalizeText(token)));

  if (row.medium && hits(row.medium)) return true;

  const tags = tagSet(row.tags);
  if (tags.size) {
    // A non-excluded device-side bearer rescues the solution.
    const hasAllowedBearer = [...tags].some(
      (tag) => BEARER_TRANSPORT[tag] && !hits(BEARER_TRANSPORT[tag]),
    );
    if (!hasAllowedBearer) {
      const isIpPlatform = [...tags].some((tag) => IP_PLATFORM_TAGS.has(tag));
      const isAnalog = [...tags].some((tag) => ANALOG_TAGS.has(tag));
      if (isIpPlatform && (hits("ethernet") || hits("ethernet_ip"))) return true;
      if (isAnalog && (hits("analog") || hits("pstn") || hits("tdm"))) return true;
    }
  }

  // Fallback for rows without structured transport: scan remaining text fields.
  const transportText = [row.protocols, row.standards, row.category, row.description].join(" ");
  return hits(transportText);
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
      ...transportClassification(item.row),
      suitability_percent: suitabilityPercent(item.score),
      cost: item.row.cost_model || item.row.cost_band || "",
      risk_level: riskLevel(item.row),
      pros: splitList(item.row.pros).slice(0, 4),
      cons: splitList(item.row.cons).slice(0, 4),
      reason: makeReason(scene, item.row, kind),
      resource_url: item.row.resource_url || "",
    }));
}

function suitabilityPercent(score) {
  return Math.max(55, Math.min(98, Math.round(58 + Math.sqrt(Math.max(0, score)) * 3.1)));
}

function riskLevel(row) {
  const text = normalizeText([row.complexity, row.security, row.reliability, row.cons, row.tags, row.description].join(" "));
  if (/high|complex|specialist|regulatory|coverage|not all|overkill|internet-dependent|implementation required/.test(text)) return "High";
  if (/medium|subscription|usage|validation|varies|limited|cost extra|engineering/.test(text)) return "Medium";
  return "Low";
}

function splitList(value) {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  return String(value || "")
    .split(/\s*(?:;|\||\n)\s*/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function tableRows(kind, rows) {
  return rows.map((row) => ({
    type: kind,
    rank: row.rank,
    name: row.name,
    label: row.transport_label,
    transport_type: row.transport_type,
    suitability_percent: row.suitability_percent,
    score: row.score,
    cost: row.cost,
    risk_level: row.risk_level,
    pros: row.pros,
    cons: row.cons,
    reason: row.reason,
    resource_url: row.resource_url,
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

function buildAiPrompt(scene, alternatives, solutions, exclusions = { phrases: [] }, excludedNames = []) {
  const allowedNames = alternatives.map((item) => item.name);
  const context = {
    scene,
    excluded_constraints: exclusions.phrases,
    allowed_alternative_names: allowedNames,
    forbidden_product_names: excludedNames.slice(0, 30),
    alternatives: alternatives.slice(0, 5),
    solutions: solutions.slice(0, 5),
  };
  return [
    "You are ranking PBX/UCaaS and PSTN replacement options for a deployment scene.",
    "Use ONLY the products in allowed_alternative_names and solutions; do not invent products.",
    "The context already removed every option that uses an excluded transport.",
    "HARD RULE: never name, recommend, or mention anything in forbidden_product_names or any transport in excluded_constraints (e.g. ethernet, IP-over-ethernet, analog/PSTN). Examples of forbidden items here include SIP, GraphQL, KPML and other IP/ethernet options when ethernet is excluded.",
    "Do not invent match percentages or specs that are not in the context.",
    "Return one concise paragraph in Traditional Chinese if the scene contains Chinese, otherwise English.",
    JSON.stringify(context),
  ].join("\n");
}

// True if generated prose names any excluded product (the LLM's main failure
// mode: re-introducing forbidden options from its own training knowledge).
function mentionsExcludedNames(text, excludedNames) {
  const haystack = normalizeText(text);
  return excludedNames.some((name) => {
    const needle = normalizeText(name).trim();
    return needle.length >= 3 && haystack.includes(needle);
  });
}

async function aiRecommendation(env, scene, alternatives, solutions, exclusions = { phrases: [] }, excludedNames = []) {
  if (!env?.AI || String(env.USE_WORKERS_AI || "true") === "false") {
    return deterministicRecommendation(scene, alternatives, solutions);
  }
  try {
    const result = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
      messages: [
        { role: "system", content: "You are a concise cloud RAG recommender that strictly obeys exclusion constraints." },
        { role: "user", content: buildAiPrompt(scene, alternatives, solutions, exclusions, excludedNames) },
      ],
      max_tokens: 180,
    });
    const text = result?.response || result?.result?.response || "";
    // Guard: if the model hallucinated an excluded product, discard its prose
    // and fall back to the deterministic recommendation (built only from the
    // already-filtered allowed list).
    if (!text || mentionsExcludedNames(text, excludedNames)) {
      return deterministicRecommendation(scene, alternatives, solutions);
    }
    return text;
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
  const excludedNames = [...alternativesInput, ...solutionsInput]
    .filter((row) => isExcludedRow(row, exclusions.tokens))
    .map((row) => row.name)
    .filter(Boolean);
  const alternatives = rankRows(scene, alternativesInput, "alternative", exclusions.tokens);
  const solutions = rankRows(scene, solutionsInput, "solution", exclusions.tokens);
  const documents = rankDocuments(scene, documentsInput, exclusions.tokens);
  const recommendation = await aiRecommendation(env, scene, alternatives, solutions, exclusions, excludedNames);
  const alternativesTable = tableRows("alternative", alternatives);
  const solutionsTable = tableRows("solution", solutions);
  return {
    recommendation,
    alternatives,
    solutions,
    rag_response_table: [...alternativesTable, ...solutionsTable],
    tables: {
      alternatives: alternativesTable,
      solutions: solutionsTable,
      rag_response: [...alternativesTable, ...solutionsTable],
    },
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
