/**
 * Configuration management for the MCP server.
 *
 * Loads configuration from environment variables with sensible defaults.
 */

import { config } from 'dotenv';
import { z } from 'zod';

// Load .env file
config();

/**
 * Configuration schema with validation
 */
const ConfigSchema = z.object({
  // Server
  port: z.coerce.number().default(3001),
  host: z.string().default('localhost'),
  logLevel: z.enum(['debug', 'info', 'warn', 'error']).default('info'),

  // Search
  searchProvider: z.enum(['duckduckgo', 'serper']).default('duckduckgo'),
  serperApiKey: z.string().optional(),
  maxSearchResults: z.coerce.number().default(5),
  searchTimeoutMs: z.coerce.number().default(10000),

  // Fetch
  maxPageSize: z.coerce.number().default(50000),
  fetchTimeoutMs: z.coerce.number().default(15000),
  userAgent: z.string().default('ResearchCopilot/1.0'),

  // Database
  dbPath: z.string().default('./data/notes.db'),

  // Rate limiting (requests per minute)
  rateLimitSearch: z.coerce.number().default(10),
  rateLimitFetch: z.coerce.number().default(30),
  rateLimitNotes: z.coerce.number().default(50),
});

type Config = z.infer<typeof ConfigSchema>;

/**
 * Load and validate configuration from environment variables
 */
function loadConfig(): Config {
  const rawConfig = {
    port: process.env['PORT'],
    host: process.env['HOST'],
    logLevel: process.env['LOG_LEVEL'],
    searchProvider: process.env['SEARCH_PROVIDER'],
    serperApiKey: process.env['SERPER_API_KEY'],
    maxSearchResults: process.env['MAX_SEARCH_RESULTS'],
    searchTimeoutMs: process.env['SEARCH_TIMEOUT_MS'],
    maxPageSize: process.env['MAX_PAGE_SIZE'],
    fetchTimeoutMs: process.env['FETCH_TIMEOUT_MS'],
    userAgent: process.env['USER_AGENT'],
    dbPath: process.env['DB_PATH'],
    rateLimitSearch: process.env['RATE_LIMIT_SEARCH'],
    rateLimitFetch: process.env['RATE_LIMIT_FETCH'],
    rateLimitNotes: process.env['RATE_LIMIT_NOTES'],
  };

  const result = ConfigSchema.safeParse(rawConfig);

  if (!result.success) {
    console.error('Configuration validation failed:');
    console.error(result.error.format());
    process.exit(1);
  }

  // Validate serper API key if using serper provider
  if (result.data.searchProvider === 'serper' && !result.data.serperApiKey) {
    console.error('SERPER_API_KEY is required when using serper provider');
    process.exit(1);
  }

  return result.data;
}

export const config_values = loadConfig();
export type { Config };
