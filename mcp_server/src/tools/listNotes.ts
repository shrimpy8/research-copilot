/**
 * List notes tool implementation.
 *
 * Lists research notes with optional full-text search and tag filtering.
 */

import { listNotes as listNotesFromService, type NoteListItem } from '../services/index.js';
import { ValidationError } from '../errors/index.js';

/**
 * List notes input parameters
 */
export interface ListNotesInput {
  query?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

/**
 * List notes response
 */
export interface ListNotesResponse {
  notes: NoteListItem[];
  count: number;
  total_count: number;
  has_more: boolean;
  query?: string;
  tags?: string[];
  limit: number;
  offset: number;
}

/**
 * Default and maximum limits
 */
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;

/**
 * List research notes with optional filtering
 */
export function listNotes(input: ListNotesInput = {}): ListNotesResponse {
  // Validate and normalize input
  let limit = DEFAULT_LIMIT;
  if (input.limit !== undefined) {
    if (typeof input.limit !== 'number' || isNaN(input.limit)) {
      throw new ValidationError('Limit must be a number');
    }
    limit = Math.min(Math.max(1, Math.floor(input.limit)), MAX_LIMIT);
  }

  // Validate query
  let query: string | undefined;
  if (input.query !== undefined) {
    if (typeof input.query !== 'string') {
      throw new ValidationError('Query must be a string');
    }
    query = input.query.trim();
    if (query.length === 0) {
      query = undefined;
    }
  }

  // Validate and normalize tags
  let tags: string[] | undefined;
  if (input.tags !== undefined) {
    if (!Array.isArray(input.tags)) {
      throw new ValidationError('Tags must be an array of strings');
    }
    tags = [];
    for (const tag of input.tags) {
      if (typeof tag !== 'string') {
        throw new ValidationError('Each tag must be a string');
      }
      const cleanTag = tag.trim().toLowerCase();
      if (cleanTag.length > 0 && !tags.includes(cleanTag)) {
        tags.push(cleanTag);
      }
    }
    if (tags.length === 0) {
      tags = undefined;
    }
  }

  let offset = 0;
  if (input.offset !== undefined) {
    if (typeof input.offset !== 'number' || isNaN(input.offset)) {
      throw new ValidationError('Offset must be a number');
    }
    offset = Math.max(0, Math.floor(input.offset));
  }

  // Fetch notes
  const { notes, totalCount } = listNotesFromService({
    query,
    tags,
    limit,
    offset,
  });

  return {
    notes,
    count: notes.length,
    total_count: totalCount,
    has_more: offset + notes.length < totalCount,
    query,
    tags,
    limit,
    offset,
  };
}
