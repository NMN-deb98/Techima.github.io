/* Article category filter (external file: the site CSP only allows script-src 'self'). */
(() => {
  const filters = Array.from(document.querySelectorAll('.article-category-filter'));
  const cards = Array.from(document.querySelectorAll('.article-feed-card[data-category]'));
  const groups = document.querySelectorAll('.article-timeline-group');
  const endMarker = document.querySelector('.article-timeline-end');
  const timeline = document.querySelector('.article-timeline');
  if (!filters.length || !cards.length) return;

  const valid = new Set(filters.map((b) => b.dataset.filter));
  const fa = (n) => String(n).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);

  // number of articles next to each category name
  filters.forEach((button) => {
    const key = button.dataset.filter;
    const count = key === 'all' ? cards.length : cards.filter((c) => c.dataset.category === key).length;
    if (!button.querySelector('.article-category-count')) {
      const badge = document.createElement('span');
      badge.className = 'article-category-count';
      badge.textContent = fa(count);
      button.appendChild(badge);
    }
  });

  let emptyMessage = document.querySelector('.article-category-empty');
  if (!emptyMessage && timeline) {
    emptyMessage = document.createElement('p');
    emptyMessage.className = 'article-category-empty';
    emptyMessage.setAttribute('role', 'status');
    emptyMessage.hidden = true;
    emptyMessage.textContent = 'هنوز مقاله‌ای در این دسته‌بندی منتشر نشده است.';
    timeline.insertBefore(emptyMessage, endMarker || null);
  }

  const applyFilter = (category, updateUrl) => {
    if (!valid.has(category)) category = 'all';
    let visibleCount = 0;
    filters.forEach((button) => {
      const active = button.dataset.filter === category;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    cards.forEach((card) => {
      const visible = category === 'all' || card.dataset.category === category;
      card.hidden = !visible;
      if (visible) visibleCount += 1;
    });
    groups.forEach((group) => {
      group.hidden = !Array.from(group.querySelectorAll('.article-feed-card[data-category]'))
        .some((card) => !card.hidden);
    });
    if (emptyMessage) emptyMessage.hidden = visibleCount !== 0;
    if (endMarker) endMarker.hidden = category !== 'all';
    if (updateUrl) {
      try {
        const url = new URL(window.location.href);
        if (category === 'all') url.searchParams.delete('category'); else url.searchParams.set('category', category);
        history.replaceState(null, '', url.pathname + url.search + url.hash);
      } catch (e) { /* ignore */ }
    }
  };

  filters.forEach((button) => {
    button.addEventListener('click', () => applyFilter(button.dataset.filter, true));
  });

  // /articles/?category=seo opens the page already filtered
  let initial = 'all';
  try { initial = new URL(window.location.href).searchParams.get('category') || 'all'; } catch (e) { /* ignore */ }
  applyFilter(initial, false);
})();
