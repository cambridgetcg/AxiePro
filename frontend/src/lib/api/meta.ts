/**
 * Meta Shifts API functions.
 *
 * Provides typed functions for all meta shift endpoints.
 */
import { apiClient } from './client';
import type {
  MetaSummaryResponse,
  MetaShiftsResponse,
  TrendingResponse,
  ClassMetaResponse,
  TraitHistoryResponse,
  MetaHealthResponse,
  ShiftType,
  MetaShiftsParams,
  TrendingParams,
  VelocityLeadersParams,
  ClassMetaParams,
  TraitHistoryParams,
} from '@/types/meta';

/**
 * Build URL search params from an object, filtering out undefined values.
 */
function buildSearchParams(params: object): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      // Convert camelCase to snake_case for API
      const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
      searchParams.set(snakeKey, String(value));
    }
  }
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export const metaApi = {
  // =========================================================================
  // Core Endpoints
  // =========================================================================

  /**
   * Get meta shifts summary.
   * GET /meta/summary
   */
  getSummary: (useCache = true): Promise<MetaSummaryResponse> =>
    apiClient(`/meta/summary?use_cache=${useCache}`),

  /**
   * Get meta shifts with optional filters.
   * GET /meta/shifts
   */
  getShifts: (params?: MetaShiftsParams): Promise<MetaShiftsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/shifts${query}`);
  },

  /**
   * Get trending traits based on recent meta shifts.
   * GET /meta/trending
   */
  getTrending: (params?: TrendingParams): Promise<TrendingResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/trending${query}`);
  },

  /**
   * Get traits with highest price velocity (fastest movers).
   * GET /meta/velocity-leaders
   */
  getVelocityLeaders: (params?: VelocityLeadersParams): Promise<MetaShiftsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/velocity-leaders${query}`);
  },

  /**
   * Get meta analysis for a specific Axie class.
   * GET /meta/class/{class}
   */
  getClassMeta: (axieClass: string, params?: ClassMetaParams): Promise<ClassMetaResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/class/${encodeURIComponent(axieClass)}${query}`);
  },

  /**
   * Get meta shift history for a specific trait.
   * GET /meta/trait/{trait_key}
   */
  getTraitHistory: (traitKey: string, params?: TraitHistoryParams): Promise<TraitHistoryResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/trait/${encodeURIComponent(traitKey)}${query}`);
  },

  // =========================================================================
  // Convenience Endpoints (shift type shortcuts)
  // =========================================================================

  /**
   * Get rising meta shifts.
   * GET /meta/rising
   */
  getRising: (params?: {
    limit?: number;
    minConfidence?: number;
    hours?: number;
    useCache?: boolean;
  }): Promise<MetaShiftsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/rising${query}`);
  },

  /**
   * Get falling meta shifts.
   * GET /meta/falling
   */
  getFalling: (params?: {
    limit?: number;
    minConfidence?: number;
    hours?: number;
    useCache?: boolean;
  }): Promise<MetaShiftsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/falling${query}`);
  },

  /**
   * Get emerging meta trends.
   * GET /meta/emerging
   */
  getEmerging: (params?: {
    limit?: number;
    minConfidence?: number;
    hours?: number;
    useCache?: boolean;
  }): Promise<MetaShiftsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/emerging${query}`);
  },

  /**
   * Get fading meta trends.
   * GET /meta/fading
   */
  getFading: (params?: {
    limit?: number;
    minConfidence?: number;
    hours?: number;
    useCache?: boolean;
  }): Promise<MetaShiftsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/meta/fading${query}`);
  },

  // =========================================================================
  // Health Check
  // =========================================================================

  /**
   * Check meta service health.
   * GET /meta/health
   */
  getHealth: (): Promise<MetaHealthResponse> => apiClient('/meta/health'),
};
