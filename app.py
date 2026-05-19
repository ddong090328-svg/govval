import feedparser
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import time

app = Flask(__name__)

RSS_FEEDS = {
    "BBC": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/rss.xml",
    ],
    "The Guardian": [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/global-development/rss",
    ],
    "Reuters": [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://feeds.reuters.com/Reuters/worldNews",
    ],
}

DEFAULT_KEYWORDS = ["refugee", "crisis", "humanitarian", "duty", "international", "community"]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Global Dispatch — Conflict & Refugee Watch</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #0d0d0d;
    --paper: #f5f0e8;
    --accent: #c0392b;
    --muted: #6b6355;
    --rule: #d4cfc5;
    --tag-bbc: #bb1919;
    --tag-guardian: #005689;
    --tag-reuters: #ff8000;
    --highlight: #fff3cd;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--paper);
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 300;
    min-height: 100vh;
  }

  /* ── MASTHEAD ── */
  .masthead {
    border-bottom: 3px solid var(--ink);
    padding: 24px 48px 16px;
    position: relative;
  }
  .masthead-top {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .masthead h1 {
    font-family: 'Playfair Display', serif;
    font-weight: 900;
    font-size: clamp(2rem, 5vw, 3.6rem);
    letter-spacing: -1px;
    line-height: 1;
  }
  .masthead h1 span { color: var(--accent); }
  .edition-info {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--muted);
    text-align: right;
    line-height: 1.6;
  }
  .tagline {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 6px;
    border-top: 1px solid var(--rule);
    padding-top: 8px;
  }

  /* ── TOOLBAR ── */
  .toolbar {
    padding: 16px 48px;
    background: var(--ink);
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .search-wrap {
    flex: 1;
    min-width: 200px;
    position: relative;
  }
  .search-wrap svg {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.5;
  }
  #searchInput {
    width: 100%;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.2);
    color: #fff;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
    padding: 9px 12px 9px 38px;
    outline: none;
    transition: border-color 0.2s;
  }
  #searchInput::placeholder { color: rgba(255,255,255,0.35); }
  #searchInput:focus { border-color: rgba(255,255,255,0.6); }

  .source-filters {
    display: flex;
    gap: 6px;
  }
  .src-btn {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    padding: 6px 12px;
    border: 1px solid rgba(255,255,255,0.25);
    background: transparent;
    color: rgba(255,255,255,0.6);
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .src-btn:hover, .src-btn.active {
    background: rgba(255,255,255,0.12);
    color: #fff;
    border-color: rgba(255,255,255,0.5);
  }
  .src-btn.active { font-weight: 500; }

  .refresh-btn {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    padding: 8px 18px;
    background: var(--accent);
    border: none;
    color: #fff;
    cursor: pointer;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    transition: opacity 0.2s, transform 0.15s;
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .refresh-btn:hover { opacity: 0.85; }
  .refresh-btn:active { transform: scale(0.97); }
  .refresh-btn.loading svg { animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── STATUS BAR ── */
  .status-bar {
    padding: 8px 48px;
    border-bottom: 1px solid var(--rule);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  #statusMsg { }
  #countMsg { }

  /* ── KEYWORD CHIPS ── */
  .kw-strip {
    padding: 10px 48px;
    border-bottom: 1px solid var(--rule);
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }
  .kw-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-right: 4px;
  }
  .kw-chip {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    padding: 3px 9px;
    border: 1px solid var(--ink);
    background: transparent;
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: 0.03em;
  }
  .kw-chip:hover, .kw-chip.active {
    background: var(--ink);
    color: var(--paper);
  }

  /* ── NEWS GRID ── */
  .news-container {
    padding: 24px 48px 48px;
    max-width: 1400px;
    margin: 0 auto;
  }
  .news-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 0;
    border-top: 2px solid var(--ink);
    border-left: 1px solid var(--rule);
  }
  .news-item {
    padding: 20px 22px;
    border-right: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    display: flex;
    flex-direction: column;
    gap: 10px;
    transition: background 0.15s;
    animation: fadeUp 0.35s ease both;
    position: relative;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .news-item:hover { background: rgba(0,0,0,0.03); }
  .news-item a {
    text-decoration: none;
    color: inherit;
    display: block;
  }

  .item-meta {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .source-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    padding: 2px 7px;
    color: #fff;
  }
  .source-tag.bbc      { background: var(--tag-bbc); }
  .source-tag.guardian { background: var(--tag-guardian); }
  .source-tag.reuters  { background: var(--tag-reuters); }

  .item-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: var(--muted);
  }

  .item-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.02rem;
    font-weight: 700;
    line-height: 1.4;
    color: var(--ink);
  }
  .news-item:hover .item-title { color: var(--accent); }
  .item-title mark {
    background: var(--highlight);
    color: var(--accent);
    padding: 0 2px;
  }

  .item-summary {
    font-size: 0.8rem;
    color: var(--muted);
    line-height: 1.55;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .item-arrow {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: var(--accent);
    opacity: 0;
    transition: opacity 0.15s;
    margin-top: auto;
    letter-spacing: 0.05em;
  }
  .news-item:hover .item-arrow { opacity: 1; }

  /* ── EMPTY / ERROR ── */
  .empty-state {
    grid-column: 1/-1;
    padding: 60px 20px;
    text-align: center;
  }
  .empty-state .big { font-family: 'Playfair Display', serif; font-size: 2rem; color: var(--muted); }
  .empty-state .sub { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--muted); margin-top: 8px; }

  .skeleton {
    background: linear-gradient(90deg, var(--rule) 25%, #e8e3d9 50%, var(--rule) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.2s infinite;
    border-radius: 2px;
    height: 14px;
    margin-bottom: 8px;
  }
  @keyframes shimmer { to { background-position: -200% 0; } }

  @media (max-width: 600px) {
    .masthead, .toolbar, .status-bar, .kw-strip, .news-container { padding-left: 16px; padding-right: 16px; }
    .news-grid { border-left: none; }
    .news-item { border-right: none; }
  }
</style>
</head>
<body>

<header class="masthead">
  <div class="masthead-top">
    <h1>Global <span>Dispatch</span></h1>
    <div class="edition-info">
      <div id="editionDate">—</div>
      <div>Conflict &amp; Refugee Watch</div>
    </div>
  </div>
  <div class="tagline">Live headlines · BBC · The Guardian · Reuters</div>
</header>

<div class="toolbar">
  <div class="search-wrap">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
    <input type="text" id="searchInput" placeholder="Search headlines…" autocomplete="off">
  </div>

  <div class="source-filters">
    <button class="src-btn active" data-src="all">All</button>
    <button class="src-btn" data-src="BBC">BBC</button>
    <button class="src-btn" data-src="The Guardian">Guardian</button>
    <button class="src-btn" data-src="Reuters">Reuters</button>
  </div>

  <button class="refresh-btn" id="refreshBtn" onclick="fetchNews()">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polyline points="23 4 23 10 17 10"/>
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    </svg>
    Refresh
  </button>
</div>

<div class="status-bar">
  <span id="statusMsg">Loading latest headlines…</span>
  <span id="countMsg"></span>
</div>

<div class="kw-strip">
  <span class="kw-label">Keywords:</span>
  {% for kw in keywords %}
  <button class="kw-chip" onclick="applyKeyword(this)" data-kw="{{ kw }}">{{ kw }}</button>
  {% endfor %}
  <button class="kw-chip" style="border-style:dashed; opacity:0.5" onclick="clearKeyword()">✕ clear</button>
</div>

<div class="news-container">
  <div class="news-grid" id="newsGrid">
    <!-- skeleton placeholders -->
    {% for _ in range(6) %}
    <div class="news-item">
      <div class="skeleton" style="width:40%; height:10px;"></div>
      <div class="skeleton" style="width:90%; height:18px;"></div>
      <div class="skeleton" style="width:80%; height:18px;"></div>
      <div class="skeleton" style="width:60%; height:10px;"></div>
    </div>
    {% endfor %}
  </div>
</div>

<script>
let allItems = [];
let activeSource = 'all';
let activeKeyword = '';

function slugSource(src) {
  if (src.includes('BBC')) return 'bbc';
  if (src.includes('Guardian')) return 'guardian';
  if (src.includes('Reuters')) return 'reuters';
  return 'bbc';
}

function highlight(text, term) {
  if (!term) return text;
  const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(re, '<mark>$1</mark>');
}

function renderGrid() {
  const grid = document.getElementById('newsGrid');
  const search = document.getElementById('searchInput').value.trim().toLowerCase();
  const filterTerm = activeKeyword || search;

  let items = [...allItems];

  if (activeSource !== 'all') {
    items = items.filter(i => i.source === activeSource);
  }
  if (filterTerm) {
    items = items.filter(i =>
      (i.title || '').toLowerCase().includes(filterTerm) ||
      (i.summary || '').toLowerCase().includes(filterTerm)
    );
  }

  document.getElementById('countMsg').textContent = `${items.length} headline${items.length !== 1 ? 's' : ''}`;

  if (items.length === 0) {
    grid.innerHTML = `<div class="empty-state">
      <div class="big">No headlines found</div>
      <div class="sub">Try a different keyword or refresh</div>
    </div>`;
    return;
  }

  grid.innerHTML = items.map((item, i) => {
    const slug = slugSource(item.source);
    const titleHtml = highlight(item.title || 'Untitled', filterTerm);
    const summary = item.summary ? item.summary.replace(/<[^>]+>/g, '').slice(0, 140) + '…' : '';
    return `
    <div class="news-item" style="animation-delay:${i * 0.03}s">
      <a href="${item.link}" target="_blank" rel="noopener">
        <div class="item-meta">
          <span class="source-tag ${slug}">${item.source}</span>
          <span class="item-date">${item.date || ''}</span>
        </div>
        <div class="item-title">${titleHtml}</div>
        ${summary ? `<div class="item-summary">${summary}</div>` : ''}
        <div class="item-arrow">Read full story →</div>
      </a>
    </div>`;
  }).join('');
}

async function fetchNews() {
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('loading');
  btn.disabled = true;
  document.getElementById('statusMsg').textContent = 'Fetching latest headlines…';

  try {
    const resp = await fetch('/api/news');
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    allItems = data.items;
    document.getElementById('statusMsg').textContent =
      `Last updated: ${data.updated}`;
    renderGrid();
  } catch (e) {
    document.getElementById('statusMsg').textContent = 'Failed to fetch — check your connection.';
    document.getElementById('newsGrid').innerHTML =
      `<div class="empty-state"><div class="big">Could not load</div><div class="sub">${e.message}</div></div>`;
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

function applyKeyword(el) {
  document.querySelectorAll('.kw-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  activeKeyword = el.dataset.kw;
  document.getElementById('searchInput').value = '';
  renderGrid();
}

function clearKeyword() {
  document.querySelectorAll('.kw-chip').forEach(c => c.classList.remove('active'));
  activeKeyword = '';
  renderGrid();
}

document.querySelectorAll('.src-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.src-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeSource = btn.dataset.src;
    renderGrid();
  });
});

document.getElementById('searchInput').addEventListener('input', () => {
  activeKeyword = '';
  document.querySelectorAll('.kw-chip').forEach(c => c.classList.remove('active'));
  renderGrid();
});

// init
document.getElementById('editionDate').textContent = new Date().toLocaleDateString('en-GB', {
  weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
});
fetchNews();
</script>
</body>
</html>
"""


def parse_date(entry):
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6]).strftime("%d %b %Y, %H:%M")
            except Exception:
                pass
    return ""


def fetch_all_feeds():
    items = []
    for source, urls in RSS_FEEDS.items():
        fetched = False
        for url in urls:
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    for entry in feed.entries[:25]:
                        items.append({
                            "source": source,
                            "title": entry.get("title", ""),
                            "link": entry.get("link", "#"),
                            "date": parse_date(entry),
                            "summary": entry.get("summary", ""),
                        })
                    fetched = True
                    break
            except Exception:
                continue
        if not fetched:
            print(f"[WARN] Could not fetch any feed for {source}")

    # Sort by date descending (best effort)
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, keywords=DEFAULT_KEYWORDS)


@app.route("/api/news")
def api_news():
    items = fetch_all_feeds()
    return jsonify({
        "items": items,
        "updated": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
        "count": len(items),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
