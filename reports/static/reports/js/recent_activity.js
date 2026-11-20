document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('activity-filter-form');
    if (!form) return;

    const timeFilter = form.querySelector('[data-filter-value="time_filter"]');
    const dateRange = form.querySelector('[data-activity-custom-range]');
    const startDate = form.querySelector('[name="start_date"]');
    const endDate = form.querySelector('[name="end_date"]');
    const customMenu = dateRange.closest('.activity-time-dropdown');

    function setCustomMode(enabled) {
        dateRange.hidden = !enabled;
        startDate.required = enabled;
        endDate.required = enabled;
        if (enabled) {
            customMenu.open = true;
            endDate.min = startDate.value;
            startDate.max = endDate.value;
        }
    }

    form.querySelectorAll('[data-filter-key][data-filter-choice]').forEach((option) => {
        option.addEventListener('click', () => {
            const key = option.dataset.filterKey;
            const hidden = form.querySelector(`[data-filter-value="${key}"]`);
            if (!hidden) return;
            hidden.value = option.dataset.filterChoice;

            if (key === 'time_filter') {
                if (hidden.value === 'custom') {
                    setCustomMode(true);
                    return;
                }
                startDate.value = '';
                endDate.value = '';
                setCustomMode(false);
            }
            form.requestSubmit();
        });
    });

    form.querySelector('[data-activity-custom-toggle]').addEventListener('click', () => {
        if (timeFilter.value !== 'custom') {
            startDate.value = '';
            endDate.value = '';
        }
        timeFilter.value = 'custom';
        setCustomMode(true);
        startDate.focus();
    });

    startDate.addEventListener('change', () => {
        endDate.min = startDate.value;
        endDate.setCustomValidity('');
    });
    endDate.addEventListener('change', () => {
        startDate.max = endDate.value;
        endDate.setCustomValidity('');
    });

    form.querySelector('[data-activity-custom-apply]').addEventListener('click', () => {
        timeFilter.value = 'custom';
        setCustomMode(true);
        endDate.setCustomValidity(
            startDate.value && endDate.value && endDate.value < startDate.value
                ? 'End date must be on or after the start date.'
                : '',
        );
        if (form.reportValidity()) form.requestSubmit();
    });

    document.addEventListener('click', (event) => {
        form.querySelectorAll('.activity-dropdown[open]').forEach((dropdown) => {
            if (!event.composedPath().includes(dropdown) || event.target === dropdown) dropdown.open = false;
        });
    });

    const list = document.querySelector('[data-activity-mobile-list]');
    const count = document.querySelector('[data-activity-count]');
    const loadMore = document.querySelector('[data-activity-load-more]');
    if (list && loadMore) {
        loadMore.addEventListener('click', async (event) => {
            event.preventDefault();
            const nextUrl = loadMore.href;
            loadMore.textContent = 'Loading...';
            try {
                const response = await fetch(nextUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!response.ok) throw new Error('Unable to load more activity records.');
                const nextDocument = new DOMParser().parseFromString(await response.text(), 'text/html');
                const nextList = nextDocument.querySelector('[data-activity-mobile-list]');
                if (!nextList) throw new Error('Activity records were not found in the response.');
                const nextCards = [...nextList.querySelectorAll('.activity-mobile-card')];
                if (!list.querySelector('.activity-mobile-card')) list.replaceChildren();
                list.append(...nextCards);

                const nextCount = nextDocument.querySelector('[data-activity-count]');
                if (count && nextCount) {
                    const loaded = Number(nextCount.dataset.loaded || 0);
                    const total = Number(nextCount.dataset.total || 0);
                    count.textContent = total ? `Showing 1–${loaded} of ${total} activities` : 'Showing 0–0 of 0 activities';
                }
                const nextButton = nextDocument.querySelector('[data-activity-load-more]');
                if (nextButton) {
                    loadMore.href = nextButton.href;
                    loadMore.textContent = 'Load More';
                } else {
                    loadMore.remove();
                }
            } catch (error) {
                window.location.assign(nextUrl);
            }
        });
    }

    setCustomMode(timeFilter.value === 'custom');
});
