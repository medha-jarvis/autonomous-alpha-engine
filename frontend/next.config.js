/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    TYPESENSE_HOST: process.env.TYPESENSE_HOST || 'localhost',
    TYPESENSE_PORT: process.env.TYPESENSE_PORT || '8108',
    TYPESENSE_PROTOCOL: process.env.TYPESENSE_PROTOCOL || 'http',
  },
}

module.exports = nextConfig