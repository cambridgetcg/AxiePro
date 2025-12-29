'use client';

/**
 * Floor Chart component displaying floor prices by class.
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { BarChart3 } from 'lucide-react';
import { useFloorPrices } from '@/hooks/use-floor-prices';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { AXIE_CLASSES } from '@/types/valuation';

// Class colors matching Axie Infinity theme
const CLASS_COLORS: Record<string, string> = {
  beast: '#FFB812',
  bug: '#FF5341',
  bird: '#FF80C5',
  plant: '#6CC000',
  aquatic: '#00B8CE',
  reptile: '#A16FF9',
  mech: '#C6BDD4',
  dawn: '#FFFACD',
  dusk: '#9370DB',
};

interface FloorChartProps {
  className?: string;
}

export function FloorChart({ className }: FloorChartProps) {
  const { data, isLoading, isError } = useFloorPrices();

  // Transform data for Recharts
  const chartData = AXIE_CLASSES.map((axieClass) => ({
    name: axieClass.charAt(0).toUpperCase() + axieClass.slice(1),
    class: axieClass,
    floor: data?.data?.[axieClass] ?? 0,
    color: CLASS_COLORS[axieClass] ?? '#888888',
  })).filter((item) => item.floor > 0);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          Floor Prices by Class
        </CardTitle>
        <CardDescription>Current lowest listing prices per class</CardDescription>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            Failed to load floor prices.
          </div>
        ) : isLoading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="space-y-2 w-full">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-4/5" />
              <Skeleton className="h-8 w-3/5" />
              <Skeleton className="h-8 w-2/5" />
              <Skeleton className="h-8 w-1/5" />
            </div>
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No floor price data available.
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                <XAxis
                  type="number"
                  tickFormatter={(value) => `${value.toFixed(3)}`}
                  fontSize={12}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={70}
                  fontSize={12}
                />
                <Tooltip
                  formatter={(value) => {
                    const numValue = typeof value === 'number' ? value : 0;
                    return [`${numValue.toFixed(4)} ETH`, 'Floor Price'];
                  }}
                  labelStyle={{ fontWeight: 'bold' }}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="floor" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
