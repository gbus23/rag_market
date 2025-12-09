
"""
Continuous finance news scraper (prints only NEW headlines).
- Runs forever with a configurable interval (default: 60s)
- Prints only items not seen before (key = (source, title))
- Optional per-source toggles: --no-bfm --no-ts --no-yahoo --no-zb
"""

"""
comment run :
# toutes les sources, boucle chaque minute, fenêtre fraicheur 60 min
python scrapping.py --interval 60 --fresh-minutes 60

# désactiver TradingSat et ZoneBourse
python scrapping.py --no-ts --no-zb

# boucle rapide toutes les 30s, fraicheur 10 min, sans Yahoo
python scrapping.py --interval 30 --fresh-minutes 10 --no-yahoo
"""


import re, json, time, datetime, argparse, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from html import unescape

import requests
import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from zoneinfo import ZoneInfo

# -------------------- Config --------------------
PARIS = ZoneInfo("Europe/Paris")
MINUTES = 60                     # freshness window for '< minutes' scrapers
MAX_LINKS_PER_SOURCE = 100        # per-source article URL cap
MAX_WORKERS = 16                 # parallel fetch for article pages
TIMEOUT = 12                     # HTTP timeout seconds

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

def ts_now():
    """Human clock string in Europe/Paris."""
    return datetime.datetime.now(PARIS).strftime("%Y-%m-%d %H:%M:%S")

# -------------------- Small utils --------------------
def normalize_text(t: str) -> str:
    if not t: return ""
    t = unescape(t)
    t = (t.replace("\u2019","'").replace("\u2018","'").replace("\u2032","'")
           .replace("\u02BC","'").replace("´","'").replace("`","'"))
    return " ".join(t.split())

def try_get(session: requests.Session, url: str, timeout=TIMEOUT):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    return r

def chrono_step(name):
    """Silent timer; returns start and end wrappers without printing."""
    def _wrap_start():
        return time.perf_counter()
    def _wrap_end(t0, n):
        dt = time.perf_counter() - t0
        return dt
    return _wrap_start, _wrap_end

