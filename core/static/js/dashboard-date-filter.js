document.addEventListener('DOMContentLoaded', () => {
    const picker = document.querySelector('.dashboard-time-filter');
    const menu = picker?.querySelector('.dashboard-time-menu');
    if (!picker || !menu) return;

    const form = menu.querySelector('.dashboard-date-form');
    const filterInput = form.querySelector('[data-filter-value]');
    const startInput = form.querySelector('[data-start-value]');
    const endInput = form.querySelector('[data-end-value]');
    const calendars = menu.querySelector('[data-calendars]');
    const summary = menu.querySelector('[data-range-summary]');
    const mobileRange = menu.querySelector('[data-mobile-custom-range]');
    const mobileStart = menu.querySelector('[data-mobile-start]');
    const mobileEnd = menu.querySelector('[data-mobile-end]');
    const mobileRangeError = menu.querySelector('[data-mobile-range-error]');
    const presets = [...menu.querySelectorAll('[data-preset]')];
    const weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

    const parseDate = (value) => {
        if (!value) return null;
        const parts = value.split('-').map(Number);
        if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
        return new Date(parts[0], parts[1] - 1, parts[2]);
    };
    const toISO = (date) => {
        if (!date) return '';
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    };
    const sameDay = (a, b) => Boolean(a && b && toISO(a) === toISO(b));
    const today = () => {
        const value = new Date();
        return new Date(value.getFullYear(), value.getMonth(), value.getDate());
    };
    const initial = {
        filter: menu.dataset.initialFilter || 'all',
        start: parseDate(menu.dataset.initialStart),
        end: parseDate(menu.dataset.initialEnd),
    };
    const state = { ...initial };
    let firstMonth = new Date((state.start || today()).getFullYear(), (state.start || today()).getMonth(), 1);

    function formatLong(date) {
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function syncForm() {
        filterInput.value = state.filter;
        startInput.value = toISO(state.start);
        endInput.value = toISO(state.end);
        mobileRange.hidden = state.filter !== 'custom';
        mobileStart.value = toISO(state.start);
        mobileEnd.value = toISO(state.end);
        presets.forEach((button) => button.classList.toggle('is-selected', button.dataset.preset === state.filter));
        if (!state.start) summary.textContent = state.filter === 'all' ? 'Any date' : 'Select a start date';
        else if (!state.end && state.filter === 'custom') summary.textContent = `Start: ${formatLong(state.start)}. Select an end date.`;
        else summary.textContent = state.end ? `${formatLong(state.start)} to ${formatLong(state.end)}` : formatLong(state.start);
        renderCalendars();
    }

    function renderMonth(monthDate) {
        const year = monthDate.getFullYear();
        const month = monthDate.getMonth();
        const firstWeekday = new Date(year, month, 1).getDay();
        const dayCount = new Date(year, month + 1, 0).getDate();
        const section = document.createElement('section');
        section.className = 'dashboard-calendar-month';

        const heading = document.createElement('h3');
        heading.className = 'dashboard-calendar-title';
        heading.textContent = monthDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
        section.append(heading);

        const grid = document.createElement('div');
        grid.className = 'dashboard-calendar-grid';
        weekdays.forEach((day) => {
            const label = document.createElement('span');
            label.className = 'dashboard-calendar-weekday';
            label.textContent = day;
            grid.append(label);
        });
        for (let blank = 0; blank < firstWeekday; blank += 1) {
            const empty = document.createElement('span');
            empty.className = 'dashboard-calendar-day is-empty';
            grid.append(empty);
        }
        for (let day = 1; day <= dayCount; day += 1) {
            const date = new Date(year, month, day);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'dashboard-calendar-day';
            button.textContent = String(day);
            button.setAttribute('aria-label', formatLong(date));
            if (sameDay(date, today())) button.classList.add('is-today');
            if (sameDay(date, state.start)) button.classList.add('is-range-start');
            if (sameDay(date, state.end)) button.classList.add('is-range-end');
            if (state.start && state.end && date > state.start && date < state.end) button.classList.add('is-in-range');
            button.addEventListener('click', () => {
                if (!state.start || state.end) {
                    state.start = date;
                    state.end = null;
                } else if (date < state.start) {
                    state.end = state.start;
                    state.start = date;
                } else {
                    state.end = date;
                }
                state.filter = 'custom';
                syncForm();
            });
            grid.append(button);
        }
        section.append(grid);
        return section;
    }

    function renderCalendars() {
        calendars.replaceChildren(
            renderMonth(firstMonth),
            renderMonth(new Date(firstMonth.getFullYear(), firstMonth.getMonth() + 1, 1)),
        );
    }

    presets.forEach((button) => {
        button.addEventListener('click', () => {
            const selected = button.dataset.preset;
            const now = today();
            state.filter = selected;
            if (selected === 'today') {
                state.start = now;
                state.end = now;
            } else if (selected === '7_days' || selected === '30_days') {
                state.end = now;
                state.start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (selected === '7_days' ? 6 : 29));
            } else if (selected === '3_months') {
                state.end = now;
                state.start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 89);
            } else if (selected === 'this_month') {
                state.start = new Date(now.getFullYear(), now.getMonth(), 1);
                state.end = now;
            } else if (selected === 'this_quarter') {
                const quarterMonth = Math.floor(now.getMonth() / 3) * 3;
                state.start = new Date(now.getFullYear(), quarterMonth, 1);
                state.end = now;
            } else if (selected === 'this_year') {
                state.start = new Date(now.getFullYear(), 0, 1);
                state.end = now;
            } else if (selected === 'all') {
                state.start = null;
                state.end = null;
            } else if (selected === 'custom') {
                state.start = null;
                state.end = null;
            }
            if (state.start) firstMonth = new Date(state.start.getFullYear(), state.start.getMonth(), 1);
            syncForm();
            if (button.hasAttribute('data-auto-apply')) form.requestSubmit();
        });
    });

    [mobileStart, mobileEnd].forEach((input) => {
        input.addEventListener('change', () => {
            state.filter = 'custom';
            state.start = parseDate(mobileStart.value);
            state.end = parseDate(mobileEnd.value);
            if (state.start && state.end && state.start > state.end) {
                [state.start, state.end] = [state.end, state.start];
            }
            if (state.start) firstMonth = new Date(state.start.getFullYear(), state.start.getMonth(), 1);
            syncForm();
        });
    });

    menu.querySelector('[data-calendar-prev]').addEventListener('click', () => {
        firstMonth = new Date(firstMonth.getFullYear(), firstMonth.getMonth() - 1, 1);
        renderCalendars();
    });
    menu.querySelector('[data-calendar-next]').addEventListener('click', () => {
        firstMonth = new Date(firstMonth.getFullYear(), firstMonth.getMonth() + 1, 1);
        renderCalendars();
    });
    menu.querySelector('[data-cancel]').addEventListener('click', () => {
        state.filter = initial.filter;
        state.start = initial.start;
        state.end = initial.end;
        firstMonth = new Date((state.start || today()).getFullYear(), (state.start || today()).getMonth(), 1);
        syncForm();
        picker.open = false;
    });
    form.addEventListener('submit', (event) => {
        if (state.filter === 'custom' && (!state.start || !state.end)) {
            event.preventDefault();
            summary.textContent = !state.start ? 'Select a start date.' : 'Select an end date.';
            mobileRangeError.hidden = false;
        } else {
            mobileRangeError.hidden = true;
        }
    });

    document.addEventListener('click', (event) => {
        if (!event.composedPath().includes(picker) || event.target === picker) picker.open = false;
    });
    picker.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') picker.open = false;
    });

    syncForm();
});
