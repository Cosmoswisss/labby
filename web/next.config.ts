import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Fully static site: `next build` writes HTML/JS to out/ (no server needed).
  output: "export",
  // /projects/abc -> out/projects/abc/index.html, served without rewrites on any host.
  trailingSlash: true,
  // cacheComponents / partialPrefetching (create-next-app defaults) need a server
  // ("PPR cannot be enabled in export mode"): not used for this static site.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
