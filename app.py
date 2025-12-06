from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from supabase import create_client, Client
import os
import uuid
from functools import wraps
import re

# FLASK APP CONFIGURATION
# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client for file storage
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Create a new instance of Flask as our web application
app = Flask(__name__)

# Configure the database connection to Supabase PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
# Disable modification tracking to save resources (not needed for this app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Set a secret key for session security (needed for file uploads)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Configure file upload settings
# Directory where uploaded files will be stored
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Maximum file size allowed (16 MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size
# Allowed file extensions for uploads (PDFs, images, and documents)
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'txt', 'ppt', 'pptx'}

# Initialize SQLAlchemy database with our app
db = SQLAlchemy(app)

# List of available class codes for the dropdown filter
CLASSES = ["CS124", "CS128", "CS173", "MATH221", "MATH231", "ENG100", "CS100", "RHET105", "PHY211", "PHY212"]

# PAGE_SIZE controls how many notes are returned per page for pagination.
PAGE_SIZE = 5


# DATABASE MODELS
# These classes define the structure of our database tables

class Note(db.Model):
    """
    Note model - represents a single note in the database
    Each note can have multiple file attachments, likes, and comments
    """
    # Primary key - unique identifier for each note (auto-increments)
    id = db.Column(db.Integer, primary_key=True)

    # Author of the note (default: "Anonymous")
    author = db.Column(db.String(100), nullable=False, default="Anonymous")

    # Title of the note (default: "Untitled")
    title = db.Column(db.String(200), nullable=False, default="Untitled")

    # Main content/body of the note (can be long text)
    body = db.Column(db.Text, nullable=False)

    # Which class this note belongs to (e.g., "CS124")
    class_code = db.Column(db.String(50), nullable=False)

    # Foreign key linking note to Supabase auth user (UUID string)
    user_id = db.Column(db.String(36), nullable=False)

    # Tags for the note (stored as comma-separated string)
    tags = db.Column(db.Text, nullable=True)

    # When this note was created (automatically set to current time)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship: One note can have many attachments
    # The 'backref' creates a reverse reference from Attachment back to Note
    # 'cascade' means if we delete a note, all its attachments are deleted too
    attachments = db.relationship('Attachment', backref='note', lazy=True, cascade='all, delete-orphan')

    # Relationship: One note can have many likes
    likes = db.relationship('Like', backref='note', lazy=True, cascade='all, delete-orphan')

    # Relationship: One note can have many comments
    comments = db.relationship('Comment', backref='note', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        """String representation for debugging"""
        return f'<Note {self.id}: {self.title}>'

    def get_tags_list(self):
        """Return tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def get_hashtags(self):
        """Extract hashtags from body and tags"""
        hashtags = set()
        # Extract from body
        hashtags.update(extract_hashtags(self.body))
        # Extract from tags
        for tag in self.get_tags_list():
            if tag.startswith('#'):
                hashtags.add(tag[1:])
            else:
                hashtags.add(tag)
        return list(hashtags)


class Attachment(db.Model):
    """
    Attachment model - represents a file attached to a note
    Each attachment belongs to exactly one note
    """
    # Primary key - unique identifier for each attachment (auto-increments)
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key - links this attachment to a specific note
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)

    # The unique filename stored on disk (with UUID to prevent collisions)
    filename = db.Column(db.String(255), nullable=False)

    # The original filename when user uploaded it (for display purposes)
    original_filename = db.Column(db.String(255), nullable=False)

    # File type/extension (e.g., "pdf", "png", "docx")
    file_type = db.Column(db.String(10), nullable=False)

    # When this file was uploaded (automatically set to current time)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        """String representation for debugging"""
        return f'<Attachment {self.id}: {self.original_filename}>'


class Like(db.Model):
    """
    Like model - represents a user liking a note
    Prevents duplicate likes from the same user
    """
    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key - links to a specific note
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)

    # User ID who liked (from Supabase auth, or "Anonymous")
    user_id = db.Column(db.String(36), nullable=False)

    # When this like was created
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Like {self.id}: Note {self.note_id} by User {self.user_id}>'


class Comment(db.Model):
    """
    Comment model - represents a comment on a note
    """
    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key - links to a specific note
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)

    # Comment author (email)
    author = db.Column(db.String(100), nullable=False, default="Anonymous")

    # Comment body/content
    body = db.Column(db.Text, nullable=False)

    # User ID from Supabase (for permission tracking)
    user_id = db.Column(db.String(36), nullable=True)

    # When this comment was created
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Comment {self.id}: {self.author} on Note {self.note_id}>'


class Mention(db.Model):
    """
    Mention model - represents when a user is @mentioned in a comment
    """
    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key - links to the comment where mention occurred
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)

    # Foreign key - links to the note where mention occurred
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)

    # Email of the mentioned user (from Supabase auth)
    mentioned_user_email = db.Column(db.String(100), nullable=False)

    # User ID of mentioned user (for linking to auth system)
    mentioned_user_id = db.Column(db.String(36), nullable=True)

    # Author who created the mention
    mentioning_author = db.Column(db.String(100), nullable=False)

    # Has this mention been read/seen?
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    # When this mention was created
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Mention {self.id}: @{self.mentioned_user_email} in Comment {self.comment_id}>'


# AUTHENTICATION HELPER FUNCTIONS

def login_required(f):
    """
    Decorator to protect routes that require authentication
    Checks if user has a valid Supabase session
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the access token from session cookie
        access_token = request.cookies.get('access_token')

        if not access_token:
            # No token found, redirect to login
            return redirect(url_for('login'))

        try:
            # Verify the token with Supabase
            user = supabase.auth.get_user(access_token)
            if not user:
                return redirect(url_for('login'))
        except Exception as e:
            # Token is invalid or expired
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_function

class UserWrapper:
    """Wrapper class to add is_admin attribute to Supabase user"""
    def __init__(self, supabase_user, is_admin=False):
        self._user = supabase_user
        self.is_admin = is_admin

    def __getattr__(self, name):
        # Delegate attribute access to the wrapped user object
        return getattr(self._user, name)

    def __bool__(self):
        # Make sure the wrapper evaluates to True if user exists
        return self._user is not None

def get_current_user():
    """
    Get the currently logged-in user from Supabase
    Returns:
        UserWrapper object with is_admin attribute, or None if not authenticated
    """
    access_token = request.cookies.get('access_token')
    if not access_token:
        print("DEBUG: No access_token cookie found")
        return None

    try:
        response = supabase.auth.get_user(access_token)
        if response and response.user:
            user = response.user
            print(f"DEBUG: User logged in: {user.email}, ID: {user.id}")

            # Fetch admin status from profiles table
            is_admin = False
            try:
                profile = supabase.table('profiles').select('is_admin').eq('id', user.id).execute()
                if profile.data and len(profile.data) > 0:
                    is_admin = profile.data[0].get('is_admin', False)
                    print(f"DEBUG: User is_admin: {is_admin}")
                else:
                    print("DEBUG: No profile found, setting is_admin=False")
            except Exception as e:
                print(f"DEBUG: Error fetching profile: {e}")

            # Return wrapped user with is_admin attribute
            return UserWrapper(user, is_admin)
        print("DEBUG: No user found in response")
        return None
    except Exception as e:
        print(f"DEBUG: Error in get_current_user: {e}")
        return None

# HELPER FUNCTIONS

def allowed_file(filename):
    """
    Check if a file has an allowed extension
    Args:
        filename: The name of the file to check
    Returns:
        True if the file extension is in ALLOWED_EXTENSIONS, False otherwise
    """
    # Check if filename has a dot AND the extension (after the dot) is allowed
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_hashtags(text):
    """Extract hashtags from text (e.g., #python, #flask)"""
    return [tag[1:] for tag in re.findall(r"#[\w-]+", text)]


def extract_mentions(text):
    """Extract @mentions from text (e.g., @user@example.com or @example@gmail.com)"""
    # Pattern to match emails after @ symbol
    # Matches @email@domain.com or @username (without email)
    mentions = re.findall(r"@([\w\.-]+@[\w\.-]+\.\w+)", text)
    return mentions


@app.template_filter('time_ago')
def time_ago_filter(dt):
    """
    Convert a datetime to a human-readable 'time ago' format
    Args:
        dt: datetime object to convert
    Returns:
        String like "2 min ago", "1 hour ago", "3 days ago"
    """
    if not dt:
        return ""

    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:  # Less than 1 hour
        minutes = int(seconds / 60)
        return f"{minutes} min ago"
    elif seconds < 86400:  # Less than 1 day
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:  # Less than 1 week
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        # For older dates, just show the date
        return dt.strftime("%b %d, %Y")


def _get_filtered_notes(args):
    """Return the filtered & sorted notes (full list) according to query args.

    This helper performs filtering and sorting for notes based on various criteria.
    Used by both the main index route and the pagination endpoint.
    """
    selected_filter = args.get("class_filter", "All")
    search_query = args.get("search", "").strip().lower()
    tag_filter = args.get("tag_filter", "All")
    date_filter = args.get("date_filter", "All")
    sort_by = args.get("sort_by", "recent")

    # Start with a database query for all notes
    query = Note.query

    # --- Filter by class (e.g., only show CS124 notes) ---
    if selected_filter and selected_filter != "All":
        query = query.filter(Note.class_code == selected_filter)

    # --- Filter by search term (looks in title, body, AND author) ---
    if search_query:
        query = query.filter(
            (Note.title.ilike(f"%{search_query}%")) |
            (Note.body.ilike(f"%{search_query}%")) |
            (Note.author.ilike(f"%{search_query}%"))
        )

    # --- Filter by tag (if provided) ---
    if tag_filter and tag_filter != "All":
        # Search for the tag in the tags field
        query = query.filter(Note.tags.ilike(f"%{tag_filter}%"))

    # --- Filter by date (Today, This Week, This Month, or All Time) ---
    if date_filter and date_filter != "All":
        now = datetime.now()

        # Calculate the cutoff date based on selected filter
        if date_filter == "Today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Week":
            cutoff = now - timedelta(days=7)
        elif date_filter == "Month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        if cutoff:
            query = query.filter(Note.created >= cutoff)

    # STEP 3: Sort the filtered results
    if sort_by == "recent":
        query = query.order_by(Note.id.desc())
    elif sort_by == "oldest":
        query = query.order_by(Note.id.asc())
    elif sort_by == "title":
        query = query.order_by(Note.title.asc())
    elif sort_by == "author":
        query = query.order_by(Note.author.asc())
    elif sort_by == "most_liked":
        # Sort by number of likes (using subquery to count)
        query = query.outerjoin(Like).group_by(Note.id).order_by(db.func.count(Like.id).desc())
    elif sort_by == "most_commented":
        # Sort by number of comments (using subquery to count)
        query = query.outerjoin(Comment).group_by(Note.id).order_by(db.func.count(Comment.id).desc())
    elif sort_by == "popular":
        # Popularity: primarily by comments, then by likes
        query = query.outerjoin(Comment).outerjoin(Like).group_by(Note.id).order_by(
            db.func.count(Comment.id).desc(),
            db.func.count(Like.id).desc()
        )

    return query.all()


# ROUTES
# These functions handle different URLs and user requests

# Homepage route - landing page
@app.route("/")
def home():
    """Display the home page with 3 most recent notes"""
    current_user = get_current_user()

    # Fetch 3 most recent notes for the live feed display
    recent_notes = Note.query.order_by(Note.created.desc()).limit(3).all()

    return render_template("homev3.html", current_user=current_user, recent_notes=recent_notes)

# Notes feed route - handles both displaying notes (GET) and creating new notes (POST)
@app.route("/notes", methods=["GET", "POST"])
def notes():
    print("===== INDEX ROUTE CALLED =====")
    # HANDLING NOTE CREATION (POST REQUEST)
    # This runs when user submits the "Create Note" form
    if request.method == "POST":
        # Get the current user from Supabase
        # Only logged-in users can create notes
        current_user = get_current_user()
        if not current_user:
            # Redirect anonymous users to login if they try to create a note
            return redirect(url_for('login'))

        # Get form data, with fallback defaults if fields are empty
        # Author is automatically set to the logged-in user's email
        author = current_user.email
        title = request.form.get("title", "").strip() or "Untitled"
        body = request.form.get("body", "").strip()
        selected_class = request.form.get("class", "General")

        # Parse tags from comma-separated input
        raw_tags = request.form.get("tags", "")
        tags_list = []
        if raw_tags:
            # Split on comma and remove hashtag symbols if present
            parts = [p.strip() for p in raw_tags.replace('#', '').split(',')]
            tags_list = [p for p in parts if p]

        # Extract hashtags from body
        hashtags = set(extract_hashtags(body))
        # Combine with tags
        hashtags.update(tags_list)
        # Store as comma-separated string
        tags_str = ','.join(hashtags) if hashtags else ''

        # Only create note if body is not empty
        if body:
            # Create a new Note object with the form data
            new_note = Note(
                author=author,
                title=title,
                body=body,
                class_code=selected_class,
                user_id=current_user.id,  # Link to Supabase auth user
                tags=tags_str
            )

            # Add the note to the database session (prepares it to be saved)
            db.session.add(new_note)
            # Commit the transaction (actually saves to database)
            # We need to commit here so the note gets an ID before we can attach files
            db.session.commit()

            # HANDLE FILE UPLOADS
            # Check if any files were uploaded with the form
            if 'attachments' in request.files:
                # Get all uploaded files (user can upload multiple at once)
                files = request.files.getlist('attachments')

                # Process each uploaded file
                for file in files:
                    # Check if file exists and has a valid filename
                    if file and file.filename and allowed_file(file.filename):
                        # Secure the filename to prevent directory traversal attacks
                        original_filename = secure_filename(file.filename)

                        # Get the file extension (e.g., "pdf", "png")
                        file_ext = original_filename.rsplit('.', 1)[1].lower()

                        # Create a unique filename using UUID to prevent conflicts
                        # Format: uuid_originalname.ext
                        unique_filename = f"{uuid.uuid4()}_{original_filename}"

                        # Save the file to the uploads directory
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)

                        # Create an Attachment record in the database
                        attachment = Attachment(
                            note_id=new_note.id,  # Link to the note we just created
                            filename=unique_filename,  # The UUID-based filename on disk
                            original_filename=original_filename,  # Keep original name for display
                            file_type=file_ext  # Store file extension
                        )

                        # Add attachment to database
                        db.session.add(attachment)

                # Save all attachments to database
                db.session.commit()

        # Redirect back to the notes feed to show the new note
        return redirect(url_for("notes"))

    # HANDLING NOTE DISPLAY (GET REQUEST)
    # This runs when user visits the page to view notes

    # Get filter parameters from the URL
    selected_filter = request.args.get("class_filter", "All")
    search_query = request.args.get("search", "").strip().lower()
    tag_filter = request.args.get("tag_filter", "All")
    date_filter = request.args.get("date_filter", "All")
    sort_by = request.args.get("sort_by", "recent")

    # Get filtered notes using the helper function
    filtered_notes = _get_filtered_notes(request.args)

    # Pagination
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    total = len(filtered_notes)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    notes_page = filtered_notes[start:end]
    has_more = end < total

    # Build tag cloud (tag -> count)
    tag_counts = {}
    all_notes = Note.query.all()
    for n in all_notes:
        for t in n.get_tags_list():
            key = t.strip()
            if not key:
                continue
            tag_counts[key] = tag_counts.get(key, 0) + 1
    # Sorted list of (tag, count) descending
    tags_sorted = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

    # Get current user from Supabase
    current_user = get_current_user()

    # Get unread mentions for current user
    unread_mentions = []
    if current_user:
        unread_mentions = Mention.query.filter_by(
            mentioned_user_email=current_user.email,
            is_read=False
        ).order_by(Mention.created.desc()).all()

    # Get list of note IDs that current user has liked
    user_liked_notes = set()
    if current_user:
        user_likes = Like.query.filter_by(user_id=current_user.id).all()
        user_liked_notes = {like.note_id for like in user_likes}

    # Send everything to the template to display
    return render_template(
        "index.html",
        notes=notes_page,  # The paginated notes to display
        page=page,
        has_more=has_more,
        total=total,
        tag_filter=tag_filter,
        classes=CLASSES,  # List of all available classes
        selected_filter=selected_filter,  # Currently selected class filter
        search_query=search_query,  # Current search term
        date_filter=date_filter,  # Currently selected date range
        sort_by=sort_by,  # Current sort option
        current_user=current_user,  # Current Supabase user
        tags=tags_sorted,  # Tag cloud data
        unread_mentions=unread_mentions,  # Unread @mentions for current user
        user_liked_notes=user_liked_notes,  # Set of note IDs the user has liked
    )


