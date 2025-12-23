/**
 * Valuation API functions.
 *
 * Provides typed functions for all valuation endpoints.
 */
import { apiClient } from './client';
import type {
  ValuationResponse,
  BatchValuationResponse,
  DealsListResponse,
  FloorPricesResponse,
  TraitStatsResponse,
} from '@/types/valuation';

export const valuationApi = {
  /**
   * Get valuation for a single Axie.
   * GET /valuation/{axie_id}
   */
  getValuation: (axieId: number, useCache = true): Promise<ValuationResponse> =>
    apiClient(`/valuation/${axieId}?use_cache=${useCache}`),

  /**
   * Get valuations for multiple Axies.
   * POST /valuation/batch
   */
  getBatchValuations: (axieIds: number[]): Promise<BatchValuationResponse> =>
    apiClient('/valuation/batch', {
      method: 'POST',
      body: JSON.stringify({ axie_ids: axieIds }),
    }),

  /**
   * Get live deal opportunities.
   * GET /valuation/deals/live
   */
  getLiveDeals: (params?: {
    class?: string;
    minScore?: number;
    limit?: number;
  }): Promise<DealsListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.class) searchParams.set('class', params.class);
    if (params?.minScore !== undefined) searchParams.set('min_score', String(params.minScore));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return apiClient(`/valuation/deals/live${query ? `?${query}` : ''}`);
  },

  /**
   * Get top snipe opportunities (high-value deals).
   * GET /valuation/deals/snipes
   */
  getSnipes: (limit = 20): Promise<DealsListResponse> =>
    apiClient(`/valuation/deals/snipes?limit=${limit}`),

  /**
   * Get price statistics for a specific trait.
   * GET /valuation/stats/trait/{trait_key}
   */
  getTraitStats: (traitKey: string): Promise<TraitStatsResponse> =>
    apiClient(`/valuation/stats/trait/${encodeURIComponent(traitKey)}`),

  /**
   * Get current floor prices by class.
   * GET /valuation/stats/floors
   */
  getFloorPrices: (): Promise<FloorPricesResponse> =>
    apiClient('/valuation/stats/floors'),

  /**
   * Get model information.
   * GET /valuation/model/info
   */
  getModelInfo: (): Promise<{ success: boolean; data: Record<string, unknown> }> =>
    apiClient('/valuation/model/info'),
};
