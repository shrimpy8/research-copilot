/**
 * Fetch page tool implementation.
 *
 * Fetches web pages and extracts readable text content.
 * Includes security protections against SSRF attacks.
 */

import * as cheerio from 'cheerio';
import { lookup } from 'dns/promises';
import { Agent } from 'undici';
import { config_values } from '../config/index.js';
import { ErrorCodes, FetchError, ValidationError } from '../errors/index.js';

/**
 * Fetch page response
 */
export interface FetchPageResponse {
  url: string;
  title: string;
  content: string;
  content_length: number;
  truncated: boolean;
}

/**
 * Blocked IP ranges for SSRF protection
 */
const BLOCKED_IP_PATTERNS = [
  /^127\./,                          // Loopback
  /^10\./,                           // Private Class A
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,  // Private Class B
  /^192\.168\./,                     // Private Class C
  /^169\.254\./,                     // Link-local
  /^0\./,                            // Current network
  /^224\./,                          // Multicast
  /^255\./,                          // Broadcast
  /^::1$/,                           // IPv6 loopback
  /^fc00:/i,                         // IPv6 private
  /^fe80:/i,                         // IPv6 link-local
];

/**
 * Blocked hostnames
 */
const BLOCKED_HOSTNAMES = [
  'localhost',
  'localhost.localdomain',
  '0.0.0.0',
  '[::]',
  '[::1]',
];

/**
 * Allowed protocols
 */
const ALLOWED_PROTOCOLS = ['http:', 'https:'];

/**
 * Maximum redirects to follow
 */
const MAX_REDIRECTS = 5;

/**
 * Check if an IP address is in a private or local range
 */
function isPrivateIp(ip: string): boolean {
  // IPv4 private ranges
  if (BLOCKED_IP_PATTERNS.some((pattern) => pattern.test(ip))) {
    return true;
  }

  // IPv6 local ranges
  const lower = ip.toLowerCase();
  return lower.startsWith('fc00:') || lower.startsWith('fe80:') || lower === '::1';
}

/**
 * Resolve hostname and return a public IP for pinning
 */
async function resolvePublicIp(hostname: string): Promise<{ address: string; family: number }> {
  const records = await lookup(hostname, { all: true, verbatim: true });

  const publicRecord = records.find((record) => !isPrivateIp(record.address));
  if (!publicRecord) {
    throw new FetchError(
      ErrorCodes.FETCH_BLOCKED,
      'Access to private/internal IP ranges is not allowed',
      { hostname }
    );
  }

  return publicRecord;
}

/**
 * Create an HTTP dispatcher that pins requests to a resolved IP
 */
function createPinnedDispatcher(record: { address: string; family: number }): Agent {
  return new Agent({
    connect: {
      lookup: (_hostname, _options, callback) => {
        callback(null, record.address, record.family);
      },
    },
  });
}

/**
 * Validate URL for security
 */
function validateUrl(urlString: string): URL {
  let url: URL;

  try {
    url = new URL(urlString);
  } catch {
    throw new FetchError(
      ErrorCodes.FETCH_INVALID_URL,
      `Invalid URL format: ${urlString}`
    );
  }

  // Check protocol
  if (!ALLOWED_PROTOCOLS.includes(url.protocol)) {
    throw new FetchError(
      ErrorCodes.FETCH_INVALID_URL,
      `Protocol not allowed: ${url.protocol}. Only HTTP(S) is supported.`
    );
  }

  // Check hostname
  const hostname = url.hostname.toLowerCase();

  if (BLOCKED_HOSTNAMES.includes(hostname)) {
    throw new FetchError(
      ErrorCodes.FETCH_BLOCKED,
      'Access to local/internal hosts is not allowed'
    );
  }

  // Check for IP addresses in blocked ranges
  for (const pattern of BLOCKED_IP_PATTERNS) {
    if (pattern.test(hostname)) {
      throw new FetchError(
        ErrorCodes.FETCH_BLOCKED,
        'Access to private/internal IP ranges is not allowed'
      );
    }
  }

  // Block numeric IPs that could be obfuscated
  // e.g., 2130706433 = 127.0.0.1 in decimal
  if (/^\d+$/.test(hostname)) {
    throw new FetchError(
      ErrorCodes.FETCH_BLOCKED,
      'Numeric IP addresses are not allowed'
    );
  }

  // Block IPv6 embedded in URLs
  if (hostname.startsWith('[') && hostname.endsWith(']')) {
    throw new FetchError(
      ErrorCodes.FETCH_BLOCKED,
      'Direct IPv6 addresses are not allowed'
    );
  }

  return url;
}

