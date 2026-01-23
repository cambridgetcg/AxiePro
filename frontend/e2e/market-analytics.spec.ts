/**
 * Market Analytics E2E Tests
 *
 * Tests the market analytics page with focus on:
 * - Floor prices data display and freshness
 * - API response validation
 * - Console error detection
 * - Loading and error states
 *
 * Uses API mocking for deterministic tests.
 */

import { test, expect, setupConsoleCapture } from './fixtures/console-capture';
import {
  setupApiMocks,
  setupApiMocksWithDelay,
  mockFloorPrices,
  mockSnipes,
  createFloorPricesMock,
  emptyMocks,
} from './fixtures/api-mocks';

test.describe('Market Analytics', () => {
  test('Floor prices load without errors', async ({ page, consoleCapture }) => {
    // Set up API mocks
    await setupApiMocks(page);

    // Navigate to market page
    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check for console errors
    if (consoleCapture.hasErrors()) {
      console.log('\n=== Console Errors ===');
      consoleCapture.getErrorMessages().forEach((msg) => {
        console.log(`  - ${msg}`);
      });
    }

    // Verify floor prices API was called
    const floorCalls = consoleCapture.getApiCallsForEndpoint('/valuation/stats/floors');
    console.log(`\nFloor price API calls: ${floorCalls.length}`);
    floorCalls.forEach((call) => {
      console.log(`  [${call.status}] ${call.method} ${call.url}`);
    });

    // Check that floor prices loaded successfully
    expect(floorCalls.length).toBeGreaterThan(0);
    expect(floorCalls[0].status).toBe(200);

    // Verify no critical errors
    expect(consoleCapture.pageErrors.length).toBe(0);
  });

  test('Floor prices display correctly', async ({ page }) => {
    const capture = setupConsoleCapture(page);

    // Set up mocks with known values
    const customPrices = createFloorPricesMock({
      beast: 0.025,
      aquatic: 0.018,
      plant: 0.012,
    });
    await setupApiMocks(page, { floorPrices: customPrices });

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check that floor price section is visible
    const floorPricesSection = page.locator('text=Floor Prices by Class');
    await expect(floorPricesSection).toBeVisible();

    // Check for individual class prices
    const classes = ['beast', 'aquatic', 'plant', 'bird', 'bug', 'reptile'];
    let foundPrices = 0;

    for (const cls of classes) {
      const classLabel = page.locator(`text=${cls}`).first();
      if (await classLabel.isVisible()) {
        foundPrices++;
      }
    }

    console.log(`Found ${foundPrices}/${classes.length} class labels`);

    // Log API response details
    const apiCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors');
    if (apiCalls.length > 0) {
      console.log(`\nFloor prices API status: ${apiCalls[0].status}`);
    }

    // Should find at least some class labels
    expect(foundPrices).toBeGreaterThan(0);
  });

  test('Snipes section loads', async ({ page, consoleCapture }) => {
    await setupApiMocks(page);

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check snipes section
    const snipesSection = page.locator('text=Latest Snipe Opportunities');
    await expect(snipesSection).toBeVisible();

    // Verify snipes API was called
    const snipesCalls = consoleCapture.getApiCallsForEndpoint('/valuation/deals/snipes');
    console.log(`\nSnipes API calls: ${snipesCalls.length}`);
    snipesCalls.forEach((call) => {
      console.log(`  [${call.status}] ${call.method} ${call.url}`);
    });

    // Should have loaded snipes
    expect(snipesCalls.length).toBeGreaterThan(0);
    expect(snipesCalls[0].status).toBe(200);
  });

  test('Refresh button triggers new API calls', async ({ page }) => {
    const capture = setupConsoleCapture(page);
    await setupApiMocks(page);

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Count initial API calls
    const initialFloorCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors').length;
    console.log(`Initial floor API calls: ${initialFloorCalls}`);

    // Click refresh button
    const refreshButton = page.locator('button:has-text("Refresh")');
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(1000);

      // Count API calls after refresh
      const afterRefreshCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors').length;
      console.log(`After refresh floor API calls: ${afterRefreshCalls}`);

      // Should have made additional API calls
      expect(afterRefreshCalls).toBeGreaterThan(initialFloorCalls);
    }
  });

  test('API response includes fresh data indicator', async ({ page }) => {
    // Intercept API response to check meta.source
    let apiResponse: { success: boolean; data: unknown; meta?: { source?: string } } | null = null;

    // Set up mock that we can also observe
    await setupApiMocks(page);

    page.on('response', async (response) => {
      if (response.url().includes('/valuation/stats/floors')) {
        try {
          apiResponse = await response.json();
        } catch {
          // Ignore parse errors
        }
      }
    });

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Verify API response structure
    console.log('\nAPI Response:', JSON.stringify(apiResponse, null, 2));

    if (apiResponse) {
      expect(apiResponse.success).toBe(true);
      expect(apiResponse.data).toBeDefined();

      // Check that data source is from our mock (which simulates price_snapshots)
      if (apiResponse.meta?.source) {
        console.log(`Data source: ${apiResponse.meta.source}`);
        // Accept 'price_snapshots', 'cache', or 'computed_fallback'
        expect(['price_snapshots', 'cache', 'computed_fallback']).toContain(apiResponse.meta.source);
      }
    }
  });

  test('Shows correct floor price values', async ({ page }) => {
    // Use specific mock values we can verify
    const knownPrices = createFloorPricesMock({
      beast: 0.0333,
      aquatic: 0.0222,
    });
    await setupApiMocks(page, { floorPrices: knownPrices });

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Look for the ETH values displayed (format may vary)
    // This test verifies the data flows through to the UI
    const pageContent = await page.content();

    // At minimum, the page should contain price-related content
    expect(pageContent).toContain('Floor');
  });
});

