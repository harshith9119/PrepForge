function toggleProblemStatus(problemId, checkbox) {
    fetch('/toggle_problem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_id: problemId })
    })
    .then(res => res.json())
    .then(data => {
        const solved = data.status === 'solved';
        if (checkbox) checkbox.checked = solved;
        document.querySelectorAll(`[data-problem-id="${problemId}"] input[type="checkbox"]`)
            .forEach(cb => { cb.checked = solved; });
    })
    .catch(() => {
        if (checkbox) checkbox.checked = !checkbox.checked;
    });
}

function initMobileNav() {
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    if (!btn || !menu) return;

    btn.addEventListener('click', () => {
        menu.classList.toggle('hidden');
        btn.setAttribute('aria-expanded', menu.classList.contains('hidden') ? 'false' : 'true');
    });
}

function initThemeToggle() {
    function toggleTheme() {
        const html = document.documentElement;
        const isDark = html.classList.contains('dark');
        if (isDark) {
            html.classList.remove('dark');
            localStorage.setItem('prepforge-theme', 'light');
        } else {
            html.classList.add('dark');
            localStorage.setItem('prepforge-theme', 'dark');
        }
    }

    document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
    document.getElementById('theme-toggle-mobile')?.addEventListener('click', toggleTheme);
}

function initCommandPalette() {
    const palette = document.getElementById('command-palette');
    const input = document.getElementById('command-input');
    const results = document.getElementById('command-results');
    const backdrop = document.getElementById('command-backdrop');
    const openBtn = document.getElementById('quick-search-btn');

    if (!palette || !input || !results) return;

    let debounceTimer;

    function openPalette() {
        palette.classList.remove('hidden');
        input.value = '';
        results.innerHTML = '<p class="px-4 py-6 text-sm text-gray-500 text-center">Type to search problems...</p>';
        input.focus();
    }

    function closePalette() {
        palette.classList.add('hidden');
    }

    function renderResults(items) {
        if (!items.length) {
            results.innerHTML = '<p class="px-4 py-6 text-sm text-gray-500 text-center">No results found.</p>';
            return;
        }

        results.innerHTML = items.map(item => {
            const diffColor = item.difficulty === 'Easy' ? 'green' : item.difficulty === 'Medium' ? 'yellow' : 'red';
            const solved = item.is_solved ? '<i class="fas fa-check text-green-400 text-xs"></i>' : '';
            return `<a href="${item.url}" target="_blank" rel="noopener noreferrer"
                class="flex items-center justify-between px-4 py-3 hover:bg-gray-800 border-b border-gray-800/50 transition group">
                <div class="min-w-0 mr-3">
                    <p class="text-white text-sm font-medium truncate group-hover:text-brand">${item.title} ${solved}</p>
                    <p class="text-xs text-gray-500">${item.topic_name} · ${item.difficulty}</p>
                </div>
                <span class="text-xs text-${diffColor}-400 shrink-0">Open</span>
            </a>`;
        }).join('');
    }

    function search(query) {
        clearTimeout(debounceTimer);
        if (query.length < 2) {
            results.innerHTML = '<p class="px-4 py-6 text-sm text-gray-500 text-center">Type at least 2 characters...</p>';
            return;
        }
        debounceTimer = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(renderResults)
                .catch(() => {
                    results.innerHTML = '<p class="px-4 py-6 text-sm text-red-400 text-center">Search failed.</p>';
                });
        }, 250);
    }

    openBtn?.addEventListener('click', openPalette);
    backdrop?.addEventListener('click', closePalette);

    input.addEventListener('input', (e) => search(e.target.value));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closePalette();
    });

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            openPalette();
        }
        if (e.key === 'Escape' && !palette.classList.contains('hidden')) {
            closePalette();
        }
    });
}

function filterProblems(diff) {
    window.activeDifficulty = diff;
    applyTopicFilters();

    document.querySelectorAll('.diff-filter-btn').forEach(btn => {
        btn.classList.remove('ring-2', 'ring-brand', 'bg-gray-600');
        if (btn.dataset.diff === diff) {
            btn.classList.add('ring-2', 'ring-brand', 'bg-gray-600');
        }
    });
}

function applyTopicFilters() {
    const input = document.getElementById('searchInput');
    const query = input ? input.value.toLowerCase() : '';
    const diff = window.activeDifficulty || 'All';

    document.querySelectorAll('.problem-row').forEach(row => {
        const matchesDiff = diff === 'All' || row.dataset.diff === diff;
        const matchesSearch = !query || row.innerText.toLowerCase().includes(query);
        row.style.display = matchesDiff && matchesSearch ? '' : 'none';
    });
}

function searchTable() {
    applyTopicFilters();
}

function showCompany(companyName) {
    document.querySelectorAll('.company-btn').forEach(btn => {
        btn.classList.remove('bg-brand', 'text-white', 'shadow-lg', 'shadow-brand/30');
        btn.classList.add('bg-gray-800', 'text-gray-300', 'border-gray-700');
    });

    const activeBtnId = companyName === 'All' ? 'btn-All' : 'btn-' + companyName.replace(/\s+/g, '-');
    const activeBtn = document.getElementById(activeBtnId);
    if (activeBtn) {
        activeBtn.classList.remove('bg-gray-800', 'text-gray-300', 'border-gray-700');
        activeBtn.classList.add('bg-brand', 'text-white', 'shadow-lg', 'shadow-brand/30');
    }

    document.querySelectorAll('.company-section').forEach(section => {
        if (companyName === 'All') {
            section.style.display = 'block';
        } else {
            const expectedId = 'section-' + companyName.replace(/\s+/g, '-');
            section.style.display = section.id === expectedId ? 'block' : 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    initThemeToggle();
    initCommandPalette();
});
