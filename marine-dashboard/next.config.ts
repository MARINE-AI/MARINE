import { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/service-worker.js',
        headers: [
          {
            key: 'Service-Worker-Allowed',
            value: '/'
          }
        ]
      }
    ];
  },
  assetPrefix: process.env.NODE_ENV === 'production' ? 'https://marine-ai.vercel.app' : '',

  distDir: '.next',

  output: 'standalone',
};

export default nextConfig;
