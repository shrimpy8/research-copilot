/**
 * MCP Server entry point.
 *
 * Implements JSON-RPC 2.0 over HTTP for the Model Context Protocol.
 * Handles tool calls for web search, page fetching, and notes management.
 */

import express, { Request, Response, NextFunction } from 'express';
import { config_values } from './config/index.js';
import { initDatabase, closeDatabase } from './db/index.js';
import { MCPServerError, ErrorCodes } from './errors/index.js';
import { checkRateLimit, getRateLimitInfo } from './middleware/index.js';
import { webSearch, fetchPage, saveNote, listNotes, getNote } from './tools/index.js';

/**
 * JSON-RPC 2.0 request structure
 */
interface JsonRpcRequest {
  jsonrpc: '2.0';
  method: string;
  params?: Record<string, unknown>;
  id: string | number | null;
}

/**
 * JSON-RPC 2.0 response structure
 */
interface JsonRpcResponse {
  jsonrpc: '2.0';
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
  id: string | number | null;
}

/**
 * JSON-RPC 2.0 error codes
 */
const JSON_RPC_ERRORS = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
  SERVER_ERROR: -32000, // Custom server errors (-32000 to -32099)
  RATE_LIMITED: -32001,
};

/**
 * Create a JSON-RPC error response
 */
function createErrorResponse(
  id: string | number | null,
  code: number,
  message: string,
  data?: unknown
): JsonRpcResponse {
  return {
    jsonrpc: '2.0',
    error: { code, message, data },
    id,
  };
}

/**
 * Create a JSON-RPC success response
 */
function createSuccessResponse(id: string | number | null, result: unknown): JsonRpcResponse {
  return {
    jsonrpc: '2.0',
    result,
    id,
  };
}

/**
 * Handle tool calls
 */
async function handleToolCall(
  toolName: string,
  params: Record<string, unknown>
): Promise<unknown> {
  // Check rate limit
  checkRateLimit(toolName);

  switch (toolName) {
    case 'web_search':
      return await webSearch(
        params['query'] as string,
        params['limit'] as number | undefined,
        params['provider'] as 'duckduckgo' | 'serper' | undefined
      );

    case 'fetch_page':
      return await fetchPage(
        params['url'] as string,
        params['max_chars'] as number | undefined,
        params['extract_mode'] as 'text' | 'markdown' | undefined
      );

    case 'save_note':
      return saveNote({
        title: params['title'] as string,
        content: params['content'] as string,
        tags: params['tags'] as string[] | undefined,
        source_urls: params['source_urls'] as string[] | undefined,
      });

    case 'list_notes':
      return listNotes({
        query: params['query'] as string | undefined,
        tags: params['tags'] as string[] | undefined,
        limit: params['limit'] as number | undefined,
        offset: params['offset'] as number | undefined,
      });

    case 'get_note':
      return getNote({
        id: params['id'] as string,
      });

    default:
      throw new MCPServerError(
        ErrorCodes.INVALID_REQUEST,
        `Unknown tool: ${toolName}`
      );
  }
}

/**
 * Handle JSON-RPC request
 */
