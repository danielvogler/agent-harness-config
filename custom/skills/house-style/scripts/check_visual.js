#!/usr/bin/env node
// Render a page, an SVG or an image and fail on what made visuals look bland or sloppy.
//
//   node check_visual.js <url | page.html | picture.svg | shot.png> [--width 1440]
//                        [--height 900] [--dark] [--shot first-screen.png] [--json]
//                        [--shown 830]   (SVG: the width it is shown at)
//
// Needs playwright-core and an installed Chrome (CHROME_PATH overrides the default path).
// Exit 0 when every check passes, 1 when one fails, 2 when it could not be rendered.
//
// Page (URL or .html), on the first screen unless said otherwise:
//   marks      coloured marks on the screen, and on at least half of its rows and cards;
//              on the whole page, at least one coloured element per two rows and items
//   exhibits   whole page: every raster and card grid carries a coloured mark on most of
//              its chips or cards (neutral and tidy is the bland failure); a table without
//              a coloured column is named in the note, and its rows count to the floor
//   hues       at most 3 hue families on any one screen of the whole page, the accent one of them (logos and
//              pictures hidden); a ramp of one hue is one family
//   nav        at most 9 top-level navigation items (a named group counts as one)
//   head       an eyebrow, a title of at most two lines, and text below it
//   contents   left-column labels of at most two lines and about 40 characters
//   headrows   at most 4 text rows above the first exhibit (nav and the left contents column
//              not counted)
//   counts     the title does not open with a number; no number in 3 or more head elements
//              (eyebrow, title, points, section titles, KPI values, list heads)
//   overflow   no clipped or ellipsis-truncated text, no sideways scroll (whole page)
//   phrases    none of the banned phrases (whole page)
// SVG: marks (coloured shapes), hues (at most 4 families, the part colours, embedded pictures hidden),
//   overflow (a label running out of the box it sits in, or off the canvas), phrases,
//   labels (at the width the picture is shown, --shown 830 for a README column by default: the
//   median label at least 8px, aim 11, none below 5px), width (at most 1320px wide).
// An element marked data-visual-skip="hues" (a colour-token sheet) is left out of the hue count.
// PNG or JPEG: hues only (at most 3 families; logos count, so read it as a hint).
//
// Banned phrases come from ../references/banned-phrases.txt plus the `visual.extraPhrases`
// list of the nearest .house-style.json (from the file's folder, or the working
// directory for a URL, up to the git root).
'use strict';
const path = require('path');
const fs = require('fs');

let chromium;
try { ({ chromium } = require('playwright-core')); } catch (e) {
  console.error('playwright-core is missing: npm install --no-save playwright-core');
  process.exit(2);
}

const CHROME = process.env.CHROME_PATH || {
  darwin: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  linux: '/usr/bin/google-chrome',
  win32: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
}[process.platform];

const MIN_MARKS = 5;          // coloured elements on the first screen
const MIN_SVG_MARKS = 2;      // a banner has its dot and one more
const MIN_MARKED_SHARE = 0.5; // of the rows and cards on the first screen
const MIN_EXHIBIT_SHARE = 0.6; // of the rows, chips or cards of one exhibit
const MIN_EXHIBIT_ITEMS = 3;   // smaller exhibits are not judged
const MAX_HEAD_ROWS = 4;        // text rows above the first exhibit
const MAX_TOC_LINES = 2;        // a left-column label wraps to at most two lines
const MAX_TOC_CHARS = 48;       // and is a short label, not the section's whole title
const MAX_NUMBER_HEADS = 2;     // the same number in this many head elements is the limit
const MARKS_PER_ITEM = 0.5;    // page floor: coloured elements per row, chip or card
const MAX_FULL_HEIGHT = 12000; // px of the page the hue count looks at
const MAX_HUE_FAMILIES = { page: 3, svg: 4, image: 3, monitoring: 5 }; // a diagram keeps its four part colours // the accent counts as one; a one-hue ramp is one
const MAX_NAV_ITEMS = 9;
const MAX_TITLE_LINES = 2;
const MIN_SHOWN_LABEL = 7.5;    // px the median label keeps at the width it is shown (aim for 11)
const MIN_SHOWN_ANY = 5;        // px below which any single label is unreadable
const MAX_SVG_WIDTH = 1320;     // a README picture wider than this shrinks its labels away

