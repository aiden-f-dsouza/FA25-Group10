// ============================================
// NOTES PAGE JAVASCRIPT
// Dependencies: Choices.js, theme-toggle.js
// ============================================

// === GLOBAL VARIABLES ===

let currentPage = 1;
let CLASSES = [];
let COURSES_DICT = {};
let SUBJECTS = [];
let subjectChoice, numberChoice;
let createSubjectChoice, createNumberChoice;

// === UTILITY FUNCTIONS ===

/**
 * Toggles the edit form visibility for a note
 * @param {number} noteId - The ID of the note to edit
 */
function toggleEdit(noteId) {
  const editForm = document.getElementById('edit-form-' + noteId);
  const noteContent = document.getElementById('note-content-' + noteId);
  editForm.classList.toggle('active');
  noteContent.classList.toggle('editing');
}

// === MODAL FUNCTIONS ===

/**
 * Opens the create note modal
 */
function openModal() {
  const modal = document.getElementById('note-modal');
  modal.classList.add('active');
  document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

/**
 * Closes the create note modal and resets form
 */
function closeModal() {
  const modal = document.getElementById('note-modal');
  modal.classList.remove('active');
  document.body.style.overflow = ''; // Restore scrolling

  // Clear the form
  const form = document.getElementById('create-note-form');
  form.reset();
}

// === PAGINATION ===

/**
 * Loads the next page of notes via AJAX
 */
async function loadMore() {
  currentPage += 1;
  const form = document.querySelector('.filter-form');
  const params = new URLSearchParams(new FormData(form));
  params.set('page', currentPage);
  const url = '/notes?' + params.toString();

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    const container = document.getElementById('notes-container');
    container.insertAdjacentHTML('beforeend', data.html);

    if (!data.has_more) {
      const btn = document.getElementById('load-more');
      if (btn) btn.style.display = 'none';
    }
  } catch (err) {
    console.error('Failed to load more notes', err);
  }
}

// === COURSE FILTER LOGIC ===

/**
 * Returns course data from global COURSES_DICT variable
 * Data is already structured from the backend JSON file
 * @returns {Object} - { subjects: Array, classesBySubject: Object }
 */
function parseClasses() {
  return {
    subjects: SUBJECTS,
    classesBySubject: COURSES_DICT
  };
}

/**
 * Populates the subject dropdown with unique subjects
 * @param {string} currentFilter - The currently selected class filter (e.g., "CS124")
 */
function populateSubjects(currentFilter) {
  const { subjects } = parseClasses();
  const subjectSelect = document.getElementById('subject-select');

  let currentSubject = "";

  // Extract subject from current filter (e.g., "CS124" -> "CS")
  if (currentFilter && currentFilter !== "All") {
    const match = currentFilter.match(/^([A-Z]+)(\d+)$/);
    if (match) {
      currentSubject = match[1];
    }
  }

  // Clear existing options (except "All Subjects")
  while (subjectSelect.options.length > 1) {
    subjectSelect.remove(1);
  }

  // Add each subject as an option
  subjects.forEach(subject => {
    const option = document.createElement('option');
    option.value = subject;
    option.textContent = subject;

    // Set as selected if it matches current filter
    if (subject === currentSubject) {
      option.selected = true;
    }

    subjectSelect.appendChild(option);
  });
}

/**
 * Updates the number dropdown based on selected subject
 * @param {boolean} preserveSelection - Whether to preserve current selection
 * @param {string} currentFilter - The currently selected class filter
 */
