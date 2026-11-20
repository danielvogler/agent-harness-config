// Every number chip explains itself: on hover it shows its id and the item's name.
// The names come from the page's own lists: a `.lines` or `.toplist` entry (id + bold name), a
// table row whose first cell is the id (the name from `td.name`, else the second cell),
// or an element with `data-id` and `data-name`. A chip with `title` already set is left
// alone. Load it at the end of the page: <script src="chips.js"></script>
(function () {
  'use strict';
  const names = new Map();
  const put = (id, name) => { id = (id || '').trim(); name = (name || '').trim(); if (id && name && !names.has(id)) names.set(id, name); };
  for (const el of document.querySelectorAll('[data-id][data-name]')) put(el.dataset.id, el.dataset.name);
  for (const li of document.querySelectorAll('.lines li, .toplist li')) {
    const chip = li.querySelector('.no, .n'), name = li.querySelector('b');
    if (chip && name) put(chip.textContent, name.textContent);
  }
  for (const tr of document.querySelectorAll('table tr')) {
    const cells = tr.querySelectorAll('td');
    if (cells.length < 2) continue;
    const name = tr.querySelector('td.name') || cells[1];
    if (name !== cells[0]) put(cells[0].textContent, name.textContent);
  }
  for (const chip of document.querySelectorAll('.n')) {
    if (chip.title) continue;
    const id = chip.textContent.trim();
    // A raster chip often shows only the number of an id like "R4": try both forms.
    const name = names.get(id) || [...names.keys()].filter(k => k.replace(/^\D+/, '') === id).map(k => names.get(k))[0];
    chip.title = name ? `${id} · ${name}` : id;
  }
})();
