function initInventoryLiveSearch() {
  const searchInput = document.getElementById('searchInput');
  const visibleCountEl = document.getElementById('visibleCount');
  const allRows = Array.from(document.querySelectorAll('.inventory-row'));

  if (!searchInput || !visibleCountEl || allRows.length === 0) return;

  const applyFilter = () => {
    const filter = (searchInput.value || '').toLowerCase().trim();
    let visible = 0;

    for (const row of allRows) {
      const show = row.innerText.toLowerCase().includes(filter);
      row.style.display = show ? '' : 'none';
      if (show) visible += 1;
    }

    visibleCountEl.textContent = String(visible);
  };

  searchInput.addEventListener('keyup', applyFilter);
  applyFilter();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initInventoryLiveSearch);
} else {
  initInventoryLiveSearch();
}

