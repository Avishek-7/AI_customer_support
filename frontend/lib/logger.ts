/**
 * Frontend Logger Utility
 * 
 * Provides structured logging for the frontend application.
 * Logs are output to the browser console with different levels.
 * 
 * Usage:
 *   import { logger } from '@/lib/logger';
 *   logger.info('User logged in', { userId: 123 });
 *   logger.error('Failed to fetch', { error: err.message });
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  module?: string;
  data?: Record<string, unknown>;
}

// Color codes for console output
const levelColors: Record<LogLevel, string> = {
  debug: '#6b7280', // gray
  info: '#3b82f6',  // blue
  warn: '#f59e0b',  // amber
  error: '#ef4444', // red
};

const levelIcons: Record<LogLevel, string> = {
  debug: '🔍',
  info: 'ℹ️',
  warn: '⚠️',
  error: '❌',
};

class Logger {
  private module: string;
  private isDev: boolean;
  private isEnabled: boolean;
  private sensitiveKeyPattern = /(email|token|password|secret|ssn|userid|user_id|authorization|cookie)/i;

  constructor(module: string = 'app') {
    this.module = module;
    this.isDev = process.env.NODE_ENV !== 'production';
    const explicitEnable = process.env.NEXT_PUBLIC_ENABLE_CLIENT_LOGS === 'true';
    this.isEnabled = this.isDev || explicitEnable;
  }

  private sanitizeData(data?: Record<string, unknown>): Record<string, unknown> | undefined {
    if (!data) return data;
    const sanitized: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data)) {
      if (this.sensitiveKeyPattern.test(key)) {
        sanitized[key] = '[REDACTED]';
      } else {
        sanitized[key] = value;
      }
    }
    return sanitized;
  }

  private formatLog(level: LogLevel, message: string, data?: Record<string, unknown>): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      module: this.module,
      data,
    };
  }

  private log(level: LogLevel, message: string, data?: Record<string, unknown>) {
    if (!this.isEnabled) {
      return;
    }

    const sanitizedData = this.sanitizeData(data);
    const entry = this.formatLog(level, message, sanitizedData);
    const color = levelColors[level];
    const icon = levelIcons[level];
    
    const prefix = `%c${icon} [${entry.timestamp.split('T')[1].split('.')[0]}] [${this.module}]`;
    const style = `color: ${color}; font-weight: bold;`;
    
    if (sanitizedData && Object.keys(sanitizedData).length > 0) {
      console[level === 'debug' ? 'log' : level](prefix, style, message, sanitizedData);
    } else {
      console[level === 'debug' ? 'log' : level](prefix, style, message);
    }

    // In development, also store logs for debugging
    if (this.isDev && typeof window !== 'undefined') {
      try {
        const logs = JSON.parse(sessionStorage.getItem('__app_logs') || '[]');
        logs.push(entry);
        // Keep only last 100 logs
        if (logs.length > 100) logs.shift();
        sessionStorage.setItem('__app_logs', JSON.stringify(logs));
      } catch {
        // Ignore storage errors so logging flow continues
      }
    }
  }

  debug(message: string, data?: Record<string, unknown>) {
    if (this.isDev) {
      this.log('debug', message, data);
    }
  }

  info(message: string, data?: Record<string, unknown>) {
    this.log('info', message, data);
  }

  warn(message: string, data?: Record<string, unknown>) {
    this.log('warn', message, data);
  }

  error(message: string, data?: Record<string, unknown>) {
    this.log('error', message, data);
  }

  // Special method for logging API responses - specifically for answer comparison
  logAnswer(source: string, answer: string, metadata?: Record<string, unknown>, storeFullAnswer = false) {
    const truncated = answer.length > 500 ? `${answer.slice(0, 500)}...` : answer;
    const payload: Record<string, unknown> = {
      answer_preview: truncated,
      answer_length: answer.length,
      ...metadata,
    };
    if (storeFullAnswer) {
      payload.answer = answer;
    }
    this.info(`=== ${source} ===`, {
      ...payload,
    });
    console.log(`%c[${source}] ${truncated}`, 'color: #10b981; font-weight: bold;');
  }

  // Get all stored logs (for debugging)
  getLogs(): LogEntry[] {
    if (typeof window === 'undefined') return [];
    try {
      return JSON.parse(sessionStorage.getItem('__app_logs') || '[]');
    } catch {
      sessionStorage.removeItem('__app_logs');
      return [];
    }
  }

  // Clear stored logs
  clearLogs() {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('__app_logs');
    }
  }
}

// Create module-specific loggers
export function createLogger(module: string): Logger {
  return new Logger(module);
}

// Default logger instance
export const logger = new Logger('app');

// Pre-configured loggers for different modules
export const authLogger = createLogger('auth');
export const chatLogger = createLogger('chat');
export const docsLogger = createLogger('documents');
export const apiLogger = createLogger('api');
