'use client';

import { cn } from '@/lib/utils';
import { PriceDisplay } from './price-display';
import { DealIndicator } from './deal-indicator';
import { Skeleton } from '@/components/ui/skeleton';

interface ValuationCompactProps {
  /** Axie ID */
  axieId: number;
  /** Fair value estimate in ETH */
  valuationEth: number | null;
  /** Current listing price in ETH */
  listingEth?: number | null;
  /** Discount percentage */
  discountPercent?: number;
  /** Whether this is a deal */
  isDeal?: boolean;
  /** Whether this is a snipe */
  isSnipe?: boolean;
  /** Loading state */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Compact inline valuation display for use in lists/tables.
 *
 * Shows: Fair Value | Listing | Deal Badge
 */
export function ValuationCompact({
  valuationEth,
  listingEth,
  discountPercent = 0,
  isDeal = false,
  isSnipe = false,
  isLoading = false,
  className,
}: ValuationCompactProps) {
  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>
    );
  }

  return (
    <div className={cn('flex items-center gap-3 flex-wrap', className)}>
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-muted-foreground">Fair:</span>
        <PriceDisplay ethValue={valuationEth} size="sm" />
      </div>

      {listingEth !== undefined && listingEth !== null && (
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">List:</span>
          <PriceDisplay ethValue={listingEth} size="sm" />
        </div>
      )}

      {(isDeal || isSnipe) && (
        <DealIndicator
          discountPercent={discountPercent}
          isDeal={isDeal}
          isSnipe={isSnipe}
          size="sm"
        />
      )}
    </div>
  );
}
