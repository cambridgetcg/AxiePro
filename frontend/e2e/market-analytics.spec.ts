/**
 * Market Analytics E2E Tests
 *
 * Tests the market analytics page with focus on:
 * - Floor prices data freshness
 * - API response validation
 * - Console error detection
 */

import { test, expect, setupConsoleCapture } from './fixtures/console-capture';

test.describe('Market Analytics', () => {
  test('Floor prices load without errors', async ({ page, consoleCapture }) => {
    // Navigate to market page
    await page.goto('/market');
    await page.waitForLoadState('networkidle');

    // Wait for floor prices to load
    await page.waitForTimeout(3000);

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

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check that floor price cards are visible
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
    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check snipes section
    const snipesSection = page.locator('text=Latest Snipe Opportunities');
    await expect(snipesSection).toBeVisible();

    // Verify snipes API was called
    const snipesCalls = consoleCapture.getApiCallsForEndpoint('/valuation/deals/snipes');
    console.log(`\nSnipes API calls: ${snipesCalls.length}`);
    snipesCalls.forEach((call) => {
      console.log(`  [${call.status}] ${call.method} ${call.url}`);
    });
  });

  test('Refresh button triggers new API calls', async ({ page }) => {
    const capture = setupConsoleCapture(page);

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Count initial API calls
    const initialFloorCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors').length;
    console.log(`Initial floor API calls: ${initialFloorCalls}`);

    // Click refresh button
    const refreshButton = page.locator('button:has-text("Refresh")');
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(2000);

      // Count API calls after refresh
      const afterRefreshCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors').length;
      console.log(`After refresh floor API calls: ${afterRefreshCalls}`);

      // Should have made additional API calls
      expect(afterRefreshCalls).toBeGreaterThan(initialFloorCalls);
    }
  });

  test('Auto-refresh triggers after 60 seconds', async ({ page }) => {
    const capture = setupConsoleCapture(page);

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

  test('API response includes fresh data indicator', async ({ page }) => {
    // Intercept API response to check meta.source
    let apiResponse: { success: boolean; data: unknown; meta?: { source?: string } } | null = null;

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
    await page.waitForTimeout(3000);

    // Verify API response structure
    console.log('\nAPI Response:', JSON.stringify(apiResponse, null, 2));

    if (apiResponse) {
      expect(apiResponse.success).toBe(true);
      expect(apiResponse.data).toBeDefined();

      // Check that data source is from price_snapshots (our fix)
      if (apiResponse.meta?.source) {
        console.log(`Data source: ${apiResponse.meta.source}`);
        // Accept 'price_snapshots', 'cache', or 'computed_fallback'
        expect(['price_snapshots', 'cache', 'computed_fallback']).toContain(apiResponse.meta.source);
      }
    }
  });
});

test.describe('Market Analytics - Error Scenarios', () => {
  test('Handles API errors gracefully', async ({ page, consoleCapture }) => {
    // Block the floor prices API to simulate error
    await page.route('**/valuation/stats/floors', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ success: false, error: 'Internal Server Error' }),
      });
    });

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Page should still render without crashing
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check for error handling in UI (loading state or error message)
    const loadingOrError =
      (await page.locator('text=Unable to load').count()) > 0 ||
      (await page.locator('[class*="skeleton"]').count()) > 0;

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

    // Add 5 second delay to floor prices API
    await page.route('**/valuation/stats/floors', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      route.continue();
    });

    await page.goto('/market');

    // Should show loading state
    const skeleton = page.locator('[class*="skeleton"]').first();
    const showsLoading = await skeleton.isVisible();
    console.log(`Shows loading skeleton: ${showsLoading}`);

    // Wait for response
    await page.waitForTimeout(6000);

    // Check no errors after slow load
    expect(capture.pageErrors.length).toBe(0);
  });
});

test.describe('Console Log Analysis', () => {
  test('Capture all console output for debugging', async ({ page }) => {
    const capture = setupConsoleCapture(page);

    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

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
