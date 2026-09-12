/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  output: 'export',
  experimental: {
    // Cloudflare can restore a truncated Turbopack cache. Compile production
    // builds from scratch instead of reopening that persistent database.
    turbopackFileSystemCacheForBuild: false,
  },
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
