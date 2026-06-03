const LANG = process.env.NEXT_PUBLIC_LANG || "zh";
const BASE = LANG === "en" ? "/pbx_estimation/en" : "/pbx_estimation/zh";

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
  },
};

export default nextConfig;
