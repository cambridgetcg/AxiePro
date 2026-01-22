'use client';

/**
 * Market Overview Stats component showing key metrics across time periods.
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { useMarketStats } from '@/hooks/use-market-stats';
import { cn } from '@/lib/utils';

interface MetricRowProps {
  label: string;
  value24h: string;
  value7d: string;
  value30d: string;
  isLoading?: boolean;
}

function MetricRow({ label, value24h, value7d, value30d, isLoading }: MetricRowProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-4 py-3 border-b last:border-0">
        <div className="text-sm text-muted-foreground">{label}</div>
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-20" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-4 gap-4 py-3 border-b last:border-0">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-sm font-medium">{value24h}</div>
      <div className="text-sm font-medium">{value7d}</div>
      <div className="text-sm font-medium">{value30d}</div>
    </div>
  );
}

function formatEth(value: number | undefined): string {
  if (value === undefined) return '--';
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  if (value >= 1) return value.toFixed(2);
  return value.toFixed(4);
}

function formatNumber(value: number | undefined): string {
  if (value === undefined) return '--';
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toLocaleString();
}

interface MarketOverviewStatsProps {
  className?: string;
}

export function MarketOverviewStats({ className }: MarketOverviewStatsProps) {
  const { data, isLoading, isError } = useMarketStats();

  const stats24h = data?.data?.['24h'];
  const stats7d = data?.data?.['7d'];
  const stats30d = data?.data?.['30d'];

  // Calculate period changes (guard against division by zero)
  const volumeChange7d = stats24h && stats7d && stats7d.volume_eth > 0
    ? ((stats24h.volume_eth * 7 - stats7d.volume_eth) / stats7d.volume_eth) * 100
    : null;

  // Ensure volumeChange7d is a valid finite number
  const safeVolumeChange7d = volumeChange7d !== null && Number.isFinite(volumeChange7d)
    ? volumeChange7d
    : null;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          Market Overview
        </CardTitle>
        <CardDescription>Key metrics across different time periods</CardDescription>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="py-8 text-center text-muted-foreground">
            Failed to load market data.
          </div>
        ) : (
          <div className="space-y-1">
            {/* Header */}
            <div className="grid grid-cols-4 gap-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wider">
              <div>Metric</div>
              <div>24h</div>
              <div>7d</div>
              <div>30d</div>
            </div>

            <MetricRow
              label="Volume (ETH)"
              value24h={formatEth(stats24h?.volume_eth)}
              value7d={formatEth(stats7d?.volume_eth)}
              value30d={formatEth(stats30d?.volume_eth)}
              isLoading={isLoading}
            />

            <MetricRow
              label="Sales Count"
              value24h={formatNumber(stats24h?.sales_count)}
              value7d={formatNumber(stats7d?.sales_count)}
              value30d={formatNumber(stats30d?.sales_count)}
              isLoading={isLoading}
            />

            <MetricRow
              label="Unique Buyers"
              value24h={formatNumber(stats24h?.unique_buyers)}
              value7d={formatNumber(stats7d?.unique_buyers)}
              value30d={formatNumber(stats30d?.unique_buyers)}
              isLoading={isLoading}
            />

            <MetricRow
              label="Unique Sellers"
              value24h={formatNumber(stats24h?.unique_sellers)}
              value7d={formatNumber(stats7d?.unique_sellers)}
              value30d={formatNumber(stats30d?.unique_sellers)}
              isLoading={isLoading}
            />

            <MetricRow
              label="Avg Price (ETH)"
              value24h={formatEth(stats24h?.avg_price_eth)}
              value7d={formatEth(stats7d?.avg_price_eth)}
              value30d={formatEth(stats30d?.avg_price_eth)}
              isLoading={isLoading}
            />

            <MetricRow
              label="Median Price (ETH)"
              value24h={formatEth(stats24h?.median_price_eth)}
              value7d={formatEth(stats7d?.median_price_eth)}
              value30d={formatEth(stats30d?.median_price_eth)}
              isLoading={isLoading}
            />

            <MetricRow
              label="Floor Price (ETH)"
              value24h={formatEth(stats24h?.floor_price_eth)}
              value7d={formatEth(stats7d?.floor_price_eth)}
              value30d={formatEth(stats30d?.floor_price_eth)}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Volume Trend Indicator */}
        {safeVolumeChange7d !== null && (
          <div className="mt-4 pt-4 border-t flex items-center justify-between">
            <span className="text-sm text-muted-foreground">7-day Volume Trend</span>
            <Badge
              variant="outline"
              className={cn(
                safeVolumeChange7d >= 0
                  ? 'border-green-500 text-green-500'
                  : 'border-red-500 text-red-500'
              )}
            >
              {safeVolumeChange7d >= 0 ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1" />
              )}
              {safeVolumeChange7d >= 0 ? '+' : ''}
              {safeVolumeChange7d.toFixed(1)}%
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
