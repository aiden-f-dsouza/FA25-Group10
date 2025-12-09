# UIUC Turbolearn

**CS124 Honors Project - FA25-Group10**

A collaborative note-sharing platform built by UIUC students, for UIUC students.

## Project Overview

UIUC Turbolearn is a centralized platform where students can post, search, and organize class notes by course. Stop searching through endless GroupMe threads - keep your notes organized, searchable, and accessible to everyone who needs them.

## Core Features

### User Accounts & Authentication
- Secure user registration and login powered by Supabase Auth
- User profiles to track contributions and manage notes
- Email verification and password reset functionality
- Admin roles for content moderation

### Note Management
- **Create & Edit Notes**: Post notes with titles, content, and class assignments
- **File Attachments**: Upload PDFs, images, documents, and presentations (up to 16MB)
- **Rich Organization**: Tag notes with hashtags for easy discovery
- **Permission System**: Edit and delete your own notes, with admin override capabilities

### Social & Collaboration Features
- **Likes**: Show appreciation for helpful notes
- **Comments**: Discuss content and ask questions
- **@Mentions**: Notify specific users in comments with real-time mention tracking
- **Comment Management**: Edit or delete your own comments

### Smart Search & Filtering
- Filter notes by course (CS124, CS128, CS173, MATH221, etc.)
- Search by keywords in title, body, or author
- Filter by tags and hashtags
- Date range filtering (Today, This Week, This Month, All Time)
- Multiple sort options:
  - Most Recent / Oldest First
  - By Title or Author
  - Most Liked / Most Commented
  - Popular (combined engagement)

### AI-Powered Tools
- **Note Summarizer**: Paste lengthy lecture notes and get AI-generated concise summaries
- Powered by OpenAI GPT-4o-mini for fast, accurate summarization
- Perfect for quick reviews before exams

### User Experience
- **Pagination**: Efficient "Load More" functionality for browsing notes
- **Real-time Updates**: Live feed of recent notes on the homepage
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL via Supabase
- **ORM**: SQLAlchemy
- **Authentication**: Supabase Auth
- **File Storage**: Local file system with secure uploads
- **AI/ML**: OpenAI GPT-4o-mini for text summarization
- **Frontend**: HTML, CSS (custom dark mode styling), JavaScript
- **Icons**: Phosphor Icons
- **Fonts**: Google Fonts (Merriweather + Inter)

## Project Structure

```
Illinotes/
├── app.py                  # Main Flask application with all routes
├── templates/              # HTML templates
│   ├── homev3.html        # Landing page
│   ├── index.html         # Notes feed page
│   ├── profile.html       # User profile page
│   ├── login.html         # Authentication pages
│   ├── signup.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   └── summarizer.html    # AI summarizer page
├── static/                 # Static assets
│   ├── turbolearn-darkmode.css
│   ├── theme-toggle.js
│   └── images/
│       └── logo.png
├── uploads/                # User-uploaded files
├── .env                    # Environment variables (not in repo)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Database Models

- **Note**: Main content with author, title, body, class_code, tags, timestamps
- **Attachment**: Files attached to notes with metadata
- **Like**: User likes on notes (one per user per note)
- **Comment**: Discussion threads on notes with edit/delete permissions
- **Mention**: Tracks @mentions in comments with read/unread status

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database (via Supabase)
- OpenAI API key (for summarizer feature)

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd Illinotes
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Create a `.env` file with:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
DATABASE_URL=your_postgresql_connection_string
OPENAI_API_KEY=your_openai_api_key
```

5. Initialize the database
```bash
python app.py
```
This will create all necessary database tables and the uploads folder.

6. Run the development server
```bash
python app.py
```
The app will be available at `http://localhost:5000`

## Supported Classes

Currently supporting 10+ UIUC courses:
- CS124, CS128, CS173, CS100
- MATH221, MATH231
- ENG100, RHET105
- PHY211, PHY212

## Future Enhancements
 - tbd
