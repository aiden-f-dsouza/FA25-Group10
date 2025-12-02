from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
import requests

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
    tag_filter = args.get("tag_filter", "All")
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

    # --- Filter by tag (if provided) ---
    if tag_filter and tag_filter != "All":
        tf = tag_filter.lower()
        filtered = [n for n in filtered if any(t.lower() == tf for t in n.get("tags", []))]

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
        tag_filter = args.get("tag_filter", "All")

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
    elif sort_by == "most_liked":
        # Sort by number of likes (descending)
        filtered = sorted(filtered, key=lambda n: n.get("likes", 0), reverse=True)
    elif sort_by == "most_commented":
        # Sort by number of comments (descending)
        filtered = sorted(filtered, key=lambda n: len(n.get("comments", [])), reverse=True)
    elif sort_by == "popular":
        # Popularity: primarily by comments, then by likes
        filtered = sorted(
            filtered,
            key=lambda n: (len(n.get("comments", [])), n.get("likes", 0), n.get("id", 0)),
            reverse=True,
        )

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
        # parse tags from comma-separated input; normalize by trimming
        raw_tags = request.form.get("tags", "")
        tags = []
        if raw_tags:
            # split on comma and also accept spaces; keep original casing trimmed
            parts = [p.strip() for p in raw_tags.replace('#', '').split(',')]
            tags = [p for p in parts if p]
        import re
        def extract_hashtags(text):
            return [tag[1:] for tag in re.findall(r"#[\w-]+", text)]

        hashtags = set()
        hashtags.update(extract_hashtags(body))
        hashtags.update([t for t in tags if t.startswith('#')])
        hashtags.update([t for t in tags if t])
        hashtags = [h.lstrip('#') for h in hashtags if h]

        if body:
            NOTES.append({
                "id": next_id(),
                "author": author,
                "title": title,
                "body": body,
                "class": selected_class,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                # initialize social fields for future sorting/features
                "likes": 0,
                "comments": [],  # list of comment dicts: {author, body, created}
                "tags": tags,
                "hashtags": hashtags,
            })
        # returns index.html (the main page)
        return redirect(url_for("index"))
    
    # Read filter/sort parameters (for template rendering) and get filtered & sorted list
    selected_filter = request.args.get("class_filter", "All")
    search_query = request.args.get("search", "").strip().lower()
    author_filter = request.args.get("author_filter", "All")
    tag_filter = request.args.get("tag_filter", "All")
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

    # Build tag cloud (tag -> count)
    tag_counts = {}
    for n in NOTES:
        for t in n.get("tags", []):
            key = t.strip()
            if not key:
                continue
            tag_counts[key] = tag_counts.get(key, 0) + 1
    # Sorted list of (tag, count) descending
    tags_sorted = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

    # ===== STEP 5: Send everything to the template to display =====
    return render_template(
        "indexv2.html",
        notes=notes_page,  # The paginated notes to display
        page=page,
        has_more=has_more,
        total=total,
        tag_filter=tag_filter,
        classes=CLASSES,  # List of all available classes
        selected_filter=selected_filter,  # Currently selected class filter
        search_query=search_query,  # Current search term
        author_filter=author_filter,  # Currently selected author filter
        date_filter=date_filter,  # Currently selected date range
        sort_by=sort_by,  # Current sort option
        authors=unique_authors,  # List of all authors for the dropdown
        tags=tags_sorted,
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


# Endpoint to increment likes for a note
@app.route("/like/<int:note_id>", methods=["POST"])
def like_note(note_id):
    for note in NOTES:
        if note["id"] == note_id:
            note["likes"] = note.get("likes", 0) + 1
            break
    # Redirect back to the referring page if available
    return redirect(request.referrer or url_for("index"))


# Endpoint to add a comment to a note
@app.route("/comment/<int:note_id>", methods=["POST"])
def add_comment(note_id):
    author = request.form.get("comment_author", "Anonymous").strip() or "Anonymous"
    body = request.form.get("comment_body", "").strip()
    if not body:
        return redirect(request.referrer or url_for("index"))

    for note in NOTES:
        if note["id"] == note_id:
            note.setdefault("comments", []).append({
                "author": author,
                "body": body,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            break

    return redirect(request.referrer or url_for("index"))

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
            # update tags if provided (comma-separated)
            raw_tags = request.form.get("tags")
            if raw_tags is not None:
                parts = [p.strip() for p in raw_tags.split(',')]
                note["tags"] = [p for p in parts if p]
            # update hashtags from body and tags
            import re
            def extract_hashtags(text):
                return [tag[1:] for tag in re.findall(r"#[\w-]+", text)]
            hashtags = set()
            hashtags.update(extract_hashtags(note["body"]))
            hashtags.update([t for t in note["tags"] if t.startswith('#')])
            hashtags.update([t for t in note["tags"] if t])
            note["hashtags"] = [h.lstrip('#') for h in hashtags if h]
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

@app.route("/summarizer")
def summarizer():
    return render_template("summarizer.html")

@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        notes = data.get("notes", "").strip()

        if not notes:
            return jsonify({"error": "No notes provided"}), 400

        # Simple extractive summarization (free, no API needed)
        # Split into sentences more carefully to avoid splitting on decimals
        import re

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

            # Penalize repetitive phrases (like "dominated the global market")
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
        # This ensures actual summarization, not just slight reduction
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

        # Format with bullet points for better readability - use actual line breaks
        formatted_parts = ['• ' + part for part in summary_parts]
        summary_text = '\n'.join(formatted_parts)

        # Only enforce max length if summary is unreasonably long (like 2000+ chars)
        # But allow it to scale with input - aim for 40-50% character reduction minimum
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

if __name__ == "__main__":
    app.run(debug=True)