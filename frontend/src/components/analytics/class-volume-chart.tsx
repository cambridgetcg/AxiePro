'use client';

/**
 * Class Volume Chart component showing sales distribution by class.
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { PieChart as PieChartIcon } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
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

interface ClassVolumeChartProps {
  /** Sales data by class */
  data?: Record<string, number>;
  /** Loading state */
  isLoading?: boolean;
  /** Error state */
  isError?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function ClassVolumeChart({
  data,
  isLoading,
  isError,
  className,
}: ClassVolumeChartProps) {
  // Transform data for pie chart
  const chartData = AXIE_CLASSES.map((axieClass) => ({
    name: axieClass.charAt(0).toUpperCase() + axieClass.slice(1),
    value: data?.[axieClass] ?? 0,
    color: CLASS_COLORS[axieClass] ?? '#888888',
  })).filter((item) => item.value > 0);

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChartIcon className="h-5 w-5 text-primary" />
          Sales by Class
        </CardTitle>
        <CardDescription>Distribution of recent sales volume</CardDescription>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            Failed to load volume data.
          </div>
        ) : isLoading ? (
          <div className="h-64 flex items-center justify-center">
            <Skeleton className="h-48 w-48 rounded-full" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No volume data available.
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => {
                    const numValue = typeof value === 'number' ? value : 0;
                    return [
                      `${numValue.toLocaleString()} (${((numValue / total) * 100).toFixed(1)}%)`,
                      'Volume',
                    ];
                  }}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
