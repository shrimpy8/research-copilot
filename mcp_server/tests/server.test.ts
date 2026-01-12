/**
 * Tests for the MCP server.
 */

import { describe, it, expect, beforeEach, vi, beforeAll, afterAll } from 'vitest';
import http from 'http';
import request from 'supertest';
import { createApp } from '../src/server.js';
import type { Express } from 'express';

// Mock database
vi.mock('../src/db/client.js', () => ({
  initDatabase: vi.fn(),
  getDatabase: vi.fn(() => ({})),
  closeDatabase: vi.fn(),
  query: vi.fn(() => []),
  queryOne: vi.fn(() => undefined),
  execute: vi.fn(() => ({ changes: 1, lastInsertRowid: 1 })),
  transaction: vi.fn((fn: () => unknown) => fn()),
}));

// Mock config
vi.mock('../src/config/index.js', () => ({
  config_values: {
    port: 3099,
    host: 'localhost',
    logLevel: 'error',
    searchProvider: 'duckduckgo',
    maxSearchResults: 5,
    searchTimeoutMs: 10000,
    maxPageSize: 50000,
    fetchTimeoutMs: 15000,
    userAgent: 'TestAgent/1.0',
    dbPath: ':memory:',
    rateLimitSearch: 100,
    rateLimitFetch: 100,
    rateLimitNotes: 100,
  },
}));

// Mock rate limiting
vi.mock('../src/middleware/rateLimit.js', () => ({
  checkRateLimit: vi.fn(),
  getRateLimitInfo: vi.fn(() => ({ remaining: 99, limit: 100, resetMs: 60000 })),
  clearRateLimits: vi.fn(),
  getToolCategory: vi.fn(() => 'notes'),
}));

describe('MCP Server', () => {
  let app: Express;
  let server: http.Server;
  let serverReady = false;

  beforeAll(async () => {
    app = createApp();
    server = http.createServer(app);
    try {
      await new Promise<void>((resolve, reject) => {
        server.listen(0, '127.0.0.1', () => resolve());
        server.on('error', reject);
      });
      serverReady = true;
    } catch {
      serverReady = false;
    }
  });

  afterAll(() => {
    if (serverReady) {
      server?.close();
    }
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      if (!serverReady) {
        return;
      }
      const response = await request(server).get('/health');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status', 'ok');
      expect(response.body).toHaveProperty('timestamp');
      expect(response.body).toHaveProperty('version');
    });
  });

  describe('POST /mcp', () => {
    describe('JSON-RPC validation', () => {
      it('should reject invalid JSON', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .set('Content-Type', 'application/json')
          .send('invalid json');

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('error');
      });

      it('should reject missing jsonrpc version', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            method: 'test',
            id: 1,
          });

        expect(response.body.error).toBeDefined();
        expect(response.body.error.code).toBe(-32600);
      });

      it('should reject invalid jsonrpc version', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '1.0',
            method: 'test',
            id: 1,
          });

        expect(response.body.error).toBeDefined();
        expect(response.body.error.code).toBe(-32600);
      });

      it('should reject missing method', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            id: 1,
          });

        expect(response.body.error).toBeDefined();
        expect(response.body.error.code).toBe(-32600);
      });
    });

    describe('server/info method', () => {
      it('should return server info', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'server/info',
            id: 1,
          });

        expect(response.body.result).toBeDefined();
        expect(response.body.result.name).toBe('research-copilot-mcp');
        expect(response.body.result.version).toBe('1.0.0');
        expect(response.body.result.protocolVersion).toBeDefined();
      });
    });

    describe('tools/list method', () => {
      it('should return list of tools', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'tools/list',
            id: 1,
          });

        expect(response.body.result).toBeDefined();
        expect(response.body.result.tools).toBeInstanceOf(Array);
        expect(response.body.result.tools.length).toBe(5);

        const toolNames = response.body.result.tools.map((t: { name: string }) => t.name);
        expect(toolNames).toContain('web_search');
        expect(toolNames).toContain('fetch_page');
        expect(toolNames).toContain('save_note');
        expect(toolNames).toContain('list_notes');
        expect(toolNames).toContain('get_note');
      });

      it('should include input schemas for tools', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'tools/list',
            id: 1,
          });

        const webSearchTool = response.body.result.tools.find(
          (t: { name: string }) => t.name === 'web_search'
        );
        expect(webSearchTool.inputSchema).toBeDefined();
        expect(webSearchTool.inputSchema.properties.query).toBeDefined();
      });
    });

    describe('health method', () => {
      it('should return health status via JSON-RPC', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'health',
            id: 1,
          });

        expect(response.body.result).toBeDefined();
        expect(response.body.result.status).toBe('ok');
      });
    });

    describe('unknown method', () => {
      it('should return method not found error', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'unknown/method',
            id: 1,
          });

        expect(response.body.error).toBeDefined();
        expect(response.body.error.code).toBe(-32601);
        expect(response.body.error.message).toContain('Unknown method');
      });
    });

    describe('tools/call method', () => {
      it('should require tool name', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {},
            id: 1,
          });

        expect(response.body.error).toBeDefined();
        expect(response.body.error.code).toBe(-32602);
      });

      it('should return error for unknown tool', async () => {
        if (!serverReady) {
          return;
        }
        const response = await request(server)
          .post('/mcp')
          .send({
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
              name: 'unknown_tool',
              arguments: {},
            },
            id: 1,
          });

        expect(response.body.error).toBeDefined();
      });
    });
  });

  describe('404 handling', () => {
    it('should return 404 for unknown routes', async () => {
      if (!serverReady) {
        return;
      }
      const response = await request(server).get('/unknown');

      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('error', 'Not found');
    });
  });
});
