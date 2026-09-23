import type { MetadataRoute } from "next";

export const dynamic = "force-static";

// Machine-readable map of the site, for search engines and agents.
export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://axiepro.io";
  const paths = [
    "",
    "/explorer",
    "/deals",
    "/analytics",
    "/meta",
    "/portfolio",
    "/breeding",
    "/terms",
    "/privacy",
  ];
  return paths.map((path) => ({
    url: `${base}${path}`,
    changeFrequency:
      path === "" || path === "/deals" || path === "/analytics" ? "daily" : "weekly",
    priority: path === "" ? 1 : path === "/terms" || path === "/privacy" ? 0.3 : 0.7,
  }));
}
