'use client';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Zap, Target } from 'lucide-react';

interface DealIndicatorProps {
  /** Discount percentage (negative means below fair value) */
  discountPercent: number;
  /** Whether this is classified as a deal */
  isDeal: boolean;
  /** Whether this is classified as a snipe (exceptional deal) */
  isSnipe: boolean;
  /** Display size */
  size?: 'sm' | 'md';
  /** Additional CSS classes */
  className?: string;
}

/**
 * Visual indicator for deal/snipe status.
 *
 * - Snipe: Red/orange badge with Zap icon (-40%+ discount)
 * - Deal: Green badge with Target icon (-20% to -40% discount)
 * - No indicator for non-deals
 */
export function DealIndicator({
  discountPercent,
  isDeal,
  isSnipe,
  size = 'md',
  className,
}: DealIndicatorProps) {
  if (!isDeal && !isSnipe) {
    return null;
  }

  const Icon = isSnipe ? Zap : Target;
  const formattedDiscount = Math.abs(discountPercent).toFixed(0);

  return (
    <Badge
      variant={isSnipe ? 'destructive' : 'default'}
      className={cn(
        'gap-1',
        size === 'sm' && 'text-xs px-1.5 py-0.5',
        isSnipe && 'bg-orange-500 hover:bg-orange-600',
        !isSnipe && isDeal && 'bg-green-500 hover:bg-green-600',
        className
      )}
    >
      <Icon className={cn('h-3 w-3', size === 'sm' && 'h-2.5 w-2.5')} />
      <span>-{formattedDiscount}%</span>
    </Badge>
  );
}
