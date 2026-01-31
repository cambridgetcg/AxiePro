/**
 * Development console logging utility.
 *
 * Provides structured, colored logging for debugging.
 * Automatically disabled in production unless NEXT_PUBLIC_DEBUG=true.
 *
 * @example
 * ```typescript
 * import { createLogger } from '@/lib/logger';
 *
 * const log = createLogger('MyComponent');
 * log.debug('Processing data', { items: 5 });
 * log.info('Operation complete');
 * log.warn('Slow response detected', { latency: 2000 });
 * log.error('Failed to fetch', { error: err.message });
 * ```
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  [key: string]: unknown;
}

interface LoggerConfig {
  enabled: boolean;
  minLevel: LogLevel;
}

// Log level hierarchy for filtering
const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

// Console colors for browser DevTools
const LOG_COLORS: Record<LogLevel, string> = {
  debug: 'color: #6b7280', // gray
  info: 'color: #3b82f6',  // blue
  warn: 'color: #f59e0b',  // orange
  error: 'color: #ef4444', // red
};

// Badge styles for level indicator
const BADGE_STYLES: Record<LogLevel, string> = {
  debug: 'background: #374151; color: #d1d5db; padding: 1px 4px; border-radius: 2px; font-size: 10px;',
  info: 'background: #1d4ed8; color: #dbeafe; padding: 1px 4px; border-radius: 2px; font-size: 10px;',
  warn: 'background: #d97706; color: #fef3c7; padding: 1px 4px; border-radius: 2px; font-size: 10px;',
  error: 'background: #dc2626; color: #fee2e2; padding: 1px 4px; border-radius: 2px; font-size: 10px;',
};

/**
 * Get current logger configuration from environment.
 */
function getConfig(): LoggerConfig {
  // Check if we're in a browser environment
  const isBrowser = typeof window !== 'undefined';

  // Determine if logging should be enabled
  const isDevelopment = process.env.NODE_ENV !== 'production';
  const debugOverride = process.env.NEXT_PUBLIC_DEBUG === 'true';
  const enabled = isDevelopment || debugOverride;

  // Get minimum log level (default to 'debug' in development)
  const envLevel = process.env.NEXT_PUBLIC_LOG_LEVEL as LogLevel | undefined;
  const minLevel: LogLevel = envLevel && LOG_LEVELS[envLevel] !== undefined
    ? envLevel
    : (isDevelopment ? 'debug' : 'warn');

  return { enabled: enabled && isBrowser, minLevel };
}

/**
 * Format timestamp as HH:MM:SS.
 */
function formatTime(): string {
  const now = new Date();
  return [
    now.getHours().toString().padStart(2, '0'),
    now.getMinutes().toString().padStart(2, '0'),
    now.getSeconds().toString().padStart(2, '0'),
  ].join(':');
}

/**
 * Core logging function.
 */
function log(
  level: LogLevel,
  source: string,
  message: string,
  context?: LogContext
): void {
  const config = getConfig();

  // Skip if logging disabled or level too low
  if (!config.enabled || LOG_LEVELS[level] < LOG_LEVELS[config.minLevel]) {
    return;
  }

  const timestamp = formatTime();
  const levelUpper = level.toUpperCase().padEnd(5);

  // Build the log message with styling
  const prefix = `%c[${timestamp}] %c${levelUpper}%c [${source}]`;
  const prefixStyles = [
    'color: #9ca3af;', // timestamp gray
    BADGE_STYLES[level], // level badge
    LOG_COLORS[level], // source color matches level
  ];

  // Choose console method
  const consoleFn = level === 'error'
    ? console.error
    : level === 'warn'
      ? console.warn
      : level === 'info'
        ? console.info
        : console.debug;

  // Log with or without context
  if (context && Object.keys(context).length > 0) {
    consoleFn(prefix, ...prefixStyles, message, context);
  } else {
    consoleFn(prefix, ...prefixStyles, message);
  }
}

/**
 * Scoped logger interface.
 */
export interface ScopedLogger {
  debug: (message: string, context?: LogContext) => void;
  info: (message: string, context?: LogContext) => void;
  warn: (message: string, context?: LogContext) => void;
  error: (message: string, context?: LogContext) => void;
}

/**
 * Create a scoped logger for a component or module.
 *
 * @param source - Name of the component/module (e.g., 'WalletStore', 'ApiClient')
 * @returns Logger instance with debug, info, warn, error methods
 *
 * @example
 * ```typescript
 * const log = createLogger('AuthService');
 * log.info('User authenticated', { userId: '123' });
 * ```
 */
export function createLogger(source: string): ScopedLogger {
  return {
    debug: (message: string, context?: LogContext) => log('debug', source, message, context),
    info: (message: string, context?: LogContext) => log('info', source, message, context),
    warn: (message: string, context?: LogContext) => log('warn', source, message, context),
    error: (message: string, context?: LogContext) => log('error', source, message, context),
  };
}

/**
 * Global logger for quick one-off logging.
 * Prefer createLogger() for consistent source naming.
 */
export const logger = createLogger('App');
