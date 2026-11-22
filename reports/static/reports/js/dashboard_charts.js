(() => {
  const openColor = '#68161d';
  const closedColor = '#d18b8f';
  const svgNamespace = 'http://www.w3.org/2000/svg';

  function readData(id) {
    const element = document.getElementById(id);
    if (!element) return [];
    try {
      const data = JSON.parse(element.textContent);
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error(`Could not read dashboard chart data (${id}).`, error);
      return [];
    }
  }

  function svgElement(name, attributes = {}, text = '') {
    const element = document.createElementNS(svgNamespace, name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    if (text) element.textContent = text;
    return element;
  }

  function drawChart(containerId, title, data, labelKey) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.replaceChildren();

    const width = Math.max(320, Math.floor(container.clientWidth) || 900);
    const rowHeight = 41;
    const top = 34;
    const height = Math.max(76, top + data.length * rowHeight + 8);
    const svg = svgElement('svg', {
      viewBox: `0 0 ${width} ${height}`,
      width,
      height,
      role: 'img',
      'aria-label': title,
      preserveAspectRatio: 'xMinYMin meet',
    });

    const legend = [
      { label: 'Open', color: openColor, x: 2 },
      { label: 'Closed', color: closedColor, x: 58 },
    ];
    legend.forEach((item) => {
      svg.append(svgElement('rect', { x: item.x, y: 5, width: 9, height: 9, rx: 2, fill: item.color }));
      svg.append(svgElement('text', {
        x: item.x + 14, y: 13, fill: '#57535b', 'font-size': 11, 'font-family': 'Inter, Arial, sans-serif',
      }, item.label));
    });

    if (!data.length) {
      svg.append(svgElement('text', {
        x: 2, y: 51, fill: '#77737a', 'font-size': 12, 'font-family': 'Inter, Arial, sans-serif',
      }, 'No records for this selection.'));
      container.append(svg);
      return;
    }

    const maxValue = Math.max(1, ...data.map((item) => (Number(item.open) || 0) + (Number(item.closed) || 0)));
    const barWidth = width - 12;
    data.forEach((item, index) => {
      const open = Math.max(0, Number(item.open) || 0);
      const closed = Math.max(0, Number(item.closed) || 0);
      const y = top + index * rowHeight;
      const label = String(item[labelKey] || 'Unknown');
      svg.append(svgElement('text', {
        x: 1, y: y + 9, fill: '#38353a', 'font-size': 11, 'font-family': 'Inter, Arial, sans-serif',
      }, `${label}: ${open} open · ${closed} closed`));
      const openWidth = barWidth * open / maxValue;
      const closedWidth = barWidth * closed / maxValue;
      if (openWidth > 0) svg.append(svgElement('rect', { x: 1, y: y + 15, width: openWidth, height: 14, fill: openColor }));
      if (closedWidth > 0) svg.append(svgElement('rect', { x: 1 + openWidth, y: y + 15, width: closedWidth, height: 14, fill: closedColor }));
    });

    container.append(svg);
  }

  function render() {
    drawChart('causeChart', 'NCR counts by cause', readData('cause-chart-data'), 'cause');
    const projects = readData('project-chart-data');
    const pageSize = 5;
    const pageCount = Math.max(1, Math.ceil(projects.length / pageSize));
    const chart = document.getElementById('projectChart');
    let currentPage = Number(chart?.dataset.page || 0);
    currentPage = Math.min(Math.max(0, currentPage), pageCount - 1);
    if (chart) chart.dataset.page = String(currentPage);
    drawChart('projectChart', 'NCR counts by project', projects.slice(currentPage * pageSize, (currentPage + 1) * pageSize), 'project');

    const summary = document.getElementById('projectPageSummary');
    if (summary) {
      const first = projects.length ? currentPage * pageSize + 1 : 0;
      const last = Math.min((currentPage + 1) * pageSize, projects.length);
      summary.textContent = `Showing ${first}–${last} of ${projects.length} projects`;
    }
    const previous = document.getElementById('projectPagePrevious');
    const next = document.getElementById('projectPageNext');
    if (previous) previous.disabled = currentPage === 0;
    if (next) next.disabled = currentPage >= pageCount - 1;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render, { once: true });
  } else {
    render();
  }

  document.getElementById('projectPagePrevious')?.addEventListener('click', () => {
    const chart = document.getElementById('projectChart');
    if (chart) chart.dataset.page = String(Math.max(0, Number(chart.dataset.page || 0) - 1));
    render();
  });
  document.getElementById('projectPageNext')?.addEventListener('click', () => {
    const chart = document.getElementById('projectChart');
    if (chart) chart.dataset.page = String(Number(chart.dataset.page || 0) + 1);
    render();
  });

  let resizeTimer;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(render, 120);
  }, { passive: true });
})();