@app.route("/api/notes")
def notes_api():
    """Return a page of notes as JSON (HTML fragment + has_more flag).

    This endpoint supports the client-side "Load More" UI. It accepts the same
    filter/sort query parameters as the main route plus a page parameter.
    """
    filtered_notes = _get_filtered_notes(request.args)
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    total = len(filtered_notes)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    notes_page = filtered_notes[start:end]
    has_more = end < total

    # Get current user from Supabase
    current_user = get_current_user()

    # Render only the notes HTML fragment
    html = render_template("notes_fragment.html", notes=notes_page, classes=CLASSES, current_user=current_user)
    return jsonify({"html": html, "has_more": has_more})


# Endpoint to toggle like for a note
@app.route("/like/<int:note_id>", methods=["POST"])
def like_note(note_id):
    """Toggle like for a note. Add if not liked, remove if already liked."""
    # Get current user (or use "Anonymous" if not logged in)
    current_user = get_current_user()
    user_id = current_user.id if current_user else "Anonymous"

    # Check if user already liked this note
    existing_like = Like.query.filter_by(note_id=note_id, user_id=user_id).first()

    if existing_like:
        # Unlike - remove the existing like
        db.session.delete(existing_like)
        db.session.commit()
    else:
        # Like - create a new like
        new_like = Like(note_id=note_id, user_id=user_id)
        db.session.add(new_like)
        db.session.commit()

    # Redirect back to the referring page
    return redirect(request.referrer or url_for("notes"))


