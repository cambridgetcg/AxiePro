/**
 * TypeScript types for the Meta Shifts API.
 *
 * These types match the backend response schemas from
 * backend/src/api/routes/meta.py
 */

/**
 * Shift type classification.
 */
export type ShiftType = 'rising' | 'falling' | 'emerging' | 'fading';

/**
 * Price velocity data for a time period.
 */
export interface PriceVelocity {
  current_price: number | null;
  past_price: number | null;
  velocity_percent: number;
  period_hours: number;
}

/**
 * Volume change data.
 */
export interface VolumeChange {
  current_volume: number;
  past_volume: number;
  change_percent: number;
  period_hours: number;
}

/**
 * Individual meta shift signal.
 */
export interface MetaShift {
  trait_key: string;
  class: string | null;
  shift_type: ShiftType;
  confidence: number; // 0-100
  signals: string[];
  price_velocity_24h: PriceVelocity | null;
  price_velocity_7d: PriceVelocity | null;
  volume_change: VolumeChange | null;
  detected_at: string; // ISO timestamp
}

/**
 * Meta shifts summary.
 */
export interface MetaSummary {
  timestamp: string;
  total_shifts: number;
  rising: number;
  falling: number;
  emerging: number;
  fading: number;
}

/**
 * Meta summary response from GET /meta/summary
 */
export interface MetaSummaryResponse {
  success: boolean;
  data: MetaSummary;
  meta: {
    cache_key: string;
    ttl_seconds: number;
  };
}

/**
 * Meta shifts list response from GET /meta/shifts
 */
export interface MetaShiftsResponse {
  success: boolean;
  data: MetaShift[];
  meta: {
    count: number;
    shift_type_filter: ShiftType | null;
    min_confidence: number;
    timestamp: string;
  };
}

/**
 * Shift type display configuration.
 */
export const SHIFT_TYPE_CONFIG: Record<
  ShiftType,
  { label: string; color: string; bgColor: string; icon: string; description: string }
> = {
  rising: {
    label: 'Rising',
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    icon: 'TrendingUp',
    description: 'Rapid price increase (>15% in 24h)',
  },
  falling: {
    label: 'Falling',
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    icon: 'TrendingDown',
    description: 'Rapid price decrease (>15% in 24h)',
  },
  emerging: {
    label: 'Emerging',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    icon: 'Sparkles',
    description: 'Sustained growth (>10% over 7 days)',
  },
  fading: {
    label: 'Fading',
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    icon: 'TrendingDown',
    description: 'Sustained decline (>10% over 7 days)',
  },
};
