import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Search,
  Dna,
  Zap,
  Shield,
  Target,
  ArrowRight,
  Activity,
} from "lucide-react";

// Mock data for the landing page
const marketStats = [
  { label: "24h Volume", value: "125 ETH", change: "+12%", positive: true },
  { label: "Total Sales", value: "4,521", change: "+8%", positive: true },
  { label: "Floor Price", value: "0.008 ETH", change: "-3%", positive: false },
  { label: "Avg Price", value: "0.027 ETH", change: "+5%", positive: true },
];

const trendingTraits = [
  { name: "Nut Cracker", type: "mouth", change: "+15%", positive: true },
  { name: "Ronin", type: "back", change: "+12%", positive: true },
  { name: "Cottontail", type: "tail", change: "+10%", positive: true },
  { name: "Cute Bunny", type: "ears", change: "-8%", positive: false },
];

const features = [
  {
    icon: Search,
    title: "Advanced Explorer",
    description:
      "Filter Axies by class, purity, parts, genes, and price. Find exactly what you're looking for.",
  },
  {
    icon: BarChart3,
    title: "Market Analytics",
    description:
      "Track price trends, volume, and market movements. Make data-driven trading decisions.",
  },
  {
    icon: Dna,
    title: "Breeding Simulator",
    description:
      "Predict offspring outcomes with gene probability calculations. Maximize your breeding ROI.",
  },
  {
    icon: Target,
    title: "Deal Detection",
    description:
      "Get alerts when undervalued Axies hit the market. Snipe deals before anyone else.",
  },
  {
    icon: Zap,
    title: "Real-time Data",
    description:
      "Live market data with sub-second updates. Never miss a market movement.",
  },
  {
    icon: Shield,
    title: "Portfolio Tracking",
    description:
      "Track your holdings, P&L, and trade history. Understand your performance.",
  },
];

export default function HomePage() {
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

      {/* Market Overview */}
      <section className="border-y bg-muted/30">
        <div className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {marketStats.map((stat) => (
              <Card key={stat.label} className="bg-card/50">
                <CardContent className="p-4">
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <div className="flex items-center gap-1 mt-1">
                    {stat.positive ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                    <span
                      className={
                        stat.positive ? "text-green-500 text-sm" : "text-red-500 text-sm"
                      }
                    >
                      {stat.change}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
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
              <Card key={feature.title} className="group hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                    <feature.icon className="h-6 w-6 text-primary" />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Trending Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Trending Traits */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" />
                  Trending Traits
                </CardTitle>
                <CardDescription>
                  Most price movement in the last 24 hours
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {trendingTraits.map((trait) => (
                    <div
                      key={trait.name}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                    >
                      <div>
                        <p className="font-medium">{trait.name}</p>
                        <p className="text-sm text-muted-foreground capitalize">
                          {trait.type}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        {trait.positive ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                        <span
                          className={
                            trait.positive
                              ? "text-green-500 font-medium"
                              : "text-red-500 font-medium"
                          }
                        >
                          {trait.change}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <Link href="/analytics/trends">
                  <Button variant="ghost" className="w-full mt-4 gap-2">
                    View All Trends
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {/* Quick Actions */}
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
              <CardContent className="space-y-3">
                <Link href="/explorer">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <Search className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Find Axies</p>
                      <p className="text-xs text-muted-foreground">
                        Search with advanced filters
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/breeding">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <Dna className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Breeding Simulator</p>
                      <p className="text-xs text-muted-foreground">
                        Calculate offspring probabilities
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/market">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <BarChart3 className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Market Overview</p>
                      <p className="text-xs text-muted-foreground">
                        Sales, listings, and floor prices
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/analytics">
                  <Button variant="outline" className="w-full justify-start gap-3 h-14">
                    <Target className="h-5 w-5" />
                    <div className="text-left">
                      <p className="font-medium">Deal Alerts</p>
                      <p className="text-xs text-muted-foreground">
                        Get notified of undervalued Axies
                      </p>
                    </div>
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
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
