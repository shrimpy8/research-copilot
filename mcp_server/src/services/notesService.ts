/**
 * Notes service for CRUD operations on research notes.
 *
 * Handles validation, database operations, and error handling
 * for the notes storage system.
 */

import { randomUUID } from 'crypto';
import { query, queryOne, execute, transaction } from '../db/index.js';
import { ErrorCodes, NoteError } from '../errors/index.js';

/**
 * Note data structure
 */
export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  source_urls: string[];
  created_at: string;
  updated_at: string;
}

/**
 * Note list item structure (lightweight)
 */
export interface NoteListItem {
  id: string;
  title: string;
  tags: string[];
  created_at: string;
  snippet: string;
}

/**
 * Database row structure (JSON strings for arrays)
 */
interface NoteRow {
  id: string;
  title: string;
  content: string;
  tags: string;
  source_urls: string;
  created_at: string;
  updated_at: string;
}

/**
 * Input for creating a new note
 */
export interface CreateNoteInput {
  title: string;
  content: string;
  tags?: string[];
  source_urls?: string[];
}

/**
 * Input for listing notes
 */
export interface ListNotesInput {
  query?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

/**
 * Validation constants
 */
const MAX_TITLE_LENGTH = 200;
const MAX_TAGS = 10;
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;
const DEFAULT_SNIPPET_LENGTH = 100;

/**
 * Convert a database row to a Note object
 */
function rowToNote(row: NoteRow): Note {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    tags: JSON.parse(row.tags) as string[],
    source_urls: JSON.parse(row.source_urls) as string[],
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

/**
 * Convert a database row to a list item
 */
function rowToListItem(row: NoteRow): NoteListItem {
  const content = row.content.replace(/\s+/g, ' ').trim();
  const snippet = content.length > DEFAULT_SNIPPET_LENGTH
    ? `${content.slice(0, DEFAULT_SNIPPET_LENGTH)}...`
    : content;

  return {
    id: row.id,
    title: row.title,
    tags: JSON.parse(row.tags) as string[],
    created_at: row.created_at,
    snippet,
  };
}

/**
 * Validate note input
 */
function validateNoteInput(input: CreateNoteInput): void {
  if (!input.title || input.title.trim().length === 0) {
    throw new NoteError(
      ErrorCodes.NOTE_TITLE_REQUIRED,
      'Note title is required'
    );
  }

  if (input.title.length > MAX_TITLE_LENGTH) {
    throw new NoteError(
      ErrorCodes.NOTE_TITLE_TOO_LONG,
      `Note title must be ${MAX_TITLE_LENGTH} characters or less`,
      { maxLength: MAX_TITLE_LENGTH, actualLength: input.title.length }
    );
  }

  if (!input.content || input.content.trim().length === 0) {
    throw new NoteError(
      ErrorCodes.NOTE_CONTENT_REQUIRED,
      'Note content is required'
    );
  }

  if (input.tags && input.tags.length > MAX_TAGS) {
    throw new NoteError(
      ErrorCodes.NOTE_TOO_MANY_TAGS,
      `Maximum ${MAX_TAGS} tags allowed`,
      { maxTags: MAX_TAGS, actualTags: input.tags.length }
    );
  }
}

/**
 * Create a new note
 */
export function createNote(input: CreateNoteInput): Note {
  validateNoteInput(input);

  const id = randomUUID();
  const now = new Date().toISOString();
  const tags = input.tags || [];
  const sourceUrls = input.source_urls || [];

  const sql = `
    INSERT INTO notes (id, title, content, tags, source_urls, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `;

  execute(sql, [
    id,
    input.title.trim(),
    input.content.trim(),
    JSON.stringify(tags),
    JSON.stringify(sourceUrls),
    now,
    now,
  ]);

  return {
    id,
    title: input.title.trim(),
    content: input.content.trim(),
    tags,
    source_urls: sourceUrls,
    created_at: now,
    updated_at: now,
  };
}

/**
 * Get a note by ID
 */
export function getNoteById(id: string): Note {
  const sql = `
    SELECT id, title, content, tags, source_urls, created_at, updated_at
    FROM notes
    WHERE id = ?
  `;

  const row = queryOne<NoteRow>(sql, [id]);

  if (!row) {
    throw new NoteError(ErrorCodes.NOTE_NOT_FOUND, `Note not found: ${id}`, {
      noteId: id,
    });
  }

  return rowToNote(row);
}

/**
 * List notes with optional search and filtering
 */
export function listNotes(input: ListNotesInput = {}): { notes: NoteListItem[]; totalCount: number } {
  const limit = Math.min(input.limit || DEFAULT_LIMIT, MAX_LIMIT);
  const hasQuery = input.query && input.query.trim().length > 0;
  const hasTags = input.tags && input.tags.length > 0;
  const offset = Math.max(0, input.offset || 0);

  let sql: string;
  const params: unknown[] = [];
  let countSql: string;
  const countParams: unknown[] = [];

  if (hasQuery) {
    // Use FTS5 for full-text search
    sql = `
      SELECT n.id, n.title, n.content, n.tags, n.source_urls, n.created_at, n.updated_at
      FROM notes n
      JOIN notes_fts fts ON n.rowid = fts.rowid
      WHERE notes_fts MATCH ?
    `;
    countSql = `
      SELECT COUNT(*) as count
      FROM notes n
      JOIN notes_fts fts ON n.rowid = fts.rowid
      WHERE notes_fts MATCH ?
    `;
    // FTS5 query syntax: escape special characters and add prefix matching
    const ftsQuery = input.query!
      .trim()
      .split(/\s+/)
      .map((term) => `"${term}"*`)
      .join(' OR ');
    params.push(ftsQuery);
    countParams.push(ftsQuery);
  } else {
    sql = `
      SELECT id, title, content, tags, source_urls, created_at, updated_at
      FROM notes
      WHERE 1=1
    `;
    countSql = `
      SELECT COUNT(*) as count
      FROM notes
      WHERE 1=1
    `;
  }

  // Add tag filtering
  if (hasTags) {
    // Filter by tags using JSON array containment
    for (const tag of input.tags!) {
      sql += ` AND tags LIKE ?`;
      params.push(`%"${tag}"%`);
      countSql += ` AND tags LIKE ?`;
      countParams.push(`%"${tag}"%`);
    }
  }

  // Order by creation date (newest first) and limit
  sql += ` ORDER BY created_at DESC LIMIT ? OFFSET ?`;
  params.push(limit);
  params.push(offset);

  const rows = query<NoteRow>(sql, params);
  const countRow = queryOne<{ count: number }>(countSql, countParams);
  const totalCount = countRow?.count ?? 0;

  return {
    notes: rows.map(rowToListItem),
    totalCount,
  };
}

/**
 * Delete a note by ID
 */
export function deleteNote(id: string): void {
  const sql = `DELETE FROM notes WHERE id = ?`;
  const result = execute(sql, [id]);

  if (result.changes === 0) {
    throw new NoteError(ErrorCodes.NOTE_NOT_FOUND, `Note not found: ${id}`, {
      noteId: id,
    });
  }
}

/**
 * Get note count
 */
export function getNoteCount(): number {
  const sql = `SELECT COUNT(*) as count FROM notes`;
  const row = queryOne<{ count: number }>(sql);
  return row?.count || 0;
}

/**
 * Search notes by full-text query (returns just IDs for efficiency)
 */
export function searchNoteIds(searchQuery: string, limit: number = DEFAULT_LIMIT): string[] {
  const ftsQuery = searchQuery
    .trim()
    .split(/\s+/)
    .map((term) => `"${term}"*`)
    .join(' OR ');

  const sql = `
    SELECT n.id
    FROM notes n
    JOIN notes_fts fts ON n.rowid = fts.rowid
    WHERE notes_fts MATCH ?
    ORDER BY rank
    LIMIT ?
  `;

  const rows = query<{ id: string }>(sql, [ftsQuery, Math.min(limit, MAX_LIMIT)]);
  return rows.map((row) => row.id);
}
