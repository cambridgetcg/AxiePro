/**
 * API Mocking Fixtures for Playwright E2E Tests
 *
 * Provides mock data and route handlers for API endpoints.
 * Use these to make tests deterministic and avoid CORS/network issues.
 */

import { Page, Route } from '@playwright/test';

/**
 * Mock floor prices data
 */
export const mockFloorPrices = {
  success: true,
  data: {
    beast: 0.0152,
    aquatic: 0.0128,
    plant: 0.0095,
    bird: 0.0142,
    bug: 0.0088,
    reptile: 0.0115,
    mech: 0.0245,
    dawn: 0.0198,
    dusk: 0.0176,
  },
  meta: {
    source: 'price_snapshots',
    cached: false,
    timestamp: new Date().toISOString(),
  },
};

/**
 * Mock snipes data
 */
export const mockSnipes = {
  success: true,
  data: [
    {
      axie_id: '12345678',
      class: 'beast',
      listing_price_eth: 0.012,
      fair_value_eth: 0.018,
      discount_pct: 33.3,
      purity: 85,
      breed_count: 0,
      listed_at: new Date(Date.now() - 300000).toISOString(),
    },
    {
      axie_id: '23456789',
      class: 'aquatic',
      listing_price_eth: 0.01,
      fair_value_eth: 0.014,
      discount_pct: 28.6,
      purity: 80,
      breed_count: 1,
      listed_at: new Date(Date.now() - 600000).toISOString(),
    },
    {
      axie_id: '34567890',
      class: 'plant',
      listing_price_eth: 0.008,
      fair_value_eth: 0.011,
      discount_pct: 27.3,
      purity: 75,
      breed_count: 2,
      listed_at: new Date(Date.now() - 900000).toISOString(),
    },
  ],
  meta: {
    total: 3,
    timestamp: new Date().toISOString(),
  },
};

/**
 * Mock market stats data
 */
export const mockMarketStats = {
  success: true,
  data: {
    total_listings: 15234,
    total_volume_24h_eth: 125.5,
    total_sales_24h: 892,
    avg_price_eth: 0.0145,
    floor_price_eth: 0.0088,
  },
  meta: {
    timestamp: new Date().toISOString(),
  },
};

/**
 * Mock meta analysis data
 */
export const mockMetaAnalysis = {
  success: true,
  data: {
    top_cards: [
      { card_id: 'beast-risky-beast', name: 'Risky Beast', usage_rate: 0.45, win_rate: 0.52 },
      { card_id: 'aquatic-swift-escape', name: 'Swift Escape', usage_rate: 0.42, win_rate: 0.51 },
      { card_id: 'plant-october-treat', name: 'October Treat', usage_rate: 0.38, win_rate: 0.49 },
    ],
    meta_shift: 'stable',
    last_updated: new Date().toISOString(),
  },
};

/**
 * API route handlers configuration
 */
export interface MockConfig {
  floorPrices?: typeof mockFloorPrices | null;
  snipes?: typeof mockSnipes | null;
  marketStats?: typeof mockMarketStats | null;
  metaAnalysis?: typeof mockMetaAnalysis | null;
  delay?: number; // Add artificial delay in ms
  failEndpoints?: string[]; // Endpoints to return 500 for
}

/**
 * Set up API mocking for a page with default mock data.
 *
 * @example
 * ```ts
 * test('my test', async ({ page }) => {
 *   await setupApiMocks(page);
 *   await page.goto('/market');
 *   // API calls will return mock data
 * });
 * ```
 */
export async function setupApiMocks(page: Page, config: MockConfig = {}): Promise<void> {
  const {
    floorPrices = mockFloorPrices,
    snipes = mockSnipes,
    marketStats = mockMarketStats,
    metaAnalysis = mockMetaAnalysis,
    delay = 0,
    failEndpoints = [],
  } = config;

  // Helper to create route handler
  const createHandler = (data: unknown, endpoint: string) => {
    return async (route: Route) => {
      if (delay > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }

      if (failEndpoints.includes(endpoint)) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            error: 'Internal Server Error',
            message: 'Mock error for testing',
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(data),
      });
    };
  };

  // Mock floor prices endpoint (with or without query params)
  if (floorPrices !== null) {
    await page.route('**/valuation/stats/floors**', createHandler(floorPrices, 'floors'));
  }

  // Mock snipes endpoint (with or without query params)
  if (snipes !== null) {
    await page.route('**/valuation/deals/snipes**', createHandler(snipes, 'snipes'));
  }

  // Mock market stats endpoint (with or without query params)
  if (marketStats !== null) {
    await page.route('**/market/stats**', createHandler(marketStats, 'marketStats'));
  }

  // Mock meta analysis endpoint (with or without query params)
  if (metaAnalysis !== null) {
    await page.route('**/meta/analysis**', createHandler(metaAnalysis, 'metaAnalysis'));
  }
}

/**
 * Set up API mocking for error scenarios.
 *
 * @example
 * ```ts
 * test('handles API errors', async ({ page }) => {
 *   await setupApiMocksWithErrors(page, ['floors']);
 *   await page.goto('/market');
 *   // Floor prices API will return 500
 * });
 * ```
 */
export async function setupApiMocksWithErrors(
  page: Page,
  failEndpoints: string[]
): Promise<void> {
  await setupApiMocks(page, { failEndpoints });
}

/**
 * Set up API mocking with slow responses for testing loading states.
 *
 * @example
 * ```ts
 * test('shows loading state', async ({ page }) => {
 *   await setupApiMocksWithDelay(page, 3000);
 *   await page.goto('/market');
 *   // Should show loading skeleton
 * });
 * ```
 */
export async function setupApiMocksWithDelay(page: Page, delayMs: number): Promise<void> {
  await setupApiMocks(page, { delay: delayMs });
}

/**
 * Create custom floor prices mock with specific values.
 *
 * @example
 * ```ts
 * const customPrices = createFloorPricesMock({
 *   beast: 0.025,
 *   aquatic: 0.020,
 * });
 * await setupApiMocks(page, { floorPrices: customPrices });
 * ```
 */
export function createFloorPricesMock(
  prices: Partial<Record<string, number>>,
  source: 'price_snapshots' | 'cache' | 'computed_fallback' = 'price_snapshots'
): typeof mockFloorPrices {
  return {
    success: true,
    data: {
      beast: prices.beast ?? 0.015,
      aquatic: prices.aquatic ?? 0.012,
      plant: prices.plant ?? 0.009,
      bird: prices.bird ?? 0.014,
      bug: prices.bug ?? 0.008,
      reptile: prices.reptile ?? 0.011,
      mech: prices.mech ?? 0.024,
      dawn: prices.dawn ?? 0.019,
      dusk: prices.dusk ?? 0.017,
    },
    meta: {
      source,
      cached: source === 'cache',
      timestamp: new Date().toISOString(),
    },
  };
}

/**
 * Create empty/no-data mock responses for testing empty states.
 */
export const emptyMocks = {
  floorPrices: {
    success: true,
    data: {},
    meta: { source: 'price_snapshots', cached: false, timestamp: new Date().toISOString() },
  },
  snipes: {
    success: true,
    data: [],
    meta: { total: 0, timestamp: new Date().toISOString() },
  },
};
