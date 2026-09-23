import type { NextConfig } from "next";

// Pages keeps an explicit static-export mode; Vercel retains its normal build.
const staticExport = process.env.AXIEPRO_STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  ...(staticExport ? { output: "export" as const } : {}),
  images: {
    unoptimized: true,
  },
  trailingSlash: true,

  // Mark pino and related packages as external to avoid SSR bundling issues
  // These packages use Node.js modules not available in the browser
  serverExternalPackages: ["pino", "pino-pretty", "thread-stream"],

  // Turbopack configuration for handling wallet SDK modules
  turbopack: {
    resolveAlias: {
      // Provide empty fallbacks for Node.js modules not available in browser
      fs: { browser: "" },
      net: { browser: "" },
      tls: { browser: "" },
      "why-is-node-running": { browser: "" },
      tap: { browser: "" },
    },
  },

  // Proxy API requests to backend during local development
  // This avoids CORS issues when frontend and backend run on different ports
  rewrites: staticExport ? undefined : async () => {
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
