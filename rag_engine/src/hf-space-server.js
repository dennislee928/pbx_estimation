import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, normalize } from "node:path";
import { handleRagRequest } from "./worker.js";

const PORT = Number(process.env.PORT || 7860);
const HOST = process.env.HOST || "0.0.0.0";
const ASSET_ROOT = process.env.HF_RAG_ASSET_ROOT || join(process.cwd(), "dist", "hf_assets");
const RAG_ASSET_PREFIX = process.env.RAG_ASSET_PREFIX || "latest";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": process.env.ALLOWED_ORIGINS || "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  };
}

function sendJson(response, status, body) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    ...corsHeaders(),
  });
  response.end(JSON.stringify(body, null, 2));
}

async function readBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

function localAssetPath(key) {
  const safeKey = normalize(key).replace(/^(\.\.(\/|\\|$))+/, "");
  return join(ASSET_ROOT, safeKey);
}

function localAssetBinding() {
  return {
    async get(key) {
      const path = localAssetPath(key);
      try {
        const buffer = await readFile(path);
        return {
          async json() {
            return JSON.parse(buffer.toString("utf8"));
          },
          async text() {
            return buffer.toString("utf8");
          },
        };
      } catch {
        return null;
      }
    },
  };
}

function envForRequest() {
  return {
    USE_WORKERS_AI: "false",
    RAG_ASSET_PREFIX,
    ALLOWED_ORIGINS: process.env.ALLOWED_ORIGINS || "*",
    RAG_ASSETS: localAssetBinding(),
  };
}

const server = createServer(async (request, response) => {
  if (request.method === "OPTIONS") {
    response.writeHead(204, corsHeaders());
    response.end();
    return;
  }

  const url = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);

  if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
    sendJson(response, 200, {
      ok: true,
      service: "pbx-rag-engine",
      runtime: "hugging-face-space",
      asset_prefix: RAG_ASSET_PREFIX,
    });
    return;
  }

  if (request.method === "GET" && url.pathname === "/assets/manifest") {
    const env = envForRequest();
    const object = await env.RAG_ASSETS.get(`${RAG_ASSET_PREFIX}/rag_engine/dist/rag_assets_manifest.json`);
    sendJson(response, 200, object ? await object.json() : { assets: [], asset_count: 0 });
    return;
  }

  if (request.method !== "POST") {
    sendJson(response, 405, { error: "Use POST / with a JSON body." });
    return;
  }

  try {
    const rawBody = await readBody(request);
    const payload = rawBody ? JSON.parse(rawBody) : {};
    const result = await handleRagRequest(payload, envForRequest());
    sendJson(response, 200, result);
  } catch (error) {
    sendJson(response, 400, { error: error.message || String(error) });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`PBX RAG engine listening on http://${HOST}:${PORT}`);
});
