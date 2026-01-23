/**
 * Console Capture Fixtures for Playwright E2E Tests
 *
 * Provides reusable utilities for capturing and analyzing browser console output.
 * Use these in any test to debug frontend issues.
 */

import { test as base, Page, ConsoleMessage } from '@playwright/test';

/**
 * Detailed console log entry with full context
 */
export interface ConsoleLogEntry {
  type: 'log' | 'debug' | 'info' | 'error' | 'warning' | 'dir' | 'table' | 'trace' | 'assert' | string;
  text: string;
  args: unknown[];
  location: {
    url: string;
    lineNumber: number;
    columnNumber: number;
  };
  timestamp: string;
  stackTrace?: string;
}

/**
 * Network request/response entry
 */
export interface NetworkEntry {
  method: string;
  url: string;
  status?: number;
  statusText?: string;
  duration?: number;
  error?: string;
  timestamp: string;
}

/**
 * Aggregated console capture results
 */
export interface ConsoleCaptureResult {
  logs: ConsoleLogEntry[];
  errors: ConsoleLogEntry[];
  warnings: ConsoleLogEntry[];
  networkRequests: NetworkEntry[];
  networkErrors: NetworkEntry[];
  apiCalls: NetworkEntry[];
  pageErrors: string[];

  // Helper methods
  hasErrors: () => boolean;
  hasWarnings: () => boolean;
  getErrorMessages: () => string[];
  getApiCallsForEndpoint: (endpoint: string) => NetworkEntry[];
  findLogContaining: (text: string) => ConsoleLogEntry | undefined;
  toJSON: () => string;
  toMarkdown: () => string;
}

/**
 * Set up comprehensive console and network capture for a page.
 * Call this at the start of your test.
 *
 * @example
 * ```ts
 * test('my test', async ({ page }) => {
 *   const capture = setupConsoleCapture(page);
 *
 *   await page.goto('/market');
 *   // ... do stuff ...
 *
 *   // Check for errors
 *   expect(capture.hasErrors()).toBe(false);
 *
 *   // Get API calls
 *   const floorCalls = capture.getApiCallsForEndpoint('/valuation/stats/floors');
 *   expect(floorCalls.length).toBeGreaterThan(0);
 * });
 * ```
 */
