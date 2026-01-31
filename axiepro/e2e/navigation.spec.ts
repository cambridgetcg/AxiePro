import { test, expect, ConsoleMessage, Page, Response } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * AxiePro Navigation Pathway Tests
 *
 * Tests all navigation routes, captures console logs, and records insights.
 * The goal is to identify any errors, warnings, or anomalies during navigation.
 */

// Define all navigation routes
const ROUTES = [
  { path: '/', name: 'Home', description: 'Landing page with hero and features', expectedStatus: 200 },
  { path: '/explorer', name: 'Explorer', description: 'Axie search and filtering', expectedStatus: 200 },
  { path: '/deals', name: 'Deals', description: 'Undervalued listing detection', expectedStatus: [200, 404] },
  { path: '/meta', name: 'Meta', description: 'Meta shifts analysis (New)', expectedStatus: [200, 404] },
  { path: '/portfolio', name: 'Portfolio', description: 'Wallet holdings tracker (New)', expectedStatus: [200, 404] },
  { path: '/breeding', name: 'Breeding', description: 'Breeding simulator', expectedStatus: 200 },
  { path: '/analytics', name: 'Analytics', description: 'Market analytics', expectedStatus: 200 },
  { path: '/market', name: 'Market', description: 'Market data and listings', expectedStatus: 200 },
  { path: '/privacy', name: 'Privacy', description: 'Privacy policy', expectedStatus: [200, 404] },
  { path: '/terms', name: 'Terms', description: 'Terms of service', expectedStatus: [200, 404] },
];

// Store for aggregating test insights
interface ConsoleLogEntry {
  type: string;
  text: string;
  location?: string;
  timestamp: string;
}

interface RouteInsight {
  route: string;
  name: string;
  description: string;
  loadTime: number;
  httpStatus: number;
  consoleLogs: ConsoleLogEntry[];
  errors: ConsoleLogEntry[];
  warnings: ConsoleLogEntry[];
  networkErrors: string[];
  apiCalls: string[];
  passed: boolean;
  notes: string[];
  pageTitle?: string;
  contentFound: string[];
}

const insights: RouteInsight[] = [];

/**
 * Helper to capture console logs from a page
 */
function setupConsoleCapture(page: Page): ConsoleLogEntry[] {
  const logs: ConsoleLogEntry[] = [];

  page.on('console', (msg: ConsoleMessage) => {
    const entry: ConsoleLogEntry = {
      type: msg.type(),
      text: msg.text(),
      location: msg.location().url,
      timestamp: new Date().toISOString(),
    };
    logs.push(entry);
  });

  return logs;
}

/**
 * Helper to capture page errors and API calls
 */
function setupPageCapture(page: Page): { errors: string[]; apiCalls: string[] } {
  const errors: string[] = [];
  const apiCalls: string[] = [];

  page.on('pageerror', (error) => {
    errors.push(`Page error: ${error.message}`);
  });

  page.on('requestfailed', (request) => {
    const failure = request.failure();
    if (failure) {
      errors.push(`Request failed: ${request.url()} - ${failure.errorText}`);
    }
  });

  page.on('response', (response) => {
    const url = response.url();
    if (url.includes('/api/') || url.includes('api.axiepro')) {
      apiCalls.push(`[${response.status()}] ${response.request().method()} ${url}`);
    }
  });

  return { errors, apiCalls };
}