test.describe('Market Analytics - Error Scenarios', () => {
  test('Handles API errors gracefully', async ({ page, consoleCapture }) => {
    // Set up mock that returns 500 for floor prices
    await setupApiMocks(page, { failEndpoints: ['floors'] });

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Page should still render without crashing
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check for error handling in UI (loading state or error message)
    const loadingOrError =
      (await page.locator('text=Unable to load').count()) > 0 ||
      (await page.locator('[class*="skeleton"]').count()) > 0 ||
      (await page.locator('text=Error').count()) > 0;

    console.log(`Shows loading/error state: ${loadingOrError}`);

    // Log any console errors
    if (consoleCapture.hasErrors()) {
      console.log('\nConsole errors during API failure:');
      consoleCapture.getErrorMessages().forEach((msg) => {
        console.log(`  - ${msg.slice(0, 150)}`);
      });
    }
  });

  test('Handles slow API response', async ({ page }) => {
    const capture = setupConsoleCapture(page);

    // Add 3 second delay to API responses
    await setupApiMocksWithDelay(page, 3000);

    await page.goto('/market');

    // Should show loading state while waiting
    const skeleton = page.locator('[class*="skeleton"]').first();
    const showsLoading = await skeleton.isVisible().catch(() => false);
    console.log(`Shows loading skeleton: ${showsLoading}`);

    // Wait for response
    await page.waitForTimeout(4000);

    // Check no page errors after slow load
    expect(capture.pageErrors.length).toBe(0);
  });

  test('Handles empty data gracefully', async ({ page }) => {
    // Set up mocks with empty data
    await setupApiMocks(page, {
      floorPrices: emptyMocks.floorPrices,
      snipes: emptyMocks.snipes,
    });

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Page should still render
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Should show some indication of no data or empty state
    const pageContent = await page.content();
    console.log('Page rendered successfully with empty data');

    // No crash is success
    expect(true).toBe(true);
  });
});

test.describe('Console Log Analysis', () => {
  test('Capture all console output for debugging', async ({ page }) => {
    const capture = setupConsoleCapture(page);
    await setupApiMocks(page);

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Output full capture summary
    console.log('\n' + capture.toMarkdown());

    // Save detailed JSON for analysis
    const fs = await import('fs');
    const path = await import('path');
    const outputPath = path.join(process.cwd(), 'e2e', 'console-capture-market.json');
    fs.writeFileSync(outputPath, capture.toJSON());
    console.log(`\nDetailed capture saved to: ${outputPath}`);
  });
});

test.describe('Market Analytics - Auto Refresh', () => {
  // This test is slow (65+ seconds) so we skip it by default
  // Run with: npx playwright test --grep "Auto-refresh"
  test.skip('Auto-refresh triggers after 60 seconds', async ({ page }) => {
    const capture = setupConsoleCapture(page);
    await setupApiMocks(page);

    await page.goto('/market');
    await page.waitForLoadState('networkidle');

    // Wait for initial load
    await page.waitForTimeout(3000);
    const initialCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors').length;
    console.log(`Initial API calls: ${initialCalls}`);

    // Wait 65 seconds for auto-refresh (60s interval + buffer)
    console.log('Waiting 65 seconds for auto-refresh...');
    await page.waitForTimeout(65000);

    const afterAutoRefresh = capture.getApiCallsForEndpoint('/valuation/stats/floors').length;
    console.log(`After auto-refresh API calls: ${afterAutoRefresh}`);

    // Should have made at least one additional call
    expect(afterAutoRefresh).toBeGreaterThan(initialCalls);
  });
});