const PHRASES_FILE = path.join(__dirname, '..', 'references', 'banned-phrases.txt');

// One regular expression per line, case-insensitive; `#` starts a comment.
function bannedPhrases(target) {
  const lines = fs.readFileSync(PHRASES_FILE, 'utf8').split('\n').map(l => l.replace(/\s+#.*$|^#.*$/, '').trim()).filter(Boolean);
  const extra = (houseStyle(target).visual || {}).extraPhrases || [];
  const escape = w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return lines.concat(extra.map(w => `\\b${escape(w)}\\b`)).map(src => src.startsWith('head: ')
    ? { source: src.slice(6), flags: 'i', head: true } : { source: src, flags: 'i' });
}

function houseStyle(target) {
  let dir = /^[a-z]+:\/\//i.test(target) ? process.cwd() : path.dirname(path.resolve(target.split('#')[0]));
  for (;;) {
    const f = path.join(dir, '.house-style.json');
    if (fs.existsSync(f)) {
      try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { console.error(`${f}: not valid JSON`); process.exit(2); }
    }
    if (fs.existsSync(path.join(dir, '.git')) || path.dirname(dir) === dir) return {};
    dir = path.dirname(dir);
  }
}

function arg(name, dflt) {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : dflt;
}

function toUrl(target) {
  if (/^[a-z]+:\/\//i.test(target)) return target;
  const [file, hash] = target.split('#');
  return 'file://' + path.resolve(file) + (hash ? '#' + hash : '');
}

// In the page: everything except the pixel hues.
function inspect({ vh, banned, MIN }) {
  // color-mix() computes to color(srgb r g b / a) with channels from 0 to 1.
  const rgb = s => { const m = s && s.match(/[\d.]+/g); if (!m) return null; const v = m.map(Number);
    return s.startsWith('color(srgb') ? v.map((x, i) => i < 3 ? x * 255 : x) : v; };
  const chromatic = s => {
    const c = rgb(s); if (!c || (c.length > 3 && c[3] < 0.15)) return false;
    const [r, g, b] = c.slice(0, 3).map(v => v / 255), mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    const l = (mx + mn) / 2; if (mx === mn || l < 0.12 || l > 0.95) return false;
    // A saturated colour, or a clear tint of one (a muted accent mixed into white keeps its
    // hue but loses HSL saturation); greys and paper tints stay below both.
    const d = mx - mn; return (l <= 0.92 && (l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn)) >= 0.25) || d >= 0.08;
  };
  const visible = el => {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width >= 2 && r.height >= 2 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity !== 0;
  };
  const onScreen = el => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < vh; };
  const isMark = el => {
    if (['IMG', 'svg', 'CANVAS', 'PICTURE'].includes(el.tagName)) return false;
    // A group dot encodes membership even in ink or grey (the legend names it).
    if (/(^|\s)grp-\d(\s|$)/.test(typeof el.className === 'string' ? el.className : '')) return true;
    const cs = getComputedStyle(el);
    const text = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    const border = ['Top', 'Right', 'Bottom', 'Left'].some(s => parseFloat(cs['border' + s + 'Width']) > 0 && chromatic(cs['border' + s + 'Color']));
    // A dot drawn by ::before or ::after is a mark too.
    const pseudo = ['::before', '::after'].some(p => { const ps = getComputedStyle(el, p);
      return ps.content !== 'none' && ps.content !== 'normal' && (chromatic(ps.backgroundColor) || chromatic(ps.borderTopColor) && parseFloat(ps.borderTopWidth) > 0 || (ps.content.length > 2 && chromatic(ps.color))); });
    return (text && chromatic(cs.color)) || chromatic(cs.backgroundColor) || border || pseudo ||
      (el.tagName !== 'svg' && !!el.closest('svg') && (chromatic(cs.fill) || chromatic(cs.stroke)));
  };
  const out = {};
  const all = [...document.querySelectorAll('body *')].filter(visible);
  const first = all.filter(onScreen);
  out.marks = first.filter(isMark).length;

  // Rows and cards on the first screen, and how many carry a coloured mark.
  // The header (its .top-row, the nav) is frame, not content.
  const units = first.filter(el => !el.closest('header, nav, .top') && (
    (el.tagName === 'TR' && el.closest('tbody') && el.cells.length > 1) ||
    (el.tagName !== 'TR' && /(^|[\s_-])(card|tile|opt|item|row)([\s_-]|$)/i.test(typeof el.className === 'string' ? el.className : '')
      && el.getBoundingClientRect().height > 40)));
  const marked = units.filter(u => isMark(u) || [...u.querySelectorAll('*')].some(isMark));
  out.units = units.length; out.markedUnits = marked.length;

  // Exhibits, whole page. A table's body rows, a raster's chips (short labels in small
  // styled boxes inside a grid), a grid's cards. An empty state is not judged.
  const skip = el => el.closest('[class*=empty], nav, header, footer, .legend');
  const markedIn = u => isMark(u) || [...u.querySelectorAll('*')].some(e => visible(e) && isMark(e));
  out.exhibits = [];
  let items = 0;
  const judge = (name, list) => {
    const xs = list.filter(u => !skip(u));
    items += xs.length;
    if (xs.length < MIN.items) return;
    const m = xs.filter(markedIn).length;
    out.exhibits.push({ name, items: xs.length, marked: m, soft: name.startsWith('table') });
  };
  for (const t of all.filter(el => el.tagName === 'TABLE'))
    judge('table "' + ((t.querySelector('th') || t).innerText || '').trim().slice(0, 30) + '"',
      [...t.querySelectorAll('tbody tr')].filter(r => r.cells.length > 1 && ![...r.cells].some(c => c.colSpan > 1) && visible(r)));
  const chip = el => {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el), t = (el.textContent || '').trim();
    return t.length >= 1 && t.length <= 5 && r.width <= 64 && r.height <= 36 && !el.children.length &&
      (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || parseFloat(cs.borderTopWidth) > 0);
  };
  const grids = all.filter(el => getComputedStyle(el).display.includes('grid') && el.children.length >= MIN.items && !skip(el));
  for (const g of grids) {
    const chips = [...g.querySelectorAll('*')].filter(e => visible(e) && chip(e));
    if (chips.length >= 6) { judge('raster of ' + chips.length + ' chips', chips); continue; }
    const cards = [...g.children].filter(c => visible(c) && c.getBoundingClientRect().height > 60 && (() => {
      const cs = getComputedStyle(c); return parseFloat(cs.borderTopWidth) > 0 || cs.backgroundColor !== 'rgba(0, 0, 0, 0)'; })());
    if (cards.length >= MIN.items) judge('grid of ' + cards.length + ' cards', cards);
  }
  out.items = items;
  out.allMarks = all.filter(isMark).length;

  // Navigation: the first nav (or header) with links; a named group counts as one item.
  const nav = [...document.querySelectorAll('nav, [role=navigation], header')].find(n => visible(n) && n.querySelectorAll('a, button').length > 1);
  if (nav) {
    // The logo (a link holding only a picture, or the .brand link) is not a nav item.
    const isLogo = a => a.matches('.brand, [class*=logo]') || (!a.innerText.trim() && !!a.querySelector('img, svg'));
    const links = [...nav.querySelectorAll('a, button')].filter(a => visible(a) && !isLogo(a));
    // Links that share a parent form a set. A set with its own label (a group name) is one
    // item, so is a set of up to three (an area switch); otherwise every link counts.
    const sets = new Map();
    for (const a of links) sets.set(a.parentElement, (sets.get(a.parentElement) || []).concat(a));
    // A labelled group inside the nav (the open group's pages) is one item; the nav's own label is not.
    const labelled = p => (!p.matches('nav, header, [role=navigation]') && (p.hasAttribute('aria-label') || p.hasAttribute('aria-labelledby'))) ||
      [...p.children].some(c => !c.matches('a, button') && !c.querySelector('a, button') && c.innerText && c.innerText.trim());
    out.navItems = [...sets.entries()].reduce((n, [p, ls]) => n + (ls.length <= 3 || labelled(p) ? 1 : ls.length), 0);
  } else out.navItems = 0;

  // Page head: the biggest text near the top is the title.
  const texts = first.filter(el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 3) && el.getBoundingClientRect().top < vh * 0.6 && !el.closest('nav, header'));
  // The title is a sentence of at least three words: an h1, else a heading-like class, else
  // the biggest such text. A big number or a wordmark is not a title.
  const words = el => el.innerText.trim().split(/\s+/).length >= 3;
  const size = el => parseFloat(getComputedStyle(el).fontSize);
  const byClass = el => /(^|[\s_-])(shows|title|headline|page-title)([\s_-]|$)/i.test(typeof el.className === 'string' ? el.className : '');
  const cands = first.filter(el => !el.closest('nav, header') && el.getBoundingClientRect().top < vh * 0.6 && el.innerText && words(el));
  const title = cands.find(el => el.tagName === 'H1') || cands.find(byClass) ||
    texts.filter(words).sort((a, b) => size(b) - size(a))[0];
  out.head = { title: null };
  if (title) {
    const r = title.getBoundingClientRect(), cs = getComputedStyle(title);
    const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.25;
    const near = (el, above) => { const q = el.getBoundingClientRect(); return above ? q.bottom <= r.top + 2 && q.bottom > r.top - 90 : q.top >= r.bottom - 2 && q.top < r.bottom + 120; };
    const eyebrow = texts.concat(first.filter(el => !el.closest('nav, header'))).some(el => el !== title && near(el, true) &&
      (getComputedStyle(el).textTransform === 'uppercase' || parseFloat(getComputedStyle(el).letterSpacing) > 0.5) && parseFloat(getComputedStyle(el).fontSize) <= 14);
    const below = first.some(el => el !== title && !title.contains(el) && near(el, false) && el.innerText && el.innerText.trim().length > 10 && parseFloat(getComputedStyle(el).fontSize) < parseFloat(cs.fontSize));
    out.head = { title: title.innerText.trim().slice(0, 120), lines: Math.round(r.height / lh), eyebrow, below };
  }

  // Counts in the head: a title that opens with a number is a count, not a subject, and a
  // number belongs in one place (a KPI or the points line), not in the eyebrow, title,
  // points, section titles and list heads at once.
  const NUM = /\b\d+(?:[.,]\d+)?\b/g;
  const headEls = [...document.querySelectorAll('h1, h2, h3, [class*=eyebrow], [class*=kicker], [class*=points], .weigh, [class*=sec-title], .kpi b, .toplist .cap, .toplist .head')]
    .filter(e => visible(e) && !e.closest('nav, header, footer') && !e.parentElement.closest('h1, h2, h3, [class*=eyebrow], [class*=points], [class*=sec-title], .kpi b'));
  const seen = new Map();
  for (const e of headEls) for (const n of new Set(e.innerText.match(NUM) || [])) seen.set(n, (seen.get(n) || 0) + 1);
  // Text rows above the first exhibit: the head is eyebrow, title and one points line.
  const EXHIBIT = 'table, .raster, .grid, .map, .fig, figure, canvas, [class*=chart], [class*=exhibit], .with-top, section.sec';
  const ex = [...document.querySelectorAll(EXHIBIT)].filter(e => visible(e) && !e.closest('header, footer, .side, aside'))
    .sort((a, b2) => a.getBoundingClientRect().top - b2.getBoundingClientRect().top)[0];
  const exTop = ex ? ex.getBoundingClientRect().top : Infinity;
  // Count line boxes, not elements: every text line above the exhibit, merged by height.
  const tops = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) {
    const host = t.parentElement;
    if (!t.textContent.trim() || !host || !visible(host) || host.closest('header, footer, nav, aside, .side') || (ex && ex.contains(host))) continue;
    const range = document.createRange(); range.selectNodeContents(t);
    for (const q of range.getClientRects()) if (q.height > 4 && q.bottom <= exTop + 1) tops.push(q.top + q.height / 2);
  }
  tops.sort((a, b2) => a - b2);
  let rows = 0, last = -Infinity;
  for (const y of tops) { if (y - last > 8) rows++; last = y; }
  out.headRows = ex ? rows : null;

  out.counts = { titleNumber: !!(out.head.title && /^\s*\d/.test(out.head.title)),
    repeated: [...seen.entries()].filter(([, c]) => c >= MIN.repeat).map(([n, c]) => `${n} in ${c} heads`) };

  // Overflow, whole page: ellipsis that cuts text, clipped text boxes, sideways scroll.
  out.overflow = [];
  for (const el of all) {
    const cs = getComputedStyle(el);
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!hasText) continue;
    const clipsX = el.scrollWidth > el.clientWidth + 1 && /hidden|clip/.test(cs.overflowX + cs.overflow);
    const clipsY = el.scrollHeight > el.clientHeight + 2 && /hidden|clip/.test(cs.overflowY + cs.overflow) && cs.webkitLineClamp !== 'none';
    if (clipsX || clipsY || (cs.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1))
      out.overflow.push(el.innerText.trim().slice(0, 60));
  }
  if (document.documentElement.scrollWidth > innerWidth + 1) out.overflow.push(`page is ${document.documentElement.scrollWidth}px wide`);
  out.overflow = out.overflow.slice(0, 8);

  // `head:` phrases are checked in titles, headings and eyebrows only ("A wins over B" is
  // fine in a sentence on precedence, not as a page's headline).
  const body = document.body.innerText;
  const heads = [...document.querySelectorAll('h1, h2, h3, [class*=title], [class*=shows], [class*=eyebrow], [class*=kicker]')].map(e => e.innerText).join('\n');
  // Left column: each section label is a short label, at most two lines.
  out.tocLong = [...document.querySelectorAll('.toc a, nav.toc a, [class*=toc] li a')].filter(visible).map(a => {
    const t = a.querySelector('span') || a, cs = getComputedStyle(t);
    const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.3;
    return { text: t.innerText.trim(), lines: Math.round(t.getBoundingClientRect().height / lh) };
  }).filter(x => x.lines > MIN.tocLines || x.text.length > MIN.tocChars).map(x => x.text.slice(0, 50));
  out.phrases = banned.map(x => [(x.head ? heads : body), new RegExp(x.source, x.flags)]).map(([t, re]) => (t.match(re) || [])[0]).filter(Boolean);
  out.monitoring = document.documentElement.dataset.board === "monitoring";
  return out;
}