function updateNumberDropdown(preserveSelection, currentFilter) {
  const { classesBySubject } = parseClasses();
  const subjectSelect = document.getElementById('subject-select');
  const numberSelect = document.getElementById('number-select');

  const selectedSubject = subjectSelect.value;
  let currentNumber = "";

  if (preserveSelection && currentFilter && currentFilter !== "All") {
    const match = currentFilter.match(/^([A-Z]+)(\d+)$/);
    if (match) {
      currentNumber = match[2];
    }
  }

  // Clear number dropdown
  numberSelect.innerHTML = '<option value="">All Numbers</option>';

  if (selectedSubject) {
    // Get numbers for selected subject
    const numbers = classesBySubject[selectedSubject] || [];
    numbers.sort((a, b) => parseInt(a) - parseInt(b));

    // Populate number dropdown
    numbers.forEach(number => {
      const option = document.createElement('option');
      option.value = number;
      option.textContent = number;

      // Set as selected if it matches current filter
      if (number === currentNumber) {
        option.selected = true;
      }

      numberSelect.appendChild(option);
    });
  }
}

/**
 * Applies the selected class filter and submits the form
 */
function applyClassFilter() {
  const subjectSelect = document.getElementById('subject-select');
  const numberSelect = document.getElementById('number-select');
  const hiddenInput = document.getElementById('class-filter-hidden');
  const form = document.getElementById('course-filter-form');

  const selectedSubject = subjectSelect.value;
  const selectedNumber = numberSelect.value;

  // Combine subject + number to create class filter
  if (selectedSubject && selectedNumber) {
    hiddenInput.value = selectedSubject + selectedNumber;  // e.g., "CS124"
  } else if (selectedSubject) {
    // If only subject selected, show all classes for that subject
    hiddenInput.value = 'All';
  } else {
    hiddenInput.value = 'All';
  }

  // Submit the form to apply filter
  form.submit();
}

/**
 * Handles subject dropdown change event
 */
function handleSubjectChange() {
  const subjectSelect = document.getElementById('subject-select');
  const numberSelect = document.getElementById('number-select');

  updateNumberDropdown(false, null);

  // Destroy and reinitialize number Choices.js to reflect new options
  numberChoice.destroy();
  numberChoice = new Choices(numberSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Type to search numbers...',
    itemSelectText: '',
    shouldSort: false,
    searchResultLimit: 20,
    removeItemButton: false
  });

  // If "All Subjects" selected, clear and submit
  if (!subjectSelect.value) {
    document.getElementById('class-filter-hidden').value = 'All';
    document.getElementById('course-filter-form').submit();
  }
}

/**
 * Handles number dropdown change event
 */
function handleNumberChange() {
  const subjectSelect = document.getElementById('subject-select');
  const numberSelect = document.getElementById('number-select');

  // Update the hidden class filter value
  if (!numberSelect.value && subjectSelect.value) {
    document.getElementById('class-filter-hidden').value = 'All';
  } else {
    const selectedSubject = subjectSelect.value;
    const selectedNumber = numberSelect.value;
    if (selectedSubject && selectedNumber) {
      document.getElementById('class-filter-hidden').value = selectedSubject + selectedNumber;
    } else {
      document.getElementById('class-filter-hidden').value = 'All';
    }
  }

  // Use AJAX instead of form submit
  applyFiltersAjax();
}

// === MODAL DROPDOWN HANDLERS ===

/**
 * Initialize dropdowns in the Create Note modal
 */
function initializeCreateModalDropdowns() {
  const createSubjectSelect = document.getElementById('create-subject-select');
  const createNumberSelect = document.getElementById('create-number-select');
  if (!createSubjectSelect || !createNumberSelect) return;

  createSubjectChoice = new Choices(createSubjectSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Search subjects...',
    itemSelectText: '',
    shouldSort: false
  });

  createNumberChoice = new Choices(createNumberSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Search numbers...',
    itemSelectText: '',
    shouldSort: false
  });

  createSubjectSelect.addEventListener('change', function() {
    const numbers = COURSES_DICT[this.value] || [];
    createNumberChoice.clearStore();
    createNumberChoice.setChoices([
      { value: '', label: 'Number', selected: true },
      ...numbers.sort((a, b) => a - b).map(num => ({value: num.toString(), label: num.toString()}))
    ], 'value', 'label', true);
  });

  createNumberSelect.addEventListener('change', function() {
    const subject = createSubjectSelect.value;
    const number = this.value;
    document.getElementById('create-class-hidden').value = subject && number ? subject + number : '';
  });
}

