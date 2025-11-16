from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta

#new instance of flask as an app
app = Flask(__name__)
NOTES = []
CLASSES = ["CS124", "CS128", "CS173", "MATH221", "MATH231", "ENG100", "CS100", "RHET105", "PHY211", "PHY212"]

# returns the next ID placed in the last index
def next_id():
    if (NOTES):
        return (NOTES[-1]["id"] + 1)
    else:
        return 1
# reroutes to the main page
@app.route("/", methods=["GET", "POST"])
def index():
    # gives server information of any post to be made 
    if request.method == "POST":
        author = request.form.get("author", "").strip() or "Anonymous"
        title = request.form.get("title", "").strip() or "Untitled"
        body = request.form.get("body", "").strip()
        selected_class = request.form.get("class", "General")
        if body:
            NOTES.append({
                "id": next_id(),
                "author": author,
                "title": title,
                "body": body,
                "class": selected_class,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        # returns index.html (the main page)
        return redirect(url_for("index"))
    
    # ===== STEP 1: Get all filter parameters from the URL =====
    # These are passed as query parameters when user submits the filter form
    selected_filter = request.args.get("class_filter", "All")  # Which class to show
    search_query = request.args.get("search", "").strip().lower()  # Search term
    author_filter = request.args.get("author_filter", "All")  # Which author to show
    date_filter = request.args.get("date_filter", "All")  # Time range filter
    sort_by = request.args.get("sort_by", "recent")  # How to sort the results

    # ===== STEP 2: Start with all notes, then apply filters one by one =====
    filtered_notes = NOTES

    # --- Filter by class (e.g., only show CS124 notes) ---
    if selected_filter and selected_filter != "All":
        filtered_notes = [n for n in filtered_notes if n["class"] == selected_filter]

    # --- Filter by author (e.g., only show notes from "John") ---
    if author_filter and author_filter != "All":
        filtered_notes = [n for n in filtered_notes if n["author"] == author_filter]

    # --- Filter by search term (looks in both title and body) ---
    if search_query:
        filtered_notes = [
            n for n in filtered_notes
            if search_query in n["title"].lower() or search_query in n["body"].lower()
        ]

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
            cutoff = None  # Show all notes

        # If we have a cutoff date, filter notes created after that date
        if cutoff:
            # Parse each note's creation date and compare it to the cutoff
            filtered_notes = [
                n for n in filtered_notes
                if datetime.strptime(n["created"], "%Y-%m-%d %H:%M") >= cutoff
            ]

    # ===== STEP 3: Sort the filtered results =====
    # Different sorting options to organize notes
    if sort_by == "recent":
        # Most recent notes first (default)
        filtered_notes = sorted(filtered_notes, key=lambda n: n["id"], reverse=True)
    elif sort_by == "oldest":
        # Oldest notes first
        filtered_notes = sorted(filtered_notes, key=lambda n: n["id"])
    elif sort_by == "title":
        # Alphabetical by title (A-Z)
        filtered_notes = sorted(filtered_notes, key=lambda n: n["title"].lower())
    elif sort_by == "author":
        # Alphabetical by author name (A-Z)
        filtered_notes = sorted(filtered_notes, key=lambda n: n["author"].lower())

    # ===== STEP 4: Get list of unique authors for the author filter dropdown =====
    # This creates a dropdown showing all authors who have posted notes
    unique_authors = sorted(list(set([n["author"] for n in NOTES])))

    # ===== STEP 5: Send everything to the template to display =====
    return render_template(
        "index.html",
        notes=filtered_notes,  # The filtered and sorted notes to display
        classes=CLASSES,  # List of all available classes
        selected_filter=selected_filter,  # Currently selected class filter
        search_query=search_query,  # Current search term
        author_filter=author_filter,  # Currently selected author filter
        date_filter=date_filter,  # Currently selected date range
        sort_by=sort_by,  # Current sort option
        authors=unique_authors  # List of all authors for the dropdown
    )

# ===== EDIT NOTE ROUTE =====
# Handles updating an existing note
@app.route("/edit/<int:note_id>", methods=["POST"])
def edit_note(note_id):
    # Find the note with the matching ID in the NOTES list
    for note in NOTES:
        if note["id"] == note_id:
            # Update the note's fields with new data from the form
            # Use .get() with fallback to preserve original values if field is empty
            note["title"] = request.form.get("title", "").strip() or note["title"]
            note["body"] = request.form.get("body", "").strip() or note["body"]
            note["author"] = request.form.get("author", "").strip() or note["author"]
            note["class"] = request.form.get("class", note["class"])
            break

    # Redirect back to the main page to show the updated note
    return redirect(url_for("index"))

# ===== DELETE NOTE ROUTE =====
# Handles removing a note from the system
@app.route("/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    global NOTES
    # Filter out the note with the matching ID (removes it from the list)
    NOTES = [note for note in NOTES if note["id"] != note_id]

    # Redirect back to the main page
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)