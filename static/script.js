/**
 * script.js - Lightweight Frontend Interactions
 * Handles modal dialog opening/closing, background overlay clicks,
 * Escape key events, and flash notification auto-dismissal.
 */

// Open a modal dialog by its HTML element ID
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }
}

// Close a modal dialog by its HTML element ID
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = ''; // Restore background scrolling
    }
}

// Global Event Listeners
document.addEventListener('DOMContentLoaded', function () {
    // 1. Close modal when clicking outside the dialog card (on the backdrop overlay)
    const modals = document.querySelectorAll('.modal-overlay');
    modals.forEach(function (modal) {
        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // 2. Close active modal when the Escape key is pressed
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            modals.forEach(function (modal) {
                if (modal.classList.contains('active')) {
                    modal.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });
        }
    });

    // 3. Auto-dismiss flash alert notifications after 6 seconds
    const flashAlerts = document.querySelectorAll('.flash-alert');
    if (flashAlerts.length > 0) {
        setTimeout(function () {
            flashAlerts.forEach(function (alert) {
                alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-6px)';
                setTimeout(function () {
                    alert.remove();
                }, 400);
            });
        }, 6000);
    }
});

// =============================================================================
// Student Autocomplete Dropdown Logic
// =============================================================================

function openStudentDropdown(prefix) {
    const list = document.getElementById(prefix + '_student_dropdown');
    if (!list) return;
    list.style.display = 'block';
    filterStudentDropdown(prefix);
}

function closeStudentDropdown(prefix) {
    const list = document.getElementById(prefix + '_student_dropdown');
    if (list) list.style.display = 'none';
}

function filterStudentDropdown(prefix) {
    const input = document.getElementById(prefix + '_student_search_input');
    const list = document.getElementById(prefix + '_student_dropdown');
    const clearBtn = document.getElementById(prefix + '_student_clear_btn');
    const emptyMsg = document.getElementById(prefix + '_student_empty');
    if (!input || !list) return;

    list.style.display = 'block';
    const query = input.value.trim().toLowerCase();

    if (clearBtn) {
        clearBtn.style.display = query ? 'block' : 'none';
    }

    const items = list.querySelectorAll('.student-dropdown-item');
    let visibleCount = 0;

    items.forEach(function (item) {
        const sid = (item.getAttribute('data-sid') || '').toLowerCase();
        const name = (item.getAttribute('data-name') || '').toLowerCase();
        const course = (item.getAttribute('data-course') || '').toLowerCase();
        const phone = (item.getAttribute('data-phone') || '').toLowerCase();

        const match = !query || sid.includes(query) || name.includes(query) || course.includes(query) || phone.includes(query);
        if (match) {
            item.style.display = 'flex';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
        item.classList.remove('active-highlight');
    });

    if (emptyMsg) {
        emptyMsg.style.display = (visibleCount === 0) ? 'block' : 'none';
        const qSpan = emptyMsg.querySelector('.query-span');
        if (qSpan) qSpan.textContent = input.value;
    }
}

function selectStudentItem(prefix, element) {
    const id = element.getAttribute('data-id');
    const sid = element.getAttribute('data-sid');
    const name = element.getAttribute('data-name');
    const course = element.getAttribute('data-course');
    const phone = element.getAttribute('data-phone');
    const email = element.getAttribute('data-email');

    // Populate hidden input for form submission
    const hiddenRef = document.getElementById(prefix + '_student_ref');
    if (hiddenRef) hiddenRef.value = id;

    // Display formatted student in search input
    const searchInput = document.getElementById(prefix + '_student_search_input');
    if (searchInput) searchInput.value = `[ID: ${sid}] ${name} (${course})`;

    // Show clear button
    const clearBtn = document.getElementById(prefix + '_student_clear_btn');
    if (clearBtn) clearBtn.style.display = 'block';

    // Hide dropdown
    closeStudentDropdown(prefix);

    // Populate and show student confirmation card
    const card = document.getElementById(prefix + '_student_card');
    if (card) {
        const nameEl = card.querySelector('[data-field="name"]');
        const sidEl = card.querySelector('[data-field="sid"]');
        const courseEl = card.querySelector('[data-field="course"]');
        const phoneEl = card.querySelector('[data-field="phone"]');
        const emailEl = card.querySelector('[data-field="email"]');

        if (nameEl) nameEl.textContent = name;
        if (sidEl) sidEl.textContent = 'ID: ' + sid;
        if (courseEl) courseEl.textContent = course;
        if (phoneEl) phoneEl.textContent = phone;
        if (emailEl) emailEl.textContent = email;
        card.style.display = 'block';
    }
}

function clearStudentSelection(prefix) {
    const hiddenRef = document.getElementById(prefix + '_student_ref');
    if (hiddenRef) hiddenRef.value = '';

    const searchInput = document.getElementById(prefix + '_student_search_input');
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }

    const clearBtn = document.getElementById(prefix + '_student_clear_btn');
    if (clearBtn) clearBtn.style.display = 'none';

    const card = document.getElementById(prefix + '_student_card');
    if (card) card.style.display = 'none';

    filterStudentDropdown(prefix);
}

