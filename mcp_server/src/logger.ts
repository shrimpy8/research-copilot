/**
 * Structured logger for the MCP server.
 *
 * Uses pino for structured JSON logging in production and pretty output in development.
 */

import pino from 'pino';

const isDev = process.env['NODE_ENV'] !== 'production';

export const logger = pino({
  level: process.env['LOG_LEVEL'] ?? 'info',
  transport: isDev
    ? { target: 'pino/file', options: { destination: process.stderr.fd } }
    : undefined,
});
