/**
 * Error classes for the MCP server.
 *
 * All errors include a code for machine-readable identification
 * and a message for human-readable context.
 */

/**
 * Error codes matching the Python client error codes
 */
export const ErrorCodes = {
  // Search errors
  SEARCH_FAILED: 'search_failed',
  SEARCH_TIMEOUT: 'search_timeout',
  SEARCH_NO_RESULTS: 'search_no_results',
  SEARCH_RATE_LIMITED: 'search_rate_limited',

  // Fetch errors
  FETCH_FAILED: 'fetch_failed',
  FETCH_TIMEOUT: 'fetch_timeout',
  FETCH_BLOCKED: 'fetch_blocked',
  FETCH_INVALID_URL: 'fetch_invalid_url',
  FETCH_CONTENT_TYPE: 'fetch_content_type',

  // Note errors
  NOTE_NOT_FOUND: 'note_not_found',
  NOTE_SAVE_FAILED: 'note_save_failed',
  NOTE_TITLE_REQUIRED: 'note_title_required',
  NOTE_CONTENT_REQUIRED: 'note_content_required',
  NOTE_TITLE_TOO_LONG: 'note_title_too_long',
  NOTE_TOO_MANY_TAGS: 'note_too_many_tags',
  NOTES_DB_UNAVAILABLE: 'notes_db_unavailable',
  NOTES_QUERY_FAILED: 'notes_query_failed',

  // Validation errors
  INVALID_REQUEST: 'invalid_request',
  MISSING_PARAMETER: 'missing_parameter',
  INVALID_URL: 'invalid_url',

  // Internal errors
  INTERNAL_ERROR: 'internal_error',
} as const;

export type ErrorCode = (typeof ErrorCodes)[keyof typeof ErrorCodes];

/**
 * Base error class for MCP server errors
 */
export class MCPServerError extends Error {
  readonly code: ErrorCode;
  readonly details?: Record<string, unknown>;

  constructor(code: ErrorCode, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'MCPServerError';
    this.code = code;
    this.details = details;
  }

  toJSON() {
    return {
      code: this.code,
      message: this.message,
      details: this.details,
    };
  }
}

/**
 * Search-related errors
 */
export class SearchError extends MCPServerError {
  constructor(
    code: ErrorCode = ErrorCodes.SEARCH_FAILED,
    message: string,
    details?: Record<string, unknown>
  ) {
    super(code, message, details);
    this.name = 'SearchError';
  }
}

/**
 * Fetch-related errors
 */
export class FetchError extends MCPServerError {
  constructor(
    code: ErrorCode = ErrorCodes.FETCH_FAILED,
    message: string,
    details?: Record<string, unknown>
  ) {
    super(code, message, details);
    this.name = 'FetchError';
  }
}

/**
 * Note-related errors
 */
export class NoteError extends MCPServerError {
  constructor(
    code: ErrorCode = ErrorCodes.NOTE_SAVE_FAILED,
    message: string,
    details?: Record<string, unknown>
  ) {
    super(code, message, details);
    this.name = 'NoteError';
  }
}

/**
 * Validation errors
 */
export class ValidationError extends MCPServerError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(ErrorCodes.INVALID_REQUEST, message, details);
    this.name = 'ValidationError';
  }
}

/**
 * Rate limit errors
 */
export class RateLimitError extends MCPServerError {
  constructor(tool: string) {
    super(ErrorCodes.SEARCH_RATE_LIMITED, `Rate limit exceeded for ${tool}`, { tool });
    this.name = 'RateLimitError';
  }
}
