'use client';

/**
 * React Query hooks for fetching meta shift data.
 */
import { useQuery } from '@tanstack/react-query';
import { metaApi } from '@/lib/api/meta';
import { config } from '@/lib/config';
import type { MetaSummaryResponse, MetaShiftsResponse, TraitHistoryResponse, ShiftType } from '@/types/meta';

/**
 * Query key factory for meta shifts.
 */
export const metaKeys = {
  all: ['meta'] as const,
  summary: () => [...metaKeys.all, 'summary'] as const,
  shifts: (filters?: { shiftType?: ShiftType; minConfidence?: number }) =>
    [...metaKeys.all, 'shifts', filters] as const,
  rising: () => [...metaKeys.all, 'rising'] as const,
  falling: () => [...metaKeys.all, 'falling'] as const,
  emerging: () => [...metaKeys.all, 'emerging'] as const,
  fading: () => [...metaKeys.all, 'fading'] as const,
  trait: (traitKey: string) => [...metaKeys.all, 'trait', traitKey] as const,
};

/**
 * Hook to fetch meta shifts summary.
 *
 * @returns Query result with summary data
 */
export function useMetaSummary() {
  return useQuery<MetaSummaryResponse>({
    queryKey: metaKeys.summary(),
    queryFn: () => metaApi.getSummary(),
    staleTime: config.defaultStaleTime,
    refetchInterval: 5 * 60_000, // 5 minutes
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch meta shifts with optional filters.
 *
 * @param filters - Optional filters for shift type and confidence
 * @returns Query result with shifts list
 */
export function useMetaShifts(filters?: {
  shiftType?: ShiftType;
  minConfidence?: number;
  limit?: number;
}) {
  return useQuery<MetaShiftsResponse>({
    queryKey: metaKeys.shifts(filters),
    queryFn: () =>
      metaApi.getShifts({
        shiftType: filters?.shiftType,
        minConfidence: filters?.minConfidence,
        limit: filters?.limit,
      }),
    staleTime: config.defaultStaleTime,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch rising meta shifts.
 *
 * @param limit - Maximum number of shifts to fetch
 * @param minConfidence - Minimum confidence score
 * @returns Query result with rising shifts
 */
export function useRisingMeta(limit = 20, minConfidence = 25) {
  return useQuery<MetaShiftsResponse>({
    queryKey: metaKeys.rising(),
    queryFn: () => metaApi.getRising({ limit, minConfidence }),
    staleTime: config.defaultStaleTime,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch falling meta shifts.
 *
 * @param limit - Maximum number of shifts to fetch
 * @param minConfidence - Minimum confidence score
 * @returns Query result with falling shifts
 */
export function useFallingMeta(limit = 20, minConfidence = 25) {
  return useQuery<MetaShiftsResponse>({
    queryKey: metaKeys.falling(),
    queryFn: () => metaApi.getFalling({ limit, minConfidence }),
    staleTime: config.defaultStaleTime,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch emerging meta trends.
 *
 * @param limit - Maximum number of shifts to fetch
 * @param minConfidence - Minimum confidence score
 * @returns Query result with emerging shifts
 */
export function useEmergingMeta(limit = 20, minConfidence = 25) {
  return useQuery<MetaShiftsResponse>({
    queryKey: metaKeys.emerging(),
    queryFn: () => metaApi.getEmerging({ limit, minConfidence }),
    staleTime: config.defaultStaleTime,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch fading meta trends.
 *
 * @param limit - Maximum number of shifts to fetch
 * @param minConfidence - Minimum confidence score
 * @returns Query result with fading shifts
 */
export function useFadingMeta(limit = 20, minConfidence = 25) {
  return useQuery<MetaShiftsResponse>({
    queryKey: metaKeys.fading(),
    queryFn: () => metaApi.getFading({ limit, minConfidence }),
    staleTime: config.defaultStaleTime,
    refetchInterval: 5 * 60_000,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch meta shift for a specific trait.
 *
 * @param traitKey - Trait key (e.g., "class:beast", "part:horn:lagging")
 * @param options - Query options
 * @returns Query result with trait shift data
 */
export function useTraitMeta(
  traitKey: string,
  options?: { enabled?: boolean }
) {
  return useQuery<TraitHistoryResponse>({
    queryKey: metaKeys.trait(traitKey),
    queryFn: () => metaApi.getTraitHistory(traitKey),
    staleTime: config.defaultStaleTime,
    enabled: options?.enabled ?? true,
  });
}
