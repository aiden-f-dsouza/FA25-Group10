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

  // If "All Numbers" selected with a subject, just submit
  if (!numberSelect.value && subjectSelect.value) {
    document.getElementById('class-filter-hidden').value = 'All';
    document.getElementById('course-filter-form').submit();
  } else {
    applyClassFilter();
  }
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