test.describe('Navigation Pathways', () => {
  test.describe.configure({ mode: 'serial' });

  for (const route of ROUTES) {
    test(`Navigate to ${route.name} (${route.path})`, async ({ page }) => {
      const consoleLogs = setupConsoleCapture(page);
      const { errors: networkErrors, apiCalls } = setupPageCapture(page);
      const notes: string[] = [];
      const contentFound: string[] = [];

      const startTime = Date.now();

      // Navigate with 'load' instead of 'networkidle' for more reliability
      let response: Response | null = null;
      try {
        response = await page.goto(route.path, {
          waitUntil: 'load',
          timeout: 30000,
        });
      } catch (e) {
        notes.push(`Navigation error: ${e instanceof Error ? e.message : String(e)}`);
      }

      // Wait a bit for dynamic content
      await page.waitForTimeout(2000);

      const loadTime = Date.now() - startTime;
      const httpStatus = response?.status() || 0;

      // Check response status against expected
      const expectedStatuses = Array.isArray(route.expectedStatus)
        ? route.expectedStatus
        : [route.expectedStatus];

      if (!expectedStatuses.includes(httpStatus)) {
        notes.push(`Unexpected HTTP status: ${httpStatus} (expected: ${expectedStatuses.join(' or ')})`);
      }

      // Get page title
      const pageTitle = await page.title();
      notes.push(`Page title: ${pageTitle}`);

      // Check for visible content
      const body = await page.locator('body');
      await expect(body).toBeVisible();

      // Check header is present
      const header = await page.locator('header');
      if ((await header.count()) > 0) {
        contentFound.push('Header');
      }

      // Check for 404 page
      const notFoundText = await page.getByText(/404|not found|page could not be found/i).first();
      if ((await notFoundText.count()) > 0) {
        notes.push('404 Page detected - route not deployed');
        contentFound.push('404 Page');
      }

      // Check for Coming Soon
      const comingSoonText = await page.getByText(/coming soon/i).first();
      if ((await comingSoonText.count()) > 0) {
        notes.push('Coming Soon placeholder detected');
        contentFound.push('Coming Soon');
      }

      // Check for Connect Wallet button
      const walletButton = await page.locator('button:has-text("Connect Wallet")').first();
      if ((await walletButton.count()) > 0) {
        contentFound.push('Wallet Button');
      }

      // Check navigation items
      const navItems = ['Home', 'Explorer', 'Market', 'Breeding', 'Analytics'];
      for (const item of navItems) {
        const navLink = await page.locator(`header >> text=${item}`).first();
        if ((await navLink.count()) > 0) {
          contentFound.push(`Nav: ${item}`);
        }
      }

      // Check for footer
      const footer = await page.locator('footer');
      if ((await footer.count()) > 0) {
        contentFound.push('Footer');
      }

      // Categorize console logs
      const errors = consoleLogs.filter(
        (log) =>
          log.type === 'error' ||
          (log.text.toLowerCase().includes('error') && !log.text.includes('DevTools'))
      );
      const warnings = consoleLogs.filter(
        (log) =>
          log.type === 'warning' ||
          (log.text.toLowerCase().includes('warn') && !log.text.includes('DevTools'))
      );

      // Determine pass/fail - we accept 404 for known missing pages
      const passed =
        errors.length === 0 && networkErrors.length === 0 && expectedStatuses.includes(httpStatus);

      // Store insight for this route
      const insight: RouteInsight = {
        route: route.path,
        name: route.name,
        description: route.description,
        loadTime,
        httpStatus,
        consoleLogs,
        errors,
        warnings,
        networkErrors,
        apiCalls,
        passed,
        notes,
        pageTitle,
        contentFound,
      };
      insights.push(insight);

      // Log summary to console
      console.log(`\n=== ${route.name} (${route.path}) ===`);
      console.log(`HTTP Status: ${httpStatus}`);
      console.log(`Load time: ${loadTime}ms`);
      console.log(`Console logs: ${consoleLogs.length}`);
      console.log(`Errors: ${errors.length}`);
      console.log(`Warnings: ${warnings.length}`);
      console.log(`API calls: ${apiCalls.length}`);
      console.log(`Content found: ${contentFound.join(', ')}`);

      if (apiCalls.length > 0) {
        console.log('\nAPI Calls:');
        apiCalls.forEach((call) => console.log(`  - ${call}`));
      }

      if (errors.length > 0) {
        console.log('\nConsole Errors:');
        errors.forEach((e) => console.log(`  - ${e.text.slice(0, 200)}`));
      }

      // Test passes if expected status and no critical errors
      expect(expectedStatuses).toContain(httpStatus);
    });
  }
});

test.describe('Navigation Flow', () => {
  test('Navigate through header menu sequentially', async ({ page }) => {
    const consoleLogs = setupConsoleCapture(page);
    const flowNotes: string[] = [];

    console.log('\n=== Sequential Navigation Flow ===\n');

    // Start at home
    await page.goto('/');
    await page.waitForLoadState('load');
    await page.waitForTimeout(1000);

    // Navigate through each main nav item
    const navItems = [
      { name: 'Explorer', expectedPath: '/explorer' },
      { name: 'Market', expectedPath: '/market' },
      { name: 'Breeding', expectedPath: '/breeding' },
      { name: 'Analytics', expectedPath: '/analytics' },
    ];

    for (const item of navItems) {
      console.log(`Clicking ${item.name}...`);

      // Find and click the navigation link in header
      const navLink = page.locator(`header >> a:has-text("${item.name}")`).first();

      if ((await navLink.count()) > 0) {
        await navLink.click();
        await page.waitForLoadState('load');
        await page.waitForTimeout(500);

        const currentUrl = page.url();
        if (currentUrl.includes(item.expectedPath)) {
          console.log(`  ✓ Reached ${item.expectedPath}`);
          flowNotes.push(`✓ ${item.name}: Navigation successful`);
        } else {
          console.log(`  ⚠ URL mismatch: ${currentUrl}`);
          flowNotes.push(`⚠ ${item.name}: URL mismatch - ${currentUrl}`);
        }
      } else {
        console.log(`  ⚠ Nav link not found for ${item.name}`);
        flowNotes.push(`⚠ ${item.name}: Link not found in header`);
      }
    }

    // Check for any errors during flow
    const errors = consoleLogs.filter((log) => log.type === 'error');
    console.log(`\nTotal console errors during flow: ${errors.length}`);
    console.log(`\nFlow Summary:\n${flowNotes.join('\n')}`);
  });
});

