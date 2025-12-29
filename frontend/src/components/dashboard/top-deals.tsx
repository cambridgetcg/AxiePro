'use client';

/**
 * Top Deals component displaying live deal opportunities.
 */
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Target, ArrowRight, ExternalLink, TrendingDown, Zap } from 'lucide-react';
import { useDeals } from '@/hooks/use-deals';
import type { Deal } from '@/types/valuation';

interface DealRowProps {
  deal: Deal;
}

function DealRow({ deal }: DealRowProps) {
  const discountColor =
    deal.discount_percent >= 30
      ? 'text-green-500'
      : deal.discount_percent >= 20
        ? 'text-green-400'
        : 'text-yellow-500';

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <span className="text-sm font-bold text-primary">
            #{deal.axie_id.toString().slice(-4)}
          </span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <p className="font-medium">Axie #{deal.axie_id}</p>
            <Badge variant="outline" className="capitalize text-xs">
              {deal.class}
            </Badge>
            {deal.deal_type === 'snipe' && (
              <Badge variant="secondary" className="text-xs">
                <Zap className="h-3 w-3 mr-1" />
                Snipe
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{deal.listing_price_eth.toFixed(4)} ETH</span>
            <span className="text-muted-foreground/50">vs</span>
            <span>{deal.fair_value_eth.toFixed(4)} ETH fair</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <div className={`flex items-center gap-1 font-bold ${discountColor}`}>
            <TrendingDown className="h-4 w-4" />
            -{deal.discount_percent.toFixed(0)}%
          </div>
          <p className="text-xs text-muted-foreground">
            Score: {deal.deal_score.toFixed(0)}
          </p>
        </div>
        <a
          href={deal.marketplace_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground hover:text-primary transition-colors"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}

function DealRowSkeleton() {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <div>
          <Skeleton className="h-4 w-32 mb-2" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <Skeleton className="h-5 w-16 mb-1" />
          <Skeleton className="h-3 w-12" />
        </div>
        <Skeleton className="h-4 w-4" />
      </div>
    </div>
  );
}

interface TopDealsProps {
  limit?: number;
}

export function TopDeals({ limit = 5 }: TopDealsProps) {
  const { data, isLoading, isError } = useDeals({ minScore: 50 });

  const deals = data?.data?.slice(0, limit) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5 text-primary" />
          Top Deals
        </CardTitle>
        <CardDescription>Best value opportunities right now</CardDescription>
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="p-4 text-center text-muted-foreground">
            Failed to load deals. Please try again.
          </div>
        ) : isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: limit }).map((_, i) => (
              <DealRowSkeleton key={i} />
            ))}
          </div>
        ) : deals.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            No deals found at the moment. Check back soon!
          </div>
        ) : (
          <div className="space-y-3">
            {deals.map((deal) => (
              <DealRow key={deal.axie_id} deal={deal} />
            ))}
          </div>
        )}
        <Link href="/deals">
          <Button variant="ghost" className="w-full mt-4 gap-2">
            View All Deals
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
