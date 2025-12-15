import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, BarChart3, LineChart, PieChart, Activity } from "lucide-react";

const trendingUp = [
  { name: "Nut Cracker", type: "mouth", change: "+15%" },
  { name: "Ronin", type: "back", change: "+12%" },
  { name: "Cottontail", type: "tail", change: "+10%" },
  { name: "Little Branch", type: "horn", change: "+8%" },
];

const trendingDown = [
  { name: "Cute Bunny", type: "ears", change: "-8%" },
  { name: "Imp", type: "horn", change: "-6%" },
  { name: "Gerbil", type: "ears", change: "-5%" },
  { name: "Hot Butt", type: "back", change: "-4%" },
];

export default function AnalyticsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Market trends, price analysis, and insights
          </p>
        </div>

        {/* Trending Traits */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-500" />
                Top Gainers (24h)
              </CardTitle>
              <CardDescription>Traits with the most price increase</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {trendingUp.map((trait, index) => (
                  <div key={trait.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground w-6">{index + 1}</span>
                      <div>
                        <p className="font-medium">{trait.name}</p>
                        <p className="text-sm text-muted-foreground capitalize">{trait.type}</p>
                      </div>
                    </div>
                    <span className="text-green-500 font-medium">{trait.change}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingDown className="h-5 w-5 text-red-500" />
                Top Losers (24h)
              </CardTitle>
              <CardDescription>Traits with the most price decrease</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {trendingDown.map((trait, index) => (
                  <div key={trait.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground w-6">{index + 1}</span>
                      <div>
                        <p className="font-medium">{trait.name}</p>
                        <p className="text-sm text-muted-foreground capitalize">{trait.type}</p>
                      </div>
                    </div>
                    <span className="text-red-500 font-medium">{trait.change}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Coming Soon */}
        <Card className="border-dashed">
          <CardHeader className="text-center py-12">
            <Badge variant="secondary" className="w-fit mx-auto mb-4">
              Coming Soon
            </Badge>
            <CardTitle className="text-2xl">Full Analytics Suite</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Interactive charts, historical data, deal detection alerts, and
              meta shift analysis coming soon.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {[
                { name: "Price Charts", icon: LineChart },
                { name: "Volume Analysis", icon: BarChart3 },
                { name: "Class Distribution", icon: PieChart },
                { name: "Real-time Alerts", icon: Activity },
              ].map((feature) => (
                <div key={feature.name} className="p-4 rounded-lg bg-muted/50 flex flex-col items-center gap-2">
                  <feature.icon className="h-5 w-5 text-muted-foreground" />
                  <p className="text-sm font-medium">{feature.name}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