# Endpoint to add a comment to a note
@app.route("/comment/<int:note_id>", methods=["POST"])
@login_required
def add_comment(note_id):
    """Add a comment to a note. Requires login."""
    # Get current user (must be logged in due to @login_required)
    current_user = get_current_user()
    author = current_user.email

    body = request.form.get("comment_body", "").strip()

    if not body:
        return redirect(request.referrer or url_for("notes"))

    # Create a new comment with user_id for permission tracking
    new_comment = Comment(
        note_id=note_id,
        author=author,
        body=body,
        user_id=current_user.id
    )
    db.session.add(new_comment)
    db.session.commit()

    # Extract @mentions and create Mention records
    mentioned_emails = extract_mentions(body)
    for email in mentioned_emails:
        # Check if this email exists in the system
        # Try to find user ID from Supabase (optional, can be None for now)
        user_id = None

        # Create mention record
        mention = Mention(
            comment_id=new_comment.id,
            note_id=note_id,
            mentioned_user_email=email,
            mentioned_user_id=user_id,
            mentioning_author=author,
            is_read=False
        )
        db.session.add(mention)

    # Commit all mentions
    if mentioned_emails:
        db.session.commit()

    return redirect(request.referrer or url_for("notes"))


# Endpoint to edit a comment
@app.route("/comment/<int:comment_id>/edit", methods=["POST"])
@login_required
def edit_comment(comment_id):
    """Edit a comment. User can edit their own comments, admin can edit all."""
    current_user = get_current_user()
    comment = Comment.query.get_or_404(comment_id)

    # Check permissions: user must own the comment OR be an admin
    if comment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    new_body = request.form.get("comment_body", "").strip()
    if not new_body:
        return redirect(request.referrer or url_for("notes"))

    # Update the comment body
    comment.body = new_body
    db.session.commit()

    return redirect(request.referrer or url_for("notes"))


