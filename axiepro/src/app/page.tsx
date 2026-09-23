'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
    title: "Axie Explorer",
    description:
      "Look up any Axie by ID to see its traits and valuation. Full class/parts/gene filtering is coming soon.",
    href: "/explorer",
    comingSoon: true,
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
    title: "Breeding ROI",
    description:
      "Breed-vs-buy with gene probabilities and live costs. Coming soon.",
    href: "/breeding",
    comingSoon: true,
  },
  {
    icon: Target,
    title: "Deal Detection",
    description:
      "Inspect how a listing compares with uncertain value estimates and their assumptions.",
    href: "/deals",
  },
  {
    icon: Sparkles,
    title: "Meta Shifts",
    description:
      "Explore changes in traits and market observations, including their uncertainty.",
    href: "/meta",
    isNew: true,
  },
  {
    icon: Wallet,
    title: "Portfolio P&L",
    description:
      "Understand existing holdings, cost basis and estimated changes in value.",
    href: "/portfolio",
    isNew: true,
  },
];

export default function HomePage() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // accept a raw ID or a marketplace link — grab the first long digit run
    const match = search.trim().match(/(\d{3,})/);
    if (match) router.push(`/explorer?id=${match[1]}`);
  };

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
              Beta
            </Badge>
            <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-foreground via-primary to-accent bg-clip-text text-transparent">
              Explore Axie traits and value estimates
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Explore traits, historical market observations and uncertain value estimates.
              There are no paid plans, growth targets or pressure to turn understanding into profit.
            </p>
            <form
              onSubmit={handleSearch}
              className="flex flex-col sm:flex-row gap-2 max-w-xl mx-auto mb-4"
            >
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Enter an Axie ID (e.g. 12345)"
                  aria-label="Axie ID or marketplace link"
                  className="pl-11 h-12 text-base"
                />
              </div>
              <Button type="submit" size="lg" className="gap-2 h-12">
                Value it
                <ArrowRight className="h-4 w-4" />
              </Button>
            </form>
            <div className="flex flex-wrap gap-2 justify-center text-sm text-muted-foreground">
              <Link href="/deals" className="hover:text-foreground underline-offset-4 hover:underline">
                or browse today&apos;s deals
              </Link>
              <span>·</span>
              <Link href="/analytics" className="hover:text-foreground underline-offset-4 hover:underline">
                see market analytics
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Meta Alert Banner */}
      {(metaShiftsData?.data?.length ?? 0) > 0 && (
        <section className="border-b">
          <div className="container mx-auto px-4 py-4">
            <MetaAlertBanner
              shifts={metaShiftsData?.data ?? []}
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
              Different ways to understand
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
                      {feature.comingSoon && (
                        <Badge variant="outline" className="text-muted-foreground">
                          Soon
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
                Explore at your own pace
              </h2>
              <p className="text-white/80 mb-6 max-w-xl mx-auto">
                Read-only tools for exploring Axies and market observations.
                New paid plans and checkout are retired. Informational, not financial advice.
              </p>
              <Link href="/explorer">
                <Button size="lg" variant="secondary" className="gap-2">
                  Open the explorer
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
