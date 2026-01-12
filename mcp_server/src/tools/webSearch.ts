/**
 * Web search tool implementation.
 *
 * Supports two providers:
 * - DuckDuckGo (default, no API key required)
 * - Serper (requires API key, better quality)
 */

import { config_values } from '../config/index.js';
import { ErrorCodes, SearchError } from '../errors/index.js';

/**
 * Search result structure
 */
export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

/**
 * Web search response
 */
export interface WebSearchResponse {
  results: SearchResult[];
  provider: 'duckduckgo' | 'serper';
  query: string;
}

/**
 * DuckDuckGo API response structure
 */
interface DuckDuckGoResult {
  Text: string;
  FirstURL: string;
  Icon?: { URL: string };
  Result?: string;
}

interface DuckDuckGoResponse {
  Abstract: string;
  AbstractURL: string;
  AbstractText: string;
  RelatedTopics: DuckDuckGoResult[];
  Results: DuckDuckGoResult[];
}

/**
 * Serper API response structure
 */
interface SerperResult {
  title: string;
  link: string;
  snippet: string;
  position: number;
}

interface SerperResponse {
  organic: SerperResult[];
  searchParameters: {
    q: string;
  };
}

/**
 * Search using DuckDuckGo Instant Answer API
 *
 * Note: DuckDuckGo's API is limited - it returns instant answers
 * rather than full search results. For production, consider using
 * a proper search API like Serper.
 */
async function searchDuckDuckGo(
  query: string,
  limit: number
): Promise<SearchResult[]> {
  const encodedQuery = encodeURIComponent(query);
  const url = `https://api.duckduckgo.com/?q=${encodedQuery}&format=json&no_html=1&skip_disambig=1`;

  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    config_values.searchTimeoutMs
  );

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': config_values.userAgent,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new SearchError(
        ErrorCodes.SEARCH_FAILED,
        `DuckDuckGo API returned ${response.status}`,
        { status: response.status }
      );
    }

    const data = (await response.json()) as DuckDuckGoResponse;
    const results: SearchResult[] = [];

    // Extract from Abstract
    if (data.Abstract && data.AbstractURL) {
      results.push({
        title: data.AbstractText.substring(0, 100) || query,
        url: data.AbstractURL,
        snippet: data.Abstract,
      });
    }

    // Extract from RelatedTopics
    for (const topic of data.RelatedTopics || []) {
      if (results.length >= limit) break;

      if (topic.FirstURL && topic.Text) {
        // Extract title from Text (usually before " - ")
        const titleMatch = topic.Text.match(/^([^-]+)/);
        const title = titleMatch?.[1]?.trim() ?? topic.Text.substring(0, 50);

        results.push({
          title,
          url: topic.FirstURL,
          snippet: topic.Text,
        });
      }

      // Handle nested topics
      if ('Topics' in topic && Array.isArray((topic as unknown as { Topics: DuckDuckGoResult[] }).Topics)) {
        for (const subTopic of (topic as unknown as { Topics: DuckDuckGoResult[] }).Topics) {
          if (results.length >= limit) break;
          if (subTopic.FirstURL && subTopic.Text) {
            const titleMatch = subTopic.Text.match(/^([^-]+)/);
            const title = titleMatch?.[1]?.trim() ?? subTopic.Text.substring(0, 50);

            results.push({
              title,
              url: subTopic.FirstURL,
              snippet: subTopic.Text,
            });
          }
        }
      }
    }

    // Extract from Results
    for (const result of data.Results || []) {
      if (results.length >= limit) break;
      if (result.FirstURL && result.Text) {
        results.push({
          title: result.Text.substring(0, 100),
          url: result.FirstURL,
          snippet: result.Text,
        });
      }
    }

    return results.slice(0, limit);
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof SearchError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SearchError(
          ErrorCodes.SEARCH_TIMEOUT,
          'DuckDuckGo search timed out',
          { timeoutMs: config_values.searchTimeoutMs }
        );
      }
      throw new SearchError(
        ErrorCodes.SEARCH_FAILED,
        `DuckDuckGo search failed: ${error.message}`
      );
    }

    throw new SearchError(
      ErrorCodes.SEARCH_FAILED,
      'DuckDuckGo search failed with unknown error'
    );
  }
}

/**
 * Search using Serper API (Google search results)
 */
async function searchSerper(query: string, limit: number): Promise<SearchResult[]> {
  const apiKey = config_values.serperApiKey;

  if (!apiKey) {
    throw new SearchError(
      ErrorCodes.SEARCH_FAILED,
      'Serper API key is required but not configured'
    );
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    config_values.searchTimeoutMs
  );

  try {
    const response = await fetch('https://google.serper.dev/search', {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': apiKey,
      },
      body: JSON.stringify({
        q: query,
        num: limit,
      }),
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 429) {
        throw new SearchError(
          ErrorCodes.SEARCH_RATE_LIMITED,
          'Serper API rate limit exceeded'
        );
      }
      throw new SearchError(
        ErrorCodes.SEARCH_FAILED,
        `Serper API returned ${response.status}`,
        { status: response.status }
      );
    }

    const data = (await response.json()) as SerperResponse;

    if (!data.organic || data.organic.length === 0) {
      return [];
    }

    return data.organic.slice(0, limit).map((result) => ({
      title: result.title,
      url: result.link,
      snippet: result.snippet || '',
    }));
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof SearchError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SearchError(
          ErrorCodes.SEARCH_TIMEOUT,
          'Serper search timed out',
          { timeoutMs: config_values.searchTimeoutMs }
        );
      }
      throw new SearchError(
        ErrorCodes.SEARCH_FAILED,
        `Serper search failed: ${error.message}`
      );
    }

    throw new SearchError(
      ErrorCodes.SEARCH_FAILED,
      'Serper search failed with unknown error'
    );
  }
}

/**
 * Perform a web search using the configured provider
 */
export async function webSearch(
  query: string,
  limit: number = 3,
  provider?: 'duckduckgo' | 'serper'
): Promise<WebSearchResponse> {
  // Validate input
  if (!query || query.trim().length === 0) {
    throw new SearchError(ErrorCodes.SEARCH_FAILED, 'Search query is required');
  }

  const actualLimit = Math.min(Math.max(1, limit), 5);
  const actualProvider = provider || config_values.searchProvider;

  let results: SearchResult[];

  if (actualProvider === 'serper') {
    results = await searchSerper(query.trim(), actualLimit);
  } else {
    results = await searchDuckDuckGo(query.trim(), actualLimit);
  }

  // Check for no results
  if (results.length === 0) {
    throw new SearchError(
      ErrorCodes.SEARCH_NO_RESULTS,
      `No results found for: ${query}`,
      { query }
    );
  }

  return {
    results,
    provider: actualProvider,
    query: query.trim(),
  };
}
