// ============================================
// NOTES PAGE JAVASCRIPT
// Dependencies: Choices.js, theme-toggle.js
// ============================================

// === GLOBAL VARIABLES ===

let currentPage = 1;
let CLASSES = [];
let subjectChoice, numberChoice;

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
 * Parses the CLASSES array into subjects and numbers
 * @returns {Object} - { subjects: Array, classesBySubject: Object }
 */
function parseClasses() {
  const subjects = new Set();
  const classesBySubject = {};

  CLASSES.forEach(cls => {
    // Extract subject (letters) and number (digits)
    // Example: "CS124" -> subject="CS", number="124"
    const match = cls.match(/^([A-Z]+)(\d+)$/);
    if (match) {
      const subject = match[1];  // "CS"
      const number = match[2];    // "124"

      subjects.add(subject);

      if (!classesBySubject[subject]) {
        classesBySubject[subject] = [];
      }
      classesBySubject[subject].push(number);
    }
  });

  return {
    subjects: Array.from(subjects).sort(),
    classesBySubject: classesBySubject
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

  // If "All Numbers" selected with a subject, just submit
  if (!numberSelect.value && subjectSelect.value) {
    document.getElementById('class-filter-hidden').value = 'All';
    document.getElementById('course-filter-form').submit();
  } else {
    applyClassFilter();
  }
}

// === INITIALIZATION ===

/**
 * Initializes all page functionality when DOM is ready
 * @param {number} initialPage - The current page number
 * @param {Array} classes - Array of available class names
 * @param {string} selectedFilter - Currently selected class filter
 */
function initializePage(initialPage, classes, selectedFilter) {
  // Set initial values from template
  currentPage = initialPage;
  CLASSES = classes;

  // Populate course filter dropdowns
  populateSubjects(selectedFilter);
  updateNumberDropdown(true, selectedFilter);

  // Initialize Choices.js on dropdowns
  const subjectSelect = document.getElementById('subject-select');
  subjectChoice = new Choices(subjectSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Type to search subjects...',
    itemSelectText: '',
    shouldSort: false,
    searchResultLimit: 20,
    removeItemButton: false
  });

  const numberSelect = document.getElementById('number-select');
  numberChoice = new Choices(numberSelect, {
    searchEnabled: true,
    searchPlaceholderValue: 'Type to search numbers...',
    itemSelectText: '',
    shouldSort: false,
    searchResultLimit: 20,
    removeItemButton: false
  });

  // Add event listeners
  subjectSelect.addEventListener('change', handleSubjectChange);
  numberSelect.addEventListener('change', handleNumberChange);

  // Modal event listeners
  const modal = document.getElementById('note-modal');
  modal.addEventListener('click', function(e) {
    // If click is on the overlay (not the content box)
    if (e.target === modal) {
      closeModal();
    }
  });

  // Close modal with Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
      closeModal();
    }
  });
}

// === AUTO-INITIALIZATION ===

document.addEventListener('DOMContentLoaded', function() {
  // Get initial values from data attributes set by template
  const pageData = document.getElementById('page-data');
  const initialPage = parseInt(pageData.dataset.page || '1');
  const classes = JSON.parse(pageData.dataset.classes || '[]');
  const selectedFilter = pageData.dataset.selectedFilter || 'All';

  initializePage(initialPage, classes, selectedFilter);
});