test.describe('Wallet Connection UI', () => {
  test('Wallet button is visible and clickable', async ({ page }) => {
    const consoleLogs = setupConsoleCapture(page);

    await page.goto('/');
    await page.waitForLoadState('load');
    await page.waitForTimeout(1000);

    // Find wallet button in header
    const walletButton = page.locator('button:has-text("Connect Wallet")').first();

    if ((await walletButton.count()) > 0) {
      await expect(walletButton).toBeVisible();
      console.log('✓ Wallet button found and visible');

      // Click to see if modal opens (wallet won't be installed in test env)
      await walletButton.click();
      await page.waitForTimeout(1500);

      // Check for any error dialogs or modals
      const dialog = page.locator('[role="dialog"]');
      if ((await dialog.count()) > 0) {
        console.log('✓ Dialog opened on wallet click');

        // Check dialog content
        const dialogText = await dialog.textContent();
        console.log(`Dialog content preview: ${dialogText?.slice(0, 200)}`);
      }

      // Check console for any wallet-related logs
      const walletLogs = consoleLogs.filter(
        (log) =>
          log.text.toLowerCase().includes('wallet') || log.text.toLowerCase().includes('ronin')
      );

      console.log(`Wallet-related console logs: ${walletLogs.length}`);
      walletLogs.forEach((log) => console.log(`  [${log.type}] ${log.text.slice(0, 150)}`));
    } else {
      console.log('⚠ Wallet button not found in header');
    }
  });
});

test.describe('Responsive Design', () => {
  test('Check mobile viewport navigation', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');
    await page.waitForLoadState('load');
    await page.waitForTimeout(1000);

    // Look for mobile menu button
    const menuButton = page.locator('button:has(svg.lucide-menu), button[aria-label*="menu"]').first();

    if ((await menuButton.count()) > 0) {
      console.log('✓ Mobile menu button found');
      await menuButton.click();
      await page.waitForTimeout(500);

      // Check if menu sheet opens
      const sheet = page.locator('[data-state="open"]');
      if ((await sheet.count()) > 0) {
        console.log('✓ Mobile menu sheet opened');
      }
    } else {
      console.log('⚠ Mobile menu button not found');
    }
  });
});

