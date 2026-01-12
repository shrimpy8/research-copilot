/**
 * Database schema definitions for the notes database.
 *
 * Uses SQLite with FTS5 for full-text search capabilities.
 */

/**
 * SQL statements to create the notes table and FTS index
 */
export const CREATE_NOTES_TABLE = `
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL,           -- JSON array
    source_urls TEXT NOT NULL,    -- JSON array
    created_at TEXT NOT NULL,     -- ISO 8601
    updated_at TEXT NOT NULL      -- ISO 8601
)
`;

/**
 * SQL to create the FTS5 virtual table for full-text search
 */
export const CREATE_FTS_TABLE = `
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    content,
    tags,
    content='notes',
    content_rowid='rowid'
)
`;

/**
 * Trigger to keep FTS in sync after INSERT
 */
export const CREATE_INSERT_TRIGGER = `
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags);
END
`;

/**
 * Trigger to keep FTS in sync after DELETE
 */
export const CREATE_DELETE_TRIGGER = `
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
    VALUES('delete', old.rowid, old.title, old.content, old.tags);
END
`;

/**
 * Trigger to keep FTS in sync after UPDATE
 */
export const CREATE_UPDATE_TRIGGER = `
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
    VALUES('delete', old.rowid, old.title, old.content, old.tags);
    INSERT INTO notes_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags);
END
`;

/**
 * Index for efficient sorting by creation date
 */
export const CREATE_DATE_INDEX = `
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC)
`;

/**
 * All schema creation statements in order
 */
export const SCHEMA_STATEMENTS = [
  CREATE_NOTES_TABLE,
  CREATE_FTS_TABLE,
  CREATE_INSERT_TRIGGER,
  CREATE_DELETE_TRIGGER,
  CREATE_UPDATE_TRIGGER,
  CREATE_DATE_INDEX,
];