async function handleJsonRpcRequest(request: JsonRpcRequest): Promise<JsonRpcResponse> {
  const { jsonrpc, method, params, id } = request;

  // Validate JSON-RPC version
  if (jsonrpc !== '2.0') {
    return createErrorResponse(id, JSON_RPC_ERRORS.INVALID_REQUEST, 'Invalid JSON-RPC version');
  }

  // Validate method
  if (!method || typeof method !== 'string') {
    return createErrorResponse(id, JSON_RPC_ERRORS.INVALID_REQUEST, 'Method is required');
  }

  try {
    // Handle different methods
    switch (method) {
      case 'tools/call': {
        const toolName = params?.['name'] as string;
        const toolParams = (params?.['arguments'] as Record<string, unknown>) || {};

        if (!toolName) {
          return createErrorResponse(
            id,
            JSON_RPC_ERRORS.INVALID_PARAMS,
            'Tool name is required in params.name'
          );
        }

        const result = await handleToolCall(toolName, toolParams);
        return createSuccessResponse(id, result);
      }

      case 'tools/list': {
        // Return list of available tools with their schemas
        const tools = [
          {
            name: 'web_search',
            description: 'Search the web using DuckDuckGo or Serper',
            inputSchema: {
              type: 'object',
              properties: {
                query: { type: 'string', description: 'Search query' },
                limit: { type: 'number', description: 'Max results (1-5)', default: 3 },
                provider: {
                  type: 'string',
                  enum: ['duckduckgo', 'serper'],
                  description: 'Search provider',
                },
              },
              required: ['query'],
            },
          },
          {
            name: 'fetch_page',
            description: 'Fetch and extract content from a web page',
            inputSchema: {
              type: 'object',
              properties: {
                url: { type: 'string', description: 'URL to fetch' },
                max_chars: {
                  type: 'number',
                  description: 'Max content length',
                  default: 8000,
                },
                extract_mode: {
                  type: 'string',
                  enum: ['text', 'markdown'],
                  description: 'Output format',
                  default: 'text',
                },
              },
              required: ['url'],
            },
          },
          {
            name: 'save_note',
            description: 'Save a research note',
            inputSchema: {
              type: 'object',
              properties: {
                title: { type: 'string', description: 'Note title' },
                content: { type: 'string', description: 'Note content' },
                tags: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'Tags for categorization',
                },
                source_urls: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'Source URLs',
                },
              },
              required: ['title', 'content'],
            },
          },
          {
            name: 'list_notes',
            description: 'List research notes with optional search and filtering',
            inputSchema: {
              type: 'object',
              properties: {
                query: { type: 'string', description: 'Full-text search query' },
                tags: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'Filter by tags',
                },
                limit: { type: 'number', description: 'Max results', default: 20 },
                offset: { type: 'number', description: 'Pagination offset', default: 0 },
              },
            },
          },
          {
            name: 'get_note',
            description: 'Get a single note by ID',
            inputSchema: {
              type: 'object',
              properties: {
                id: { type: 'string', description: 'Note ID (UUID)' },
              },
              required: ['id'],
            },
          },
        ];

        return createSuccessResponse(id, { tools });
      }

      case 'server/info': {
        return createSuccessResponse(id, {
          name: 'research-copilot-mcp',
          version: '1.0.0',
          protocolVersion: '2024-11-05',
        });
      }

      case 'health': {
        return createSuccessResponse(id, {
          status: 'ok',
          timestamp: new Date().toISOString(),
        });
      }

      default:
        return createErrorResponse(
          id,
          JSON_RPC_ERRORS.METHOD_NOT_FOUND,
          `Unknown method: ${method}`
        );
    }
  } catch (error) {
    // Handle known errors
    if (error instanceof MCPServerError) {
      // Check for rate limit error
      if (error.code === ErrorCodes.SEARCH_RATE_LIMITED) {
        return createErrorResponse(id, JSON_RPC_ERRORS.RATE_LIMITED, error.message, {
          code: error.code,
          details: error.details,
        });
      }

      return createErrorResponse(id, JSON_RPC_ERRORS.SERVER_ERROR, error.message, {
        code: error.code,
        details: error.details,
      });
    }

    // Handle unexpected errors
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('Unexpected error:', error);

    return createErrorResponse(id, JSON_RPC_ERRORS.INTERNAL_ERROR, message);
  }
}

/**
 * Create and configure Express app
 */
export function createApp(): express.Application {
  const app = express();

  // Parse JSON bodies with error handling
  app.use(express.json({ limit: '1mb' }));

  // Handle JSON parsing errors
  app.use((err: Error & { status?: number; type?: string }, req: Request, res: Response, next: NextFunction) => {
    if (err.type === 'entity.parse.failed') {
      res.json(createErrorResponse(null, JSON_RPC_ERRORS.PARSE_ERROR, 'Invalid JSON'));
      return;
    }
    next(err);
  });

  // Health check endpoint
  app.get('/health', (_req: Request, res: Response) => {
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      search_provider: config_values.searchProvider,
    });
  });

  // MCP endpoint
  app.post('/mcp', async (req: Request, res: Response) => {
    try {
      const request = req.body as JsonRpcRequest;

      // Validate request is JSON-RPC
      if (!request || typeof request !== 'object') {
        res.json(
          createErrorResponse(null, JSON_RPC_ERRORS.PARSE_ERROR, 'Invalid JSON')
        );
        return;
      }

      const response = await handleJsonRpcRequest(request);

      // Add rate limit headers if applicable
      if (request.params?.['name']) {
        const toolName = request.params['name'] as string;
        const rateLimitInfo = getRateLimitInfo(toolName);
        res.setHeader('X-RateLimit-Limit', rateLimitInfo.limit);
        res.setHeader('X-RateLimit-Remaining', rateLimitInfo.remaining);
        res.setHeader('X-RateLimit-Reset', Math.ceil(rateLimitInfo.resetMs / 1000));
      }

      res.json(response);
    } catch (error) {
      console.error('Request handling error:', error);
      res.json(
        createErrorResponse(
          null,
          JSON_RPC_ERRORS.INTERNAL_ERROR,
          'Internal server error'
        )
      );
    }
  });

  // 404 handler
  app.use((_req: Request, res: Response) => {
    res.status(404).json({
      error: 'Not found',
      message: 'Use POST /mcp for MCP requests or GET /health for health checks',
    });
  });

  // Error handler
  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    console.error('Unhandled error:', err);
    res.status(500).json({
      error: 'Internal server error',
      message: err.message,
    });
  });

  return app;
}

/**
 * Start the server
 */
export function startServer(): void {
  // Initialize database
  initDatabase();

  const app = createApp();
  const port = config_values.port;
  const host = config_values.host;

  const server = app.listen(port, host, () => {
    console.log(`MCP Server running at http://${host}:${port}`);
    console.log(`Health check: http://${host}:${port}/health`);
    console.log(`MCP endpoint: http://${host}:${port}/mcp`);
    console.log(`Search provider: ${config_values.searchProvider}`);
  });

  // Graceful shutdown
  const shutdown = () => {
    console.log('\nShutting down...');
    server.close(() => {
      closeDatabase();
      console.log('Server closed');
      process.exit(0);
    });
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

// Run if executed directly
const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  startServer();
}
