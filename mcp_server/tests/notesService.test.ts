/**
 * Tests for the notes service.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { randomUUID } from 'crypto';

// Mock the database client
vi.mock('../src/db/client.js', () => {
  const notes = new Map<string, {
    id: string;
    title: string;
    content: string;
    tags: string;
    source_urls: string;
    created_at: string;
    updated_at: string;
    rowid?: number;
  }>();
  let rowIdCounter = 0;

  return {
    initDatabase: vi.fn(),
    getDatabase: vi.fn(),
    closeDatabase: vi.fn(),
    query: vi.fn((sql: string, params: unknown[]) => {
      // Simple query implementation for testing
      if (sql.includes('SELECT') && sql.includes('FROM notes')) {
        const allNotes = Array.from(notes.values());
        // Extract LIMIT from SQL if present
        const limitMatch = sql.match(/LIMIT\s+\?/);
        if (limitMatch && params.length > 1) {
          const limit = params[params.length - 2] as number;
          const offset = params[params.length - 1] as number;
          return allNotes.slice(offset, offset + limit);
        }
        return allNotes;
      }
      return [];
    }),
    queryOne: vi.fn((sql: string, params: unknown[]) => {
      if (sql.includes('WHERE id = ?') && params[0]) {
        return notes.get(params[0] as string) || undefined;
      }
      if (sql.includes('COUNT(*)')) {
        return { count: notes.size };
      }
      return undefined;
    }),
    execute: vi.fn((sql: string, params: unknown[]) => {
      if (sql.includes('INSERT INTO notes')) {
        const [id, title, content, tags, source_urls, created_at, updated_at] = params as string[];
        rowIdCounter++;
        notes.set(id, { id, title, content, tags, source_urls, created_at, updated_at, rowid: rowIdCounter });
        return { changes: 1, lastInsertRowid: rowIdCounter };
      }
      if (sql.includes('DELETE FROM notes WHERE id = ?')) {
        const id = params[0] as string;
        if (notes.has(id)) {
          notes.delete(id);
          return { changes: 1 };
        }
        return { changes: 0 };
      }
      return { changes: 0 };
    }),
    transaction: vi.fn((fn: () => unknown) => fn()),
    // Helper to clear notes for testing
    _clearNotes: () => notes.clear(),
    _getNotes: () => notes,
  };
});

import {
  createNote,
  getNoteById,
  listNotes,
  deleteNote,
  getNoteCount,
} from '../src/services/notesService.js';
import { NoteError } from '../src/errors/index.js';
import * as dbClient from '../src/db/client.js';

describe('NotesService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (dbClient as unknown as { _clearNotes: () => void })._clearNotes?.();
  });

  describe('createNote', () => {
    it('should create a note with required fields', () => {
      const note = createNote({
        title: 'Test Note',
        content: 'This is test content',
      });

      expect(note).toBeDefined();
      expect(note.id).toMatch(/^[0-9a-f-]{36}$/i);
      expect(note.title).toBe('Test Note');
      expect(note.content).toBe('This is test content');
      expect(note.tags).toEqual([]);
      expect(note.source_urls).toEqual([]);
      expect(note.created_at).toBeDefined();
      expect(note.updated_at).toBeDefined();
    });

    it('should create a note with tags and source URLs', () => {
      const note = createNote({
        title: 'Research Note',
        content: 'Research findings',
        tags: ['ai', 'research'],
        source_urls: ['https://example.com'],
      });

      expect(note.tags).toEqual(['ai', 'research']);
      expect(note.source_urls).toEqual(['https://example.com']);
    });

    it('should throw error for empty title', () => {
      expect(() =>
        createNote({
          title: '',
          content: 'Content',
        })
      ).toThrow(NoteError);
    });

    it('should throw error for empty content', () => {
      expect(() =>
        createNote({
          title: 'Title',
          content: '',
        })
      ).toThrow(NoteError);
    });

    it('should throw error for title too long', () => {
      expect(() =>
        createNote({
          title: 'x'.repeat(250),
          content: 'Content',
        })
      ).toThrow(NoteError);
    });

    it('should throw error for too many tags', () => {
      expect(() =>
        createNote({
          title: 'Title',
          content: 'Content',
          tags: Array(15).fill('tag'),
        })
      ).toThrow(NoteError);
    });
  });

  describe('getNoteById', () => {
    it('should retrieve a note by ID', () => {
      const created = createNote({
        title: 'Find Me',
        content: 'Content to find',
      });

      const found = getNoteById(created.id);
      expect(found.id).toBe(created.id);
      expect(found.title).toBe('Find Me');
    });

    it('should throw error for non-existent note', () => {
      expect(() => getNoteById('non-existent-id')).toThrow(NoteError);
    });
  });

  describe('listNotes', () => {
    it('should list all notes', () => {
      createNote({ title: 'Note 1', content: 'Content 1' });
      createNote({ title: 'Note 2', content: 'Content 2' });

      const notes = listNotes();
      expect(notes.notes).toHaveLength(2);
      expect(notes.totalCount).toBe(2);
    });

    it('should respect limit parameter', () => {
      createNote({ title: 'Note 1', content: 'Content 1' });
      createNote({ title: 'Note 2', content: 'Content 2' });
      createNote({ title: 'Note 3', content: 'Content 3' });

      const notes = listNotes({ limit: 2 });
      expect(notes.notes.length).toBeLessThanOrEqual(2);
    });
  });

  describe('deleteNote', () => {
    it('should delete an existing note', () => {
      const note = createNote({
        title: 'Delete Me',
        content: 'To be deleted',
      });

      expect(() => deleteNote(note.id)).not.toThrow();
    });

    it('should throw error for non-existent note', () => {
      expect(() => deleteNote('non-existent-id')).toThrow(NoteError);
    });
  });

  describe('getNoteCount', () => {
    it('should return correct count', () => {
      createNote({ title: 'Note 1', content: 'Content 1' });
      createNote({ title: 'Note 2', content: 'Content 2' });

      const count = getNoteCount();
      expect(count).toBe(2);
    });
  });
});
