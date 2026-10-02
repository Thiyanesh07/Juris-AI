/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    unoptimized: true,
  },
  // Explicit turbopack config prevents the "webpack config with no turbopack config" warning.
  // Path aliases are resolved via tsconfig.json paths (Turbopack reads these natively).
  turbopack: {},
};

export default nextConfig;
