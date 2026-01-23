'use client';

/**
 * Recent Sales Chart showing price distribution.
 */
import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity } from 'lucide-react';
import { useRecentSales } from '@/hooks/use-market-stats';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface RecentSalesChartProps {
  className?: string;
}

export function RecentSalesChart({ className }: RecentSalesChartProps) {
  const { data, isLoading, isError } = useRecentSales({ hours: 24, limit: 200 });

  // Transform sales data into time-series for chart
  const chartData = useMemo(() => {
    if (!data?.data) return [];

    // Group by hour and calculate average price
    const hourlyData: Record<string, { prices: number[]; count: number }> = {};

    data.data.forEach((sale) => {
      const date = new Date(sale.sold_at);
      const hourKey = `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:00`;

      if (!hourlyData[hourKey]) {
        hourlyData[hourKey] = { prices: [], count: 0 };
      }
      hourlyData[hourKey].prices.push(sale.price_eth);
      hourlyData[hourKey].count++;
    });

    // Convert to array and calculate averages
    return Object.entries(hourlyData)
      .map(([time, { prices, count }]) => ({
        time,
        avgPrice: prices.reduce((a, b) => a + b, 0) / prices.length,
        volume: count,
        minPrice: Math.min(...prices),
        maxPrice: Math.max(...prices),
      }))
      .slice(-24); // Last 24 data points
  }, [data]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Recent Sales Activity
        </CardTitle>
        <CardDescription>Price trends from recent sales</CardDescription>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            Failed to load sales data.
          </div>
        ) : isLoading ? (
          <div className="h-64 flex items-center justify-center">
            <Skeleton className="h-full w-full" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No sales data available.
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `${value.toFixed(3)}`}
                />
                <Tooltip
                  formatter={(value, name) => {
                    const numValue = typeof value === 'number' ? value : 0;
                    const strName = String(name);
                    const labels: Record<string, string> = {
                      avgPrice: 'Avg Price',
                      volume: 'Sales',
                    };
                    return [
                      strName === 'avgPrice' ? `${numValue.toFixed(4)} ETH` : numValue,
                      labels[strName] || strName,
                    ];
                  }}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="avgPrice"
                  stroke="hsl(var(--primary))"
                  fillOpacity={1}
                  fill="url(#colorPrice)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
