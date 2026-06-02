/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // GitHub Pages serves project repos under /<repo-name>/
  basePath: "/pbx_estimation",
  assetPrefix: "/pbx_estimation",
  images: { unoptimized: true },
  trailingSlash: true,
  // Expose basePath to client components for constructing iframe src
  env: {
    NEXT_PUBLIC_BASE_PATH: "/pbx_estimation",
  },
};

export default nextConfig;
