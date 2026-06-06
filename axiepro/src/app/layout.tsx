import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { QueryProvider } from "@/components/providers/query-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://axiepro.io"),
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
  openGraph: {
    title: "AxiePro — Axie Infinity deal-finder & valuation",
    description:
      "Read-only analytics for Axie traders — find undervalued deals and value Axies by traits.",
    url: "https://axiepro.io",
    siteName: "AxiePro",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AxiePro — Axie Infinity deal-finder & valuation",
    description:
      "Read-only analytics for Axie traders — find undervalued deals and value Axies by traits.",
  },
};

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
