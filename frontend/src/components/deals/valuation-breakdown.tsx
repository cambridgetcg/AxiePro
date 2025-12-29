'use client';

/**
 * Valuation Breakdown component showing hedonic price decomposition.
 */
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Info, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { ValuationResponse } from '@/types/valuation';

interface ValuationBreakdownProps {
  /** Full valuation response */
  valuation: ValuationResponse;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Progress bar component for visualizing contribution.
 */
function ContributionBar({
  value,
  maxValue = 0.5,
}: {
  value: number;
  maxValue?: number;
}) {
  const normalizedValue = Math.min(Math.abs(value), maxValue) / maxValue;
  const isPositive = value >= 0;

  return (
    <div className="flex items-center gap-2 w-full">
      {/* Negative side */}
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden flex justify-end">
        {!isPositive && (
          <div
            className="h-full bg-red-500 rounded-full transition-all"
            style={{ width: `${normalizedValue * 100}%` }}
          />
        )}
      </div>
      {/* Center line */}
      <div className="w-px h-4 bg-border" />
      {/* Positive side */}
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        {isPositive && (
          <div
            className="h-full bg-green-500 rounded-full transition-all"
            style={{ width: `${normalizedValue * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}

/**
 * Z-Score gauge visualization.
 */
function ZScoreGauge({ zScore }: { zScore: number | null }) {
  if (zScore === null) return null;

  // Z-score ranges: < -2 (great deal), -2 to -1 (good deal), -1 to 1 (fair), > 1 (overpriced)
  const clampedZ = Math.max(-3, Math.min(3, zScore));
  const position = ((clampedZ + 3) / 6) * 100; // Map -3 to 3 => 0% to 100%

  const getLabel = () => {
    if (zScore <= -2) return { text: 'Exceptional', color: 'text-green-500' };
    if (zScore <= -1) return { text: 'Good Deal', color: 'text-green-400' };
    if (zScore <= 1) return { text: 'Fair Price', color: 'text-yellow-500' };
    return { text: 'Overpriced', color: 'text-red-500' };
  };

  const label = getLabel();

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Z-Score</span>
        <span className={cn('text-sm font-medium', label.color)}>
          {zScore.toFixed(2)} ({label.text})
        </span>
      </div>
      <div className="relative h-3 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full">
        <div
          className="absolute top-0 w-3 h-3 bg-white border-2 border-gray-800 rounded-full shadow transform -translate-x-1/2 transition-all"
          style={{ left: `${position}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Undervalued</span>
        <span>Fair</span>
        <span>Overvalued</span>
      </div>
    </div>
  );
}

/**
 * Confidence indicator bar.
 */
function ConfidenceBar({ confidence }: { confidence: number }) {
  const percentage = confidence * 100;
  const color =
    confidence >= 0.8 ? 'bg-green-500' : confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Model Confidence</span>
        <span className="text-sm font-medium">{percentage.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Main valuation breakdown component.
 */
export function ValuationBreakdown({ valuation, className }: ValuationBreakdownProps) {
  const { deal_analysis, market_context, feature_contributions } = valuation;
  const fairValue = valuation.valuation.ensemble_eth ?? valuation.valuation.hedonic_eth ?? 0;
  const listingPrice = market_context.current_listing_eth ?? 0;
  const classFloor = market_context.class_floor_eth ?? 0;

  // Sort and get top feature contributions
  const sortedContributions = Object.entries(feature_contributions)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    .slice(0, 8);

  // Calculate premium over floor
  const premiumOverFloor = classFloor > 0 ? ((fairValue - classFloor) / classFloor) * 100 : 0;

  // Generate "Why it's a deal" explanation
  const getDealExplanation = () => {
    const reasons: string[] = [];

    if (deal_analysis.discount_percent >= 30) {
      reasons.push(`Listed ${deal_analysis.discount_percent.toFixed(0)}% below fair value`);
    } else if (deal_analysis.discount_percent >= 15) {
      reasons.push(`Listed ${deal_analysis.discount_percent.toFixed(0)}% under market value`);
    }

    if (deal_analysis.z_score && deal_analysis.z_score <= -1.5) {
      reasons.push('Statistically significant underpricing');
    }

    if (listingPrice < classFloor && classFloor > 0) {
      reasons.push('Below class floor price');
    }

    // Check for valuable traits
    const valuableTraits = sortedContributions.filter(([, v]) => v > 0.1);
    if (valuableTraits.length > 0) {
      reasons.push(`Has ${valuableTraits.length} premium trait(s)`);
    }

    return reasons.length > 0 ? reasons : ['Good value based on trait analysis'];
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Price Decomposition */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Info className="h-4 w-4" />
            Price Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xs text-muted-foreground">Class Floor</p>
              <p className="font-bold">{classFloor.toFixed(4)} ETH</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Fair Value</p>
              <p className="font-bold text-primary">{fairValue.toFixed(4)} ETH</p>
              {premiumOverFloor > 0 && (
                <p className="text-xs text-green-500">+{premiumOverFloor.toFixed(0)}% vs floor</p>
              )}
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Listing</p>
              <p className="font-bold text-green-500">{listingPrice.toFixed(4)} ETH</p>
              <p className="text-xs text-green-500">-{deal_analysis.discount_percent.toFixed(0)}%</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Z-Score & Confidence */}
      <Card>
        <CardContent className="pt-4 space-y-4">
          <ZScoreGauge zScore={deal_analysis.z_score} />
          <ConfidenceBar confidence={valuation.valuation.confidence_score} />
        </CardContent>
      </Card>

      {/* Feature Contributions */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Trait Contributions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {sortedContributions.map(([feature, value]) => (
            <div key={feature} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground truncate max-w-[180px]">
                  {feature.replace(/_/g, ' ')}
                </span>
                <span
                  className={cn(
                    'font-mono font-medium',
                    value > 0 ? 'text-green-500' : 'text-red-500'
                  )}
                >
                  {value > 0 ? '+' : ''}
                  {(value * 100).toFixed(1)}%
                </span>
              </div>
              <ContributionBar value={value} />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Why It's a Deal */}
      {deal_analysis.is_deal || deal_analysis.is_snipe ? (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-green-500">
              <CheckCircle2 className="h-4 w-4" />
              Why It&apos;s a {deal_analysis.is_snipe ? 'Snipe' : 'Deal'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {getDealExplanation().map((reason, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-green-500 mt-1">•</span>
                  {reason}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-yellow-500/50 bg-yellow-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-yellow-500">
              <AlertTriangle className="h-4 w-4" />
              Fair Value Assessment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              This Axie is priced near its fair market value based on trait analysis.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/**
 * Loading skeleton for ValuationBreakdown.
 */
export function ValuationBreakdownSkeleton() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="text-center space-y-2">
                <Skeleton className="h-3 w-16 mx-auto" />
                <Skeleton className="h-5 w-20 mx-auto" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-1">
              <div className="flex justify-between">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-12" />
              </div>
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
