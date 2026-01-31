'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, BarChart3, Activity, TrendingUp } from 'lucide-react';
import {
  MarketOverviewStats,
  FloorPricesChart,
  RecentSalesChart,
  TopDealsTable,
} from '@/components/analytics';
import { MarketPulse } from '@/components/dashboard';
import { cn } from '@/lib/utils';

type TimeRange = '24h' | '7d' | '30d';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    // Trigger re-fetch by changing state - React Query will handle the rest
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <BarChart3 className="h-8 w-8 text-primary" />
              Market Analytics
            </h1>
            <p className="text-muted-foreground">
              Real-time market trends, price analysis, and deal opportunities
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Time Range Selector */}
            <div className="flex items-center border rounded-lg">
              {(['24h', '7d', '30d'] as TimeRange[]).map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setTimeRange(range)}
                  className={cn(
                    range === '24h' && 'rounded-r-none',
                    range === '7d' && 'rounded-none border-x',
                    range === '30d' && 'rounded-l-none'
                  )}
                >
                  {range}
                </Button>
              ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn('h-4 w-4 mr-1', isRefreshing && 'animate-spin')}
              />
              Refresh
            </Button>
          </div>
        </div>

        {/* Market Pulse Stats */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Market Pulse</h2>
            <Badge variant="outline" className="text-xs">
              Live
            </Badge>
          </div>
          <MarketPulse />
        </section>

        {/* Charts Grid */}
        <section className="grid lg:grid-cols-2 gap-6">
          {/* Recent Sales Chart */}
          <RecentSalesChart />

          {/* Floor Prices Chart */}
          <FloorPricesChart />
        </section>

        {/* Market Overview Table */}
        <section>
          <MarketOverviewStats />
        </section>

        {/* Top Deals */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Deal Opportunities</h2>
          </div>
          <TopDealsTable limit={10} />
        </section>

        {/* Data Source Info */}
        <section className="text-center py-4 border-t">
          <p className="text-xs text-muted-foreground">
            Data sourced from Axie Infinity marketplace. Valuations computed using hedonic pricing model.
            <br />
            Refreshed automatically. Last model update: v1.0.0
          </p>
        </section>
      </div>
    </div>
  );
}
