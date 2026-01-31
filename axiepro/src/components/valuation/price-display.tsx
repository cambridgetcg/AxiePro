'use client';

import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface PriceDisplayProps {
  /** ETH value to display */
  ethValue: number | null;
  /** Display size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Optional trend percentage to show with arrow */
  trendPercent?: number;
  /** Additional CSS classes */
  className?: string;
  /** Show "N/A" when null, otherwise hide */
  showNa?: boolean;
}

/**
 * Formats an ETH value for display.
 * Uses appropriate decimal places based on magnitude.
 */
function formatEth(value: number): string {
  if (value >= 1) {
    return value.toFixed(2);
  } else if (value >= 0.1) {
    return value.toFixed(3);
  } else {
    return value.toFixed(4);
  }
}

/**
 * Displays an ETH price with optional trend indicator.
 *
 * Examples:
 * - "0.025 ETH"
 * - "0.025 ETH +12%" (with green arrow)
 * - "0.025 ETH -5%" (with red arrow)
 */
export function PriceDisplay({
  ethValue,
  size = 'md',
  trendPercent,
  className,
  showNa = true,
}: PriceDisplayProps) {
  if (ethValue === null) {
    if (!showNa) return null;
    return (
      <span
        className={cn(
          'text-muted-foreground',
          size === 'sm' && 'text-sm',
          size === 'lg' && 'text-2xl font-bold',
          className
        )}
      >
        N/A
      </span>
    );
  }

  const isPositiveTrend = trendPercent !== undefined && trendPercent > 0;
  const isNegativeTrend = trendPercent !== undefined && trendPercent < 0;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1',
        size === 'sm' && 'text-sm',
        size === 'md' && 'text-base',
        size === 'lg' && 'text-2xl font-bold',
        className
      )}
    >
      <span>{formatEth(ethValue)} ETH</span>

      {trendPercent !== undefined && trendPercent !== 0 && (
        <span
          className={cn(
            'inline-flex items-center gap-0.5',
            size === 'sm' && 'text-xs',
            size === 'md' && 'text-sm',
            size === 'lg' && 'text-base',
            isPositiveTrend && 'text-green-500',
            isNegativeTrend && 'text-red-500'
          )}
        >
          {isPositiveTrend ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {isPositiveTrend ? '+' : ''}
          {trendPercent.toFixed(0)}%
        </span>
      )}
    </span>
  );
}
