# UIUC Turbolearn - Local Setup Guide

This guide will help you set up and run the project on your local machine.

## Prerequisites

- Python 3.x installed
- Git installed
- A code editor (VS Code recommended)

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd CS124H
```

## Step 2: Get Supabase Credentials

Since you've been added as a collaborator to the Supabase project, follow these steps:

1. **Log in to Supabase**
   - Go to https://supabase.com
   - Sign in with the email that received the collaboration invite
   - Accept the project invitation if you haven't already

2. **Navigate to the Project**
   - You should see the project in your dashboard
   - Click on the project to open it

3. **Get the API Credentials**
   - In the left sidebar, click on **Settings** (gear icon)
   - Click on **API**
   - You'll see two important values:
     - **Project URL** - Copy this (it looks like `https://xxxxx.supabase.co`)
     - **anon/public key** - Copy this (long string of characters)

4. **Get the Database URL**
   - In the left sidebar, go to **Settings** → **Database**
   - Scroll down to **Connection String**
   - Select the **URI** tab
   - Copy the connection string (it looks like `postgresql://postgres:[YOUR-PASSWORD]@...`)
   - **IMPORTANT**: Replace `[YOUR-PASSWORD]` with the actual database password
     - If you don't know the password, ask the project owner (Ammar)
     - OR you can reset it in **Settings** → **Database** → **Database password** (but coordinate with the team first!)

## Step 3: Create Your .env File

1. In the project root directory, create a new file called `.env`
2. Add the following content, replacing the values with what you copied:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
DATABASE_URL=postgresql://postgres:your-password@db.xxx.supabase.co:5432/postgres
```

**Example:**
```env
SUPABASE_URL=https://abcdefghijk.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:MySecretPassword123@db.abcdefghijk.supabase.co:5432/postgres
```

## Step 4: Install Python Dependencies

```bash
# Optional but recommended: Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

## Step 5: Run the Application

```bash
python3 app.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

## Step 6: Access the Application

Open your browser and go to:
- **Homepage**: http://localhost:5000
- **Notes Feed**: http://localhost:5000/notes

## Troubleshooting

### "ModuleNotFoundError"
- Make sure you ran `pip install -r requirements.txt`
- Make sure your virtual environment is activated

### "Connection refused" or database errors
- Check that your `.env` file has the correct credentials
- Make sure you replaced `[YOUR-PASSWORD]` in DATABASE_URL with the actual password
- Verify you can access the Supabase project dashboard

### "File not found" errors
- Make sure you're in the correct directory (CS124H)
- Check that all files were cloned from the repository

### Port 5000 already in use
- Kill the existing process or use a different port:
  ```bash
  # Find the process using port 5000
  lsof -ti:5000 | xargs kill -9
  ```

## Project Structure

```
CS124H/
├── app.py              # Main Flask application
├── templates/          # HTML templates
│   ├── index.html     # Notes feed page
│   ├── homev3.html    # Homepage
│   └── profile.html   # User profile
├── static/            # CSS, JS, images
├── .env              # Environment variables (DO NOT COMMIT!)
├── requirements.txt   # Python dependencies
└── SETUP.md          # This file
```

## Important Notes

- **NEVER commit your `.env` file to Git** - it contains sensitive credentials
- The `.env` file is already in `.gitignore` to prevent accidental commits
- If you make changes to the database schema, coordinate with the team
- We're all using the same Supabase database, so changes affect everyone

## Quick Commands Reference

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python3 app.py

# Deactivate virtual environment
deactivate
```