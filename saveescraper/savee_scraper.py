#!/usr/bin/env python3
"""
Periodic Savee scraper.

- Crawls a listing/feed/board URL that contains many blocks
  and discovers item links that look like /i/<id>.
- Visits each item page, extracts metadata (og:title, og:description, og:image, og:url)
  and downloads the primary image.
- Stores to disk under download_root/<item_id>/ with meta.json and the image file.
- Maintains a persistent seen set to avoid re-downloading across runs.
- Runs forever at a configurable interval.

Env/CLI knobs:
  START_URL           Required. Listing page that shows blocks with /i/... links
  DOWNLOAD_ROOT       Default: data
  INTERVAL_MINUTES    Default: 15
  SCROLL_STEPS        Default: 3 (number of scroll-to-bottom steps on listing page)
  SCROLL_WAIT_MS      Default: 800 (delay between scroll steps)
  MAX_ITEMS_PER_CYCLE Default: 50 (limit processed new items per cycle)
  HEADLESS            Default: 1 (1=true, 0=false)
  ITEM_BASE_URL       Default: start_url domain (e.g., https://savee.com)  (use this to open item pages)
  SAVE_EMAIL          Optional. If set with SAVE_PASSWORD, scraper will auto-login.
  SAVE_PASSWORD       Optional. Password for SAVE_EMAIL.

Example:
  START_URL="https://savee.com/" ITEM_BASE_URL="https://savee.com" RUN_ONCE=1 python savee_scraper.py
"""

import asyncio
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set, Tuple

from urllib.parse import urlsplit
import aiohttp
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# ---------------------------
# Multi-job helpers
# ---------------------------

def parse_start_urls_env() -> Optional[List[str]]:
    s = os.getenv("START_URLS")
    if not s:
        return None
    parts = re.split(r"[,\n\r\t ]+", s)
    urls = [p.strip() for p in parts if p.strip()]
    return urls or None


def job_slug_for_url(url: str) -> str:
    try:
        sp = urlsplit(url)
        path = (sp.path or "").strip("/")
        slug = sp.netloc + ("" if not path else "-" + path.replace("/", "-"))
        return sanitize_filename(slug) or "job"
    except Exception:
        return "job"


def dir_name_for_job(url: str, name: Optional[str]) -> str:
    # If explicit name provided, use it; else use last path segment or slug
    if name and name.strip():
        return sanitize_filename(name.strip())
    try:
        sp = urlsplit(url)
        path = (sp.path or "").strip("/")
        if path:
            last = path.split("/")[-1]
            if last:
                return sanitize_filename(last)
    except Exception:
        pass
    return job_slug_for_url(url)


def load_jobs_from_path(path: str) -> Optional[List[dict]]:
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        jobs: List[dict] = []
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, str):
                    jobs.append({"url": entry})
                elif isinstance(entry, dict) and entry.get("url"):
                    jobs.append(entry)
        elif isinstance(data, dict) and isinstance(data.get("jobs"), list):
            for entry in data["jobs"]:
                if isinstance(entry, str):
                    jobs.append({"url": entry})
                elif isinstance(entry, dict) and entry.get("url"):
                    jobs.append(entry)
        return jobs or None
    except Exception:
        return None

# ---------------------------
# Auth/session helpers
# ---------------------------

def _normalize_cookie_entry(entry: dict) -> Optional[dict]:
    try:
        name = entry.get('name')
        value = entry.get('value')
        domain = entry.get('domain')
        path = entry.get('path', '/') or '/'
        if not (name and value and domain):
            return None
        # expirationDate (seconds, float) -> expires (int)
        expires = entry.get('expires')
        if not expires and 'expirationDate' in entry:
            try:
                expires = int(float(entry['expirationDate']))
            except Exception:
                expires = None
        same_site = entry.get('sameSite')
        if same_site:
            s = str(same_site).lower()
            if s in ('no_restriction', 'none'):
                same_site = 'None'
            elif s in ('lax', 'lax_mode'):
                same_site = 'Lax'
            elif s in ('strict',):
                same_site = 'Strict'
            else:
                same_site = None
        cookie = {
            'name': name,
            'value': value,
            'domain': domain,
            'path': path,
            'httpOnly': bool(entry.get('httpOnly', False)),
            'secure': bool(entry.get('secure', False)),
        }
        if expires:
            cookie['expires'] = expires
        if same_site:
            cookie['sameSite'] = same_site
        return cookie
    except Exception:
        return None


