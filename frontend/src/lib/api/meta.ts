/**
 * Meta Shifts API functions.
 *
 * Provides typed functions for all meta shift endpoints.
 */
import { apiClient } from './client';
import type {
  MetaSummaryResponse,
  MetaShiftsResponse,
  ShiftType,
} from '@/types/meta';

export const metaApi = {
  /**
   * Get meta shifts summary.
   * GET /meta/summary
   */
  getSummary: (): Promise<MetaSummaryResponse> =>
    apiClient('/meta/summary'),

  /**
   * Get meta shifts with optional filters.
   * GET /meta/shifts
   */
  getShifts: (params?: {
    shiftType?: ShiftType;
    minConfidence?: number;
    limit?: number;
  }): Promise<MetaShiftsResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.shiftType) searchParams.set('shift_type', params.shiftType);
    if (params?.minConfidence !== undefined) searchParams.set('min_confidence', String(params.minConfidence));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return apiClient(`/meta/shifts${query ? `?${query}` : ''}`);
  },

  /**
   * Get meta shift for a specific trait.
   * GET /meta/shifts/{trait_key}
   */
  getTraitShift: (traitKey: string): Promise<MetaShiftsResponse> =>
    apiClient(`/meta/shifts/${encodeURIComponent(traitKey)}`),

  /**
   * Get rising meta shifts.
   * GET /meta/rising
   */
  getRising: (params?: {
    limit?: number;
    minConfidence?: number;
  }): Promise<MetaShiftsResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.minConfidence !== undefined) searchParams.set('min_confidence', String(params.minConfidence));
    const query = searchParams.toString();
    return apiClient(`/meta/rising${query ? `?${query}` : ''}`);
  },

  /**
   * Get falling meta shifts.
   * GET /meta/falling
   */
  getFalling: (params?: {
    limit?: number;
    minConfidence?: number;
  }): Promise<MetaShiftsResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.minConfidence !== undefined) searchParams.set('min_confidence', String(params.minConfidence));
    const query = searchParams.toString();
    return apiClient(`/meta/falling${query ? `?${query}` : ''}`);
  },

  /**
   * Get emerging meta trends.
   * GET /meta/emerging
   */
  getEmerging: (params?: {
    limit?: number;
    minConfidence?: number;
  }): Promise<MetaShiftsResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.minConfidence !== undefined) searchParams.set('min_confidence', String(params.minConfidence));
    const query = searchParams.toString();
    return apiClient(`/meta/emerging${query ? `?${query}` : ''}`);
  },

  /**
   * Get fading meta trends.
   * GET /meta/fading
   */
  getFading: (params?: {
    limit?: number;
    minConfidence?: number;
  }): Promise<MetaShiftsResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params?.minConfidence !== undefined) searchParams.set('min_confidence', String(params.minConfidence));
    const query = searchParams.toString();
    return apiClient(`/meta/fading${query ? `?${query}` : ''}`);
  },

  /**
   * Check meta cache health.
   * GET /meta/health
   */
  getHealth: (): Promise<{
    success: boolean;
    data: {
      redis_available: boolean;
      meta_data_present: boolean;
      last_analysis: string | null;
      total_shifts: number;
    };
  }> => apiClient('/meta/health'),
};
