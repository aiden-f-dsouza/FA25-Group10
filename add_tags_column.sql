-- Add tags column to note table for hashtag support
ALTER TABLE public.note
ADD COLUMN IF NOT EXISTS tags TEXT;

-- Create Like table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.like (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(note_id, user_id)
);

-- Create Comment table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.comment (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    author VARCHAR(100) NOT NULL DEFAULT 'Anonymous',
    body TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT NOW()
);
