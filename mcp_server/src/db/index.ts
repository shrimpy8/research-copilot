/**
 * Database module exports.
 */

export {
  initDatabase,
  getDatabase,
  closeDatabase,
  query,
  queryOne,
  execute,
  transaction,
} from './client.js';

export {
  SCHEMA_STATEMENTS,
  CREATE_NOTES_TABLE,
  CREATE_FTS_TABLE,
} from './schema.js';
