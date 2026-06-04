const LANG = process.env.NEXT_PUBLIC_LANG || "zh";
const SITE_BASE_PATH = (process.env.NEXT_PUBLIC_SITE_BASE_PATH || "/pbx_estimation").replace(/\/$/, "");
const BASE_PREFIX = SITE_BASE_PATH === "/" ? "" : SITE_BASE_PATH;
const BASE = LANG === "en" ? `${BASE_PREFIX}/en` : `${BASE_PREFIX}/zh`;
const CLOUD_RAG_ENDPOINT = process.env.NEXT_PUBLIC_CLOUD_RAG_ENDPOINT || "";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  basePath: BASE,
  assetPrefix: BASE,
  images: { unoptimized: true },
  trailingSlash: true,
  env: {
    NEXT_PUBLIC_BASE_PATH: BASE,
    NEXT_PUBLIC_LANG: LANG,
    NEXT_PUBLIC_CLOUD_RAG_ENDPOINT: CLOUD_RAG_ENDPOINT,
  },
};

export default nextConfig;
