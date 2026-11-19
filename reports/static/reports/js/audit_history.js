document.addEventListener('DOMContentLoaded', () => {
    const list = document.querySelector('[data-audit-mobile-list]');
    const counter = document.querySelector('[data-audit-count]');
    const button = document.querySelector('[data-load-more]');
    const filter = document.querySelector('.audit-filter');
    if (filter) {
        document.addEventListener('click', (event) => {
            if (filter.open && (!event.composedPath().includes(filter) || event.target === filter)) filter.open = false;
        });
        filter.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') filter.open = false;
        });
    }
    if (!list || !button) return;

    button.addEventListener('click', async (event) => {
        event.preventDefault();
        const nextUrl = button.href;
        button.textContent = 'Loading...';
        button.setAttribute('aria-disabled', 'true');

        try {
            const response = await fetch(nextUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            if (!response.ok) throw new Error('Could not load more audit records.');
            const documentNext = new DOMParser().parseFromString(await response.text(), 'text/html');
            const nextList = documentNext.querySelector('[data-audit-mobile-list]');
            if (!nextList) throw new Error('Audit records were not found in the response.');

            const nextCards = [...nextList.querySelectorAll('.audit-mobile-card')];
            if (!list.querySelector('.audit-mobile-card')) list.replaceChildren();
            list.append(...nextCards);

            const nextCounter = documentNext.querySelector('[data-audit-count]');
            if (counter && nextCounter) {
                const loaded = Number(nextCounter.dataset.loaded || 0);
                const total = Number(nextCounter.dataset.total || 0);
                counter.dataset.loaded = String(loaded);
                counter.dataset.total = String(total);
                counter.textContent = total ? `Showing 1–${loaded} of ${total} activities` : 'Showing 0–0 of 0 activities';
            }

            const nextButton = documentNext.querySelector('[data-load-more]');
            if (nextButton) {
                button.href = nextButton.href;
                button.textContent = 'Load More';
                button.removeAttribute('aria-disabled');
            } else {
                button.remove();
            }
        } catch (error) {
            window.location.assign(nextUrl);
        }
    });
});
