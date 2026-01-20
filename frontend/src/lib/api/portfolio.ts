/**
 * Portfolio P&L API functions.
 *
 * Provides typed functions for all portfolio endpoints.
 */
import { apiClient } from './client';
import type {
  PortfolioSummaryResponse,
  PortfolioHoldingsResponse,
  CostBasisUpdateResponse,
  PortfolioRefreshResponse,
  AcquisitionType,
} from '@/types/portfolio';

export const portfolioApi = {
  /**
   * Get portfolio P&L summary for a wallet.
   * GET /wallets/{address}/portfolio
   */
  getSummary: (address: string): Promise<PortfolioSummaryResponse> =>
    apiClient(`/wallets/${address.toLowerCase()}/portfolio`),

  /**
   * Get portfolio holdings with P&L.
   * GET /wallets/{address}/portfolio/holdings
   */
  getHoldings: (
    address: string,
    params?: {
      includeValuation?: boolean;
      onlyWithPnl?: boolean;
      sortBy?: 'unrealized_pnl' | 'cost_basis' | 'current_value' | 'acquired_at';
      sortOrder?: 'asc' | 'desc';
      page?: number;
      perPage?: number;
    }
  ): Promise<PortfolioHoldingsResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.includeValuation !== undefined)
      searchParams.set('include_valuation', String(params.includeValuation));
    if (params?.onlyWithPnl !== undefined)
      searchParams.set('only_with_pnl', String(params.onlyWithPnl));
    if (params?.sortBy) searchParams.set('sort_by', params.sortBy);
    if (params?.sortOrder) searchParams.set('sort_order', params.sortOrder);
    if (params?.page !== undefined) searchParams.set('page', String(params.page));
    if (params?.perPage !== undefined) searchParams.set('per_page', String(params.perPage));
    const query = searchParams.toString();
    return apiClient(`/wallets/${address.toLowerCase()}/portfolio/holdings${query ? `?${query}` : ''}`);
  },

  /**
   * Refresh portfolio valuations.
   * POST /wallets/{address}/portfolio/refresh
   */
  refreshValuations: (address: string): Promise<PortfolioRefreshResponse> =>
    apiClient(`/wallets/${address.toLowerCase()}/portfolio/refresh`, {
      method: 'POST',
    }),

  /**
   * Update cost basis for a holding.
   * PATCH /wallets/{address}/holdings/{axie_id}/cost-basis
   */
  updateCostBasis: (
    address: string,
    axieId: number,
    params: {
      costBasisEth: number;
      acquisitionType?: AcquisitionType;
      acquiredAt?: string; // ISO date
    }
  ): Promise<CostBasisUpdateResponse> => {
    const searchParams = new URLSearchParams();
    searchParams.set('cost_basis_eth', String(params.costBasisEth));
    if (params.acquisitionType) searchParams.set('acquisition_type', params.acquisitionType);
    if (params.acquiredAt) searchParams.set('acquired_at', params.acquiredAt);
    const query = searchParams.toString();
    return apiClient(
      `/wallets/${address.toLowerCase()}/holdings/${axieId}/cost-basis?${query}`,
      { method: 'PATCH' }
    );
  },
};
