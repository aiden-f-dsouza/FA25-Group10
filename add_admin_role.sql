-- Add is_admin column to profiles table
-- This allows us to designate certain users as administrators

-- Add the column (defaults to false for all existing users)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Example: Make a specific user an admin (replace with actual email)
UPDATE public.profiles
SET is_admin = TRUE
WHERE email = 'your-admin-email@example.com';

-- To check admin users:
-- SELECT id, email, is_admin FROM public.profiles WHERE is_admin = TRUE;