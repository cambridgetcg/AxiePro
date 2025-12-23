'use client';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface ValuationBadgeProps {
  /** Model confidence score (0-1) */
  confidenceScore: number;
  /** Deal score (0-100), optional */
  dealScore?: number;
  /** Display variant */
  variant?: 'confidence' | 'deal-score';
  /** Additional CSS classes */
  className?: string;
}

/**
 * Badge showing confidence score or deal score.
 *
 * Confidence colors:
 * - High (>=0.7): Green
 * - Medium (>=0.4): Yellow
 * - Low (<0.4): Red
 *
 * Deal score colors:
 * - Snipe (>=80): Orange/Red
 * - Deal (>=50): Green
 * - Below (<50): Gray
 */
export function ValuationBadge({
  confidenceScore,
  dealScore,
  variant = 'confidence',
  className,
}: ValuationBadgeProps) {
  if (variant === 'deal-score' && dealScore !== undefined) {
    const isSnipe = dealScore >= 80;
    const isDeal = dealScore >= 50;

    return (
      <Badge
        variant={isSnipe ? 'destructive' : isDeal ? 'default' : 'secondary'}
        className={cn(
          isSnipe && 'bg-orange-500 hover:bg-orange-600',
          isDeal && !isSnipe && 'bg-green-500 hover:bg-green-600',
          className
        )}
      >
        Score: {dealScore}
      </Badge>
    );
  }

  const isHigh = confidenceScore >= 0.7;
  const isMedium = confidenceScore >= 0.4;
  const percent = Math.round(confidenceScore * 100);

  return (
    <Badge
      variant="outline"
      className={cn(
        isHigh && 'border-green-500 text-green-500',
        isMedium && !isHigh && 'border-yellow-500 text-yellow-500',
        !isMedium && 'border-red-500 text-red-500',
        className
      )}
    >
      {percent}% confidence
    </Badge>
  );
}
