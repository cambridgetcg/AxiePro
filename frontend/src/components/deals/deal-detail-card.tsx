'use client';

/**
 * Deal Detail Card component with expandable valuation breakdown.
 */
import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PriceDisplay } from '@/components/valuation/price-display';
import { DealIndicator } from '@/components/valuation/deal-indicator';
import {
  ValuationBreakdown,
  ValuationBreakdownSkeleton,
} from './valuation-breakdown';
import { useValuation } from '@/hooks/use-valuation';
import {
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Target,
  Zap,
  Clock,
} from 'lucide-react';
import type { Deal } from '@/types/valuation';

interface DealDetailCardProps {
  /** Deal data */
  deal: Deal;
  /** Whether to start expanded */
  defaultExpanded?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Enhanced deal card with expandable valuation breakdown.
 */
export function DealDetailCard({
  deal,
  defaultExpanded = false,
  className,
}: DealDetailCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Fetch full valuation when expanded
  const { data: valuation, isLoading: isLoadingValuation } = useValuation(
    deal.axie_id,
    { enabled: isExpanded }
  );

  const isSnipe = deal.deal_type === 'snipe';
  const isDeal = deal.deal_type === 'deal';

  // Format detected time
  const detectedTime = new Date(deal.detected_at);
  const timeAgo = getTimeAgo(detectedTime);

  return (
    <Card
      className={cn(
        'transition-all duration-200',
        isExpanded && 'ring-2 ring-primary/20',
        isSnipe && 'border-orange-500/30',
        isDeal && !isSnipe && 'border-green-500/30',
        className
      )}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              Axie #{deal.axie_id}
              {isSnipe && (
                <Badge variant="outline" className="bg-orange-500/10 text-orange-500 border-orange-500/50">
                  <Zap className="h-3 w-3 mr-1" />
                  Snipe
                </Badge>
              )}
              {isDeal && !isSnipe && (
                <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/50">
                  <Target className="h-3 w-3 mr-1" />
                  Deal
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="flex items-center gap-2">
              <span className="capitalize">{deal.class}</span>
              <span className="text-muted-foreground/50">•</span>
              <span className="flex items-center gap-1 text-xs">
                <Clock className="h-3 w-3" />
                {timeAgo}
              </span>
            </CardDescription>
          </div>
          <DealIndicator
            discountPercent={deal.discount_percent}
            isDeal={isDeal}
            isSnipe={isSnipe}
            size="md"
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Price Comparison */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Listing</p>
            <PriceDisplay ethValue={deal.listing_price_eth} size="md" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Fair Value</p>
            <PriceDisplay ethValue={deal.fair_value_eth} size="md" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Savings</p>
            <p className="text-lg font-bold text-green-500">
              {(deal.fair_value_eth - deal.listing_price_eth).toFixed(4)} ETH
            </p>
          </div>
        </div>

        {/* Deal Score Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Deal Score</span>
            <span className="font-medium">{deal.deal_score.toFixed(0)}/100</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                deal.deal_score >= 80
                  ? 'bg-green-500'
                  : deal.deal_score >= 60
                    ? 'bg-yellow-500'
                    : 'bg-orange-500'
              )}
              style={{ width: `${deal.deal_score}%` }}
            />
          </div>
        </div>

        {/* Z-Score */}
        {deal.z_score !== null && (
          <div className="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
            <span className="text-sm text-muted-foreground">Statistical Confidence</span>
            <Badge
              variant="outline"
              className={cn(
                deal.z_score <= -2
                  ? 'border-green-500 text-green-500'
                  : deal.z_score <= -1
                    ? 'border-yellow-500 text-yellow-500'
                    : 'border-muted'
              )}
            >
              Z = {deal.z_score.toFixed(2)}
            </Badge>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-4 w-4 mr-1" />
                Hide Details
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-1" />
                Show Analysis
              </>
            )}
          </Button>
          <Button
            size="sm"
            className="flex-1"
            asChild
          >
            <a
              href={deal.marketplace_url}
              target="_blank"
              rel="noopener noreferrer"
              className="gap-1"
            >
              <ExternalLink className="h-4 w-4" />
              Buy Now
            </a>
          </Button>
        </div>

        {/* Expanded Valuation Breakdown */}
        {isExpanded && (
          <div className="pt-4 border-t">
            {isLoadingValuation ? (
              <ValuationBreakdownSkeleton />
            ) : valuation ? (
              <ValuationBreakdown valuation={valuation} />
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                Unable to load valuation details.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Loading skeleton for DealDetailCard.
 */
export function DealDetailCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-3 w-12" />
              <Skeleton className="h-6 w-20" />
            </div>
          ))}
        </div>
        <div className="space-y-1">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-12" />
          </div>
          <Skeleton className="h-2 w-full" />
        </div>
        <div className="flex gap-2 pt-2 border-t">
          <Skeleton className="h-9 flex-1" />
          <Skeleton className="h-9 flex-1" />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Helper function to format time ago.
 */
function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}
