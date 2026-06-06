import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: "https://axiepro.io/sitemap.xml",
    host: "https://axiepro.io",
  };
}