# Endpoint to delete a comment
@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    """Delete a comment. User can delete their own comments, admin can delete all."""
    current_user = get_current_user()
    comment = Comment.query.get_or_404(comment_id)

    # Check permissions: user must own the comment OR be an admin
    if comment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    # Delete associated mentions first (foreign key constraint)
    Mention.query.filter_by(comment_id=comment_id).delete()

    # Delete the comment
    db.session.delete(comment)
    db.session.commit()

    return redirect(request.referrer or url_for("notes"))


# MENTION ROUTES
@app.route("/mentions/<int:mention_id>/mark-read", methods=["POST"])
def mark_mention_read(mention_id):
    """Mark a single mention as read"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Not authenticated"}), 401

    mention = Mention.query.get_or_404(mention_id)

    # Verify this mention belongs to the current user
    if mention.mentioned_user_email != current_user.email:
        return jsonify({"error": "Unauthorized"}), 403

    mention.is_read = True
    db.session.commit()

    return jsonify({"success": True})


@app.route("/mentions/mark-all-read", methods=["POST"])
def mark_all_mentions_read():
    """Mark all mentions as read for the current user"""
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    # Find all unread mentions for this user
    unread_mentions = Mention.query.filter_by(
        mentioned_user_email=current_user.email,
        is_read=False
    ).all()

    # Mark them all as read
    for mention in unread_mentions:
        mention.is_read = True

    db.session.commit()

    return redirect(url_for("notes"))


# EDIT NOTE ROUTE
# Handles updating an existing note
@app.route("/edit/<int:note_id>", methods=["POST"])
@login_required
def edit_note(note_id):
    # Get current user
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    # Find the note in the database by its ID
    note = Note.query.get_or_404(note_id)

    # Permission check: User must own the note OR be an admin
    if note.user_id != current_user.id and not current_user.is_admin:
        # User doesn't have permission to edit this note
        return "Unauthorized: You don't have permission to edit this note", 403

    # Update the note's fields with new data from the form
    note.title = request.form.get("title", "").strip() or note.title
    note.body = request.form.get("body", "").strip() or note.body
    note.author = request.form.get("author", "").strip() or note.author
    note.class_code = request.form.get("class", note.class_code)

    # Update tags if provided
    raw_tags = request.form.get("tags")
    if raw_tags is not None:
        parts = [p.strip() for p in raw_tags.replace('#', '').split(',')]
        tags_list = [p for p in parts if p]
        # Extract hashtags from body
        hashtags = set(extract_hashtags(note.body))
        hashtags.update(tags_list)
        note.tags = ','.join(hashtags) if hashtags else ''

    # HANDLE ATTACHMENT DELETION
    attachments_to_delete = request.form.getlist("delete_attachments")
    if attachments_to_delete:
        for attachment_id in attachments_to_delete:
            attachment = Attachment.query.get(int(attachment_id))
            if attachment and attachment.note_id == note_id:
                # Delete the file from the filesystem
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Delete the attachment record from database
                db.session.delete(attachment)

    # HANDLE NEW ATTACHMENT UPLOADS
    if 'attachments' in request.files:
        files = request.files.getlist('attachments')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}_{original_filename}"

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)

                new_attachment = Attachment(
                    note_id=note.id,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_type=file_ext
                )
                db.session.add(new_attachment)

    # Save all changes to the database
    db.session.commit()

    # Redirect back to the notes feed to show the updated note
    return redirect(url_for("notes"))


# DELETE NOTE ROUTE
# Handles removing a note from the system (also deletes associated files)
@app.route("/delete/<int:note_id>", methods=["POST"])
@login_required
def delete_note(note_id):
    # Get current user
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    # Find the note in the database by its ID
    note = Note.query.get_or_404(note_id)

    # Permission check: User must own the note OR be an admin
    if note.user_id != current_user.id and not current_user.is_admin:
        # User doesn't have permission to delete this note
        return "Unauthorized: You don't have permission to delete this note", 403

    # Delete all associated files from the filesystem
    for attachment in note.attachments:
        # Build the file path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
        # Check if file exists and delete it
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete the note from the database
    # The cascade relationship will automatically delete all attachment, like, and comment records
    db.session.delete(note)
    db.session.commit()

    # Redirect back to the notes feed
    return redirect(url_for("notes"))


# AUTHENTICATION ROUTES
@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle user registration with Supabase Auth"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not email or not password:
            return render_template("signup.html", error="Email and password are required")

        # Check if passwords match
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")

        try:
            # Sign up with Supabase Auth
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": None  # Don't redirect after email confirmation
                }
            })

            if response.user:
                # Check if email confirmation is required
                if response.session and response.session.access_token:
                    # Email confirmation is disabled - log user in immediately
                    resp = redirect(url_for("notes"))
                    resp.set_cookie('access_token', response.session.access_token,
                                   httponly=True, secure=False)  # Set secure=True in production with HTTPS
                    return resp
                else:
                    # Email confirmation is enabled - show success message and redirect to login
                    return render_template("login.html",
                                         success=f"Account created successfully! We've sent a verification email to {email}. Please check your inbox and click the confirmation link, then come back here to log in.")
            else:
                return render_template("signup.html", error="Signup failed. Please try again.")

        except Exception as e:
            error_message = str(e)
            print(f"Signup error: {error_message}")  # Debug logging

            # Extract a user-friendly error message
            if "already registered" in error_message.lower():
                error_message = "Email already registered"
            elif "invalid email" in error_message.lower():
                error_message = "Invalid email format"
            elif "password" in error_message.lower():
                error_message = "Password must be at least 6 characters"
            else:
                # Show the actual error in development for debugging
                error_message = f"Signup failed: {error_message}"

            return render_template("signup.html", error=error_message)

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with Supabase Auth"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validation
        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        try:
            # Sign in with Supabase Auth
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user and response.session:
                # Set the access token as a cookie
                resp = redirect(url_for("notes"))
                resp.set_cookie('access_token', response.session.access_token,
                               httponly=True, secure=False)  # Set secure=True in production with HTTPS
                return resp
            else:
                return render_template("login.html", error="Invalid email or password")

        except Exception as e:
            error_str = str(e)
            print(f"Login error: {error_str}")  # Debug logging

            # Provide user-friendly error messages
            if "email not confirmed" in error_str.lower() or "email_not_confirmed" in error_str.lower():
                error_message = "Please verify your email address first. Check your inbox for the confirmation email we sent you."
            elif "invalid" in error_str.lower():
                error_message = "Invalid email or password. Please try again."
            else:
                error_message = f"Login failed: {error_str}"

            return render_template("login.html", error=error_message)

    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Handle password reset requests"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not email:
            return render_template("forgot_password.html", error="Please enter your email address")

        try:
            # Request password reset from Supabase
            supabase.auth.reset_password_email(
                email,
                {
                    "redirect_to": "http://localhost:5000/reset-password"
                }
            )

            # Always show success message (don't reveal if email exists or not for security)
            return render_template("forgot_password.html",
                                 success=f"If an account exists with {email}, you will receive a password reset email shortly. Please check your inbox.")

        except Exception as e:
            print(f"Password reset error: {str(e)}")
            # Show generic success message even on error (security best practice)
            return render_template("forgot_password.html",
                                 success=f"If an account exists with {email}, you will receive a password reset email shortly. Please check your inbox.")

    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Handle password reset form (after clicking email link)"""
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        access_token = request.form.get("access_token")

        # Validation
        if not password or not confirm_password:
            return render_template("reset_password.html",
                                 error="Please enter and confirm your new password",
                                 access_token=access_token)

        if password != confirm_password:
            return render_template("reset_password.html",
                                 error="Passwords do not match",
                                 access_token=access_token)

        if len(password) < 6:
            return render_template("reset_password.html",
                                 error="Password must be at least 6 characters",
                                 access_token=access_token)

        try:
            # Update the password using Supabase
            if access_token:
                supabase.auth.update_user(access_token, {"password": password})

                return render_template("login.html",
                                     success="Password updated successfully! You can now log in with your new password.")
            else:
                return render_template("reset_password.html",
                                     error="Invalid or expired reset link. Please request a new password reset.")

        except Exception as e:
            print(f"Password update error: {str(e)}")
            return render_template("reset_password.html",
                                 error=f"Failed to update password: {str(e)}",
                                 access_token=access_token)

    # GET request - show the reset form (token will be captured by JavaScript)
    return render_template("reset_password.html")

