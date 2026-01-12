/**
 * SQLite database client for notes storage.
 *
 * Provides connection management, schema initialization,
 * and query execution with proper error handling.
 */

import Database from 'better-sqlite3';
import { mkdirSync, existsSync } from 'fs';
import { dirname } from 'path';
import { config_values } from '../config/index.js';
import { ErrorCodes, NoteError } from '../errors/index.js';
import { SCHEMA_STATEMENTS } from './schema.js';

let db: Database.Database | null = null;

/**
 * Initialize the database connection and schema
 */
export function initDatabase(): Database.Database {
  if (db) {
    return db;
  }

  const dbPath = config_values.dbPath;

  // Ensure the directory exists
  const dbDir = dirname(dbPath);
  if (!existsSync(dbDir)) {
    mkdirSync(dbDir, { recursive: true });
  }

  try {
    // Create database connection
    db = new Database(dbPath);

    // Enable WAL mode for better concurrency
    db.pragma('journal_mode = WAL');

    // Initialize schema
    for (const statement of SCHEMA_STATEMENTS) {
      db.exec(statement);
    }

    console.log(`Database initialized at ${dbPath}`);
    return db;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    throw new NoteError(
      ErrorCodes.NOTES_DB_UNAVAILABLE,
      `Failed to initialize database: ${message}`,
      { dbPath }
    );
  }
}

/**
 * Get the database connection, initializing if necessary
 */
export function getDatabase(): Database.Database {
  if (!db) {
    return initDatabase();
  }
  return db;
}

/**
 * Close the database connection
 */
export function closeDatabase(): void {
  if (db) {
    db.close();
    db = null;
    console.log('Database connection closed');
  }
}

/**
 * Execute a query and return all results
 */
export function query<T>(sql: string, params: unknown[] = []): T[] {
  const database = getDatabase();
  try {
    const stmt = database.prepare(sql);
    return stmt.all(...params) as T[];
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    throw new NoteError(
      ErrorCodes.NOTES_QUERY_FAILED,
      `Query failed: ${message}`,
      { sql: sql.substring(0, 100) }
    );
  }
}

/**
 * Execute a query and return the first result
 */
export function queryOne<T>(sql: string, params: unknown[] = []): T | undefined {
  const database = getDatabase();
  try {
    const stmt = database.prepare(sql);
    return stmt.get(...params) as T | undefined;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    throw new NoteError(
      ErrorCodes.NOTES_QUERY_FAILED,
      `Query failed: ${message}`,
      { sql: sql.substring(0, 100) }
    );
  }
}

/**
 * Execute an INSERT/UPDATE/DELETE and return changes info
 */
export function execute(
  sql: string,
  params: unknown[] = []
): Database.RunResult {
  const database = getDatabase();
  try {
    const stmt = database.prepare(sql);
    return stmt.run(...params);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    throw new NoteError(
      ErrorCodes.NOTE_SAVE_FAILED,
      `Database operation failed: ${message}`,
      { sql: sql.substring(0, 100) }
    );
  }
}

/**
 * Run a function within a transaction
 */
export function transaction<T>(fn: () => T): T {
  const database = getDatabase();
  return database.transaction(fn)();
}
