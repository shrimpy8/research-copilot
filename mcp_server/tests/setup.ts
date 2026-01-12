/**
 * Test setup file.
 *
 * Configures the test environment before running tests.
 */

import { afterAll, afterEach, beforeAll } from 'vitest';
import Database from 'better-sqlite3';
import { mkdirSync, existsSync, rmSync } from 'fs';

// Use in-memory database for tests
const TEST_DB_PATH = ':memory:';

// Store the test database instance
let testDb: Database.Database | null = null;

/**
 * Initialize test database
 */
export function getTestDatabase(): Database.Database {
  if (!testDb) {
    testDb = new Database(TEST_DB_PATH);
    testDb.pragma('journal_mode = WAL');

    // Create schema
    testDb.exec(`
      CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT NOT NULL,
        source_urls TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    `);

    testDb.exec(`
      CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
        title,
        content,
        tags,
        content='notes',
        content_rowid='rowid'
      )
    `);

    // Create triggers
    testDb.exec(`
      CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
        INSERT INTO notes_fts(rowid, title, content, tags)
        VALUES (new.rowid, new.title, new.content, new.tags);
      END
    `);

    testDb.exec(`
      CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
        INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
        VALUES('delete', old.rowid, old.title, old.content, old.tags);
      END
    `);

    testDb.exec(`
      CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
        INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
        VALUES('delete', old.rowid, old.title, old.content, old.tags);
        INSERT INTO notes_fts(rowid, title, content, tags)
        VALUES (new.rowid, new.title, new.content, new.tags);
      END
    `);
  }
  return testDb;
}

/**
 * Clear test data between tests
 */
export function clearTestData(): void {
  if (testDb) {
    testDb.exec('DELETE FROM notes');
  }
}

/**
 * Close test database
 */
export function closeTestDatabase(): void {
  if (testDb) {
    testDb.close();
    testDb = null;
  }
}

// Set up environment variables for testing
process.env['PORT'] = '3099';
process.env['HOST'] = 'localhost';
process.env['LOG_LEVEL'] = 'error';
process.env['DB_PATH'] = TEST_DB_PATH;
process.env['RATE_LIMIT_SEARCH'] = '100';
process.env['RATE_LIMIT_FETCH'] = '100';
process.env['RATE_LIMIT_NOTES'] = '100';

// Clean up after all tests
afterAll(() => {
  closeTestDatabase();
});
