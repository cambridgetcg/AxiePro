'use client';

/**
 * Portfolio Summary Card - Shows total P&L overview.
 */
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  Info,
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { PortfolioSummary } from '@/types/portfolio';

interface PortfolioSummaryCardProps {
  summary: PortfolioSummary | undefined;
  isLoading?: boolean;
  className?: string;
}

export function PortfolioSummaryCard({
  summary,
  isLoading,
  className,
}: PortfolioSummaryCardProps) {
  if (isLoading) {
    return <PortfolioSummaryCardSkeleton className={className} />;
  }

  if (!summary) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center">
            Connect a wallet to view portfolio P&L
          </p>
        </CardContent>
      </Card>
    );
  }

  const isProfitable = (summary.total_unrealized_pnl_eth ?? 0) >= 0;
  const hasFullData = summary.total_cost_basis_eth !== null;

  const stats = [
    {
      label: 'Holdings',
      value: summary.holdings_count.toString(),
      icon: Wallet,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      label: 'Cost Basis',
      value: hasFullData
        ? `${summary.total_cost_basis_eth?.toFixed(3)} ETH`
        : 'Incomplete',
      icon: DollarSign,
      color: hasFullData ? 'text-blue-500' : 'text-muted-foreground',
      bgColor: 'bg-blue-500/10',
      tooltip: !hasFullData
        ? 'Some holdings are missing cost basis data. Add acquisition prices for complete P&L.'
        : undefined,
    },
    {
      label: 'Current Value',
      value:
        summary.total_current_value_eth !== null
          ? `${summary.total_current_value_eth.toFixed(3)} ETH`
          : 'N/A',
      icon: DollarSign,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      label: 'Unrealized P&L',
      value:
        summary.total_unrealized_pnl_eth !== null
          ? `${isProfitable ? '+' : ''}${summary.total_unrealized_pnl_eth.toFixed(3)} ETH`
          : 'N/A',
      icon: isProfitable ? TrendingUp : TrendingDown,
      color: isProfitable ? 'text-green-500' : 'text-red-500',
      bgColor: isProfitable ? 'bg-green-500/10' : 'bg-red-500/10',
      secondary:
        summary.total_unrealized_pnl_percent !== null
          ? `${isProfitable ? '+' : ''}${summary.total_unrealized_pnl_percent.toFixed(1)}%`
          : undefined,
    },
  ];

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Portfolio Summary
          </span>
          {!hasFullData && (
            <Badge variant="outline" className="text-xs text-yellow-600">
              Incomplete Data
            </Badge>
          )}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {summary.wallet_address.slice(0, 6)}...{summary.wallet_address.slice(-4)}
        </p>
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
              <div className="flex items-center gap-1">
                <span className={cn('text-lg font-bold', stat.color)}>
                  {stat.value}
                </span>
                {stat.tooltip && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs">{stat.tooltip}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
              </div>
              {stat.secondary && (
                <span className={cn('text-xs', stat.color)}>{stat.secondary}</span>
              )}
              <span className="text-xs text-muted-foreground">{stat.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function PortfolioSummaryCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-20" />
        </div>
        <Skeleton className="h-4 w-32 mt-1" />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="flex flex-col items-center justify-center p-4 rounded-lg bg-muted/50"
            >
              <Skeleton className="h-6 w-6 mb-2" />
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-3 w-12 mt-1" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