def vec_to_paris(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized timezone conversion; safe with NaT."""
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df["published_at"] = df["published_at"].dt.tz_convert("Europe/Paris")
    df["time"] = df["published_at"].dt.strftime("%H:%M")
    return df

# -------------------- BFM Économie (titles only) --------------------
def scrape_bfm_economie():
    start, end = chrono_step("BFM Économie")
    t0 = start()
    url = "https://www.bfmtv.com/economie/"
    rows = []
    with requests.Session() as s:
        s.headers.update(UA)
        try:
            r = try_get(s, url)
        except Exception:
            end(t0, 0); return rows
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for h3 in soup.select("h3 a, a h3"):
            t = normalize_text(h3.get_text(strip=True))
            if not t: 
                continue
            tl = t.lower()
            if tl in ("toute l'actualité éco", "économie et social"):
                continue
            if t in seen:
                continue
            seen.add(t)
            rows.append({"source":"BFM Économie", "title": t, "published_at": None})
    end(t0, len(rows))
    return rows

# -------------------- TradingSat (< MINUTES) --------------------
TS_EXCLUDE = ("/bourse.html","/forex.html","/cryptos.html","/outils.html",
              "/videos.html","/podcasts.html","/emissions.html")

def ts_is_article_link(href: str) -> bool:
    if not href: return False
    p = urlparse(href)
    if p.netloc and "tradingsat.com" not in p.netloc: return False
    h = href.lower()
    if any(x in h for x in TS_EXCLUDE): return False
    return h.endswith(".html")

def ts_extract_title_date(html: str):
    # title via og:title -> h1 -> <title>
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    title = normalize_text(m.group(1)) if m else ""
    if not title:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.I|re.S)
        if m:
            title = normalize_text(re.sub(r"<[^>]+>", " ", m.group(1)))
    if not title:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.I|re.S)
        if m: title = normalize_text(m.group(1))
    # remove suffix
    title = re.sub(r"\s*[-–|]\s*TradingSat.*$", "", title, flags=re.I)

    # date JSON-LD / <time datetime>
    pub = None
    for block in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, flags=re.S|re.I):
        try: data = json.loads(block.group(1).strip())
        except: continue
        def pick(obj):
            if isinstance(obj, dict) and obj.get("@type") in ("NewsArticle","Article"):
                v = obj.get("datePublished") or obj.get("dateModified") or obj.get("dateCreated")
                if v:
                    try: return dateparser.parse(v)
                    except: pass
            return None
        if isinstance(data, list):
            for x in data:
                pub = pick(x)
                if pub: break
        else:
            pub = pick(data)
        if pub: break
    if not pub:
        m = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            try: pub = dateparser.parse(m.group(1))
            except: pass
    return title, pub

def scrape_tradingsat_recent(minutes=MINUTES):
    start, end = chrono_step("TradingSat (<60min)")
    t0 = start()
    base = "https://www.tradingsat.com/"
    rows = []
    with requests.Session() as s:
        s.headers.update(UA)
        try:
            r = try_get(s, base)
        except Exception:
            end(t0, 0); return rows
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href","").strip()
            if not href: continue
            if href.startswith("/"): href = urljoin(base, href)
            if ts_is_article_link(href) and href not in seen:
                seen.add(href); links.append(href)
        links = links[:MAX_LINKS_PER_SOURCE]
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        def task(u):
            try:
                html = try_get(s, u).text
            except Exception:
                return None
            title, pub = ts_extract_title_date(html)
            if not title or not pub: return None
            if pub.tzinfo is None: pub = pub.replace(tzinfo=datetime.timezone.utc)
            if (now_utc - pub).total_seconds() <= minutes*60:
                return {"source":"TradingSat", "title":title, "published_at":pub}
            return None

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = [ex.submit(task, u) for u in links]
            for f in as_completed(futs):
                res = f.result()
                if res: rows.append(res)
    end(t0, len(rows))
    return rows

# -------------------- Yahoo Finance (< MINUTES) --------------------
Y_SEEDS = [
    "https://fr.finance.yahoo.com/actualites/",
    "https://fr.finance.yahoo.com/",
    "https://finance.yahoo.com/topic/stock-market-news/",
    "https://finance.yahoo.com/",
]
Y_ALLOWED = {"fr.finance.yahoo.com","finance.yahoo.com"}
Y_EXCL = ("/video","/videos","/photo","/photos","/watch","/watchlist","/screener",
          "/lookup","/m/","/live","/calendar","/quote/","/echarts","/charts",
          "/cryptocurrencies","/etfs","/futures","/currencies","/commodities",
          "/personal-finance","/topic/earnings","/ideas","/podcast")
Y_ARTICLE_HINT = re.compile(r"/(news|actualites?)/", re.I)

def y_is_article_link(href: str) -> bool:
    if not href: return False
    p = urlparse(href)
    if p.netloc and p.netloc not in Y_ALLOWED: return False
    path = p.path.lower()
    if any(x in path for x in Y_EXCL): return False
    return bool(Y_ARTICLE_HINT.search(path))

def y_extract_title_date(html: str):
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html) \
        or re.search(r'<meta[^>]+name=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    title = normalize_text(m.group(1)) if m else ""
    if not title:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.I|re.S)
        if m: title = normalize_text(re.sub(r"<[^>]+>", " ", m.group(1)))
    if not title:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.I|re.S)
        if m: title = normalize_text(m.group(1))
    pub = None
    for block in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, flags=re.S|re.I):
        try: data = json.loads(block.group(1).strip())
        except: continue
        def pick(obj):
            if isinstance(obj, dict) and obj.get("@type") in ("NewsArticle","Article"):
                v = obj.get("datePublished") or obj.get("dateCreated") or obj.get("dateModified")
                if v:
                    try: return dateparser.parse(v)
                    except: pass
            return None
        if isinstance(data, list):
            for x in data:
                pub = pick(x)
                if pub: break
        else:
            pub = pick(data)
        if pub: break
    if not pub:
        m = re.search(r'<time[^>]+(datetime|data-time)=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            try: pub = dateparser.parse(m.group(2))
            except: pass
    return title, pub

def scrape_yahoo_recent(minutes=MINUTES):
    start, end = chrono_step("Yahoo Finance (<60min)")
    t0 = start()
    rows = []
    with requests.Session() as s:
        s.headers.update(UA)
        links, seen = [], set()
        for seed in Y_SEEDS:
            try:
                r = try_get(s, seed)
            except Exception:
                continue
            sp = BeautifulSoup(r.text, "html.parser")
            for a in sp.select("a[href]"):
                href = a.get("href","").strip()
                if not href: continue
                if href.startswith("/"): href = urljoin(seed, href)
                if href in seen: continue
                seen.add(href)
                if y_is_article_link(href):
                    links.append(href)
            if len(links) >= MAX_LINKS_PER_SOURCE: break

        links = links[:MAX_LINKS_PER_SOURCE]
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        def task(u):
            try:
                html = try_get(s, u).text
            except Exception:
                return None
            title, pub = y_extract_title_date(html)
            if not title or not pub: return None
            if pub.tzinfo is None: pub = pub.replace(tzinfo=datetime.timezone.utc)
            if (now_utc - pub).total_seconds() <= minutes*60:
                return {"source":"Yahoo Finance", "title":title, "published_at":pub}
            return None

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = [ex.submit(task, u) for u in links]
            for f in as_completed(futs):
                res = f.result()
                if res: rows.append(res)
    end(t0, len(rows))
    return rows

# -------------------- ZoneBourse (< MINUTES, HTML only) --------------------
Z_SEEDS = ["https://www.zonebourse.com/actualite-bourse/"] + [
    f"https://www.zonebourse.com/actualite-bourse/?p={p}" for p in range(2, 3+1)
]
def zb_is_article_link(href: str) -> bool:
    if not href: return False
    p = urlparse(href)
    if p.netloc and "zonebourse.com" not in p.netloc: return False
    path = (p.path or "").lower()
    return ("/actualite-bourse/" in path) or ("/news/" in path) or path.endswith(".html")

def zb_extract_title_date(html: str):
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    title = normalize_text(m.group(1)) if m else ""
    if not title:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.I|re.S)
        if m: title = normalize_text(re.sub(r"<[^>]+>", " ", m.group(1)))
    if not title:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.I|re.S)
        if m: title = normalize_text(m.group(1))
    pub = None
    for block in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, flags=re.S|re.I):
        try: data = json.loads(block.group(1).strip())
        except: continue
        def pick(obj):
            if isinstance(obj, dict) and obj.get("@type") in ("NewsArticle","Article"):
                for k in ("datePublished","dateModified","dateCreated"):
                    v = obj.get(k)
                    if v:
                        try: return dateparser.parse(v)
                        except: pass
            return None
        if isinstance(data, list):
            for x in data:
                pub = pick(x)
                if pub: break
        else:
            pub = pick(data)
        if pub: break
    if not pub:
        m = re.search(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            try: pub = dateparser.parse(m.group(1))
            except: pass
    if not pub:
        m = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            try: pub = dateparser.parse(m.group(1))
            except: pass
    return title, pub

def scrape_zonebourse_recent(minutes=MINUTES):
    start, end = chrono_step("ZoneBourse (<60min)")
    t0 = start()
    rows = []
    with requests.Session() as s:
        s.headers.update(UA)
        links = []
        for seed in Z_SEEDS:
            try:
                text = try_get(s, seed, timeout=8).text
            except Exception:
                continue
            soup = BeautifulSoup(text, "html.parser")
            for a in soup.select("a[href]"):
                href = (a.get("href") or "").strip()
                if not href: continue
                if href.startswith("/"): href = urljoin(seed, href)
                if zb_is_article_link(href):
                    links.append(href)
        # dedup + cap
        dedup, seen = [], set()
        for u in links:
            if u not in seen:
                seen.add(u); dedup.append(u)
        links = dedup[:MAX_LINKS_PER_SOURCE]
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        def task(u):
            try:
                html = try_get(s, u, timeout=8).text
            except Exception:
                return None
            title, pub = zb_extract_title_date(html)
            if not title or not pub: return None
            if pub.tzinfo is None: pub = pub.replace(tzinfo=datetime.timezone.utc)
            if (now_utc - pub).total_seconds() <= minutes*60:
                return {"source":"ZoneBourse", "title":title, "published_at":pub}
            return None

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = [ex.submit(task, u) for u in links]
            for f in as_completed(futs):
                res = f.result()
                if res: rows.append(res)
    end(t0, len(rows))
    return rows

# -------------------- One-shot orchestrator --------------------
def run_once(fresh_minutes: int, enable_bfm: bool, enable_ts: bool, enable_yahoo: bool, enable_zb: bool):
    """Run a single full scrape and return a DataFrame of results."""
    rows_bfm = scrape_bfm_economie() if enable_bfm else []
    rows_ts  = scrape_tradingsat_recent(fresh_minutes) if enable_ts else []
    rows_yf  = scrape_yahoo_recent(fresh_minutes) if enable_yahoo else []
    rows_zb  = scrape_zonebourse_recent(fresh_minutes) if enable_zb else []

    all_rows = rows_bfm + rows_ts + rows_yf + rows_zb
    df = pd.DataFrame(all_rows, columns=["source","title","published_at"])
    if not df.empty:
        df = vec_to_paris(df)
        df = df.sort_values(
            by=["published_at","source","title"],
            ascending=[False, True, True],
            na_position="last"
        ).reset_index(drop=True)
    return df

# -------------------- Printing (only NEW) --------------------
def print_new_rows(df: pd.DataFrame, seen_keys: set):
    """
    Print only unseen rows. Key = (source, title).
    Always prints a 'no news headlines' line if nothing new was found.
    Returns the number of newly printed rows.
    """
    # Nothing scraped this round
    if df is None or df.empty:
        print(f"[{ts_now()}] no news headlines.")
        return 0

    new_count = 0
    for _, row in df.iterrows():
        key = (row["source"], row["title"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        t_str = row.get("time")
        t_disp = f"{t_str}" if isinstance(t_str, str) and t_str else "--:--"
        print(f"[{ts_now()}] NEW | {row['source']:>14} | {t_disp} | {row['title']}")
        new_count += 1

    # No unseen rows this round
    if new_count == 0:
        print(f"[{ts_now()}] no news headlines.")
    return new_count


# -------------------- Main loop --------------------
def main():
    ap = argparse.ArgumentParser(description="Continuous finance news scraper (prints only new headlines).")
    ap.add_argument("--interval", type=int, default=60, help="Loop interval in seconds (default: 60).")
    ap.add_argument("--fresh-minutes", type=int, default=MINUTES, help=f"Freshness window in minutes (default: {MINUTES}).")

    # Per-source toggles (disable with flags)
    ap.add_argument("--no-bfm", action="store_true", help="Disable BFM Économie")
    ap.add_argument("--no-ts", action="store_true", help="Disable TradingSat")
    ap.add_argument("--no-yahoo", action="store_true", help="Disable Yahoo Finance")
    ap.add_argument("--no-zb", action="store_true", help="Disable ZoneBourse")

    args = ap.parse_args()
    enable_bfm = not args.no_bfm
    enable_ts = not args.no_ts
    enable_yahoo = not args.no_yahoo
    enable_zb = not args.no_zb

    # Global seen set persists for the whole session (dedupe by (source, title))
    seen_keys = set()

    try:
        while True:
            loop_start = time.perf_counter()

            df = run_once(args.fresh_minutes, enable_bfm, enable_ts, enable_yahoo, enable_zb)
            print_new_rows(df, seen_keys)

            # Sleep the remainder of the interval (never negative)
            elapsed = time.perf_counter() - loop_start
            to_sleep = max(0.0, args.interval - elapsed)
            if to_sleep > 0:
                time.sleep(to_sleep)
    except KeyboardInterrupt:
        print(f"\n[{ts_now()}] stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()