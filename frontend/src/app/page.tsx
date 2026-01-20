'use client';

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart3,
  Search,
  Dna,
  Zap,
  Shield,
  Target,
  ArrowRight,
  Activity,
  Sparkles,
  Wallet,
} from "lucide-react";
import { MarketPulse, TopDeals, FloorChart } from "@/components/dashboard";
import { MetaAlertBanner } from "@/components/meta";
import { useMetaShifts } from "@/hooks/use-meta";

const features = [
  {
    icon: Search,
    title: "Advanced Explorer",
    description:
      "Filter Axies by class, purity, parts, genes, and price. Find exactly what you're looking for.",
    href: "/explorer",
  },
  {
    icon: BarChart3,
    title: "Market Analytics",
    description:
      "Track price trends, volume, and market movements. Make data-driven trading decisions.",
    href: "/analytics",
  },
  {
    icon: Dna,
    title: "Breeding Simulator",
    description:
      "Predict offspring outcomes with gene probability calculations. Maximize your breeding ROI.",
    href: "/breeding",
  },
  {
    icon: Target,
    title: "Deal Detection",
    description:
      "Get alerts when undervalued Axies hit the market. Snipe deals with normalized scoring.",
    href: "/deals",
  },
  {
    icon: Sparkles,
    title: "Meta Shifts",
    description:
      "Detect emerging trends before they become obvious. Spot rising and falling traits early.",
    href: "/meta",
    isNew: true,
  },
  {
    icon: Wallet,
    title: "Portfolio P&L",
    description:
      "Track unrealized gains, cost basis, and ROI across your holdings. Know your performance.",
    href: "/portfolio",
    isNew: true,
  },
];

export default function HomePage() {
  // Fetch meta shifts for alert banner
  const { data: metaShiftsData, isLoading: metaLoading } = useMetaShifts({
    minConfidence: 70,
    limit: 10,
  });

  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-accent/10" />
        <div className="container mx-auto px-4 py-20 md:py-32 relative">
          <div className="max-w-3xl mx-auto text-center">
            <Badge variant="secondary" className="mb-4">
              <Activity className="h-3 w-3 mr-1" />
              Live Market Data
            </Badge>
            <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-foreground via-primary to-accent bg-clip-text text-transparent">
              Dominate the Axie Market
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Professional-grade analytics, breeding tools, and deal detection for
              serious Axie Infinity traders. Find undervalued assets and optimize
              your strategy.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/explorer">
                <Button size="lg" className="gap-2">
                  Start Exploring
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/analytics">
                <Button size="lg" variant="outline" className="gap-2">
                  <BarChart3 className="h-4 w-4" />
                  View Analytics
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Meta Alert Banner */}
      {(metaShiftsData?.shifts?.length ?? 0) > 0 && (
        <section className="border-b">
          <div className="container mx-auto px-4 py-4">
            <MetaAlertBanner
              shifts={metaShiftsData?.shifts ?? []}
              isLoading={metaLoading}
              maxDisplay={3}
            />
          </div>
        </section>
      )}

      {/* Market Overview - Real Data */}
      <section className="border-y bg-muted/30">
        <div className="container mx-auto px-4 py-8">
          <MarketPulse />
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything You Need to Win
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Powerful tools designed for traders who take Axie Infinity seriously.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <Link key={feature.title} href={feature.href}>
                <Card className="group hover:border-primary/50 transition-colors h-full cursor-pointer">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                        <feature.icon className="h-6 w-6 text-primary" />
                      </div>
                      {feature.isNew && (
                        <Badge className="bg-green-500/10 text-green-500 border-green-500/50">
                          New
                        </Badge>
                      )}
                    </div>
                    <CardTitle className="group-hover:text-primary transition-colors">
                      {feature.title}
                    </CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Deals & Floor Prices Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Top Deals - Real Data */}
            <TopDeals limit={5} />

            {/* Floor Prices Chart - Real Data */}
            <FloorChart />
          </div>
        </div>
      </section>

      {/* Quick Actions */}
      <section className="py-12">
        <div className="container mx-auto px-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                Quick Actions
              </CardTitle>
              <CardDescription>
                Jump right into the tools you need
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                <Link href="/explorer">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <Search className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Find Axies</p>
                      <p className="text-xs text-muted-foreground">
                        Advanced filters
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/deals">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <Target className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Deal Finder</p>
                      <p className="text-xs text-muted-foreground">
                        Undervalued Axies
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/meta">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14 relative">
                    <Sparkles className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Meta Shifts</p>
                      <p className="text-xs text-muted-foreground">
                        Trend detection
                      </p>
                    </div>
                    <Badge className="absolute -top-2 -right-2 text-[10px] px-1.5 py-0 bg-green-500">
                      New
                    </Badge>
                  </Button>
                </Link>
                <Link href="/portfolio">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14 relative">
                    <Wallet className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Portfolio</p>
                      <p className="text-xs text-muted-foreground">
                        P&L tracking
                      </p>
                    </div>
                    <Badge className="absolute -top-2 -right-2 text-[10px] px-1.5 py-0 bg-green-500">
                      New
                    </Badge>
                  </Button>
                </Link>
                <Link href="/breeding">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <Dna className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Breeding Sim</p>
                      <p className="text-xs text-muted-foreground">
                        Gene probabilities
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/analytics">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <BarChart3 className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Analytics</p>
                      <p className="text-xs text-muted-foreground">
                        Market trends
                      </p>
                    </div>
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <Card className="gradient-primary text-white">
            <CardContent className="p-8 md:p-12 text-center">
              <h2 className="text-2xl md:text-3xl font-bold mb-4">
                Ready to Level Up Your Trading?
              </h2>
              <p className="text-white/80 mb-6 max-w-xl mx-auto">
                Join thousands of traders using AxiePro to find better deals, make
                smarter breeding decisions, and track market trends.
              </p>
              <Link href="/explorer">
                <Button size="lg" variant="secondary" className="gap-2">
                  Get Started Free
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
