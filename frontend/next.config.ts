import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  trailingSlash: true,

  // Proxy API requests to backend during local development
  // This avoids CORS issues when frontend and backend run on different ports
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Only proxy in development when using localhost backend
    if (process.env.NODE_ENV === "development" && apiUrl.includes("localhost")) {
      return [
        {
          source: "/api/:path*",
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    }

    return [];
  },
};

export default nextConfig;
