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
 * Price velocity data for a time period (legacy format from lambda cache).
 */
export interface PriceVelocity {
  current_price: number | null;
  past_price: number | null;
  velocity_percent: number;
  period_hours: number;
}

/**
 * Volume change data (legacy format from lambda cache).
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
  id?: number;
  trait_key: string;
  class: string | null;
  shift_type: ShiftType;
  confidence: number; // 0-100
  signals: string[];
  // Flat velocity fields (from database)
  velocity_24h?: number | null;
  velocity_7d?: number | null;
  volume_change_24h?: number | null;
  // Nested velocity fields (from lambda cache - legacy)
  price_velocity_24h?: PriceVelocity | null;
  price_velocity_7d?: PriceVelocity | null;
  volume_change?: VolumeChange | null;
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
  top_rising?: MetaShift[];
  top_falling?: MetaShift[];
}

/**
 * Trending trait with aggregated data.
 */
export interface TrendingTrait {
  trait_key: string;
  class: string;
  shift_type: string;
  velocity_24h: number | null;
  velocity_7d: number | null;
  confidence: number;
  first_detected: string;
  occurrences: number;
}

/**
 * Meta analysis for a specific class.
 */
export interface ClassMeta {
  class: string;
  total_shifts: number;
  avg_confidence: number;
  shift_breakdown: Record<string, number>;
  recent_shifts: MetaShift[];
}

/**
 * Historical point for a trait.
 */
export interface TraitHistoryPoint {
  detected_at: string;
  shift_type: string;
  confidence: number;
  velocity_24h: number | null;
  velocity_7d: number | null;
  volume_change_24h: number | null;
}

/**
 * Response metadata for meta endpoints.
 */
export interface MetaResponseMeta {
  count?: number;
  source?: 'database' | 'redis_cache';
  cached?: boolean;
  cache_key?: string;
  ttl_seconds?: number;
  shift_type?: string;
  shift_type_filter?: ShiftType | null;
  shift_types_filter?: string[] | null;
  min_confidence?: number;
  hours?: number;
  days?: number;
  direction?: 'up' | 'down';
  class?: string;
  trait_key?: string;
  timestamp?: string;
  total?: number;
  limit?: number;
  offset?: number;
}

/**
 * Meta summary response from GET /meta/summary
 */
export interface MetaSummaryResponse {
  success: boolean;
  data: MetaSummary;
  meta: MetaResponseMeta;
}

/**
 * Meta shifts list response from GET /meta/shifts
 */
export interface MetaShiftsResponse {
  success: boolean;
  data: MetaShift[];
  meta: MetaResponseMeta;
}

/**
 * Trending traits response from GET /meta/trending
 */
export interface TrendingResponse {
  success: boolean;
  data: TrendingTrait[];
  meta: MetaResponseMeta;
}

/**
 * Class meta response from GET /meta/class/{class}
 */
export interface ClassMetaResponse {
  success: boolean;
  data: ClassMeta;
  meta: MetaResponseMeta;
}

/**
 * Trait history response from GET /meta/trait/{trait_key}
 */
export interface TraitHistoryResponse {
  success: boolean;
  data: TraitHistoryPoint[];
  meta: MetaResponseMeta;
}

/**
 * Meta health response from GET /meta/health
 */
export interface MetaHealthResponse {
  success: boolean;
  data: {
    redis_available: boolean;
    redis_meta_present: boolean;
    redis_last_analysis: string | null;
    database_available: boolean;
    database_shifts_24h: number;
  };
}

/**
 * Parameters for fetching meta shifts.
 */
export interface MetaShiftsParams {
  shiftType?: ShiftType;
  minConfidence?: number;
  hours?: number;
  limit?: number;
  useCache?: boolean;
}

/**
 * Parameters for fetching trending traits.
 */
export interface TrendingParams {
  shiftTypes?: string;
  minConfidence?: number;
  limit?: number;
  useCache?: boolean;
}

/**
 * Parameters for velocity leaders.
 */
export interface VelocityLeadersParams {
  direction?: 'up' | 'down';
  hours?: number;
  limit?: number;
  useCache?: boolean;
}

/**
 * Parameters for class meta.
 */
export interface ClassMetaParams {
  hours?: number;
  useCache?: boolean;
}

/**
 * Parameters for trait history.
 */
export interface TraitHistoryParams {
  days?: number;
  useCache?: boolean;
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

/**
 * Helper to get velocity from a MetaShift (handles both formats).
 */
export function getVelocity24h(shift: MetaShift): number | null {
  if (shift.velocity_24h !== undefined) {
    return shift.velocity_24h;
  }
  return shift.price_velocity_24h?.velocity_percent ?? null;
}

/**
 * Helper to get 7d velocity from a MetaShift (handles both formats).
 */
export function getVelocity7d(shift: MetaShift): number | null {
  if (shift.velocity_7d !== undefined) {
    return shift.velocity_7d;
  }
  return shift.price_velocity_7d?.velocity_percent ?? null;
}

/**
 * Helper to get volume change from a MetaShift (handles both formats).
 */
export function getVolumeChange(shift: MetaShift): number | null {
  if (shift.volume_change_24h !== undefined) {
    return shift.volume_change_24h;
  }
  return shift.volume_change?.change_percent ?? null;
}