/**
 * Initialize dropdowns in Edit Note modals
 */
function initializeEditModalDropdowns() {
  document.querySelectorAll('.edit-subject-select').forEach(select => {
    const noteId = select.dataset.noteId;
    const numberSelect = document.getElementById(`edit-number-${noteId}`);
    const hiddenInput = document.getElementById(`edit-class-hidden-${noteId}`);
    const currentClassCode = hiddenInput.value;

    const match = currentClassCode.match(/^([A-Z]+)(\d+)$/);
    let currentSubject = '', currentNumber = '';
    if (match) {
      currentSubject = match[1];
      currentNumber = match[2];
    }

    if (currentSubject) {
      select.value = currentSubject;
      const numbers = COURSES_DICT[currentSubject] || [];
      numberSelect.innerHTML = '<option value="">Number</option>';
      numbers.sort((a, b) => a - b).forEach(num => {
        const option = document.createElement('option');
        option.value = num.toString();
        option.textContent = num.toString();
        if (num.toString() === currentNumber) option.selected = true;
        numberSelect.appendChild(option);
      });
    }

    select.addEventListener('change', function() {
      const numbers = COURSES_DICT[this.value] || [];
      numberSelect.innerHTML = '<option value="">Number</option>';
      numbers.sort((a, b) => a - b).forEach(num => {
        const option = document.createElement('option');
        option.value = num.toString();
        option.textContent = num.toString();
        numberSelect.appendChild(option);
      });
    });

    numberSelect.addEventListener('change', function() {
      const subject = select.value;
      const number = this.value;
      hiddenInput.value = subject && number ? subject + number : currentClassCode;
    });
  });
}

// === INITIALIZATION ===

/**
 * Initializes all page functionality when DOM is ready
 * @param {number} initialPage - The current page number
 * @param {Array} classes - Array of available class names
 * @param {Object} coursesDict - Course dictionary for two-dropdown system
 * @param {Array} subjects - List of all subjects
 * @param {string} selectedFilter - Currently selected class filter
 */
function initializePage(initialPage, classes, coursesDict, subjects, selectedFilter) {
  // Set initial values from template
  currentPage = initialPage;
  CLASSES = classes;
  COURSES_DICT = coursesDict;
  SUBJECTS = subjects;

  // Populate course filter dropdowns
  populateSubjects(selectedFilter);
  updateNumberDropdown(true, selectedFilter);

  // Initialize Choices.js on filter dropdowns
  const subjectSelect = document.getElementById('subject-select');
  subjectChoice = new Choices(subjectSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Search subjects...',
    itemSelectText: '',
    shouldSort: false
  });

  const numberSelect = document.getElementById('number-select');
  numberChoice = new Choices(numberSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Search numbers...',
    itemSelectText: '',
    shouldSort: false
  });

  // Add event listeners
  subjectSelect.addEventListener('change', handleSubjectChange);
  numberSelect.addEventListener('change', handleNumberChange);

  // Initialize create and edit modal dropdowns
  initializeCreateModalDropdowns();
  initializeEditModalDropdowns();

  // Modal event listeners
  const modal = document.getElementById('note-modal');
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        closeModal();
      }
    });
  }

  // Close modal with Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
      closeModal();
    }
  });

  // Add AJAX filter listeners to date and sort dropdowns
  const dateFilterSelect = document.querySelector('select[name="date_filter"]');
  if (dateFilterSelect) {
    dateFilterSelect.addEventListener('change', function(e) {
      e.preventDefault();
      applyFiltersAjax();
    });
  }

  const sortBySelect = document.querySelector('select[name="sort_by"]');
  if (sortBySelect) {
    sortBySelect.addEventListener('change', function(e) {
      e.preventDefault();
      applyFiltersAjax();
    });
  }

  // Update course filter to use AJAX
  const courseFilterForm = document.getElementById('course-filter-form');
  if (courseFilterForm) {
    courseFilterForm.addEventListener('submit', function(e) {
      e.preventDefault();
      applyFiltersAjax();
    });
  }
}