function handleStudentKeydown(event, prefix) {
    const list = document.getElementById(prefix + '_student_dropdown');
    if (!list || list.style.display === 'none') {
        if (event.key === 'ArrowDown' || event.key === 'Enter') {
            openStudentDropdown(prefix);
            event.preventDefault();
        }
        return;
    }

    const visibleItems = Array.from(list.querySelectorAll('.student-dropdown-item')).filter(function (el) {
        return el.style.display !== 'none';
    });
    if (visibleItems.length === 0) return;

    let currentIndex = visibleItems.findIndex(function (el) {
        return el.classList.contains('active-highlight');
    });

    if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (currentIndex >= 0) visibleItems[currentIndex].classList.remove('active-highlight');
        currentIndex = (currentIndex + 1) % visibleItems.length;
        visibleItems[currentIndex].classList.add('active-highlight');
        visibleItems[currentIndex].scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (currentIndex >= 0) visibleItems[currentIndex].classList.remove('active-highlight');
        currentIndex = (currentIndex - 1 + visibleItems.length) % visibleItems.length;
        visibleItems[currentIndex].classList.add('active-highlight');
        visibleItems[currentIndex].scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'Enter') {
        event.preventDefault();
        if (currentIndex >= 0 && visibleItems[currentIndex]) {
            selectStudentItem(prefix, visibleItems[currentIndex]);
        } else if (visibleItems.length === 1) {
            selectStudentItem(prefix, visibleItems[0]);
        }
    } else if (event.key === 'Escape') {
        closeStudentDropdown(prefix);
    }
}

function validateStudentSelection(prefix) {
    const ref = document.getElementById(prefix + '_student_ref');
    const input = document.getElementById(prefix + '_student_search_input');
    if (!ref || !ref.value) {
        alert('Please select a student from the list before issuing this book.');
        if (input) {
            input.focus();
            openStudentDropdown(prefix);
        }
        return false;
    }
    return true;
}

// Global click outside listener for all student autocomplete dropdowns
document.addEventListener('click', function (event) {
    if (!event.target.closest('.student-search-container')) {
        document.querySelectorAll('.student-dropdown-list').forEach(function (list) {
            list.style.display = 'none';
        });
    }
});

// =============================================================================
// Theme Switcher (Dark / Light Mode)
// Modern Web Guidance Compliant (Zero-FOUC, Tab Sync, System Preference Sync)
// =============================================================================

function getPreferredTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function updateThemeUI(theme) {
    const isDark = theme === 'dark';
    
    // Update all theme toggle buttons on the page
    document.querySelectorAll('.theme-toggle-btn').forEach(function (btn) {
        btn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        const icon = btn.querySelector('i');
        const text = btn.querySelector('.theme-text');
        if (icon) {
            icon.className = isDark ? 'fa-solid fa-sun text-amber' : 'fa-solid fa-moon';
        }
        if (text) {
            text.textContent = isDark ? 'Light' : 'Dark';
        }
    });

    // Update sidebar theme toggle button
    document.querySelectorAll('.sidebar-theme-btn').forEach(function (btn) {
        btn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        const icon = btn.querySelector('i');
        const label = btn.querySelector('.theme-mode-label');
        if (icon) {
            icon.className = isDark ? 'fa-solid fa-sun text-amber' : 'fa-solid fa-moon';
        }
        if (label) {
            label.textContent = isDark ? 'Light Mode' : 'Dark Mode';
        }
    });
}

function applyTheme(theme) {
    const validTheme = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', validTheme);
    
    // Keep meta color-scheme in sync
    let meta = document.querySelector('meta[name="color-scheme"]');
    if (meta) {
        meta.setAttribute('content', validTheme);
    }
    
    updateThemeUI(validTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);
    applyTheme(newTheme);
}

window.toggleTheme = toggleTheme;

// Initialize theme state on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    const currentTheme = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
    applyTheme(currentTheme);

    // Bind click events on all theme toggles
    document.addEventListener('click', function (e) {
        const toggleBtn = e.target.closest('.theme-toggle-btn, .sidebar-theme-btn');
        if (toggleBtn) {
            e.preventDefault();
            toggleTheme();
        }
    });
});

// Synchronize theme across multiple browser tabs
window.addEventListener('storage', function (e) {
    if (e.key === 'theme') {
        applyTheme(e.newValue || getPreferredTheme());
    }
});

// Synchronize with OS theme changes if user hasn't explicitly set preference
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}


