'use client';

/**
 * Meta Summary Card - Shows counts of meta shifts by type.
 */
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Sparkles, Activity } from 'lucide-react';
import type { MetaSummary } from '@/types/meta';

interface MetaSummaryCardProps {
  summary: MetaSummary | undefined;
  isLoading?: boolean;
  className?: string;
}

export function MetaSummaryCard({
  summary,
  isLoading,
  className,
}: MetaSummaryCardProps) {
  if (isLoading) {
    return <MetaSummaryCardSkeleton className={className} />;
  }

  if (!summary) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center">
            Meta analysis data not available
          </p>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    {
      label: 'Rising',
      value: summary.rising,
      icon: TrendingUp,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      label: 'Falling',
      value: summary.falling,
      icon: TrendingDown,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
    },
    {
      label: 'Emerging',
      value: summary.emerging,
      icon: Sparkles,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      label: 'Fading',
      value: summary.fading,
      icon: Activity,
      color: 'text-orange-500',
      bgColor: 'bg-orange-500/10',
    },
  ];

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center justify-between">
          <span>Meta Shifts Overview</span>
          <span className="text-sm font-normal text-muted-foreground">
            {summary.total_shifts} total
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className={cn(
                'flex flex-col items-center justify-center p-4 rounded-lg',
                stat.bgColor
              )}
            >
              <stat.icon className={cn('h-6 w-6 mb-2', stat.color)} />
              <span className={cn('text-2xl font-bold', stat.color)}>
                {stat.value}
              </span>
              <span className="text-xs text-muted-foreground">{stat.label}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground text-center mt-4">
          Last analyzed: {new Date(summary.timestamp).toLocaleString()}
        </p>
      </CardContent>
    </Card>
  );
}

function MetaSummaryCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-16" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="flex flex-col items-center justify-center p-4 rounded-lg bg-muted/50"
            >
              <Skeleton className="h-6 w-6 mb-2" />
              <Skeleton className="h-8 w-12" />
              <Skeleton className="h-3 w-16 mt-1" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