// === AUTO-INITIALIZATION ===

document.addEventListener('DOMContentLoaded', function() {
  // Get initial values from data attributes set by template
  const pageData = document.getElementById('page-data');
  const initialPage = parseInt(pageData.dataset.page || '1');
  const classes = JSON.parse(pageData.dataset.classes || '[]');
  const coursesDict = JSON.parse(pageData.dataset.coursesDict || '{}');
  const subjects = JSON.parse(pageData.dataset.subjects || '[]');
  const selectedFilter = pageData.dataset.selectedFilter || 'All';

  initializePage(initialPage, classes, coursesDict, subjects, selectedFilter);
});

// === UTILITY FUNCTIONS ===

/**
 * Escapes HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Formats relative time (e.g., "2 min ago")
 * @param {string} dateString - ISO date string
 * @returns {string} Relative time string
 */
function formatRelativeTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = (now - date) / 1000; // seconds

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) {
    const hours = Math.floor(diff / 3600);
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  }
  const days = Math.floor(diff / 86400);
  if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`;

  // Format as date
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

// === TOAST NOTIFICATION SYSTEM ===

/**
 * Shows a toast notification
 * @param {string} message - The message to display
 * @param {string} type - 'success', 'error', or 'info'
 * @param {number} duration - Auto-dismiss duration in ms (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) {
    console.warn('Toast container not found');
    return;
  }

  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  // Icon based on type
  let icon = '';
  if (type === 'success') {
    icon = '<i class="ph-fill ph-check-circle"></i>';
  } else if (type === 'error') {
    icon = '<i class="ph-fill ph-warning-circle"></i>';
  } else {
    icon = '<i class="ph-fill ph-info"></i>';
  }

  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-content">${escapeHtml(message)}</span>
    <button class="toast-close" onclick="dismissToast(this)">
      <i class="ph ph-x"></i>
    </button>
  `;

  // Add to container
  container.appendChild(toast);

  // Auto-dismiss after duration
  if (duration > 0) {
    setTimeout(() => {
      dismissToast(toast.querySelector('.toast-close'));
    }, duration);
  }
}

/**
 * Dismisses a toast notification
 * @param {HTMLElement} closeBtn - The close button element
 */
function dismissToast(closeBtn) {
  const toast = closeBtn.closest('.toast');
  if (!toast) return;

  // Add removing animation
  toast.classList.add('removing');

  // Remove from DOM after animation
  setTimeout(() => {
    toast.remove();
  }, 300);
}

// === LIKE/UNLIKE WITH OPTIMISTIC UPDATE ===

/**
 * Toggles like for a note with optimistic UI update
 * @param {number} noteId - The note ID to like/unlike
 * @param {HTMLElement} button - The like button element
 */