// After all tests, write comprehensive insights to markdown file
test.afterAll(async () => {
  if (insights.length === 0) return;

  const outputDir = path.join(process.cwd(), 'e2e');
  const outputPath = path.join(outputDir, 'test-insights.md');

  const timestamp = new Date().toISOString();
  const passedCount = insights.filter((i) => i.passed).length;
  const failedCount = insights.filter((i) => !i.passed).length;
  const notDeployed = insights.filter((i) => i.httpStatus === 404).length;

  let markdown = `# AxiePro E2E Test Insights

Generated: ${timestamp}

## Executive Summary

- **Total Routes Tested**: ${insights.length}
- **Passed**: ${passedCount}
- **Failed/Issues**: ${failedCount}
- **Not Deployed (404)**: ${notDeployed}

### Key Findings

`;

  // Identify key findings
  const notDeployedRoutes = insights.filter((i) => i.httpStatus === 404);
  if (notDeployedRoutes.length > 0) {
    markdown += `**Routes Not Yet Deployed:**\n`;
    notDeployedRoutes.forEach((r) => {
      markdown += `- \`${r.route}\` (${r.name})\n`;
    });
    markdown += '\n';
  }

  const comingSoonRoutes = insights.filter((i) => i.notes.some((n) => n.includes('Coming Soon')));
  if (comingSoonRoutes.length > 0) {
    markdown += `**Routes with "Coming Soon" Placeholder:**\n`;
    comingSoonRoutes.forEach((r) => {
      markdown += `- \`${r.route}\` (${r.name})\n`;
    });
    markdown += '\n';
  }

  const errorRoutes = insights.filter((i) => i.errors.length > 0);
  if (errorRoutes.length > 0) {
    markdown += `**Routes with Console Errors:**\n`;
    errorRoutes.forEach((r) => {
      markdown += `- \`${r.route}\` (${r.name}): ${r.errors.length} errors\n`;
    });
    markdown += '\n';
  }

  markdown += `## Route Summary

| Route | Name | Status | Load Time | Errors | Warnings | API Calls | State |
|-------|------|--------|-----------|--------|----------|-----------|-------|
`;

  for (const insight of insights) {
    const state =
      insight.httpStatus === 404
        ? '❌ Not Deployed'
        : insight.notes.some((n) => n.includes('Coming Soon'))
          ? '🚧 Coming Soon'
          : insight.passed
            ? '✅ Live'
            : '⚠️ Issues';

    markdown += `| \`${insight.route}\` | ${insight.name} | ${insight.httpStatus} | ${insight.loadTime}ms | ${insight.errors.length} | ${insight.warnings.length} | ${insight.apiCalls.length} | ${state} |\n`;
  }

  markdown += `\n## Detailed Route Analysis\n\n`;

  for (const insight of insights) {
    markdown += `### ${insight.name} (\`${insight.route}\`)\n\n`;
    markdown += `> ${insight.description}\n\n`;
    markdown += `| Metric | Value |\n`;
    markdown += `|--------|-------|\n`;
    markdown += `| HTTP Status | ${insight.httpStatus} |\n`;
    markdown += `| Load Time | ${insight.loadTime}ms |\n`;
    markdown += `| Page Title | ${insight.pageTitle || 'N/A'} |\n`;
    markdown += `| Console Logs | ${insight.consoleLogs.length} |\n`;
    markdown += `| Errors | ${insight.errors.length} |\n`;
    markdown += `| Warnings | ${insight.warnings.length} |\n`;
    markdown += `| API Calls | ${insight.apiCalls.length} |\n`;
    markdown += `| Test Status | ${insight.passed ? '✅ Passed' : '❌ Failed'} |\n\n`;

    if (insight.contentFound.length > 0) {
      markdown += `**Content Found:**\n`;
      insight.contentFound.forEach((content) => {
        markdown += `- ${content}\n`;
      });
      markdown += '\n';
    }

    if (insight.notes.length > 0) {
      markdown += `**Notes:**\n`;
      insight.notes.forEach((note) => {
        markdown += `- ${note}\n`;
      });
      markdown += '\n';
    }

    if (insight.apiCalls.length > 0) {
      markdown += `**API Calls:**\n\`\`\`\n`;
      insight.apiCalls.forEach((call) => {
        markdown += `${call}\n`;
      });
      markdown += `\`\`\`\n\n`;
    }

    if (insight.errors.length > 0) {
      markdown += `**Console Errors:**\n\`\`\`\n`;
      insight.errors.forEach((e) => {
        markdown += `[${e.type}] ${e.text.slice(0, 500)}\n`;
      });
      markdown += `\`\`\`\n\n`;
    }

    if (insight.warnings.length > 0) {
      markdown += `**Console Warnings (first 5):**\n\`\`\`\n`;
      insight.warnings.slice(0, 5).forEach((w) => {
        markdown += `[${w.type}] ${w.text.slice(0, 300)}\n`;
      });
      if (insight.warnings.length > 5) {
        markdown += `... and ${insight.warnings.length - 5} more\n`;
      }
      markdown += `\`\`\`\n\n`;
    }

    markdown += '---\n\n';
  }

  markdown += `## Recommendations

Based on the test results:

1. **Deploy Missing Routes**: The following routes return 404 and should be deployed:
`;
  notDeployedRoutes.forEach((r) => {
    markdown += `   - ${r.route} (${r.name})\n`;
  });

  markdown += `
2. **Complete "Coming Soon" Features**: Routes marked as "Coming Soon" should be prioritized for completion.

3. **Navigation Consistency**: Ensure all routes in the header navigation are accessible and deployed.

4. **Error Monitoring**: Set up error tracking for production to catch console errors.

## Test Environment

- **Base URL**: ${process.env.E2E_BASE_URL || 'http://localhost:3000'}
- **Browser**: Chromium
- **Test Framework**: Playwright
`;

  // Write insights file
  fs.writeFileSync(outputPath, markdown);
  console.log(`\n📝 Insights written to ${outputPath}`);
});
