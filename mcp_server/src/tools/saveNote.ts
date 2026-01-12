/**
 * Save note tool implementation.
 *
 * Saves research findings with title, content, tags, and source URLs.
 */

import { createNote, type Note } from '../services/index.js';
import { ErrorCodes, NoteError, ValidationError } from '../errors/index.js';

/**
 * Save note input parameters
 */
export interface SaveNoteInput {
  title: string;
  content: string;
  tags?: string[];
  source_urls?: string[];
}

/**
 * Save note response
 */
export interface SaveNoteResponse {
  note: Note;
  message: string;
}

/**
 * Validate URL format
 */
function isValidUrl(urlString: string): boolean {
  try {
    const url = new URL(urlString);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Save a research note
 */
export function saveNote(input: SaveNoteInput): SaveNoteResponse {
  // Validate input
  if (!input.title || typeof input.title !== 'string') {
    throw new NoteError(
      ErrorCodes.NOTE_TITLE_REQUIRED,
      'Note title is required and must be a string'
    );
  }

  if (!input.content || typeof input.content !== 'string') {
    throw new NoteError(
      ErrorCodes.NOTE_CONTENT_REQUIRED,
      'Note content is required and must be a string'
    );
  }

  // Validate tags
  const tags: string[] = [];
  if (input.tags) {
    if (!Array.isArray(input.tags)) {
      throw new ValidationError('Tags must be an array of strings');
    }
    for (const tag of input.tags) {
      if (typeof tag !== 'string') {
        throw new ValidationError('Each tag must be a string');
      }
      const cleanTag = tag.trim().toLowerCase();
      if (cleanTag.length > 0 && !tags.includes(cleanTag)) {
        tags.push(cleanTag);
      }
    }
  }

  // Validate source URLs
  const sourceUrls: string[] = [];
  if (input.source_urls) {
    if (!Array.isArray(input.source_urls)) {
      throw new ValidationError('Source URLs must be an array of strings');
    }
    for (const url of input.source_urls) {
      if (typeof url !== 'string') {
        throw new ValidationError('Each source URL must be a string');
      }
      if (url.trim().length > 0) {
        if (!isValidUrl(url)) {
          throw new ValidationError(`Invalid URL format: ${url}`);
        }
        if (!sourceUrls.includes(url)) {
          sourceUrls.push(url);
        }
      }
    }
  }

  // Create the note
  const note = createNote({
    title: input.title,
    content: input.content,
    tags,
    source_urls: sourceUrls,
  });

  return {
    note,
    message: `Note "${note.title}" saved successfully`,
  };
}
