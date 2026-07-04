/**
 * Configuración de Next.js 14 (App Router) del Observatorio.
 * Sin dependencias de CDN en runtime: las fuentes se autoalojan vía next/font.
 *
 * Despliegue todo-en-uno (Vercel): el backend son route handlers de Next.js
 * (src/app/api) que leen los datos de ./data/processed. `outputFileTracingIncludes`
 * asegura que esos archivos se empaqueten en las funciones serverless.
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    outputFileTracingIncludes: {
      '/api/**': ['./data/processed/**/*'],
    },
  },
};

export default nextConfig;