def _load_cookies_from_json_text(text: str) -> Optional[list]:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and 'cookies' in data:
            raw = data['cookies']
        else:
            raw = data
        if not isinstance(raw, list):
            return None
        cookies = []
        for e in raw:
            if isinstance(e, dict):
                ne = _normalize_cookie_entry(e)
                if ne and (ne['domain'].endswith('savee.com')):
                    cookies.append(ne)
        return cookies or None
    except Exception:
        return None


def load_cookies_from_env() -> Optional[list]:
    # Prefer COOKIES_JSON, then COOKIES_PATH
    cj = os.getenv('COOKIES_JSON')
    if cj:
        c = _load_cookies_from_json_text(cj)
        if c:
            return c
    cp = os.getenv('COOKIES_PATH')
    if cp and os.path.exists(cp):
        try:
            return _load_cookies_from_json_text(Path(cp).read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def load_storage_state_from_env() -> Optional[object]:
    ss_path = os.getenv('STORAGE_STATE_PATH')
    if ss_path and os.path.exists(ss_path):
        return ss_path
    ss_json = os.getenv('STORAGE_STATE_JSON')
    if ss_json:
        try:
            parsed = json.loads(ss_json)
            return parsed
        except Exception:
            return None
    return None

# ---------------------------
# End auth/session helpers
# ---------------------------


BASE_URL = "https://savee.com"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


@dataclass
class ItemMeta:
    item_id: str
    page_url: str
    og_title: Optional[str]
    og_description: Optional[str]
    og_image_url: Optional[str]
    og_url: Optional[str]
    saved_at: str
    # media additions
    media_type: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    video_poster_url: Optional[str] = None
    source_api_url: Optional[str] = None
    source_original_url: Optional[str] = None


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_seen_ids(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(data)
        if isinstance(data, dict) and "ids" in data:
            return set(data["ids"])  # backward compatibility
    except Exception:
        pass
    return set()


def save_seen_ids(path: Path, ids: Set[str]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(ids)), encoding="utf-8")
    tmp.replace(path)


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "file"


def is_valid_item_id(item_id: str) -> bool:
    if not isinstance(item_id, str):
        return False
    if item_id in {"undefined", "null", "None", ""}:
        return False
    return re.fullmatch(r"[A-Za-z0-9_-]{5,24}", item_id) is not None


def extract_item_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/i/([A-Za-z0-9_-]+)/?", url)
    if not m:
        return None
    item_id = m.group(1)
    return item_id if is_valid_item_id(item_id) else None


def build_scrolling_js(steps: int, wait_ms: int, until_idle: bool, idle_rounds: int) -> str:
    steps = max(0, int(steps))
    wait_ms = max(0, int(wait_ms))
    idle_rounds = max(1, int(idle_rounds))
    js = '''
(function() {
  let maxLoops = __STEPS__;
  let wait = __WAIT__;
  let untilIdle = __UNTIL_IDLE__;
  let idleRoundsTarget = __IDLE_ROUNDS__;
  let loops = 0;
  let prevCount = 0;
  let stagnantRounds = 0;
  function collect() {
    try {
      const anchors = Array.from(document.querySelectorAll('a'))
        .map(a => a.href)
        .filter(href => typeof href === 'string' && href.includes('/i/'));
      const ids = Array.from(document.querySelectorAll('[id]'))
        .map(el => el.id)
        .filter(id => typeof id === 'string' && id.startsWith('grid-item-'))
        .map(id => id.replace('grid-item-',''));
      document.documentElement.setAttribute('data-savee-anchors', encodeURIComponent(JSON.stringify(anchors)));
      document.documentElement.setAttribute('data-savee-ids', encodeURIComponent(JSON.stringify(ids)));
    } catch (e) {}
  }
  function step() {
    window.scrollTo(0, document.body.scrollHeight);
    loops++;
    const count = document.querySelectorAll('[id^=grid-item-]').length;
    if (count <= prevCount) stagnantRounds++; else stagnantRounds = 0;
    prevCount = count;
    const reachedMax = (maxLoops > 0 && loops >= maxLoops);
    const reachedIdle = (untilIdle && stagnantRounds >= idleRoundsTarget);
    if (reachedMax || reachedIdle) {
      collect(); window.__savee_scrolled = true; return;
    }
    setTimeout(step, wait);
  }
  step();
})();
'''
    return (js
            .replace('__STEPS__', str(steps))
            .replace('__WAIT__', str(wait_ms))
            .replace('__UNTIL_IDLE__', '1' if until_idle else '0')
            .replace('__IDLE_ROUNDS__', str(idle_rounds)))


def build_item_collect_js() -> str:
    return r'''
(function() {
  function getInfoButton() {
    const selectors = [
      'button[title^="Info" i]',
      'button[title*="Info" i]',
      'button:has(> span > span.hidden:text("Info"))',
      'button:has(svg)'
    ];
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el && ((el.getAttribute('title')||'').toLowerCase().includes('info') || (el.innerText||'').toLowerCase().includes('info'))) return el;
      } catch(e) {}
    }
    // fallback: any button whose title contains Info
    const btns = Array.from(document.querySelectorAll('button'));
    const found = btns.find(b => ((b.getAttribute('title')||'').toLowerCase().includes('info') || (b.innerText||'').toLowerCase().includes('info')));
    return found || null;
  }

  function openInfoAndWait(maxTries = 8, stepMs = 250) {
    return new Promise(resolve => {
      let tries = 0;
      function attempt() {
        const panel = document.querySelector('#infoSideBar');
        if (panel) return resolve(true);
        const btn = getInfoButton();
        if (btn) {
          try { btn.click(); } catch(e) {}
        }
        tries += 1;
        if (tries >= maxTries) return resolve(false);
        setTimeout(attempt, stepMs);
      }
      attempt();
    });
  }

  async function collect() {
    try {
      const container = document.querySelector('[data-testid="image-container"]');
      const imgEl = container ? container.querySelector('[data-testid="image-original"]') : null;
      const videoEl = container ? (container.querySelector('video[slot="media"]') || container.querySelector('video')) : null;
      const imageOriginalSrc = imgEl ? (imgEl.src || imgEl.getAttribute('src') || imgEl.getAttribute('data-src')) : null;
      const videoSrc = videoEl ? (videoEl.src || videoEl.getAttribute('src')) : null;
      const videoPosterSrc = videoEl ? (videoEl.poster || videoEl.getAttribute('poster')) : null;

      await openInfoAndWait(10, 300);
      const sidebarRoot = document.querySelector('#infoSideBar .space-y-8.px-6') || document.querySelector('#infoSideBar') || null;
      const info = {};
      let sourceApiUrl = null;
      let colorHexes = [];
      let aiTags = [];
      let sidebarTitle = null;

      if (sidebarRoot) {
        // title: try specific overflow/heading, else first large text
        const titleCand = sidebarRoot.querySelector('.text-overflow, .text-lg');
        sidebarTitle = titleCand ? (titleCand.textContent||'').trim() : null;

        const allAnchors = Array.from(sidebarRoot.querySelectorAll('a'));
        const links = allAnchors.map(a => ({ href: a.href, text: (a.textContent||'').trim(), title: (a.title||'') }));
        const texts = Array.from(sidebarRoot.querySelectorAll('p,li,div')).map(n => (n.textContent||'').trim()).filter(Boolean).slice(0, 800);
        const tags = allAnchors.map(a => (a.textContent||'').trim()).filter(t => t.startsWith('#'));
        // AI tags are anchors under /search/?q= that are not color hashtags
        aiTags = allAnchors
          .filter(a => (a.getAttribute('href')||'').includes('/search/?q='))
          .map(a => (a.textContent||'').trim())
          .filter(t => t && !t.startsWith('#'));
        const colorAnchors = allAnchors.filter(a => (a.title||'').startsWith('Search by #'));
        colorHexes = Array.from(new Set(colorAnchors.map(a => (a.title||'').replace('Search by ', '').trim()).filter(t => /^#[0-9A-Fa-f]{3,8}$/.test(t))));
        const colorEls = Array.from(sidebarRoot.querySelectorAll('[style*="background"]'));
        const colors = colorEls.map(el => { const s = el.getAttribute('style') || ''; const m = s.match(/background(?:-color)?:\s*([^;]+)/i); return m ? m[1].trim() : null; }).filter(Boolean);
        const srcLink = allAnchors.find(a => /\/api\/items\/[^/]+\/source\/?$/i.test(a.href));
        sourceApiUrl = srcLink ? srcLink.href : null;
        info.links = links; info.texts = texts; info.tags = Array.from(new Set(tags)); info.colors = Array.from(new Set(colors)); info.colorHexes = Array.from(new Set(colorHexes)); info.aiTags = Array.from(new Set(aiTags)); info.sidebarTitle = sidebarTitle;
      }

      document.documentElement.setAttribute('data-savee-item', encodeURIComponent(JSON.stringify({ imageOriginalSrc, videoSrc, videoPosterSrc, sourceApiUrl, info })));
    } catch (e) {
      document.documentElement.setAttribute('data-savee-item', encodeURIComponent(JSON.stringify({ imageOriginalSrc: null, videoSrc: null, videoPosterSrc: null, sourceApiUrl: null, info: {} })));
    }
  }

  setTimeout(() => { collect(); }, 400);
})();
'''


def build_login_js(email: str, password: str) -> str:
    # Best-effort generic login filler
    js = (
        "(function()\n"
        "{\n"
        "  const EMAIL='" + email.replace("'", "\'") + "';\n"
        "  const PASSWORD='" + password.replace("'", "\'") + "';\n"
        "  function tryFill() {\n"
        "    try {\n"
        "      const emailSel = ['input[type=email]','input[name=email]','input#email'];\n"
        "      const passSel = ['input[type=password]','input[name=password]','input#password'];\n"
        "      let e=null,p=null;\n"
        "      for (const s of emailSel) { const n=document.querySelector(s); if(n){e=n; break;} }\n"
        "      for (const s of passSel) { const n=document.querySelector(s); if(n){p=n; break;} }\n"
        "      if (e) { e.focus(); e.value=EMAIL; e.dispatchEvent(new Event('input',{bubbles:true})); }\n"
        "      if (p) { p.focus(); p.value=PASSWORD; p.dispatchEvent(new Event('input',{bubbles:true})); }\n"
        "      const submit = document.querySelector('button[type=submit],button:not([disabled])');\n"
        "      if (submit) submit.click();\n"
        "      window.__savee_login_clicked = true;\n"
        "    } catch (err) { window.__savee_login_error = String(err); }\n"
        "  }\n"
        "  setTimeout(tryFill, 300);\n"
        "})();\n"
    )
    return js


def _parse_links_from_data_attribute(html: str) -> Optional[List[str]]:
    m = re.search(r"data-savee-anchors=['\"]([^'\"]+)['\"]", html)
    if not m:
        return None
    try:
        from urllib.parse import unquote
        json_text = unquote(m.group(1))
        data = json.loads(json_text)
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
    except Exception:
        return None
    return None


def _parse_ids_from_data_attribute(html: str) -> Optional[List[str]]:
    m = re.search(r"data-savee-ids=['\"]([^'\"]+)['\"]", html)
    if not m:
        return None
    try:
        from urllib.parse import unquote
        json_text = unquote(m.group(1))
        data = json.loads(json_text)
        if isinstance(data, list):
            ids = [str(x) for x in data if isinstance(x, str) and is_valid_item_id(str(x))]
            return ids
    except Exception:
        return None
    return None


def _parse_item_data_from_attr(html: str) -> Optional[dict]:
    m = re.search(r"data-savee-item=['\"]([^'\"]+)['\"]", html)
    if not m:
        return None
    try:
        from urllib.parse import unquote
        json_text = unquote(m.group(1))
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def find_item_links_in_html(html: str, base_url: str, item_base_url: str) -> List[str]:
    # Maintain DOM order while de-duping
    seen_ids: Set[str] = set()
    ordered_ids: List[str] = []

    # 1) IDs from JS attribute (already in DOM order)
    for item_id in _parse_ids_from_data_attribute(html) or []:
        if is_valid_item_id(item_id) and item_id not in seen_ids:
            seen_ids.add(item_id)
            ordered_ids.append(item_id)

    # 2) Anchors captured via JS attribute (DOM order); extract ids
    for href in _parse_links_from_data_attribute(html) or []:
        maybe = extract_item_id_from_url(href)
        if maybe and maybe not in seen_ids:
            seen_ids.add(maybe)
            ordered_ids.append(maybe)

    # 3) DOM id="grid-item-<ID>" in appearance order
    for m in re.finditer(r"id=['\"]grid-item-([A-Za-z0-9_-]+)['\"]", html):
        item_id = m.group(1)
        if is_valid_item_id(item_id) and item_id not in seen_ids:
            seen_ids.add(item_id)
            ordered_ids.append(item_id)

    # 4) Href-based discovery in appearance order
    for m in re.finditer(r"href=\"(/i/[A-Za-z0-9_-]+[^\"]*)\"|href='(/i/[A-Za-z0-9_-]+[^']*)'", html):
        rel = m.group(1) or m.group(2)
        maybe = extract_item_id_from_url(rel)
        if maybe and maybe not in seen_ids:
            seen_ids.add(maybe)
            ordered_ids.append(maybe)

    # 5) Raw text fallback /i/<ID> in appearance order
    for m in re.finditer(r"/i/([A-Za-z0-9_-]+)", html):
        item_id = m.group(1)
        if is_valid_item_id(item_id) and item_id not in seen_ids:
            seen_ids.add(item_id)
            ordered_ids.append(item_id)

    # Build final URLs in discovered order
    links: List[str] = [f"{item_base_url}/i/{item_id}/" for item_id in ordered_ids]
    return links


def extract_meta_from_html(html: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    def find_meta_value(key_name: str) -> Optional[str]:
        for m in re.finditer(r"<meta[^>]+>", html, flags=re.IGNORECASE):
            tag = m.group(0)
            key_match = re.search(r"(?:property|name)=['\"]([^'\"]+)['\"]", tag, flags=re.IGNORECASE)
            if not key_match:
                continue
            if key_match.group(1).strip().lower() != key_name.lower():
                continue
            content_match = re.search(r"content=['\"]([^'\"]+)['\"]", tag, flags=re.IGNORECASE)
            if content_match:
                return content_match.group(1)
        return None

    title = find_meta_value("og:title")
    description = find_meta_value("og:description")
    image_url = (
        find_meta_value("og:image")
        or find_meta_value("og:image:secure_url")
        or find_meta_value("twitter:image")
    )
    og_url = find_meta_value("og:url")
    return title, description, image_url, og_url


async def download_binary(session: aiohttp.ClientSession, url: str, dest_path: Path, referer: Optional[str] = None) -> None:
    ensure_dir(dest_path.parent)
    headers = {"Referer": referer} if referer else None
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
        resp.raise_for_status()
        with dest_path.open("wb") as f:
            async for chunk in resp.content.iter_chunked(64 * 1024):
                f.write(chunk)


async def fetch_listing_html(crawler: AsyncWebCrawler, url: str, scroll_steps: int, scroll_wait_ms: int, until_idle: bool, idle_rounds: int, page_timeout_ms: int = 60000) -> Optional[str]:
    cfg = CrawlerRunConfig(
        js_code=build_scrolling_js(scroll_steps, scroll_wait_ms, until_idle, idle_rounds) if scroll_steps > 0 or until_idle else None,
        wait_for=(
            "js:() => window.__savee_scrolled === true "
            "|| document.querySelector('[id^=grid-item-]') != null "
            "|| Array.from(document.querySelectorAll('a')).some(a => (a.href||'').includes('/i/'))"
        ),
        page_timeout=page_timeout_ms,
    )
    result = await crawler.arun(url=url, config=cfg)
    if not getattr(result, "success", False):
        print(f"[listing] failed: {getattr(result, 'error_message', 'unknown error')}")
        return None
    return getattr(result, "html", None)


async def ensure_login(crawler: AsyncWebCrawler, base_url: str, email: Optional[str], password: Optional[str]) -> None:
    if not email or not password:
        return
    # Try common login paths
    for path in ("/login", "/auth/login", "/signin"):
        login_url = f"{base_url}{path}"
        cfg = CrawlerRunConfig(
            js_code=build_login_js(email, password),
            wait_for="js:() => document.readyState === 'complete'",
            page_timeout=60000,
        )
        result = await crawler.arun(url=login_url, config=cfg)
        if getattr(result, 'success', False):
            # If this path exists and didn't 404, break
            break


async def fetch_item_html(crawler: AsyncWebCrawler, url: str, page_timeout_ms: int = 45000) -> Optional[str]:
    cfg = CrawlerRunConfig(
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=page_timeout_ms,
    )
    result = await crawler.arun(url=url, config=cfg)
    if not getattr(result, "success", False):
        print(f"[item] failed {url}: {getattr(result, 'error_message', 'unknown error')}")
        return None
    return getattr(result, "html", None)

async def fetch_item_with_collect(crawler: AsyncWebCrawler, url: str, page_timeout_ms: int = 60000) -> Optional[str]:
    cfg = CrawlerRunConfig(
        js_code=build_item_collect_js(),
        wait_for=(
            "js:() => document.readyState === 'complete' && "
            "(document.documentElement.getAttribute('data-savee-item') != null)"
        ),
        page_timeout=page_timeout_ms,
    )
    result = await crawler.arun(url=url, config=cfg)
    if not getattr(result, 'success', False):
        print(f"[item+collect] failed {url}: {getattr(result, 'error_message', 'unknown error')}")
        return None
    return getattr(result, 'html', None)

async def fetch_source_final_url(crawler: AsyncWebCrawler, api_url: str) -> Optional[str]:
    try:
        cfg = CrawlerRunConfig(
            wait_for="js:() => true",
            page_timeout=20000,
        )
        result = await crawler.arun(url=api_url, config=cfg)
        if getattr(result, 'success', False):
            return getattr(result, 'url', None)
    except Exception as e:
        print(f"[api] fetch failed {api_url}: {e}")
    return None


async def process_item(
    crawler: AsyncWebCrawler,
    http_session: aiohttp.ClientSession,
    item_url: str,
    download_root: Path,
) -> Optional[str]:
    item_id = extract_item_id_from_url(item_url)
    if not item_id:
        return None

    html = await fetch_item_with_collect(crawler, item_url) or await fetch_item_html(crawler, item_url)
    if not html:
        return None

    item_data = _parse_item_data_from_attr(html) or {}
    hd_image = item_data.get('imageOriginalSrc')
    video_src = item_data.get('videoSrc')
    video_poster = item_data.get('videoPosterSrc')
    source_api_url = item_data.get('sourceApiUrl')
    sidebar_info = item_data.get('info') if isinstance(item_data.get('info'), dict) else {}

    # Build API url if not found in sidebar
    if not source_api_url:
        try:
            sp = urlsplit(item_url)
            base = f"{sp.scheme}://{sp.netloc}"
            source_api_url = f"{base}/api/items/{item_id}/source/"
        except Exception:
            source_api_url = None

    # Try to resolve original URL via API (uses browser session for auth)
    source_original_url = None
    if source_api_url:
        source_original_url = await fetch_source_final_url(crawler, source_api_url)

    og_title, og_description, og_image_url, og_url = extract_meta_from_html(html)

    media_type = 'video' if video_src else 'image'
    image_url_final = hd_image or (video_poster if media_type == 'video' else None) or og_image_url

    # Prepare paths
    item_dir = download_root / item_id
    ensure_dir(item_dir)

    try:
        (item_dir / "page.html").write_text(html, encoding="utf-8")
    except Exception:
        pass

    # Save sidebar info if present
    if sidebar_info:
        (item_dir / "sidebar.json").write_text(json.dumps(sidebar_info, ensure_ascii=False, indent=2), encoding="utf-8")

    # Download media
    # 1) Video
    if media_type == 'video' and video_src:
        v_ext = os.path.splitext(video_src.split('?')[0])[1] or '.mp4'
        v_file = sanitize_filename(f"{item_id}{v_ext}")
        try:
            await download_binary(http_session, video_src, item_dir / v_file, referer=item_url)
        except Exception as e:
            print(f"[item] video download failed {item_id}: {e}")
        # Poster if available
        if video_poster:
            p_ext = os.path.splitext(video_poster.split('?')[0])[1] or '.jpg'
            p_file = sanitize_filename(f"{item_id}-poster{p_ext}")
            try:
                await download_binary(http_session, video_poster, item_dir / p_file, referer=item_url)
            except Exception as e:
                print(f"[item] poster download failed {item_id}: {e}")

    # 2) Image (or fallback image for video)
    if image_url_final:
        i_ext = os.path.splitext(image_url_final.split('?')[0])[1] or '.jpg'
        # If this is a video poster and we already saved it, name differently to avoid collision
        is_poster = (media_type == 'video' and video_poster and image_url_final == video_poster)
        i_name = f"{item_id}-poster{i_ext}" if is_poster else f"{item_id}{i_ext}"
        try:
            await download_binary(http_session, image_url_final, item_dir / sanitize_filename(i_name), referer=item_url)
        except Exception as e:
            print(f"[item] image download failed {item_id}: {e}")

    meta = ItemMeta(
        item_id=item_id,
        page_url=item_url,
        og_title=og_title,
        og_description=og_description,
        og_image_url=og_image_url,
        og_url=og_url,
        saved_at=iso_now(),
        media_type=media_type,
        image_url=image_url_final,
        video_url=video_src,
        video_poster_url=video_poster,
        source_api_url=source_api_url,
        source_original_url=source_original_url,
    )
    (item_dir / "meta.json").write_text(json.dumps(asdict(meta), ensure_ascii=False, indent=2), encoding="utf-8")

    return item_id


async def run_cycle(
    start_url: str,
    download_root: Path,
    seen_path: Path,
    scroll_steps: int,
    scroll_wait_ms: int,
    max_items_per_cycle: int,
    headless: bool,
    item_base_url: str,
    skip_existing: bool,
    oldest_first: bool,
    until_idle: bool,
    idle_rounds: int,
) -> int:
    # Build browser config with persisted session if provided
    storage_state = load_storage_state_from_env()
    cookies = load_cookies_from_env()
    browser_cfg = BrowserConfig(
        headless=headless,
        verbose=False,
        storage_state=storage_state,
        cookies=cookies,
    )
    processed_count = 0
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # Login only if no storage_state/cookies provided
        sp0 = urlsplit(start_url)
        base_url0 = f"{sp0.scheme}://{sp0.netloc}"
        if not storage_state and not cookies:
            await ensure_login(crawler, base_url0, os.getenv("SAVE_EMAIL"), os.getenv("SAVE_PASSWORD"))

        listing_html = await fetch_listing_html(crawler, start_url, scroll_steps, scroll_wait_ms, until_idle, idle_rounds)
        if not listing_html:
            return 0
        sp = urlsplit(start_url)
        base_url = f"{sp.scheme}://{sp.netloc}"
        links = find_item_links_in_html(listing_html, base_url, item_base_url)
        if not links:
            print("No item links discovered.")
            return 0
        if oldest_first:
            links = list(reversed(links))
        print(f"Discovered {len(links)} items")

        seen = load_seen_ids(seen_path)
        if skip_existing:
            # Add existing item directories to seen to avoid duplicates/conflicts
            try:
                for entry in os.listdir(download_root):
                    item_dir = download_root / entry
                    if item_dir.is_dir() and is_valid_item_id(entry):
                        seen.add(entry)
            except Exception:
                pass

        async with aiohttp.ClientSession(
            headers={
                "User-Agent": DEFAULT_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        ) as http_session:
            for href in links:
                if processed_count >= max_items_per_cycle:
                    break
                item_id = extract_item_id_from_url(href)
                if not item_id or item_id in seen:
                    continue
                processed = await process_item(crawler, http_session, href, download_root)
                if processed:
                    seen.add(processed)
                    processed_count += 1
                    if processed_count % 5 == 0:
                        save_seen_ids(seen_path, seen)

        save_seen_ids(seen_path, seen)
    return processed_count


async def main() -> None:
    # Multi-job inputs
    jobs: List[dict] = []
    jobs_path = os.getenv("JOBS_PATH")
    if jobs_path and os.path.exists(jobs_path):
        loaded = load_jobs_from_path(jobs_path)
        if loaded:
            jobs = loaded
    if not jobs:
        start_urls_env = parse_start_urls_env()
        if start_urls_env:
            jobs = [{"url": u} for u in start_urls_env]
    # Fallback to single START_URL
    single_url = os.getenv("START_URL")
    if not jobs and single_url:
        jobs = [{"url": single_url}]

    if not jobs:
        print("ERROR: provide START_URL or START_URLS or JOBS_PATH JSON.")
        sys.exit(2)

    base_download_root = Path(os.getenv("DOWNLOAD_ROOT", "data"))
    ensure_dir(base_download_root)

    interval_minutes = int(os.getenv("INTERVAL_MINUTES", "15"))
    scroll_steps = int(os.getenv("SCROLL_STEPS", "3"))
    scroll_wait_ms = int(os.getenv("SCROLL_WAIT_MS", "800"))
    max_items_per_cycle = int(os.getenv("MAX_ITEMS_PER_CYCLE", "50"))
    headless_env = os.getenv("HEADLESS", "1").strip()
    headless = headless_env not in ("0", "false", "False")
    run_once = os.getenv("RUN_ONCE", "0").strip() not in ("0", "false", "False", "")
    skip_existing = os.getenv("SKIP_EXISTING", "1").strip() not in ("0", "false", "False")
    oldest_first = os.getenv("OLDEST_FIRST", "0").strip() not in ("0", "false", "False", "")
    until_idle = os.getenv("SCROLL_UNTIL_IDLE", "1").strip() not in ("0", "false", "False", "")
    idle_rounds = int(os.getenv("SCROLL_IDLE_ROUNDS", "5"))
    job_concurrency = int(os.getenv("JOB_CONCURRENCY", "2"))

    # For each job, compute item_base_url and its own state directory
    job_states = []
    for job in jobs:
        url = job["url"].strip()
        name = job.get("name") if isinstance(job, dict) else None
        sp = urlsplit(url)
        item_base_url = f"{sp.scheme}://{sp.netloc}"
        dir_name = dir_name_for_job(url, name)
        job_download_root = base_download_root / dir_name
        ensure_dir(job_download_root)
        state_dir = job_download_root / "_state"
        ensure_dir(state_dir)
        seen_path = state_dir / "seen.json"
        job_states.append({
            "start_url": url,
            "download_root": job_download_root,
            "seen_path": seen_path,
            "item_base_url": item_base_url,
            "dir_name": dir_name,
        })

    print("Jobs:")
    for j in job_states:
        print(f" - {j['start_url']} -> {j['download_root']}")

    sem = asyncio.Semaphore(max(1, job_concurrency))

    async def run_one_job(j: dict) -> int:
        async with sem:
            print(
                f"\n=== Job: {j['start_url']} ===\n"
                f"download_root={j['download_root']} headless={headless}\n"
                f"scroll_steps={scroll_steps} wait_ms={scroll_wait_ms} until_idle={until_idle} idle_rounds={idle_rounds}\n"
                f"oldest_first={oldest_first} max_items_per_cycle={max_items_per_cycle} skip_existing={skip_existing}\n"
            )
            return await run_cycle(
                start_url=j["start_url"],
                download_root=j["download_root"],
                seen_path=j["seen_path"],
                scroll_steps=scroll_steps,
                scroll_wait_ms=scroll_wait_ms,
                max_items_per_cycle=max_items_per_cycle,
                headless=headless,
                item_base_url=j["item_base_url"],
                skip_existing=skip_existing,
                oldest_first=oldest_first,
                until_idle=until_idle,
                idle_rounds=idle_rounds,
            )

    while True:
        tasks = [run_one_job(j) for j in job_states]
        results = []
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"Cycle gather error: {e}")
        total_processed = 0
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                print(f"Job {job_states[idx]['start_url']} error: {res}")
            else:
                print(f"Job {job_states[idx]['start_url']} new items: {res}")
                total_processed += int(res or 0)
        print(f"\nCycle complete. Total new items across jobs: {total_processed}")
        if run_once:
            break
        await asyncio.sleep(max(1, interval_minutes) * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


