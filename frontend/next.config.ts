import type { NextConfig } from 'next';

// The browser talks to the backend directly (set NEXT_PUBLIC_API_URL when
// deployed); proxying through Next rewrites can buffer the streamed answers.
const nextConfig: NextConfig = {
  // Keep the dev-only Next.js badge away from the sidebar's account button.
  devIndicators: { position: 'bottom-right' },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
};

export default nextConfig;
