(() => {
  const form = document.getElementById('exportForm');
  if (!form) return;
  const typeInput = document.getElementById('export_type');
  const excelTab = document.getElementById('tab-excel');
  const pdfTab = document.getElementById('tab-pdf');
  const excelSection = document.getElementById('section-excel');
  const pdfSection = document.getElementById('section-pdf');
  const summaryFormat = document.getElementById('summary-format');
  const summaryRecords = document.getElementById('summary-records');
  const summaryFile = document.getElementById('summary-filename');
  const summaryFilters = document.getElementById('summary-filters');
  const summaryFilterRow = document.getElementById('summary-filter-row');
  const submit = document.getElementById('btn-submit');
  const empty = document.getElementById('export-empty');
  const error = document.getElementById('export-error');
  const modal = document.getElementById('export-modal');
  const download = document.getElementById('modal-download');
  const pdfSelect = document.getElementById('single-ncr');
  let previewTimer;
  let currentDownloadUrl;

  function setTab(type) {
    const isExcel = type === 'excel';
    typeInput.value = type;
    excelTab.classList.toggle('is-active', isExcel);
    pdfTab.classList.toggle('is-active', !isExcel);
    excelTab.setAttribute('aria-selected', String(isExcel));
    pdfTab.setAttribute('aria-selected', String(!isExcel));
    excelSection.classList.toggle('d-none', !isExcel);
    pdfSection.classList.toggle('d-none', isExcel);
    summaryFormat.textContent = isExcel ? 'Excel (.xlsx)' : 'PDF';
    document.getElementById('btn-submit').textContent = isExcel ? 'Export to Excel' : 'Export to PDF';
    summaryFilterRow.classList.toggle('d-none', !isExcel);
    document.getElementById('pdf-note').classList.toggle('d-none', isExcel);
    error.classList.add('d-none');
    updateSummary();
  }

  function filterDescription() {
    const values = [];
    for (const [id, key] of [['filter-start', 'from'], ['filter-end', 'to']]) {
      const field = document.getElementById(id);
      if (field.value) values.push(`${key} ${field.value}`);
    }
    const project = document.getElementById('filter-project');
    if (project.value) values.push(project.options[project.selectedIndex].text);
    const cause = document.getElementById('filter-cause');
    if (cause.value) values.push(cause.options[cause.selectedIndex].text);
    const status = document.getElementById('filter-status');
    if (status.value) values.push(status.options[status.selectedIndex].text);
    const packageNo = document.getElementById('filter-package').value.trim();
    if (packageNo) values.push(`Package ${packageNo}`);
    return values.join(' · ') || 'All records';
  }

  function updateSummary() {
    const isExcel = typeInput.value === 'excel';
    if (isExcel) {
      summaryFilters.textContent = filterDescription();
      summaryFile.textContent = `NCR-List_${new Date().toISOString().slice(0, 10)}.xlsx`;
      submit.disabled = form.querySelectorAll('#section-excel input[name="columns"]:checked').length === 0;
      schedulePreview();
      return;
    }
    const option = pdfSelect.options[pdfSelect.selectedIndex];
    const selected = Boolean(pdfSelect.value);
    summaryRecords.textContent = selected ? option.dataset.reference : 'Select an NCR';
    summaryFile.textContent = selected ? `${option.dataset.reference}.pdf` : '—';
    document.getElementById('attachment-count').textContent = `${option.dataset.attachments || 0} files from this NCR`;
    submit.disabled = !selected;
  }

  function schedulePreview() {
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(async () => {
      const data = new FormData(form);
      data.set('export_type', 'excel');
      data.set('preview', '1');
      try {
        const response = await fetch(form.action, { method: 'POST', body: data, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not update the export summary.');
        summaryRecords.textContent = `${result.records} NCR${result.records === 1 ? '' : 's'}`;
        summaryFile.textContent = result.filename;
        empty.classList.toggle('d-none', result.records > 0);
        submit.disabled = result.records === 0 || form.querySelectorAll('#section-excel input[name="columns"]:checked').length === 0;
      } catch (err) {
        error.textContent = err.message;
        error.classList.remove('d-none');
      }
    }, 220);
  }

  excelTab.addEventListener('click', () => setTab('excel'));
  pdfTab.addEventListener('click', () => setTab('pdf'));
  pdfSelect.addEventListener('change', updateSummary);
  form.querySelectorAll('#section-excel input, #section-excel select').forEach((control) => {
    control.addEventListener('change', updateSummary);
    control.addEventListener('input', updateSummary);
  });
  form.querySelectorAll('.export-check input').forEach((checkbox) => {
    checkbox.addEventListener('change', () => checkbox.closest('.export-check').classList.toggle('is-checked', checkbox.checked));
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    error.classList.add('d-none');
    submit.disabled = true;
    const label = submit.textContent;
    submit.textContent = 'Generating…';
    try {
      const response = await fetch(form.action, { method: 'POST', body: new FormData(form) });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(result.error || 'The export could not be generated.');
      }
      const blob = await response.blob();
      if (currentDownloadUrl) URL.revokeObjectURL(currentDownloadUrl);
      currentDownloadUrl = URL.createObjectURL(blob);
      const filename = response.headers.get('X-Export-Filename') || 'NCR-Export';
      const records = response.headers.get('X-Export-Records') || '1';
      download.href = currentDownloadUrl;
      download.download = filename;
      document.getElementById('modal-filename').textContent = filename;
      document.getElementById('modal-details').textContent = `${records} record${records === '1' ? '' : 's'} · ${(blob.size / 1024).toFixed(1)} KB`;
      modal.classList.remove('d-none');
      document.body.style.overflow = 'hidden';
    } catch (err) {
      error.textContent = err.message;
      error.classList.remove('d-none');
    } finally {
      submit.textContent = label;
      submit.disabled = typeInput.value === 'pdf'
        ? !pdfSelect.value
        : form.querySelectorAll('#section-excel input[name="columns"]:checked').length === 0
          || Number.parseInt(summaryRecords.textContent, 10) === 0;
    }
  });

  function closeModal() {
    modal.classList.add('d-none');
    document.body.style.overflow = '';
  }
  document.getElementById('modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  updateSummary();
})();
