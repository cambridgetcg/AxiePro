import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { QueryProvider } from "@/components/providers/query-provider";
import { SHARE_CARD } from "@/lib/share-card";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.axiepro.io"),
  title: {
    default: "AxiePro — Axie Infinity deal-finder & valuation",
    template: "%s · AxiePro",
  },
  description:
    "Read-only, non-custodial analytics for Axie Infinity traders. Track sales, value Axies by traits, and find undervalued deals on the Ronin chain. Informational, not financial advice.",
  keywords: [
    "Axie Infinity",
    "Axie",
    "NFT",
    "Ronin",
    "breeding",
    "market",
    "analytics",
    "deal finder",
    "valuation",
  ],
  authors: [{ name: "AxiePro" }],
  // Brand kit: brand/kit/web, copied byte for byte into public/
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "32x32" },
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: "/apple-touch-icon.png",
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: "AxiePro — Axie Infinity deal-finder & valuation",
    description:
      "Read-only analytics for Axie traders — find undervalued deals and value Axies by traits.",
    url: "https://www.axiepro.io",
    siteName: "AxiePro",
    type: "website",
    images: [SHARE_CARD],
  },
  twitter: {
    card: "summary_large_image",
    title: "AxiePro — Axie Infinity deal-finder & valuation",
    description:
      "Read-only analytics for Axie traders — find undervalued deals and value Axies by traits.",
  },
};

// The page is always dark (className="dark" below), so one theme-color, as the kit's head-snippet.html has it
export const viewport: Viewport = { themeColor: "#05050D", colorScheme: "dark" };

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <QueryProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </QueryProvider>
      </body>
    </html>
  );
}
