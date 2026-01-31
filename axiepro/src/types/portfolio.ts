/**
 * TypeScript types for the Portfolio P&L API.
 *
 * These types match the backend response schemas from
 * backend/src/api/routes/wallets.py (portfolio endpoints)
 */

/**
 * Acquisition type for holdings.
 */
export type AcquisitionType = 'purchase' | 'breeding' | 'gift' | 'transfer' | 'airdrop' | 'unknown';

/**
 * Individual holding with P&L data.
 */
export interface HoldingPnL {
  axie_id: number;
  acquired_at: string | null;
  acquisition_type: AcquisitionType | null;
  cost_basis_eth: number | null;
  current_value_eth: number | null;
  last_valued_at: string | null;
  unrealized_pnl_eth: number | null;
  unrealized_pnl_percent: number | null;
  has_cost_basis: boolean;
}

/**
 * Portfolio P&L summary.
 */
export interface PortfolioSummary {
  wallet_address: string;
  holdings_count: number;
  total_cost_basis_eth: number | null;
  total_current_value_eth: number | null;
  total_unrealized_pnl_eth: number | null;
  total_unrealized_pnl_percent: number | null;
  holdings_with_cost_basis: number;
  holdings_missing_cost_basis: number;
  last_valuation_at: string | null;
}

/**
 * Portfolio summary response from GET /wallets/{address}/portfolio
 */
export interface PortfolioSummaryResponse {
  success: boolean;
  data: PortfolioSummary;
  meta: {
    timestamp: string;
    coverage_percent: number;
  };
}

/**
 * Portfolio holdings response from GET /wallets/{address}/portfolio/holdings
 */
export interface PortfolioHoldingsResponse {
  success: boolean;
  data: HoldingPnL[];
  meta: {
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
    sort_by: string;
    sort_order: string;
  };
}

/**
 * Cost basis update response.
 */
export interface CostBasisUpdateResponse {
  success: boolean;
  data: {
    axie_id: number;
    cost_basis_eth: number | null;
    acquisition_type: AcquisitionType | null;
    acquired_at: string | null;
    unrealized_pnl_eth: number | null;
    unrealized_pnl_percent: number | null;
  };
  message: string;
}

/**
 * Portfolio refresh response.
 */
export interface PortfolioRefreshResponse {
  success: boolean;
  message: string;
  wallet_address: string;
}

/**
 * P&L status indicator.
 */
export function getPnLStatus(pnlPercent: number | null): {
  label: string;
  color: string;
  bgColor: string;
} {
  if (pnlPercent === null) {
    return { label: 'Unknown', color: 'text-muted-foreground', bgColor: 'bg-muted' };
  }
  if (pnlPercent >= 50) {
    return { label: 'Excellent', color: 'text-green-500', bgColor: 'bg-green-500/10' };
  }
  if (pnlPercent >= 20) {
    return { label: 'Good', color: 'text-green-400', bgColor: 'bg-green-400/10' };
  }
  if (pnlPercent >= 0) {
    return { label: 'Positive', color: 'text-green-300', bgColor: 'bg-green-300/10' };
  }
  if (pnlPercent >= -20) {
    return { label: 'Loss', color: 'text-red-300', bgColor: 'bg-red-300/10' };
  }
  return { label: 'Significant Loss', color: 'text-red-500', bgColor: 'bg-red-500/10' };
}
