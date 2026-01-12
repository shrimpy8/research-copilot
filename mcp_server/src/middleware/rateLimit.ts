/**
 * Rate limiting middleware.
 *
 * Implements per-tool rate limiting using a sliding window algorithm.
 * Limits are configured per minute in config.
 */

import { config_values } from '../config/index.js';
import { RateLimitError } from '../errors/index.js';

/**
 * Tool categories for rate limiting
 */
export type ToolCategory = 'search' | 'fetch' | 'notes';

/**
 * Rate limit entry
 */
interface RateLimitEntry {
  timestamps: number[];
  windowMs: number;
  maxRequests: number;
}

/**
 * Rate limiter state
 */
const rateLimiters: Map<ToolCategory, RateLimitEntry> = new Map();

/**
 * Get rate limit configuration for a tool category
 */
function getRateLimitConfig(category: ToolCategory): { maxRequests: number; windowMs: number } {
  const windowMs = 60 * 1000; // 1 minute window

  switch (category) {
    case 'search':
      return { maxRequests: config_values.rateLimitSearch, windowMs };
    case 'fetch':
      return { maxRequests: config_values.rateLimitFetch, windowMs };
    case 'notes':
      return { maxRequests: config_values.rateLimitNotes, windowMs };
    default:
      return { maxRequests: 50, windowMs };
  }
}

/**
 * Map tool names to categories
 */
export function getToolCategory(toolName: string): ToolCategory {
  switch (toolName) {
    case 'web_search':
      return 'search';
    case 'fetch_page':
      return 'fetch';
    case 'save_note':
    case 'list_notes':
    case 'get_note':
      return 'notes';
    default:
      return 'notes'; // Default to notes category
  }
}

/**
 * Check rate limit for a tool category
 * Throws RateLimitError if limit exceeded
 */
export function checkRateLimit(toolName: string): void {
  const category = getToolCategory(toolName);
  const now = Date.now();
  const config = getRateLimitConfig(category);

  // Get or create rate limit entry
  let entry = rateLimiters.get(category);
  if (!entry) {
    entry = {
      timestamps: [],
      windowMs: config.windowMs,
      maxRequests: config.maxRequests,
    };
    rateLimiters.set(category, entry);
  }

  // Update config in case it changed
  entry.windowMs = config.windowMs;
  entry.maxRequests = config.maxRequests;

  // Remove expired timestamps (outside sliding window)
  const windowStart = now - entry.windowMs;
  entry.timestamps = entry.timestamps.filter((ts) => ts > windowStart);

  // Check if limit exceeded
  if (entry.timestamps.length >= entry.maxRequests) {
    throw new RateLimitError(toolName);
  }

  // Add current request timestamp
  entry.timestamps.push(now);
}

/**
 * Get rate limit info for a tool category
 */
export function getRateLimitInfo(toolName: string): {
  remaining: number;
  limit: number;
  resetMs: number;
} {
  const category = getToolCategory(toolName);
  const now = Date.now();
  const config = getRateLimitConfig(category);

  const entry = rateLimiters.get(category);
  if (!entry || entry.timestamps.length === 0) {
    return {
      remaining: config.maxRequests,
      limit: config.maxRequests,
      resetMs: 0,
    };
  }

  // Remove expired timestamps
  const windowStart = now - entry.windowMs;
  const validTimestamps = entry.timestamps.filter((ts) => ts > windowStart);

  // Calculate reset time (when oldest request expires)
  const oldestTimestamp = validTimestamps[0] || now;
  const resetMs = Math.max(0, oldestTimestamp + entry.windowMs - now);

  return {
    remaining: Math.max(0, config.maxRequests - validTimestamps.length),
    limit: config.maxRequests,
    resetMs,
  };
}

/**
 * Clear rate limit state (useful for testing)
 */
export function clearRateLimits(): void {
  rateLimiters.clear();
}
