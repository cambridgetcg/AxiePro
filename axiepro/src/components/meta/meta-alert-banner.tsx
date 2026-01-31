'use client';

/**
 * Meta Alert Banner - Shows high-confidence meta shifts on homepage.
 */
import { cn } from '@/lib/utils';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  TrendingUp,
  TrendingDown,
  Sparkles,
  Activity,
  ArrowRight,
  X,
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import type { MetaShift, ShiftType } from '@/types/meta';
import { SHIFT_TYPE_CONFIG } from '@/types/meta';

interface MetaAlertBannerProps {
  shifts: MetaShift[];
  isLoading?: boolean;
  className?: string;
  maxDisplay?: number;
}

const SHIFT_ICONS: Record<ShiftType, typeof TrendingUp> = {
  rising: TrendingUp,
  falling: TrendingDown,
  emerging: Sparkles,
  fading: Activity,
};

export function MetaAlertBanner({
  shifts,
  isLoading,
  className,
  maxDisplay = 3,
}: MetaAlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  if (isLoading) {
    return <MetaAlertBannerSkeleton className={className} />;
  }

  // Filter high-confidence shifts (>= 70%)
  const highConfidenceShifts = shifts
    .filter((s) => s.confidence >= 70)
    .slice(0, maxDisplay);

  if (highConfidenceShifts.length === 0) return null;

  // Determine alert variant based on shift types
  const hasRising = highConfidenceShifts.some((s) => s.shift_type === 'rising');
  const hasFalling = highConfidenceShifts.some((s) => s.shift_type === 'falling');

  const formatTraitName = (key: string) => {
    const parts = key.split(':');
    if (parts.length >= 2) {
      return parts.slice(1).join(' ').replace(/_/g, ' ');
    }
    return key;
  };

  return (
    <Alert
      className={cn(
        'relative border-2',
        hasRising && !hasFalling && 'border-green-500/50 bg-green-500/5',
        hasFalling && !hasRising && 'border-red-500/50 bg-red-500/5',
        hasRising && hasFalling && 'border-blue-500/50 bg-blue-500/5',
        !hasRising && !hasFalling && 'border-orange-500/50 bg-orange-500/5',
        className
      )}
    >
      <Sparkles className="h-4 w-4" />
      <AlertTitle className="flex items-center justify-between">
        <span>Meta Shift Alert</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 -mr-2"
          onClick={() => setDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      </AlertTitle>
      <AlertDescription className="mt-2">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {highConfidenceShifts.map((shift, index) => {
            const config = SHIFT_TYPE_CONFIG[shift.shift_type];
            const Icon = SHIFT_ICONS[shift.shift_type];
            return (
              <Badge
                key={index}
                variant="secondary"
                className={cn('flex items-center gap-1', config.bgColor, config.color)}
              >
                <Icon className="h-3 w-3" />
                <span className="capitalize">{formatTraitName(shift.trait_key)}</span>
                <span className="opacity-70">({shift.confidence}%)</span>
              </Badge>
            );
          })}
        </div>
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            High-confidence signals detected. Review meta shifts for trading opportunities.
          </p>
          <Button variant="link" size="sm" className="p-0 h-auto" asChild>
            <Link href="/meta" className="flex items-center gap-1">
              View All
              <ArrowRight className="h-3 w-3" />
            </Link>
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}

function MetaAlertBannerSkeleton({ className }: { className?: string }) {
  return (
    <Alert className={cn('relative', className)}>
      <Skeleton className="h-4 w-4" />
      <AlertTitle>
        <Skeleton className="h-5 w-32" />
      </AlertTitle>
      <AlertDescription className="mt-2">
        <div className="flex gap-2 mb-3">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-6 w-28" />
          <Skeleton className="h-6 w-20" />
        </div>
        <Skeleton className="h-4 w-full max-w-md" />
      </AlertDescription>
    </Alert>
  );
}
