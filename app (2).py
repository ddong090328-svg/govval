import streamlit as st
from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET
import re

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global Dispatch — Conflict & Refugee Watch",
    page_icon="🌍",
    layout="wide",
)

# ── RSS feeds ─────────────────────────────────────────────────────────────────
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

SOURCE_COLORS = {
    "BBC":          "#bb1919",
    "The Guardian": "#005689",
    "Reuters":      "#e07b00",
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1300px; }
.masthead { border-top: 4px solid #0d0d0d; border-bottom: 3px solid #0d0d0d; padding: 18px 0 14px; }
.masthead h1 { font-family:'Playfair Display',serif; font-weight:900; font-size:2.8rem; letter-spacing:-1px; line-height:1; margin:0; color:#0d0d0d; }
.masthead h1 span { color:#c0392b; }
.tagline { font-family:'IBM Plex Mono',monospace; font-size:0.65rem; color:#6b6355; letter-spacing:.1em; text-transform:uppercase; margin-top:6px; border-top:1px solid #d4cfc5; padding-top:6px; }
.card { border:1px solid #d4cfc5; border-top:3px solid #0d0d0d; padding:16px 18px; margin-bottom:14px; background:#faf7f2; }
.card a { text-decoration:none !important; color:inherit !important; }
.card-meta { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.src-badge { font-family:'IBM Plex Mono',monospace; font-size:.58rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase; padding:2px 7px; color:#fff; border-radius:2px; }
.card-date { font-family:'IBM Plex Mono',monospace; font-size:.62rem; color:#6b6355; }
.card-title { font-family:'Playfair Display',serif; font-weight:700; font-size:1rem; line-height:1.4; color:#0d0d0d; margin-bottom:6px; }
.card-summary { font-size:.78rem; color:#6b6355; line-height:1.55; }
.card-link { font-family:'IBM Plex Mono',monospace; font-size:.62rem; color:#c0392b; margin-top:8px; }
.status-row { font-family:'IBM Plex Mono',monospace; font-size:.65rem; color:#6b6355; border-bottom:1px solid #d4cfc5; padding:6px 0 10px; margin-bottom:16px; }
</style>
""", unsafe_allow_html=True)


# ── RSS parser (stdlib only) ──────────────────────────────────────────────────
def fetch_rss(url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed using only stdlib."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GlobalDispatch/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)

    ns_atom = "http://www.w3.org/2005/Atom"
    items = []

    # RSS 2.0
    for item in root.iter("item"):
        title   = (item.findtext("title") or "").strip()
        link    = (item.findtext("link") or "").strip()
        summary = re.sub(r"<[^>]+>", "", item.findtext("description") or "")
        pub     = (item.findtext("pubDate") or "").strip()
        # parse date
        date_str = ""
        try:
            from email.utils import parsedate_to_datetime
            date_str = parsedate_to_datetime(pub).strftime("%d %b %Y, %H:%M")
        except Exception:
            date_str = pub[:16] if pub else ""
        if title or link:
            items.append({"title": title, "link": link, "summary": summary, "date": date_str})

    # Atom fallback
    if not items:
        for entry in root.iter(f"{{{ns_atom}}}entry"):
            title   = (entry.findtext(f"{{{ns_atom}}}title") or "").strip()
            link_el = entry.find(f"{{{ns_atom}}}link")
            link    = link_el.get("href", "") if link_el is not None else ""
            summary = re.sub(r"<[^>]+>", "", entry.findtext(f"{{{ns_atom}}}summary") or "")
            pub     = entry.findtext(f"{{{ns_atom}}}updated") or ""
            date_str = pub[:16] if pub else ""
            if title or link:
                items.append({"title": title, "link": link, "summary": summary, "date": date_str})

    return items


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_feeds() -> list[dict]:
    all_items = []
    for source, urls in RSS_FEEDS.items():
        fetched = False
        for url in urls:
            try:
                entries = fetch_rss(url)
                if entries:
                    for e in entries[:30]:
                        e["source"] = source
                        all_items.append(e)
                    fetched = True
                    break
            except Exception:
                continue
        if not fetched:
            st.warning(f"⚠️ Could not reach {source} feed.", icon="📡")
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return all_items


# ── Card renderer ─────────────────────────────────────────────────────────────
def card_html(item: dict, search_term: str = "") -> str:
    color   = SOURCE_COLORS.get(item["source"], "#555")
    title   = item.get("title") or "Untitled"
    summary = (item.get("summary") or "")[:160]
    if len(item.get("summary", "")) > 160:
        summary += "…"

    if search_term:
        pat   = re.compile(re.escape(search_term), re.IGNORECASE)
        title = pat.sub(
            lambda m: f"<mark style='background:#fff3cd;color:#c0392b'>{m.group()}</mark>",
            title,
        )

    return f"""
    <div class="card">
      <a href="{item['link']}" target="_blank" rel="noopener">
        <div class="card-meta">
          <span class="src-badge" style="background:{color}">{item['source']}</span>
          <span class="card-date">{item.get('date','')}</span>
        </div>
        <div class="card-title">{title}</div>
        {"<div class='card-summary'>" + summary + "</div>" if summary else ""}
        <div class="card-link">Read full story →</div>
      </a>
    </div>"""


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="masthead">
  <h1>Global <span>Dispatch</span></h1>
  <div class="tagline">Live headlines · BBC · The Guardian · Reuters · Conflict &amp; Refugee Watch</div>
</div>
""", unsafe_allow_html=True)

col_s, col_src, col_btn = st.columns([3, 2, 1])
with col_s:
    search_input = st.text_input("s", placeholder="🔍  Search headlines…", label_visibility="collapsed")
with col_src:
    source_choice = st.selectbox("src", ["All Sources", "BBC", "The Guardian", "Reuters"], label_visibility="collapsed")
with col_btn:
    if st.button("↻  Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# keyword chips
kw_cols = st.columns(len(DEFAULT_KEYWORDS))
active_kw = st.session_state.get("active_kw", "")
for i, kw in enumerate(DEFAULT_KEYWORDS):
    with kw_cols[i]:
        label = f"**{kw}**" if active_kw == kw else kw
        if st.button(label, key=f"kw_{kw}", use_container_width=True):
            st.session_state["active_kw"] = "" if active_kw == kw else kw
            st.rerun()

filter_term = search_input.strip() or st.session_state.get("active_kw", "")

# fetch
with st.spinner("Fetching latest headlines…"):
    all_items = fetch_all_feeds()

# filter
filtered = all_items
if source_choice != "All Sources":
    filtered = [i for i in filtered if i["source"] == source_choice]
if filter_term:
    ft = filter_term.lower()
    filtered = [i for i in filtered
                if ft in (i.get("title") or "").lower()
                or ft in (i.get("summary") or "").lower()]

# status
note = "(filtered)" if (filter_term or source_choice != "All Sources") else ""
st.markdown(
    f'<div class="status-row">Last updated: {datetime.now().strftime("%d %b %Y, %H:%M:%S")} &nbsp;·&nbsp; '
    f'<b>{len(filtered)}</b> headline{"s" if len(filtered) != 1 else ""} {note}</div>',
    unsafe_allow_html=True,
)

# grid
if not filtered:
    st.info("No headlines found. Try a different keyword or click Refresh.")
else:
    c1, c2, c3 = st.columns(3)
    for idx, item in enumerate(filtered):
        with [c1, c2, c3][idx % 3]:
            st.markdown(card_html(item, filter_term), unsafe_allow_html=True)
