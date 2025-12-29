'use client';

/**
 * Top Deals Table component showing deal opportunities in table format.
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Target, ExternalLink, Zap, TrendingDown } from 'lucide-react';
import { useDeals } from '@/hooks/use-deals';
import { cn } from '@/lib/utils';

interface TopDealsTableProps {
  limit?: number;
  className?: string;
}

export function TopDealsTable({ limit = 10, className }: TopDealsTableProps) {
  const { data, isLoading, isError } = useDeals({ minScore: 60 });

  const deals = data?.data?.slice(0, limit) ?? [];

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5 text-primary" />
          Top Deal Opportunities
        </CardTitle>
        <CardDescription>Best value Axies currently listed</CardDescription>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="py-8 text-center text-muted-foreground">
            Failed to load deals data.
          </div>
        ) : isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <div className="flex items-center gap-4">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-6 w-12" />
                </div>
              </div>
            ))}
          </div>
        ) : deals.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            No deals found at the moment.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-xs text-muted-foreground uppercase tracking-wider">
                  <th className="text-left py-2 font-medium">Axie</th>
                  <th className="text-left py-2 font-medium">Class</th>
                  <th className="text-right py-2 font-medium">Listing</th>
                  <th className="text-right py-2 font-medium">Fair Value</th>
                  <th className="text-right py-2 font-medium">Discount</th>
                  <th className="text-right py-2 font-medium">Score</th>
                  <th className="text-right py-2 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((deal, index) => (
                  <tr
                    key={deal.axie_id}
                    className={cn(
                      'border-b last:border-0 hover:bg-muted/50 transition-colors',
                      index % 2 === 0 && 'bg-muted/20'
                    )}
                  >
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">#{deal.axie_id}</span>
                        {deal.deal_type === 'snipe' && (
                          <Badge variant="outline" className="text-orange-500 border-orange-500/50 text-xs">
                            <Zap className="h-3 w-3 mr-0.5" />
                            Snipe
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3">
                      <Badge variant="secondary" className="capitalize text-xs">
                        {deal.class}
                      </Badge>
                    </td>
                    <td className="py-3 text-right font-mono text-sm">
                      {deal.listing_price_eth.toFixed(4)} ETH
                    </td>
                    <td className="py-3 text-right font-mono text-sm text-muted-foreground">
                      {deal.fair_value_eth.toFixed(4)} ETH
                    </td>
                    <td className="py-3 text-right">
                      <span className="flex items-center justify-end gap-1 text-green-500 font-medium">
                        <TrendingDown className="h-3 w-3" />
                        -{deal.discount_percent.toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-xs',
                          deal.deal_score >= 80
                            ? 'border-green-500 text-green-500'
                            : deal.deal_score >= 60
                              ? 'border-yellow-500 text-yellow-500'
                              : 'border-muted'
                        )}
                      >
                        {deal.deal_score.toFixed(0)}
                      </Badge>
                    </td>
                    <td className="py-3 text-right">
                      <Button variant="ghost" size="sm" asChild>
                        <a
                          href={deal.marketplace_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
