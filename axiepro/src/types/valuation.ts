/**
 * TypeScript types for the valuation API.
 *
 * These types match the backend response schemas from
 * backend/src/api/routes/valuation.py
 */

/**
 * Axie class types.
 */
export type AxieClass =
  | 'beast'
  | 'bug'
  | 'bird'
  | 'plant'
  | 'aquatic'
  | 'reptile'
  | 'mech'
  | 'dawn'
  | 'dusk';

/**
 * All available Axie classes.
 */
export const AXIE_CLASSES: AxieClass[] = [
  'beast',
  'bug',
  'bird',
  'plant',
  'aquatic',
  'reptile',
  'mech',
  'dawn',
  'dusk',
];

/**
 * Valuation estimates with confidence intervals.
 */
export interface Valuation {
  hedonic_eth: number | null;
  ml_eth: number | null;
  ensemble_eth: number | null;
  confidence_lower_eth: number | null;
  confidence_upper_eth: number | null;
  confidence_score: number; // 0-1
}

/**
 * Market context for an Axie.
 */
export interface MarketContext {
  current_listing_eth: number | null;
  class_floor_eth: number | null;
  class_avg_eth: number | null;
}

/**
 * Deal analysis for an Axie.
 */
export interface DealAnalysis {
  discount_percent: number;
  z_score: number | null;
  deal_score: number; // 0-100
  is_deal: boolean;
  is_snipe: boolean;
}

/**
 * Valuation metadata.
 */
export interface ValuationMetadata {
  method: 'hedonic' | 'ensemble' | 'ml' | null;
  model_version: string | null;
  computed_at: string | null; // ISO timestamp
  available: boolean; // true if valuation was computed successfully
  reason?: string; // explanation when unavailable
}

/**
 * Full valuation response from GET /valuation/{axie_id}
 *
 * Note: valuation, market_context, and deal_analysis can be null
 * when the Axie is not found or cannot be valued. Check metadata.available
 * to determine if the valuation is valid.
 */
export interface ValuationResponse {
  axie_id: number;
  valuation: Valuation | null;
  market_context: MarketContext | null;
  deal_analysis: DealAnalysis | null;
  feature_contributions: Record<string, number>;
  metadata: ValuationMetadata;
}

/**
 * Batch valuation response from POST /valuation/batch
 */
export interface BatchValuationResponse {
  success: boolean;
  valuations: Array<ValuationResponse | { axie_id: number; error: string }>;
  meta: {
    requested: number;
    successful: number;
    cached: number;
  };
}

/**
 * Deal tier types for normalized scoring.
 */
export type DealTier = 'snipe' | 'elite' | 'good' | 'fair' | 'pass';

/**
 * Tier configuration for display.
 */
export const DEAL_TIER_CONFIG: Record<
  DealTier,
  { label: string; color: string; bgColor: string; description: string }
> = {
  snipe: {
    label: 'SNIPE',
    color: 'text-red-600',
    bgColor: 'bg-red-500/10',
    description: 'Act immediately - exceptional value',
  },
  elite: {
    label: 'Elite Deal',
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    description: 'Strong buy opportunity',
  },
  good: {
    label: 'Good Deal',
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    description: 'Above average value',
  },
  fair: {
    label: 'Fair Deal',
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    description: 'Marginal opportunity',
  },
  pass: {
    label: 'Pass',
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    description: 'Below threshold',
  },
};

/**
 * Normalized score components breakdown.
 */
export interface ScoreComponents {
  discount_percentile: number;
  confidence_percentile: number;
  liquidity_score: number;
  time_score: number;
}

/**
 * Individual deal from deals list.
 */
export interface Deal {
  axie_id: number;
  class: string;
  listing_price_eth: number;
  fair_value_eth: number;
  discount_percent: number;
  z_score: number | null;
  deal_score: number;
  deal_type: 'deal' | 'snipe';
  marketplace_url: string;
  detected_at: string;
  // Normalized scoring fields (when include_normalized=true)
  normalized_score?: number;
  tier?: DealTier;
  tier_label?: string;
  tier_color?: string;
  score_components?: ScoreComponents;
}

/**
 * Deals list response from GET /valuation/deals/live or /deals/snipes
 */
export interface DealsListResponse {
  success: boolean;
  data: Deal[];
  meta: {
    count: number;
    min_score?: number;
    class_filter?: string | null;
    timestamp: string;
  };
}

/**
 * Trait statistics response.
 */
export interface TraitStats {
  trait_key: string;
  trait_type: string;
  class: string | null;
  avg_price_eth: number | null;
  median_price_eth: number | null;
  std_dev_eth: number | null;
  sample_count: number;
  time_window_hours: number;
  computed_at: string;
}

/**
 * Trait stats response wrapper.
 */
export interface TraitStatsResponse {
  success: boolean;
  data: TraitStats;
}

/**
 * Floor prices response from GET /valuation/stats/floors
 */
export interface FloorPricesResponse {
  success: boolean;
  data: Record<string, number>; // class -> floor price in ETH
  meta: {
    source: 'cache' | 'computed';
  };
}

/**
 * Model info response from GET /valuation/model/info
 */
export interface ModelInfoResponse {
  success: boolean;
  data: {
    model_version?: string;
    r_squared?: number;
    adj_r_squared?: number;
    rmse?: number;
    sample_size?: number;
    feature_count?: number;
    train_start?: string;
    train_end?: string;
    trained_at?: string;
    status?: string;
    message?: string;
  };
}