export function setupConsoleCapture(page: Page): ConsoleCaptureResult {
  const logs: ConsoleLogEntry[] = [];
  const networkRequests: NetworkEntry[] = [];
  const pageErrors: string[] = [];

  // Capture console messages with full details
  page.on('console', async (msg: ConsoleMessage) => {
    // Get argument values (may fail for complex objects)
    let args: unknown[] = [];
    try {
      args = await Promise.all(
        msg.args().map(async (arg) => {
          try {
            return await arg.jsonValue();
          } catch {
            return '[Complex Object]';
          }
        })
      );
    } catch {
      args = ['[Failed to serialize args]'];
    }

    const location = msg.location();
    const entry: ConsoleLogEntry = {
      type: msg.type(),
      text: msg.text(),
      args,
      location: {
        url: location.url || '',
        lineNumber: location.lineNumber || 0,
        columnNumber: location.columnNumber || 0,
      },
      timestamp: new Date().toISOString(),
    };

    // Capture stack trace for errors
    if (msg.type() === 'error' || msg.type() === 'trace') {
      try {
        const stack = await msg.args()[0]?.evaluate((arg: unknown) => {
          if (arg instanceof Error) {
            return arg.stack;
          }
          return undefined;
        });
        if (stack) {
          entry.stackTrace = stack;
        }
      } catch {
        // Ignore stack trace failures
      }
    }

    logs.push(entry);
  });

  // Capture page errors (uncaught exceptions)
  page.on('pageerror', (error) => {
    pageErrors.push(`${error.name}: ${error.message}\n${error.stack || ''}`);
  });

  // Capture network requests
  page.on('request', (request) => {
    const entry: NetworkEntry = {
      method: request.method(),
      url: request.url(),
      timestamp: new Date().toISOString(),
    };
    networkRequests.push(entry);
  });

  // Update network requests with response info
  page.on('response', (response) => {
    const url = response.url();
    const existing = networkRequests.find((r) => r.url === url && !r.status);
    if (existing) {
      existing.status = response.status();
      existing.statusText = response.statusText();
    }
  });

  // Capture failed requests
  page.on('requestfailed', (request) => {
    const url = request.url();
    const existing = networkRequests.find((r) => r.url === url);
    if (existing) {
      const failure = request.failure();
      existing.error = failure?.errorText || 'Unknown failure';
    }
  });

  // Return result object with helper methods
  const result: ConsoleCaptureResult = {
    logs,
    networkRequests,
    pageErrors,

    get errors() {
      return logs.filter(
        (log) =>
          log.type === 'error' ||
          log.type === 'assert' ||
          (log.text.toLowerCase().includes('error') &&
            !log.text.includes('DevTools') &&
            !log.text.includes('React DevTools'))
      );
    },

    get warnings() {
      return logs.filter(
        (log) =>
          log.type === 'warning' ||
          (log.text.toLowerCase().includes('warn') &&
            !log.text.includes('DevTools'))
      );
    },

    get networkErrors() {
      return networkRequests.filter((r) => r.error || (r.status && r.status >= 400));
    },

    get apiCalls() {
      return networkRequests.filter(
        (r) =>
          r.url.includes('/api/') ||
          r.url.includes('/valuation/') ||
          r.url.includes('/market/') ||
          r.url.includes('/axies/') ||
          r.url.includes('/breeding/') ||
          r.url.includes('/meta/')
      );
    },

    hasErrors() {
      return this.errors.length > 0 || this.pageErrors.length > 0;
    },

    hasWarnings() {
      return this.warnings.length > 0;
    },

    getErrorMessages() {
      return [
        ...this.errors.map((e) => e.text),
        ...this.pageErrors,
      ];
    },

    getApiCallsForEndpoint(endpoint: string) {
      return this.apiCalls.filter((r) => r.url.includes(endpoint));
    },

    findLogContaining(text: string) {
      return logs.find((log) => log.text.toLowerCase().includes(text.toLowerCase()));
    },

    toJSON() {
      return JSON.stringify(
        {
          logs,
          errors: this.errors,
          warnings: this.warnings,
          networkRequests,
          networkErrors: this.networkErrors,
          apiCalls: this.apiCalls,
          pageErrors,
          summary: {
            totalLogs: logs.length,
            errorCount: this.errors.length,
            warningCount: this.warnings.length,
            apiCallCount: this.apiCalls.length,
            pageErrorCount: pageErrors.length,
          },
        },
        null,
        2
      );
    },

    toMarkdown() {
      let md = `## Console Capture Summary\n\n`;
      md += `| Metric | Count |\n|--------|-------|\n`;
      md += `| Total Logs | ${logs.length} |\n`;
      md += `| Errors | ${this.errors.length} |\n`;
      md += `| Warnings | ${this.warnings.length} |\n`;
      md += `| API Calls | ${this.apiCalls.length} |\n`;
      md += `| Page Errors | ${pageErrors.length} |\n\n`;

      if (this.errors.length > 0) {
        md += `### Errors\n\n\`\`\`\n`;
        this.errors.forEach((e) => {
          md += `[${e.type}] ${e.text}\n`;
          if (e.stackTrace) {
            md += `Stack: ${e.stackTrace.slice(0, 500)}\n`;
          }
          md += `Location: ${e.location.url}:${e.location.lineNumber}\n\n`;
        });
        md += `\`\`\`\n\n`;
      }

      if (this.apiCalls.length > 0) {
        md += `### API Calls\n\n\`\`\`\n`;
        this.apiCalls.forEach((call) => {
          const status = call.status || 'pending';
          const error = call.error ? ` (${call.error})` : '';
          md += `[${status}] ${call.method} ${call.url}${error}\n`;
        });
        md += `\`\`\`\n\n`;
      }

      return md;
    },
  };

  return result;
}

/**
 * Extended test fixture with console capture built in.
 *
 * @example
 * ```ts
 * import { test, expect } from './fixtures/console-capture';
 *
 * test('my test', async ({ page, consoleCapture }) => {
 *   await page.goto('/market');
 *
 *   // Console capture is automatically set up
 *   expect(consoleCapture.hasErrors()).toBe(false);
 * });
 * ```
 */
export const test = base.extend<{
  consoleCapture: ConsoleCaptureResult;
}>({
  consoleCapture: async ({ page }, use) => {
    const capture = setupConsoleCapture(page);
    await use(capture);

    // Log summary after test
    if (capture.errors.length > 0 || capture.pageErrors.length > 0) {
      console.log('\n--- Console Errors Detected ---');
      capture.getErrorMessages().forEach((msg) => {
        console.log(`  - ${msg.slice(0, 200)}`);
      });
    }
  },
});

export { expect } from '@playwright/test';
