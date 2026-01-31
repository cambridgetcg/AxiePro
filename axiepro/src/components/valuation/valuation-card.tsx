'use client';

import { cn } from '@/lib/utils';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { PriceDisplay } from './price-display';
import { DealIndicator } from './deal-indicator';
import { ValuationBadge } from './valuation-badge';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import type { ValuationResponse } from '@/types/valuation';

interface ValuationCardProps {
  /** Full valuation response */
  valuation: ValuationResponse;
  /** Show feature breakdown section */
  showFeatureBreakdown?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Full valuation display card.
 *
 * Shows:
 * - Axie ID and class
 * - Fair value with confidence interval
 * - Current listing and discount
 * - Market context (floor, average)
 * - Optional feature breakdown
 */
export function ValuationCard({
  valuation,
  showFeatureBreakdown = false,
  className,
}: ValuationCardProps) {
  const [showBreakdown, setShowBreakdown] = useState(showFeatureBreakdown);

  const { deal_analysis, market_context } = valuation;

  // Handle unavailable valuation
  if (!valuation.valuation || !deal_analysis || !market_context) {
    return (
      <Card className={cn('w-full', className)}>
        <CardHeader className="pb-2">
          <CardTitle className="text-xl">Axie #{valuation.axie_id}</CardTitle>
        </CardHeader>
        <CardContent className="py-6 text-center">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {valuation.metadata?.reason || 'Valuation data unavailable'}
          </p>
        </CardContent>
      </Card>
    );
  }

  const fairValue = valuation.valuation.ensemble_eth ?? valuation.valuation.hedonic_eth;

  // Sort feature contributions by absolute value
  const sortedContributions = Object.entries(valuation.feature_contributions)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    .slice(0, 10);

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl">
              Axie #{valuation.axie_id}
            </CardTitle>
            <CardDescription className="flex items-center gap-2 mt-1">
              <ValuationBadge
                confidenceScore={valuation.valuation.confidence_score}
              />
              {(deal_analysis.is_deal || deal_analysis.is_snipe) && (
                <DealIndicator
                  discountPercent={deal_analysis.discount_percent}
                  isDeal={deal_analysis.is_deal}
                  isSnipe={deal_analysis.is_snipe}
                />
              )}
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <a
              href={`https://app.axieinfinity.com/marketplace/axies/${valuation.axie_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="gap-1"
            >
              <ExternalLink className="h-3 w-3" />
              View
            </a>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Valuation Section */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Fair Value</p>
            <PriceDisplay ethValue={fairValue} size="lg" />
            {valuation.valuation.confidence_lower_eth &&
              valuation.valuation.confidence_upper_eth && (
                <p className="text-xs text-muted-foreground mt-1">
                  Range: {valuation.valuation.confidence_lower_eth.toFixed(4)} -{' '}
                  {valuation.valuation.confidence_upper_eth.toFixed(4)} ETH
                </p>
              )}
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">Listing Price</p>
            {market_context.current_listing_eth ? (
              <>
                <PriceDisplay
                  ethValue={market_context.current_listing_eth}
                  size="lg"
                  trendPercent={
                    deal_analysis.discount_percent !== 0
                      ? -deal_analysis.discount_percent
                      : undefined
                  }
                />
                {deal_analysis.deal_score > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Deal Score: {deal_analysis.deal_score}/100
                  </p>
                )}
              </>
            ) : (
              <span className="text-lg text-muted-foreground">Not Listed</span>
            )}
          </div>
        </div>

        {/* Market Context */}
        <div className="grid grid-cols-2 gap-4 pt-2 border-t">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Class Floor</p>
            <PriceDisplay ethValue={market_context.class_floor_eth} size="sm" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Class Average</p>
            <PriceDisplay ethValue={market_context.class_avg_eth} size="sm" />
          </div>
        </div>

        {/* Feature Breakdown (Collapsible) */}
        {sortedContributions.length > 0 && (
          <div className="pt-2 border-t">
            <button
              onClick={() => setShowBreakdown(!showBreakdown)}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
            >
              {showBreakdown ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Feature Contributions
            </button>

            {showBreakdown && (
              <div className="mt-2 space-y-1.5">
                {sortedContributions.map(([feature, value]) => (
                  <div
                    key={feature}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted-foreground truncate max-w-[200px]">
                      {feature}
                    </span>
                    <span
                      className={cn(
                        'font-mono',
                        value > 0 && 'text-green-500',
                        value < 0 && 'text-red-500'
                      )}
                    >
                      {value > 0 ? '+' : ''}
                      {(value * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Metadata */}
        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            Model: {valuation.metadata.model_version || 'N/A'}
            {valuation.metadata.computed_at && (
              <> | {new Date(valuation.metadata.computed_at).toLocaleString()}</>
            )}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Loading skeleton for ValuationCard.
 */
export function ValuationCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-8 w-16" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-8 w-28" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-8 w-24" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 pt-2 border-t">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-20" />
        </div>
      </CardContent>
    </Card>
  );
}