/**
 * Extract readable text content from HTML
 */
function extractContent(html: string, maxChars: number): { content: string; title: string; truncated: boolean } {
  const $ = cheerio.load(html);

  // Remove non-content elements
  $('script').remove();
  $('style').remove();
  $('nav').remove();
  $('header').remove();
  $('footer').remove();
  $('aside').remove();
  $('iframe').remove();
  $('noscript').remove();
  $('svg').remove();
  $('[role="navigation"]').remove();
  $('[role="banner"]').remove();
  $('[role="contentinfo"]').remove();
  $('[aria-hidden="true"]').remove();
  $('.nav, .navbar, .navigation').remove();
  $('.header, .site-header').remove();
  $('.footer, .site-footer').remove();
  $('.sidebar, .side-bar').remove();
  $('.ad, .ads, .advertisement').remove();
  $('.cookie-banner, .cookie-notice').remove();
  $('.popup, .modal').remove();
  $('.social-share, .share-buttons').remove();

  // Get title
  let title = $('title').text().trim();
  if (!title) {
    title = $('h1').first().text().trim();
  }
  if (!title) {
    title = $('meta[property="og:title"]').attr('content') || '';
  }
  title = title.substring(0, 200);

  // Try to find main content area
  let content = '';
  const mainSelectors = [
    'main',
    'article',
    '[role="main"]',
    '.content',
    '.post-content',
    '.article-content',
    '.entry-content',
    '#content',
    '#main',
    '.main-content',
  ];

  for (const selector of mainSelectors) {
    const element = $(selector).first();
    if (element.length > 0) {
      content = element.text();
      if (content.trim().length > 100) {
        break;
      }
    }
  }

  // Fallback to body
  if (content.trim().length < 100) {
    content = $('body').text();
  }

  // Clean up whitespace
  content = content
    .replace(/\s+/g, ' ')
    .replace(/\n\s*\n/g, '\n\n')
    .trim();

  // Truncate if needed
  let truncated = false;
  if (content.length > maxChars) {
    // Try to truncate at a sentence boundary
    const truncateAt = content.lastIndexOf('.', maxChars);
    if (truncateAt > maxChars * 0.8) {
      content = content.substring(0, truncateAt + 1);
    } else {
      // Truncate at word boundary
      const wordBoundary = content.lastIndexOf(' ', maxChars);
      content = content.substring(0, wordBoundary > 0 ? wordBoundary : maxChars);
      content += '...';
    }
    truncated = true;
  }

  return { content, title, truncated };
}

function formatMarkdown(title: string, content: string): string {
  const sentences = content.split(/(?<=[.!?])\s+/);
  const paragraphs: string[] = [];
  const chunkSize = 3;

  for (let i = 0; i < sentences.length; i += chunkSize) {
    const chunk = sentences.slice(i, i + chunkSize).join(' ').trim();
    if (chunk) {
      paragraphs.push(chunk);
    }
  }

  const heading = title || 'Untitled';
  return `# ${heading}\n\n${paragraphs.join('\n\n')}`;
}

/**
 * Fetch a web page and extract its content
 */