// In the page: decode the screenshot on a canvas and count hue families.
// A tall page is cut into screens of `slice` px; the result is the most colourful screen,
// since the rule is about what one screen shows.
function hueFamilies(arg) {
  const { url, slice } = typeof arg === 'string' ? { url: arg, slice: 0 } : arg;
  const STEP = 10, BINS = 36, MIN_SHARE = 0.0005;
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
      const g = c.getContext('2d'); g.drawImage(img, 0, 0);
      const h = slice > 0 ? slice : img.height, results = [];
      for (let y = 0; y < img.height; y += h) results.push(count(g.getImageData(0, y, c.width, Math.min(h, img.height - y)).data, y));
      resolve(results.sort((a, b) => b.families - a.families)[0]);
    };
    img.src = url;
    function count(d, y) {
      const bins = new Array(BINS).fill(0);
      let n = 0;
      for (let i = 0; i < d.length; i += 16) {
        n++;
        const r = d[i] / 255, gg = d[i + 1] / 255, b = d[i + 2] / 255, mx = Math.max(r, gg, b), mn = Math.min(r, gg, b), l = (mx + mn) / 2;
        if (mx === mn || l < 0.12 || l > 0.92) continue;
        const dd = mx - mn, s = l > 0.5 ? dd / (2 - mx - mn) : dd / (mx + mn);
        if (s < 0.25) continue;
        const h = mx === r ? (gg - b) / dd + (gg < b ? 6 : 0) : mx === gg ? (b - r) / dd + 2 : (r - gg) / dd + 4;
        bins[Math.floor(h * 60 / STEP) % BINS]++;
      }
      // A run of neighbouring 10-degree bins is one family per 60 degrees it spans: a
      // blue-to-purple ramp is one colour, a rainbow is several.
      const on = bins.map(v => v / n > MIN_SHARE);
      let fam = 0;
      const start = on.findIndex((v, k) => !v && on[(k + 1) % BINS]);
      if (on.every(Boolean)) fam = 6;
      else if (start >= 0) {
        let run = 0;
        for (let j = 1; j <= BINS; j++) {
          const k = (start + j) % BINS;
          if (on[k]) run++;
          if (!on[k] || j === BINS) { fam += Math.ceil(run * STEP / 60); run = 0; }
        }
      }
      const shares = [];
      for (let k = 0; k < BINS; k++) if (on[k]) shares.push(`${k * STEP}:${(100 * bins[k] / n).toFixed(2)}%`);
      if (y > 0) shares.push(`(screen at ${y}px)`);
      return { families: fam, bins: shares };
    }
  });
}

