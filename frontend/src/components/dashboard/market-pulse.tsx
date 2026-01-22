'use client';

/**
 * Market Pulse component displaying real-time market statistics.
 */
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, Users, BarChart3 } from 'lucide-react';
import { useMarketStats } from '@/hooks/use-market-stats';
import type { MarketStats } from '@/types/market';

interface StatCardProps {
  label: string;
  value: string;
  change?: string;
  positive?: boolean;
  icon: React.ReactNode;
  isLoading?: boolean;
}

function StatCard({ label, value, change, positive, icon, isLoading }: StatCardProps) {
  if (isLoading) {
    return (
      <Card className="bg-card/50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-5 w-5 rounded" />
          </div>
          <Skeleton className="h-8 w-24 mb-2" />
          <Skeleton className="h-4 w-12" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 hover:bg-card/70 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-muted-foreground">{label}</p>
          <div className="text-muted-foreground">{icon}</div>
        </div>
        <p className="text-2xl font-bold">{value}</p>
        {change && (
          <div className="flex items-center gap-1 mt-1">
            {positive ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
            <span className={positive ? 'text-green-500 text-sm' : 'text-red-500 text-sm'}>
              {change}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatEth(value: number | undefined | null): string {
  if (value === undefined || value === null || !Number.isFinite(value)) {
    return '--';
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K ETH`;
  }
  if (value >= 1) {
    return `${value.toFixed(1)} ETH`;
  }
  return `${value.toFixed(4)} ETH`;
}

function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null || !Number.isFinite(value)) {
    return '--';
  }
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toLocaleString();
}

function calculateChange(current: MarketStats, previous: MarketStats): {
  volumeChange: string | undefined;
  salesChange: string | undefined;
  avgPriceChange: string | undefined;
  floorChange: string | undefined;
  volumePositive: boolean;
  salesPositive: boolean;
  avgPricePositive: boolean;
  floorPositive: boolean;
} | null {
  // Guard against division by zero - return null if previous values are 0
  if (!previous.volume_eth && !previous.sales_count && !previous.avg_price_eth) {
    return null;
  }

  const safePercent = (curr: number, prev: number): number | null => {
    if (prev === 0 || !Number.isFinite(prev)) return null;
    const diff = ((curr - prev) / prev) * 100;
    return Number.isFinite(diff) ? diff : null;
  };

  const formatPercent = (val: number | null): string | undefined => {
    if (val === null || !Number.isFinite(val)) return undefined;
    return `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`;
  };

  const volumeDiff = safePercent(current.volume_eth, previous.volume_eth);
  const salesDiff = safePercent(current.sales_count, previous.sales_count);
  const avgPriceDiff = safePercent(current.avg_price_eth, previous.avg_price_eth);
  const floorDiff = safePercent(current.floor_price_eth ?? 0, previous.floor_price_eth ?? 0);

  return {
    volumeChange: formatPercent(volumeDiff),
    salesChange: formatPercent(salesDiff),
    avgPriceChange: formatPercent(avgPriceDiff),
    floorChange: formatPercent(floorDiff),
    volumePositive: (volumeDiff ?? 0) >= 0,
    salesPositive: (salesDiff ?? 0) >= 0,
    avgPricePositive: (avgPriceDiff ?? 0) >= 0,
    floorPositive: (floorDiff ?? 0) >= 0,
  };
}

export function MarketPulse() {
  const { data, isLoading, isError } = useMarketStats();

  if (isError) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="col-span-full bg-destructive/10 border-destructive/50">
          <CardContent className="p-4 text-center text-destructive">
            Failed to load market data. Please try again later.
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats24h = data?.data?.['24h'];
  const stats7d = data?.data?.['7d'];

  // Calculate 24h changes by comparing to 7d averages (approximation)
  const changes = stats24h && stats7d
    ? calculateChange(stats24h, {
        ...stats7d,
        volume_eth: stats7d.volume_eth / 7,
        sales_count: stats7d.sales_count / 7,
      })
    : null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="24h Volume"
        value={stats24h ? formatEth(stats24h.volume_eth) : '--'}
        change={changes?.volumeChange}
        positive={changes?.volumePositive}
        icon={<DollarSign className="h-5 w-5" />}
        isLoading={isLoading}
      />
      <StatCard
        label="24h Sales"
        value={stats24h ? formatNumber(stats24h.sales_count) : '--'}
        change={changes?.salesChange}
        positive={changes?.salesPositive}
        icon={<ShoppingCart className="h-5 w-5" />}
        isLoading={isLoading}
      />
      <StatCard
        label="Floor Price"
        value={stats24h ? formatEth(stats24h.floor_price_eth) : '--'}
        change={changes?.floorChange}
        positive={changes?.floorPositive}
        icon={<BarChart3 className="h-5 w-5" />}
        isLoading={isLoading}
      />
      <StatCard
        label="Avg Price"
        value={stats24h ? formatEth(stats24h.avg_price_eth) : '--'}
        change={changes?.avgPriceChange}
        positive={changes?.avgPricePositive}
        icon={<Users className="h-5 w-5" />}
        isLoading={isLoading}
      />
    </div>
  );
}