@app.route("/logout")
@login_required
def logout():
    """Handle user logout with Supabase Auth"""
    access_token = request.cookies.get('access_token')

    try:
        # Sign out from Supabase
        if access_token:
            supabase.auth.sign_out()
    except:
        pass  # Even if sign_out fails, we'll clear the cookie

    # Clear the access token cookie
    resp = redirect(url_for("login"))
    resp.set_cookie('access_token', '', expires=0)
    return resp

@app.route("/profile")
@login_required
def profile():
    """Show user profile page with Supabase user"""
    # Get the current user from Supabase
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    # Get user's notes using Supabase user ID
    user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id.desc()).all()
    return render_template("profile.html", user=current_user, notes=user_notes)

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """Allow logged-in users to change their password"""
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Validation
    if not current_password or not new_password or not confirm_password:
        user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id.desc()).all()
        return render_template("profile.html", user=current_user, notes=user_notes,
                             password_error="All fields are required")

    if new_password != confirm_password:
        user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id.desc()).all()
        return render_template("profile.html", user=current_user, notes=user_notes,
                             password_error="New passwords do not match")

    if len(new_password) < 6:
        user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id.desc()).all()
        return render_template("profile.html", user=current_user, notes=user_notes,
                             password_error="Password must be at least 6 characters")

    try:
        # Verify current password by attempting to sign in
        access_token = request.cookies.get('access_token')
        verify_response = supabase.auth.sign_in_with_password({
            "email": current_user.email,
            "password": current_password
        })

        # Update to new password using the admin API
        supabase.auth.set_session(access_token, verify_response.session.refresh_token)
        supabase.auth.update_user({"password": new_password})

        user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id.desc()).all()
        return render_template("profile.html", user=current_user, notes=user_notes,
                             password_success="Password updated successfully!")

    except Exception as e:
        error_str = str(e)
        print(f"Change password error: {error_str}")

        if "invalid" in error_str.lower():
            error_msg = "Current password is incorrect"
        else:
            error_msg = f"Failed to update password: {error_str}"

        user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.id.desc()).all()
        return render_template("profile.html", user=current_user, notes=user_notes,
                             password_error=error_msg)


