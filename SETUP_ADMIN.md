# Setting Up Admin Accounts

## Step 1: Add is_admin Column to Profiles Table

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Open the file `add_admin_role.sql` in this directory
4. Copy the SQL commands
5. Paste into Supabase SQL Editor and click **Run**

This will add an `is_admin` column to your profiles table.

## Step 2: Make Specific Users Admins

After running the SQL script above, make your developer accounts admins:

```sql
-- Replace with your actual admin email addresses
UPDATE public.profiles
SET is_admin = TRUE
WHERE email = 'your-email@example.com';

-- For multiple admins:
UPDATE public.profiles
SET is_admin = TRUE
WHERE email IN ('admin1@example.com', 'admin2@example.com', 'admin3@example.com');
```

## Step 3: Verify Admin Accounts

Check which users are admins:

```sql
SELECT id, email, is_admin, created_at
FROM public.profiles
WHERE is_admin = TRUE;
```

## Step 4: Test Admin Access

1. Log out of the application
2. Log in with an admin account
3. You should now be able to edit/delete ANY note (not just your own)

## Removing Admin Access

To remove admin privileges from a user:

```sql
UPDATE public.profiles
SET is_admin = FALSE
WHERE email = 'user@example.com';
```