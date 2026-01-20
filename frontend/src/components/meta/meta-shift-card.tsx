'use client';

/**
 * Meta Shift Card - Displays individual meta shift signal.
 */
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import {
  TrendingUp,
  TrendingDown,
  Sparkles,
  Activity,
  Info,
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { MetaShift, ShiftType } from '@/types/meta';
import { SHIFT_TYPE_CONFIG } from '@/types/meta';

interface MetaShiftCardProps {
  shift: MetaShift;
  className?: string;
}

const SHIFT_ICONS: Record<ShiftType, typeof TrendingUp> = {
  rising: TrendingUp,
  falling: TrendingDown,
  emerging: Sparkles,
  fading: Activity,
};

export function MetaShiftCard({ shift, className }: MetaShiftCardProps) {
  const config = SHIFT_TYPE_CONFIG[shift.shift_type];
  const Icon = SHIFT_ICONS[shift.shift_type];

  // Format trait key for display
  const formatTraitKey = (key: string) => {
    const parts = key.split(':');
    if (parts.length >= 2) {
      return {
        type: parts[0].charAt(0).toUpperCase() + parts[0].slice(1),
        name: parts.slice(1).join(' ').replace(/_/g, ' '),
      };
    }
    return { type: 'Trait', name: key };
  };

  const trait = formatTraitKey(shift.trait_key);

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base flex items-center gap-2">
              <span className="capitalize">{trait.name}</span>
              {shift.class && (
                <Badge variant="outline" className="text-xs capitalize">
                  {shift.class}
                </Badge>
              )}
            </CardTitle>
            <p className="text-xs text-muted-foreground">{trait.type}</p>
          </div>
          <Badge className={cn('flex items-center gap-1', config.bgColor, config.color)}>
            <Icon className="h-3 w-3" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Confidence Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground flex items-center gap-1">
              Confidence
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      Higher confidence indicates more aligned signals
                      (price velocity, volume, trend).
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </span>
            <span className="font-medium">{shift.confidence}%</span>
          </div>
          <Progress
            value={shift.confidence}
            className="h-2"
          />
        </div>

        {/* Signals */}
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Signals</p>
          <div className="flex flex-wrap gap-1">
            {shift.signals.map((signal, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {signal}
              </Badge>
            ))}
          </div>
        </div>

        {/* Price Velocity */}
        {shift.price_velocity_24h && (
          <div className="flex items-center justify-between text-sm p-2 bg-muted/50 rounded-lg">
            <span className="text-muted-foreground">24h Change</span>
            <span
              className={cn(
                'font-medium',
                shift.price_velocity_24h.velocity_percent >= 0
                  ? 'text-green-500'
                  : 'text-red-500'
              )}
            >
              {shift.price_velocity_24h.velocity_percent >= 0 ? '+' : ''}
              {shift.price_velocity_24h.velocity_percent.toFixed(1)}%
            </span>
          </div>
        )}

        {/* 7d Trend */}
        {shift.price_velocity_7d && (
          <div className="flex items-center justify-between text-sm p-2 bg-muted/50 rounded-lg">
            <span className="text-muted-foreground">7d Trend</span>
            <span
              className={cn(
                'font-medium',
                shift.price_velocity_7d.velocity_percent >= 0
                  ? 'text-green-500'
                  : 'text-red-500'
              )}
            >
              {shift.price_velocity_7d.velocity_percent >= 0 ? '+' : ''}
              {shift.price_velocity_7d.velocity_percent.toFixed(1)}%
            </span>
          </div>
        )}

        {/* Volume Change */}
        {shift.volume_change && (
          <div className="flex items-center justify-between text-sm p-2 bg-muted/50 rounded-lg">
            <span className="text-muted-foreground">Volume Change</span>
            <span
              className={cn(
                'font-medium',
                shift.volume_change.change_percent >= 0
                  ? 'text-green-500'
                  : 'text-red-500'
              )}
            >
              {shift.volume_change.change_percent >= 0 ? '+' : ''}
              {shift.volume_change.change_percent.toFixed(0)}%
            </span>
          </div>
        )}

        {/* Timestamp */}
        <p className="text-xs text-muted-foreground text-right">
          Detected: {new Date(shift.detected_at).toLocaleString()}
        </p>
      </CardContent>
    </Card>
  );
}

export function MetaShiftCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-6 w-20" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-12" />
          </div>
          <Skeleton className="h-2 w-full" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-16" />
          <div className="flex gap-1">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  );
}
