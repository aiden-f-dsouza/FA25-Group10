from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from supabase import create_client, Client
import os
import uuid
from functools import wraps

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


# DATABASE MODELS
# These classes define the structure of our database tables

class Note(db.Model):
    """
    Note model - represents a single note in the database
    Each note can have multiple file attachments
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

    # When this note was created (automatically set to current time)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship: One note can have many attachments
    # The 'backref' creates a reverse reference from Attachment back to Note
    # 'cascade' means if we delete a note, all its attachments are deleted too
    attachments = db.relationship('Attachment', backref='note', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        """String representation for debugging"""
        return f'<Note {self.id}: {self.title}>'


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

# ROUTES
# These functions handle different URLs and user requests

# Main page route - handles both displaying notes (GET) and creating new notes (POST)
# No @login_required decorator - anonymous users can view notes
@app.route("/", methods=["GET", "POST"])
def index():
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

        # Only create note if body is not empty
        if body:
            # Create a new Note object with the form data
            new_note = Note(
                author=author,
                title=title,
                body=body,
                class_code=selected_class,
                user_id=current_user.id  # Link to Supabase auth user
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

        # Redirect back to the main page to show the new note
        return redirect(url_for("index"))
    
    # HANDLING NOTE DISPLAY (GET REQUEST)
    # This runs when user visits the page to view notes

    # STEP 1: Get all filter parameters from the URL
    # These are passed as query parameters when user submits the filter form
    selected_filter = request.args.get("class_filter", "All")  # Which class to show
    search_query = request.args.get("search", "").strip().lower()  # Search term
    author_filter = request.args.get("author_filter", "All")  # Which author to show
    date_filter = request.args.get("date_filter", "All")  # Time range filter
    sort_by = request.args.get("sort_by", "recent")  # How to sort the results

    # STEP 2: Start with a database query for all notes
    # Note.query is a SQLAlchemy query object that we can filter and sort
    query = Note.query

    # --- Filter by class (e.g., only show CS124 notes) ---
    if selected_filter and selected_filter != "All":
        # Use SQLAlchemy filter to only get notes matching the selected class
        query = query.filter(Note.class_code == selected_filter)

    # --- Filter by author (e.g., only show notes from "John") ---
    if author_filter and author_filter != "All":
        # Filter to only show notes from the selected author
        query = query.filter(Note.author == author_filter)

    # --- Filter by search term (looks in both title and body) ---
    if search_query:
        # Use SQL LIKE operator to search for the query in title OR body
        # The | operator means OR in SQLAlchemy
        query = query.filter(
            (Note.title.ilike(f"%{search_query}%")) |
            (Note.body.ilike(f"%{search_query}%"))
        )

    # --- Filter by date (Today, This Week, This Month, or All Time) ---
    if date_filter and date_filter != "All":
        now = datetime.now()

        # Calculate the cutoff date based on selected filter
        if date_filter == "Today":
            # Only show notes from today
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Week":
            # Show notes from the last 7 days
            cutoff = now - timedelta(days=7)
        elif date_filter == "Month":
            # Show notes from the last 30 days
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        # If we have a cutoff date, filter notes created after that date
        if cutoff:
            query = query.filter(Note.created >= cutoff)

    # STEP 3: Sort the filtered results
    # Different sorting options to organize notes
    if sort_by == "recent":
        # Most recent notes first (default) - sort by ID descending
        query = query.order_by(Note.id.desc())
    elif sort_by == "oldest":
        # Oldest notes first - sort by ID ascending
        query = query.order_by(Note.id.asc())
    elif sort_by == "title":
        # Alphabetical by title (A-Z)
        query = query.order_by(Note.title.asc())
    elif sort_by == "author":
        # Alphabetical by author name (A-Z)
        query = query.order_by(Note.author.asc())

    # Execute the query to get the actual list of notes
    filtered_notes = query.all()

    # STEP 4: Get list of unique authors for the author filter dropdown
    # Query the database to get all distinct author names
    unique_authors = sorted([author[0] for author in db.session.query(Note.author).distinct().all()])

    # STEP 5: Get current user from Supabase
    current_user = get_current_user()

    # STEP 6: Send everything to the template to display
    return render_template(
        "index.html",
        notes=filtered_notes,  # The filtered and sorted notes to display
        classes=CLASSES,  # List of all available classes
        selected_filter=selected_filter,  # Currently selected class filter
        search_query=search_query,  # Current search term
        author_filter=author_filter,  # Currently selected author filter
        date_filter=date_filter,  # Currently selected date range
        sort_by=sort_by,  # Current sort option
        authors=unique_authors,  # List of all authors for the dropdown
        current_user=current_user  # Current Supabase user
    )

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
    # Use .get() with fallback to preserve original values if field is empty
    note.title = request.form.get("title", "").strip() or note.title
    note.body = request.form.get("body", "").strip() or note.body
    note.author = request.form.get("author", "").strip() or note.author
    note.class_code = request.form.get("class", note.class_code)

    # HANDLE ATTACHMENT DELETION
    # Get list of attachment IDs to delete (if any checkboxes were checked)
    attachments_to_delete = request.form.getlist("delete_attachments")
    if attachments_to_delete:
        for attachment_id in attachments_to_delete:
            # Find the attachment in the database
            attachment = Attachment.query.get(int(attachment_id))
            if attachment and attachment.note_id == note_id:
                # Delete the file from the filesystem
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Delete the attachment record from database
                db.session.delete(attachment)

    # HANDLE NEW ATTACHMENT UPLOADS
    # Check if any new files were uploaded
    if 'attachments' in request.files:
        files = request.files.getlist('attachments')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                # Secure the filename
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}_{original_filename}"

                # Save the file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)

                # Create attachment record
                new_attachment = Attachment(
                    note_id=note.id,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_type=file_ext
                )
                db.session.add(new_attachment)

    # Save all changes to the database
    db.session.commit()

    # Redirect back to the main page to show the updated note
    return redirect(url_for("index"))


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
    # The cascade relationship will automatically delete all attachment records
    db.session.delete(note)
    db.session.commit()

    # Redirect back to the main page
    return redirect(url_for("index"))

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
            # Note: If email confirmation is enabled in Supabase, you'll need to verify email
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
                    resp = redirect(url_for("index"))
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
                resp = redirect(url_for("index"))
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
            # Specify redirect URL so the email link goes to our reset password page
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
        # We need to set the access token in the auth client first
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

# FILE DOWNLOAD ROUTE
# Handles secure file downloads for attachments
@app.route("/download/<int:attachment_id>")
def download_file(attachment_id):
    # Find the attachment in the database
    attachment = Attachment.query.get_or_404(attachment_id)

    # Security check: ensure the file path doesn't contain directory traversal attempts
    # The secure_filename function already prevented this during upload, but double-check
    if '..' in attachment.filename or attachment.filename.startswith('/'):
        return "Invalid file path", 400

    # Send the file from the uploads directory
    # as_attachment=True forces download instead of displaying in browser
    # download_name sets the filename user sees (original filename, not the UUID one)
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