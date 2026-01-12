/**
 * Get note tool implementation.
 *
 * Retrieves a single research note by ID.
 */

import { getNoteById, type Note } from '../services/index.js';
import { ErrorCodes, NoteError, ValidationError } from '../errors/index.js';

/**
 * Get note input parameters
 */
export interface GetNoteInput {
  id: string;
}

/**
 * Get note response
 */
export interface GetNoteResponse {
  note: Note;
}

/**
 * UUID v4 validation pattern
 */
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Get a research note by ID
 */
export function getNote(input: GetNoteInput): GetNoteResponse {
  // Validate input
  if (!input.id || typeof input.id !== 'string') {
    throw new ValidationError('Note ID is required and must be a string');
  }

  const noteId = input.id.trim();

  if (noteId.length === 0) {
    throw new ValidationError('Note ID cannot be empty');
  }

  // Validate UUID format
  if (!UUID_PATTERN.test(noteId)) {
    throw new NoteError(
      ErrorCodes.NOTE_NOT_FOUND,
      `Invalid note ID format: ${noteId}`,
      { noteId }
    );
  }

  // Fetch the note
  const note = getNoteById(noteId);

  return { note };
}