export async function fetchPage(
  urlString: string,
  maxChars: number = 8000,
  extractMode: 'text' | 'markdown' = 'text'
): Promise<FetchPageResponse> {
  // Validate URL
  const url = validateUrl(urlString);

  const cappedMaxChars = Math.min(maxChars, config_values.maxPageSize);

  if (extractMode !== 'text' && extractMode !== 'markdown') {
    throw new ValidationError(`Invalid extract_mode: ${extractMode}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    config_values.fetchTimeoutMs
  );

  try {
    let currentUrl = url;
    let response: Response | null = null;

    for (let redirects = 0; redirects <= MAX_REDIRECTS; redirects += 1) {
      const resolved = await resolvePublicIp(currentUrl.hostname);
      const dispatcher = createPinnedDispatcher(resolved);

      response = await fetch(currentUrl.toString(), {
        signal: controller.signal,
        headers: {
          'User-Agent': config_values.userAgent,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
        },
        redirect: 'manual',
        dispatcher,
      });

      // Handle redirects manually so we can validate each hop
      if (response.status >= 300 && response.status < 400) {
        const location = response.headers.get('location');
        if (!location) {
          throw new FetchError(
            ErrorCodes.FETCH_FAILED,
            'Redirect response missing Location header'
          );
        }

        const nextUrl = new URL(location, currentUrl.toString());
        currentUrl = validateUrl(nextUrl.toString());
        continue;
      }

      break;
    }

    clearTimeout(timeoutId);

    if (!response) {
      throw new FetchError(
        ErrorCodes.FETCH_FAILED,
        'No response received from fetch'
      );
    }

    if (response.status >= 300 && response.status < 400) {
      throw new FetchError(
        ErrorCodes.FETCH_FAILED,
        `Too many redirects (max ${MAX_REDIRECTS})`
      );
    }

    if (!response.ok) {
      if (response.status === 403 || response.status === 401) {
        throw new FetchError(
          ErrorCodes.FETCH_BLOCKED,
          `Access denied to ${url.hostname}`,
          { status: response.status }
        );
      }
      throw new FetchError(
        ErrorCodes.FETCH_FAILED,
        `HTTP ${response.status} for ${url.hostname}`,
        { status: response.status }
      );
    }

    // Check content type
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('text/html') && !contentType.includes('application/xhtml')) {
      throw new FetchError(
        ErrorCodes.FETCH_CONTENT_TYPE,
        `Unsupported content type: ${contentType}. Only HTML is supported.`,
        { contentType }
      );
    }

    const html = await response.text();
    let { content, title, truncated } = extractContent(html, cappedMaxChars);

    if (extractMode === 'markdown') {
      content = formatMarkdown(title || url.hostname, content);
    }

    if (!content || content.trim().length === 0) {
      throw new FetchError(
        ErrorCodes.FETCH_FAILED,
        'No readable content found on page'
      );
    }

    return {
      url: response.url,
      title: title || url.hostname,
      content,
      content_length: content.length,
      truncated,
    };
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof FetchError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new FetchError(
          ErrorCodes.FETCH_TIMEOUT,
          `Request to ${url.hostname} timed out`,
          { timeoutMs: config_values.fetchTimeoutMs }
        );
      }

      // Handle network errors
      if (error.message.includes('ENOTFOUND') || error.message.includes('getaddrinfo')) {
        throw new FetchError(
          ErrorCodes.FETCH_FAILED,
          `Could not resolve hostname: ${url.hostname}`
        );
      }

      if (error.message.includes('ECONNREFUSED')) {
        throw new FetchError(
          ErrorCodes.FETCH_FAILED,
          `Connection refused by ${url.hostname}`
        );
      }

      throw new FetchError(
        ErrorCodes.FETCH_FAILED,
        `Failed to fetch page: ${error.message}`
      );
    }

    throw new FetchError(
      ErrorCodes.FETCH_FAILED,
      'Failed to fetch page with unknown error'
    );
  }
}
