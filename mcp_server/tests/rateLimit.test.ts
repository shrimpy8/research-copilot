/**
 * Tests for rate limiting middleware.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  checkRateLimit,
  getRateLimitInfo,
  clearRateLimits,
  getToolCategory,
} from '../src/middleware/rateLimit.js';
import { RateLimitError } from '../src/errors/index.js';

// Mock config to set low rate limits for testing
vi.mock('../src/config/index.js', () => ({
  config_values: {
    rateLimitSearch: 3,
    rateLimitFetch: 5,
    rateLimitNotes: 10,
  },
}));

describe('Rate Limiting', () => {
  beforeEach(() => {
    clearRateLimits();
  });

  describe('getToolCategory', () => {
    it('should map web_search to search category', () => {
      expect(getToolCategory('web_search')).toBe('search');
    });

    it('should map fetch_page to fetch category', () => {
      expect(getToolCategory('fetch_page')).toBe('fetch');
    });

    it('should map note tools to notes category', () => {
      expect(getToolCategory('save_note')).toBe('notes');
      expect(getToolCategory('list_notes')).toBe('notes');
      expect(getToolCategory('get_note')).toBe('notes');
    });

    it('should default unknown tools to notes category', () => {
      expect(getToolCategory('unknown_tool')).toBe('notes');
    });
  });

  describe('checkRateLimit', () => {
    it('should allow requests within limit', () => {
      expect(() => checkRateLimit('web_search')).not.toThrow();
      expect(() => checkRateLimit('web_search')).not.toThrow();
      expect(() => checkRateLimit('web_search')).not.toThrow();
    });

    it('should throw RateLimitError when limit exceeded', () => {
      // Use up all allowed requests
      checkRateLimit('web_search');
      checkRateLimit('web_search');
      checkRateLimit('web_search');

      // Fourth request should fail (limit is 3)
      expect(() => checkRateLimit('web_search')).toThrow(RateLimitError);
    });

    it('should track limits per category independently', () => {
      // Use up search limit
      checkRateLimit('web_search');
      checkRateLimit('web_search');
      checkRateLimit('web_search');

      // Fetch should still work
      expect(() => checkRateLimit('fetch_page')).not.toThrow();
    });
  });

  describe('getRateLimitInfo', () => {
    it('should return full quota when no requests made', () => {
      const info = getRateLimitInfo('web_search');
      expect(info.remaining).toBe(3);
      expect(info.limit).toBe(3);
    });

    it('should decrease remaining after requests', () => {
      checkRateLimit('web_search');
      const info = getRateLimitInfo('web_search');
      expect(info.remaining).toBe(2);
    });

    it('should show zero remaining when limit reached', () => {
      checkRateLimit('web_search');
      checkRateLimit('web_search');
      checkRateLimit('web_search');

      const info = getRateLimitInfo('web_search');
      expect(info.remaining).toBe(0);
    });
  });

  describe('clearRateLimits', () => {
    it('should reset all rate limits', () => {
      // Use up some limits
      checkRateLimit('web_search');
      checkRateLimit('web_search');

      // Clear
      clearRateLimits();

      // Should have full quota again
      const info = getRateLimitInfo('web_search');
      expect(info.remaining).toBe(3);
    });
  });
});
