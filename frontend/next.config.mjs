/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    // react-pdf / pdfjs-dist intentan resolver "canvas" (solo Node); en el
    // navegador no se usa. Lo marcamos como módulo vacío para evitar el error.
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
    };
    return config;
  },
};

export default nextConfig;