async function toggleLike(noteId, button) {
  // Get current state
  const isLiked = button.classList.contains('liked');
  const icon = button.querySelector('i');
  const countSpan = button.querySelector('.like-count');
  const currentCount = parseInt(countSpan.textContent) || 0;

  // Optimistic update (instant UI change)
  if (isLiked) {
    // Unlike
    button.classList.remove('liked');
    icon.classList.remove('ph-fill');
    icon.classList.add('ph');
    countSpan.textContent = Math.max(0, currentCount - 1);
  } else {
    // Like
    button.classList.add('liked');
    icon.classList.remove('ph');
    icon.classList.add('ph-fill');
    countSpan.textContent = currentCount + 1;
  }

  // Disable button during request
  button.disabled = true;

  try {
    const response = await fetch(`/api/like/${noteId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Failed to toggle like');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to toggle like');
    }

    // Verify server state matches optimistic update
    // If not, sync with server
    if (data.liked !== !isLiked) {
      console.warn('Like state mismatch, syncing with server');
      if (data.liked) {
        button.classList.add('liked');
        icon.classList.remove('ph');
        icon.classList.add('ph-fill');
      } else {
        button.classList.remove('liked');
        icon.classList.remove('ph-fill');
        icon.classList.add('ph');
      }
    }

    // Update count with server value
    countSpan.textContent = data.like_count;

    // Update like count in metadata (at top of note card)
    const metaTags = document.querySelectorAll(`#note-${noteId} .note-meta .meta-tag`);
    metaTags.forEach(tag => {
      if (tag.innerHTML.includes('ph-heart')) {
        // Preserve the filled/unfilled state based on whether user liked it
        const heartClass = data.liked ? 'ph-fill ph-heart' : 'ph ph-heart';
        tag.innerHTML = `<i class="${heartClass}"></i> ${data.like_count}`;
      }
    });

  } catch (error) {
    console.error('Error toggling like:', error);

    // Rollback optimistic update on error
    if (isLiked) {
      // Was liked, restore liked state
      button.classList.add('liked');
      icon.classList.remove('ph');
      icon.classList.add('ph-fill');
      countSpan.textContent = currentCount;
    } else {
      // Was not liked, restore unliked state
      button.classList.remove('liked');
      icon.classList.remove('ph-fill');
      icon.classList.add('ph');
      countSpan.textContent = currentCount;
    }

    showToast('Failed to update like. Please try again.', 'error');
  } finally {
    // Re-enable button
    button.disabled = false;
  }
}

// === COMMENT OPERATIONS ===

/**
 * Adds a comment via AJAX
 * @param {Event} event - Form submit event
 * @param {HTMLFormElement} form - The comment form
 * @param {number} noteId - The note ID
 */
async function addCommentAjax(event, form, noteId) {
  event.preventDefault();

  const input = form.querySelector('input[name="comment_body"]');
  const body = input.value.trim();

  if (!body) {
    showToast('Please enter a comment', 'error');
    return;
  }

  // Disable form during submission
  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  input.disabled = true;

  try {
    const response = await fetch(`/api/comment/${noteId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ comment_body: body })
    });

    if (!response.ok) {
      throw new Error('Failed to add comment');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to add comment');
    }

    // Clear input
    input.value = '';

    // Add comment to DOM
    const comment = data.comment;
    const commentsListContainer = document.querySelector(`.comments-list-${noteId}`);

    // Create comment HTML
    const commentHTML = `
      <div class="comment-item" id="comment-${comment.id}" style="animation: fadeIn 0.3s ease;">
        <div class="comment-header">
          <span class="comment-author">${escapeHtml(comment.author)}</span>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="comment-date">${comment.created_relative}</span>
            ${comment.can_edit ? `
              <button onclick="toggleEditComment(${comment.id})" class="btn-small comment-edit-btn">
                <i class="ph ph-pencil"></i> Edit
              </button>
            ` : ''}
            ${comment.can_delete ? `
              <button onclick="deleteCommentAjax(${comment.id}, ${noteId})" class="btn-small comment-delete-btn">
                <i class="ph ph-trash"></i> Delete
              </button>
            ` : ''}
          </div>
        </div>
        <div class="comment-view-${comment.id} comment-body">${escapeHtml(comment.body)}</div>
        <div class="comment-edit-${comment.id}" style="display: none;">
          <form onsubmit="editCommentAjax(event, ${comment.id})" style="display: flex; gap: 8px; align-items: center; margin-top: 8px;">
            <input type="text" name="comment_body" value="${escapeHtml(comment.body)}" class="comment-edit-input" required>
            <button type="submit" class="btn-small btn-edit" style="padding: 6px 12px; font-size: 12px;">
              <i class="ph ph-floppy-disk"></i> Save
            </button>
            <button type="button" onclick="toggleEditComment(${comment.id})" class="btn-small btn-cancel" style="padding: 6px 12px; font-size: 12px;">
              <i class="ph ph-x"></i> Cancel
            </button>
          </form>
        </div>
      </div>
    `;

    // Insert comment
    if (commentsListContainer) {
      commentsListContainer.insertAdjacentHTML('beforeend', commentHTML);
    } else {
      // No comments exist yet - create the entire comments section
      const noteCard = document.querySelector(`#note-${noteId}`);
      const commentForm = noteCard.querySelector('form[onsubmit*="addCommentAjax"]');

      const commentsContainerHTML = `
        <div class="comments-container" style="animation: fadeIn 0.3s ease;">
          <div class="comments-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
            <div class="comments-title" style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-weight: 600; font-size: 14px;">
              <i class="ph ph-chat-circle"></i> Comments (${data.comment_count})
            </div>
            <button onclick="toggleComments(${noteId})" class="comments-toggle-btn" style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 13px; padding: 4px 8px; border-radius: 4px; transition: all 0.2s ease;">
              <span class="toggle-text-${noteId}">Hide comments</span>
            </button>
          </div>
          <div class="comments-list-${noteId}">
            ${commentHTML}
          </div>
        </div>
      `;

      commentForm.insertAdjacentHTML('beforebegin', commentsContainerHTML);
    }

    // Update comment count in metadata
    const metaTags = document.querySelectorAll(`#note-${noteId} .note-meta .meta-tag`);
    metaTags.forEach(tag => {
      if (tag.innerHTML.includes('ph-chat-circle')) {
        tag.innerHTML = `<i class="ph ph-chat-circle"></i> ${data.comment_count}`;
      }
    });

    // Show success toast
    showToast('Comment posted!', 'success');

    // Show mention notification if mentions were created
    if (data.mentions_created > 0) {
      showToast(`${data.mentions_created} user(s) mentioned`, 'info', 2000);
    }

  } catch (error) {
    console.error('Error adding comment:', error);
    showToast('Failed to add comment. Please try again.', 'error');
  } finally {
    // Re-enable form
    submitBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

/**
 * Edits a comment via AJAX
 * @param {Event} event - Form submit event
 * @param {number} commentId - The comment ID
 */
async function editCommentAjax(event, commentId) {
  event.preventDefault();

  const form = event.target;
  const input = form.querySelector('input[name="comment_body"]');
  const body = input.value.trim();

  if (!body) {
    showToast('Comment cannot be empty', 'error');
    return;
  }

  // Store original value for rollback
  const viewDiv = document.querySelector(`.comment-view-${commentId}`);
  const originalBody = viewDiv.textContent;

  // Disable form
  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  input.disabled = true;

  try {
    const response = await fetch(`/api/comment/${commentId}/edit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ comment_body: body })
    });

    if (!response.ok) {
      throw new Error('Failed to edit comment');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to edit comment');
    }

    // Update comment body
    viewDiv.textContent = data.comment.body;

    // Toggle back to view mode
    toggleEditComment(commentId);

    showToast('Comment updated!', 'success');

  } catch (error) {
    console.error('Error editing comment:', error);
    showToast('Failed to update comment. Please try again.', 'error');
  } finally {
    submitBtn.disabled = false;
    input.disabled = false;
  }
}

/**
 * Deletes a comment via AJAX with confirmation
 * @param {number} commentId - The comment ID
 * @param {number} noteId - The note ID
 */
async function deleteCommentAjax(commentId, noteId) {
  if (!confirm('Delete this comment?')) {
    return;
  }

  const commentElement = document.querySelector(`#comment-${commentId}`);

  try {
    const response = await fetch(`/api/comment/${commentId}/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Failed to delete comment');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to delete comment');
    }

    // Fade out animation
    commentElement.style.animation = 'fadeOut 0.3s ease forwards';

    setTimeout(() => {
      commentElement.remove();

      // Update comment count in metadata
      const metaTags = document.querySelectorAll(`#note-${noteId} .note-meta .meta-tag`);
      metaTags.forEach(tag => {
        if (tag.innerHTML.includes('ph-chat-circle')) {
          tag.innerHTML = `<i class="ph ph-chat-circle"></i> ${data.comment_count}`;
        }
      });

      // If no comments left, hide the entire comments section
      if (data.comment_count === 0) {
        const commentsContainer = document.querySelector(`#note-${noteId} .comments-container`);
        if (commentsContainer) {
          commentsContainer.style.animation = 'fadeOut 0.3s ease forwards';
          setTimeout(() => {
            commentsContainer.remove();
          }, 300);
        }
      }

      showToast('Comment deleted', 'success');
    }, 300);

  } catch (error) {
    console.error('Error deleting comment:', error);
    showToast('Failed to delete comment. Please try again.', 'error');
  }
}

// === DELETE NOTE ===

/**
 * Deletes a note via AJAX with confirmation and fade-out
 * @param {number} noteId - The note ID to delete
 */
async function deleteNoteAjax(noteId) {
  if (!confirm('Are you sure you want to delete this note?')) {
    return;
  }

  const noteCard = document.querySelector(`#note-${noteId}`);

  try {
    const response = await fetch(`/api/note/${noteId}/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Failed to delete note');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to delete note');
    }

    // Fade out animation
    noteCard.style.animation = 'fadeOut 0.4s ease forwards';

    setTimeout(() => {
      noteCard.remove();
      showToast('Note deleted successfully', 'success');
    }, 400);

  } catch (error) {
    console.error('Error deleting note:', error);
    showToast('Failed to delete note. Please try again.', 'error');
  }
}

// === FILTER OPERATIONS ===

/**
 * Applies filters via AJAX without changing URL
 * @param {Event} event - Form submit event (optional)
 */
async function applyFiltersAjax(event) {
  if (event) {
    event.preventDefault();
  }

  // Get all filter values
  const classFilter = document.querySelector('input[name="class_filter"]')?.value || 'All';
  const searchQuery = document.querySelector('input[name="search"]')?.value || '';
  const tagFilter = document.querySelector('select[name="tag_filter"]')?.value || 'All';
  const dateFilter = document.querySelector('select[name="date_filter"]')?.value || 'All';
  const sortBy = document.querySelector('select[name="sort_by"]')?.value || 'recent';

  // Build query params
  const params = new URLSearchParams({
    class_filter: classFilter,
    search: searchQuery,
    tag_filter: tagFilter,
    date_filter: dateFilter,
    sort_by: sortBy,
    page: 1
  });

  // Show loading state
  const notesContainer = document.getElementById('notes-container');
  const loadingHTML = `
    <div style="text-align: center; padding: 60px 0; color: var(--text-tertiary);">
      <i class="ph ph-spinner" style="font-size: 48px; animation: spin 1s linear infinite;"></i>
      <div style="margin-top: 16px;">Loading notes...</div>
    </div>
  `;
  notesContainer.innerHTML = loadingHTML;

  try {
    const response = await fetch(`/api/notes?${params.toString()}`);

    if (!response.ok) {
      throw new Error('Failed to load notes');
    }

    const data = await response.json();

    // Update notes container
    notesContainer.innerHTML = data.html;

    // Update "Load More" button visibility
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      loadMoreBtn.style.display = data.has_more ? 'inline-block' : 'none';
    }

    // Reset current page
    currentPage = 1;

    // Scroll to top of notes feed smoothly
    const notesFeed = document.getElementById('notes-feed');
    if (notesFeed) {
      notesFeed.scrollIntoView({ behavior: 'smooth' });
    }

  } catch (error) {
    console.error('Error loading notes:', error);
    notesContainer.innerHTML = `
      <div class="empty-state">
        <div style="font-size: 48px; margin-bottom: 16px;">
          <i class="ph ph-warning-circle" style="font-size: 48px; color: var(--accent-terracotta);"></i>
        </div>
        <div>Failed to load notes. Please try again.</div>
      </div>
    `;
    showToast('Failed to load notes. Please try again.', 'error');
  }
}
