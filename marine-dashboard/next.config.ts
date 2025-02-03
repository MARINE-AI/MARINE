// next.config.js
module.exports = {
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
  // Add asset prefix if using absolute URLs
  assetPrefix: process.env.NODE_ENV === 'production' ? 'https://your-domain.com' : '',
};