import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, BarChart3, DollarSign, Users, ShoppingCart } from "lucide-react";

const mockStats = [
  { label: "Floor Price", value: "0.008 ETH", change: "-3%", positive: false, icon: DollarSign },
  { label: "24h Volume", value: "125 ETH", change: "+12%", positive: true, icon: BarChart3 },
  { label: "Listings", value: "12,453", change: "+5%", positive: true, icon: ShoppingCart },
  { label: "Unique Holders", value: "45,231", change: "+2%", positive: true, icon: Users },
];

export default function MarketPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Market Overview</h1>
          <p className="text-muted-foreground">
            Real-time market data and trading activity
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {mockStats.map((stat) => (
            <Card key={stat.label}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <stat.icon className="h-4 w-4 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <div className="flex items-center gap-1 mt-1">
                  {stat.positive ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  )}
                  <span className={stat.positive ? "text-green-500 text-sm" : "text-red-500 text-sm"}>
                    {stat.change}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Coming Soon */}
        <Card className="border-dashed">
          <CardHeader className="text-center py-16">
            <Badge variant="secondary" className="w-fit mx-auto mb-4">
              Coming Soon
            </Badge>
            <CardTitle className="text-2xl">Full Market Analytics</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Detailed price charts, sales history, floor price tracking by class,
              and whale activity monitoring coming soon.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-16">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              {["Price Charts", "Sales History", "Floor by Class", "Whale Tracker"].map((feature) => (
                <div key={feature} className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm font-medium">{feature}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