// In an SVG document: coloured shapes, labels that leave their box, banned phrases.
function inspectSvg({ banned, shown }) {
  const svg = document.querySelector('body > svg') || document.querySelector('svg');
  // color-mix() computes to color(srgb r g b / a) with channels from 0 to 1.
  const rgb = s => { const m = s && s.match(/[\d.]+/g); if (!m) return null; const v = m.map(Number);
    return s.startsWith('color(srgb') ? v.map((x, i) => i < 3 ? x * 255 : x) : v; };
  const chromatic = s => {
    const c = rgb(s); if (!c || (c.length > 3 && c[3] < 0.15)) return false;
    const [r, g, b] = c.slice(0, 3).map(v => v / 255), mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    const l = (mx + mn) / 2; if (mx === mn || l < 0.12 || l > 0.95) return false;
    // A saturated colour, or a clear tint of one (a muted accent mixed into white keeps its
    // hue but loses HSL saturation); greys and paper tints stay below both.
    const d = mx - mn; return (l <= 0.92 && (l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn)) >= 0.25) || d >= 0.08;
  };
  const shapes = [...svg.querySelectorAll('rect, circle, ellipse, path, line, polyline, polygon, text, tspan')]
    .filter(el => !el.closest('defs, mask, clipPath, pattern, marker'));
  const marks = shapes.filter(el => { const cs = getComputedStyle(el); return chromatic(cs.fill) || (cs.stroke !== 'none' && chromatic(cs.stroke)); }).length;
  const canvas = svg.getBoundingClientRect();
  // Only drawn boxes: drawio adds invisible hit areas (no fill, no stroke) round its labels.
  const drawn = r => { const cs = getComputedStyle(r); return !(cs.fill === 'none' || cs.fillOpacity === '0') || (cs.stroke !== 'none' && cs.strokeOpacity !== '0'); };
  const boxes = [...svg.querySelectorAll('rect')].filter(r => !r.closest('defs, mask, clipPath, pattern') && drawn(r)).map(r => r.getBoundingClientRect())
    .filter(b => b.width > 20 && b.height > 12 && b.width < canvas.width * 0.95);
  const overflow = [];
  for (const t of svg.querySelectorAll('text')) {
    if (t.closest('defs, mask, clipPath') || !t.textContent.trim()) continue;
    const b = t.getBoundingClientRect(), cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    if (b.left < canvas.left - 1 || b.right > canvas.right + 1) { overflow.push(t.textContent.trim().slice(0, 50) + ' (off the canvas)'); continue; }
    // The smallest box the label starts in is its box; the label must end inside it too.
    const home = boxes.filter(q => b.left >= q.left - 1 && b.left < q.right && cy > q.top && cy < q.bottom).sort((x, y) => x.width * x.height - y.width * y.height)[0];
    if (home && (b.left < home.left - 1 || b.right > home.right + 1)) overflow.push(t.textContent.trim().slice(0, 50));
  }
  // drawio keeps its labels as HTML inside foreignObject.
  for (const el of svg.querySelectorAll('foreignObject *')) {
    if ([...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && el.scrollWidth > el.clientWidth + 1 && /hidden|clip/.test(getComputedStyle(el).overflow))
      overflow.push(el.textContent.trim().slice(0, 50));
  }
  const text = svg.textContent;
  const phrases = banned.map(x => new RegExp(x.source, x.flags)).map(re => (text.match(re) || [])[0]).filter(Boolean);
  // Labels at the width the picture is shown: its own width scaled down to `shown`.
  const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal.width : canvas.width;
  const own = parseFloat(svg.getAttribute('width')) || vb;
  const scale = Math.min(1, shown / own);
  const sizes = [];
  for (const t of svg.querySelectorAll('text, foreignObject div, foreignObject span')) {
    if (t.closest('defs, mask, clipPath') || ![...t.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const ctm = t.getScreenCTM ? t.getScreenCTM() : null;
    const px = parseFloat(getComputedStyle(t).fontSize) * (ctm ? Math.hypot(ctm.a, ctm.b) : canvas.width / vb) * (own / canvas.width) * scale;
    sizes.push([px, t.textContent.trim().slice(0, 30)]);
  }
  sizes.sort((a, b) => a[0] - b[0]);
  return { marks, overflow: overflow.slice(0, 8), phrases, own: Math.round(own), scale: +scale.toFixed(2),
    smallest: sizes.length ? { px: +sizes[0][0].toFixed(1), text: sizes[0][1] } : null,
    median: sizes.length ? +sizes[Math.floor(sizes.length / 2)][0].toFixed(1) : null };
}

const kindOf = t => /\.svg$/i.test(t.split('#')[0]) ? 'svg' : /\.(png|jpe?g|webp)$/i.test(t) ? 'image' : 'page';

async function main() {
  const target = process.argv[2];
  if (!target || target.startsWith('--')) {
    console.error('usage: node check_visual.js <url | page.html | picture.svg | shot.png> [--width 1440] [--height 900] [--dark] [--shot out.png] [--json]');
    process.exit(2);
  }
  const kind = kindOf(target), banned = bannedPhrases(target);
  const width = +arg('--width', 1440), height = +arg('--height', 900);
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce',
      colorScheme: process.argv.includes('--dark') ? 'dark' : 'light' });
    if (kind === 'image') {
      const mime = /\.png$/i.test(target) ? 'png' : /\.webp$/i.test(target) ? 'webp' : 'jpeg';
      const hues = await page.evaluate(hueFamilies, `data:image/${mime};base64,` + fs.readFileSync(target).toString('base64'));
      return report(target, [hueCheck(hues, kind)]);
    }
    if (kind === 'svg') {
      // A screenshot of a bare SVG document hangs in headless Chrome; inline it in a page.
      const markup = fs.readFileSync(target.split('#')[0], 'utf8').replace(/^\s*<\?xml[^>]*>/, '');
      await page.setContent(`<!doctype html><body style="margin:0">${markup}</body>`, { waitUntil: 'load', timeout: 30000 });
    } else await page.goto(toUrl(target), { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(800);
    const shot = arg('--shot');
    if (shot) fs.writeFileSync(shot, await page.screenshot({ timeout: 15000 }));
    const d = await page.evaluate(kind === 'svg' ? inspectSvg : inspect, { vh: height, banned, shown: +arg('--shown', 830), MIN: { items: MIN_EXHIBIT_ITEMS, repeat: MAX_NUMBER_HEADS + 1, tocLines: MAX_TOC_LINES, tocChars: MAX_TOC_CHARS } });
    // Logos and pictures carry their own colours; the hue check is about the visual's code.
    if (kind === 'svg') await page.evaluate(() => document.querySelectorAll('image, foreignObject img').forEach(e => e.setAttribute('visibility', 'hidden')));
    else {
      // A palette sheet or a picture gallery opts out with data-visual-skip="hues".
      await page.addStyleTag({ content: 'img, picture, canvas, video, svg image, [data-visual-skip~=hues] { visibility: hidden !important; }' });
      // An inline SVG of logo size is a logo. One wider than 300px is a chart: its series
      // follow the categorical palette of the dataviz rules, not the page's code.
      await page.evaluate(() => document.querySelectorAll('svg').forEach(e => { const r = e.getBoundingClientRect();
        if ((r.width <= 48 && r.height <= 48) || r.width > 300) e.style.visibility = 'hidden'; }));
    }
    // A page is counted over its whole length, so colour further down counts too.
    const tall = kind === 'page' ? await page.evaluate(() => document.documentElement.scrollHeight) : 0;
    const png = await page.screenshot({ timeout: 30000, fullPage: kind === 'page' && tall <= MAX_FULL_HEIGHT,
      clip: kind === 'page' && tall > MAX_FULL_HEIGHT ? { x: 0, y: 0, width, height: MAX_FULL_HEIGHT } : undefined });
    const hues = await page.evaluate(hueFamilies, { url: 'data:image/png;base64,' + png.toString('base64'), slice: kind === 'page' ? height : 0 });
    const checks = kind === 'svg'
      ? [['marks', d.marks >= MIN_SVG_MARKS, `${d.marks} coloured shapes (min ${MIN_SVG_MARKS})`], hueCheck(hues, kind),
        ['labels', !d.smallest || (d.median >= MIN_SHOWN_LABEL && d.smallest.px >= MIN_SHOWN_ANY),
          d.smallest ? `at the shown width (scale ${d.scale}) the median label is ${d.median}px (min ${MIN_SHOWN_LABEL}, aim 11), the smallest ${d.smallest.px}px (min ${MIN_SHOWN_ANY}): "${d.smallest.text}"` : 'no labels'],
        ['width', d.own <= MAX_SVG_WIDTH, `${d.own}px wide (max ${MAX_SVG_WIDTH})`]]
      : pageChecks(d, hues);
    checks.push(['overflow', d.overflow.length === 0, d.overflow.length ? 'clipped: ' + d.overflow.join(' | ') : 'nothing clipped'],
      ['phrases', d.phrases.length === 0, d.phrases.length ? 'banned: ' + d.phrases.join(', ') : 'none found']);
    report(target, checks);
  } finally {
    await browser.close();
  }
}

function hueCheck(hues, kind) {
  return ['hues', hues.families <= MAX_HUE_FAMILIES[kind], `${hues.families} hue families (max ${MAX_HUE_FAMILIES[kind]}): ${hues.bins.join(' ') || 'none'}`];
}

function pageChecks(d, hues) {
  const h = d.head;
  return [
    ['marks', d.marks >= MIN_MARKS && (d.units < 3 || d.markedUnits / d.units >= MIN_MARKED_SHARE),
      `${d.marks} coloured marks (min ${MIN_MARKS}); ${d.markedUnits}/${d.units} rows and cards carry one (min half)`],
    ['exhibits', d.exhibits.every(x => x.soft || x.marked / x.items >= MIN_EXHIBIT_SHARE) && d.allMarks >= Math.ceil(d.items * MARKS_PER_ITEM),
      `${d.allMarks} coloured elements on the page (min ${Math.ceil(d.items * MARKS_PER_ITEM)} for ${d.items} rows, chips and cards)` +
      (d.exhibits.length ? '; ' + d.exhibits.map(x => `${x.marked / x.items >= MIN_EXHIBIT_SHARE ? '' : x.soft ? 'no colour column in ' : 'UNMARKED '}${x.name}: ${x.marked}/${x.items}`).join(', ') : '')],
    hueCheck(hues, d.monitoring ? 'monitoring' : 'page'),
    ['nav', d.navItems <= MAX_NAV_ITEMS, `${d.navItems} top-level navigation items (max ${MAX_NAV_ITEMS}; group them)`],
    ['head', !!(h.title && h.lines <= MAX_TITLE_LINES && h.eyebrow && h.below),
      h.title ? `title "${h.title}" on ${h.lines} line(s); eyebrow ${h.eyebrow ? 'yes' : 'missing'}; text below ${h.below ? 'yes' : 'missing'}` : 'no title found'],
    ['headrows', d.headRows === null || d.headRows <= MAX_HEAD_ROWS,
      d.headRows === null ? 'no exhibit found' : `${d.headRows} text rows above the first exhibit (max ${MAX_HEAD_ROWS}: eyebrow, title, one points line; contents go to the left column, key numbers into the exhibit)`],
    ['contents', d.tocLong.length === 0,
      d.tocLong.length ? 'left-column labels too long (max 2 lines, about 40 characters; give the section a short label): ' + d.tocLong.join(' | ') : 'left-column labels short'],
    ['counts', !d.counts.titleNumber && d.counts.repeated.length === 0,
      d.counts.titleNumber ? 'the title opens with a number: name the subject in words, put the count in the points or a KPI'
        : d.counts.repeated.length ? 'the same number in 3 or more heads: ' + d.counts.repeated.join(', ') : 'no count title, no number repeated across the heads'],
  ];
}

function report(target, checks) {
  if (process.argv.includes('--json')) console.log(JSON.stringify({ target, checks: checks.map(([name, ok, note]) => ({ name, ok, note })) }, null, 1));
  else for (const [name, ok, note] of checks) console.log(`${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(8)} ${note}`);
  process.exitCode = checks.every(c => c[1]) ? 0 : 1;
}

main().catch(e => { console.error('could not render:', String(e).slice(0, 300)); process.exit(2); });
