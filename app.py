from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta

#new instance of flask as an app
app = Flask(__name__)
NOTES = []
CLASSES = ["CS124", "CS128", "CS173", "MATH221", "MATH231", "ENG100", "CS100", "RHET105", "PHY211", "PHY212"]

# PAGE_SIZE controls how many notes are returned per page for pagination.
# I added pagination support so the UI can load notes incrementally ("Load More").
PAGE_SIZE = 5


def _get_filtered_notes(args):
    """Return the filtered & sorted notes (full list) according to query args.

    NOTE: This helper was added when implementing pagination. The original
    code performed filtering and sorting inline inside `index()`; extracting
    it here keeps `index()` small and allows the new `/notes` endpoint to
    reuse the same logic when returning additional pages.
    """
    selected_filter = args.get("class_filter", "All")
    search_query = args.get("search", "").strip().lower()
    author_filter = args.get("author_filter", "All")
    date_filter = args.get("date_filter", "All")
    sort_by = args.get("sort_by", "recent")

    filtered = NOTES

    if selected_filter and selected_filter != "All":
        filtered = [n for n in filtered if n["class"] == selected_filter]

    if author_filter and author_filter != "All":
        filtered = [n for n in filtered if n["author"] == author_filter]

    if search_query:
        filtered = [
            n for n in filtered
            if search_query in n["title"].lower() or search_query in n["body"].lower()
        ]

    if date_filter and date_filter != "All":
        now = datetime.now()
        if date_filter == "Today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "Week":
            cutoff = now - timedelta(days=7)
        elif date_filter == "Month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        if cutoff:
            filtered = [
                n for n in filtered
                if datetime.strptime(n["created"], "%Y-%m-%d %H:%M") >= cutoff
            ]

    if sort_by == "recent":
        filtered = sorted(filtered, key=lambda n: n["id"], reverse=True)
    elif sort_by == "oldest":
        filtered = sorted(filtered, key=lambda n: n["id"])
    elif sort_by == "title":
        filtered = sorted(filtered, key=lambda n: n["title"].lower())
    elif sort_by == "author":
        filtered = sorted(filtered, key=lambda n: n["author"].lower())

    return filtered

# returns the next ID placed in the last index
def next_id():
    if (NOTES):
        return (NOTES[-1]["id"] + 1)
    else:
        return 1
# main notes page route
@app.route("/notes-feed", methods=["GET", "POST"])
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
    
    # Read filter/sort parameters (for template rendering) and get filtered & sorted list
    selected_filter = request.args.get("class_filter", "All")
    search_query = request.args.get("search", "").strip().lower()
    author_filter = request.args.get("author_filter", "All")
    date_filter = request.args.get("date_filter", "All")
    sort_by = request.args.get("sort_by", "recent")

    filtered_notes = _get_filtered_notes(request.args)

    # Pagination
    # The following block implements server-side pagination. It calculates
    # the requested `page`, slices the filtered list, and sets `has_more`.
    # The template uses `notes` (this page), `has_more` and `total` to render
    # the "Load More" button. Additional pages are fetched from `/notes`.
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

    # ===== STEP 4: Get list of unique authors for the author filter dropdown =====
    # This creates a dropdown showing all authors who have posted notes
    unique_authors = sorted(list(set([n["author"] for n in NOTES])))

    # ===== STEP 5: Send everything to the template to display =====
    return render_template(
        "index.html",
        notes=notes_page,  # The paginated notes to display
        page=page,
        has_more=has_more,
        total=total,
        classes=CLASSES,  # List of all available classes
        selected_filter=selected_filter,  # Currently selected class filter
        search_query=search_query,  # Current search term
        author_filter=author_filter,  # Currently selected author filter
        date_filter=date_filter,  # Currently selected date range
        sort_by=sort_by,  # Current sort option
        authors=unique_authors  # List of all authors for the dropdown
    )



@app.route("/notes")
def notes_endpoint():
    """Return a page of notes as JSON (HTML fragment + has_more flag).

    This endpoint was added to support the client-side "Load More" UI. It
    accepts the same filter/sort query parameters as `/` plus a `page` param
    and returns an HTML fragment (rendered `notes_fragment.html`) along
    with a boolean `has_more` indicating whether more pages are available.
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

    # Render only the notes HTML fragment
    html = render_template("notes_fragment.html", notes=notes_page, classes=CLASSES)
    return jsonify({"html": html, "has_more": has_more})

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

@app.route("/")
def home():
    return render_template("homev3.html")

if __name__ == "__main__":
    app.run(debug=True)