# AIDEN'S NEW ROUTES - AI Summarizer and Home

@app.route("/summarizer")
def summarizer():
    """AI Summarizer page route (Aiden's feature)"""
    return render_template("summarizer.html")

@app.route("/api/summarize", methods=["POST"])
def summarize():
    """API endpoint for AI text summarization (Aiden's feature)"""
    try:
        data = request.get_json()
        notes = data.get("notes", "").strip()

        if not notes:
            return jsonify({"error": "No notes provided"}), 400

        # Simple extractive summarization (free, no API needed)
        # Split into sentences more carefully to avoid splitting on decimals

        # Replace common abbreviations and decimals temporarily
        text = notes
        text = re.sub(r'(\d)\.(\d)', r'\1DECIMAL\2', text)  # Protect decimals like 43.0
        text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|etc|i\.e|e\.g)\.', r'\1PERIOD', text, flags=re.IGNORECASE)

        # Now split on sentence boundaries
        sentences = re.split(r'[.!?]+\s+', text)

        # Restore the protected patterns
        sentences = [s.replace('DECIMAL', '.').replace('PERIOD', '.').strip()
                    for s in sentences if s.strip() and len(s.strip()) > 15]

        if len(sentences) == 0:
            return jsonify({"error": "Could not parse text into sentences"}), 400

        # If text is already short, return as-is
        if len(notes) < 200:
            return jsonify({"summary": notes})

        # Score sentences based on various factors
        scored_sentences = []
        seen_phrases = set()

        for idx, sentence in enumerate(sentences):
            score = 0
            sentence_lower = sentence.lower()

            # Longer sentences (but not too long) tend to be more informative
            length = len(sentence.split())
            if 15 <= length <= 35:
                score += 3
            elif 10 <= length <= 50:
                score += 2
            elif length > 50:
                score += 1

            # Position matters: first few sentences often introduce topic
            if idx < 3:
                score += 4
            # Last sentence often has conclusion
            elif idx == len(sentences) - 1:
                score += 2

            # Sentences with data/numbers are valuable
            if re.search(r'\d+\.?\d*%|\$\d+|USD \d+|\d+\.\d+', sentence):
                score += 4

            # Sentences with keywords like "important", "key", "main" are valuable
            important_words = ['important', 'key', 'main', 'significant', 'primary',
                             'critical', 'essential', 'fundamental', 'major', 'conclude',
                             'expected', 'projected', 'growth', 'market size', 'cagr', 'forecast']
            for word in important_words:
                if word in sentence_lower:
                    score += 2
                    break

            # Penalize repetitive phrases
            repetitive_phrases = ['dominated the global market in 2022 and accounted',
                                'accounted for a revenue share', 'segment accounted for',
                                'segment dominated']
            for phrase in repetitive_phrases:
                if phrase in sentence_lower:
                    score -= 3
                    break

            # Avoid very short or likely metadata sentences
            if length < 8 or any(x in sentence_lower for x in ['copyright', 'login', 'sign up', 'home', 'logo', 'click here', 'download free sample', 'to learn more']):
                score -= 10

            # Penalize if very similar to already selected sentences
            sentence_key = ' '.join(sentence_lower.split()[:5])  # First 5 words
            if sentence_key in seen_phrases:
                score -= 4
            seen_phrases.add(sentence_key)

            scored_sentences.append((score, sentence, idx))

        # Sort by score and take top sentences
        scored_sentences.sort(reverse=True, key=lambda x: x[0])

        # Make summary length proportional to input - aim for 20-30% of original sentences
        if len(sentences) <= 5:
            num_sentences = max(2, len(sentences) - 2)  # Keep most if very short
        elif len(sentences) <= 15:
            num_sentences = max(3, int(len(sentences) * 0.3))  # 30% for medium text
        else:
            num_sentences = max(4, min(8, int(len(sentences) * 0.25)))  # 25% for longer text, cap at 8

        top_sentences = scored_sentences[:num_sentences]

        # Re-sort by original position to maintain flow
        top_sentences.sort(key=lambda x: x[2])

        # Build summary with formatting - each sentence on its own line or bullet
        summary_parts = []
        for _, sentence, _ in top_sentences:
            sentence = sentence.strip()
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            summary_parts.append(sentence)

        # Format with bullet points for better readability
        formatted_parts = ['• ' + part for part in summary_parts]
        summary_text = '\n'.join(formatted_parts)

        # Only enforce max length if summary is unreasonably long
        original_length = len(notes)
        if len(summary_text) > original_length * 0.9:
            # Summary is too close to original, cut more aggressively
            target_length = int(original_length * 0.6)
            truncated = summary_text[:target_length]
            last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
            if last_period > target_length * 0.5:
                summary_text = truncated[:last_period + 1]
            else:
                summary_text = truncated + "..."

        return jsonify({"summary": summary_text})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


# FILE DOWNLOAD ROUTE
# Handles secure file downloads for attachments
@app.route("/download/<int:attachment_id>")
def download_file(attachment_id):
    # Find the attachment in the database
    attachment = Attachment.query.get_or_404(attachment_id)

    # Security check: ensure the file path doesn't contain directory traversal attempts
    if '..' in attachment.filename or attachment.filename.startswith('/'):
        return "Invalid file path", 400

    # Send the file from the uploads directory
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        attachment.filename,
        as_attachment=True,
        download_name=attachment.original_filename
    )


# DATABASE AND UPLOADS INITIALIZATION
# This function runs once when the app starts to set up the database and file storage
def init_app():
    """
    Initialize the database and create necessary directories
    This creates the database tables if they don't exist and ensures the uploads folder exists
    """
    # Create the uploads directory if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"Created uploads directory: {UPLOAD_FOLDER}")

    # Create all database tables based on the models we defined
    # This only creates tables that don't already exist (won't overwrite existing data)
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")


if __name__ == "__main__":
    # Initialize the app (create database and uploads folder)
    init_app()
    # Start the Flask development server in debug mode
    app.run(debug=True)
