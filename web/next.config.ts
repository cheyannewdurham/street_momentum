import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  images: {
    domains: ['placehold.co'],
    // or:
    // remotePatterns: [{ protocol: 'https', hostname: 'placehold.co' }],
  },
}

export default nextConfig