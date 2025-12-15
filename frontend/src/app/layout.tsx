import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AxiePro - Advanced Axie Infinity Market Analytics",
  description:
    "Professional market analytics, breeding tools, and deal detection for Axie Infinity traders. Track prices, find undervalued Axies, and optimize your breeding strategy.",
  keywords: [
    "Axie Infinity",
    "Axie",
    "NFT",
    "Ronin",
    "breeding",
    "market",
    "analytics",
    "crypto gaming",
  ],
  authors: [{ name: "AxiePro" }],
  openGraph: {
    title: "AxiePro - Advanced Axie Infinity Market Analytics",
    description:
      "Professional market analytics, breeding tools, and deal detection for Axie Infinity traders.",
    url: "https://axiepro.io",
    siteName: "AxiePro",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AxiePro - Advanced Axie Infinity Market Analytics",
    description:
      "Professional market analytics, breeding tools, and deal detection for Axie Infinity traders.",
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
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
