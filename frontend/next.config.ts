import type { NextConfig } from 'next';

// The browser talks to the backend directly (set NEXT_PUBLIC_API_URL when
// deployed); proxying through Next rewrites can buffer the streamed answers.
const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
};

export default nextConfig;
