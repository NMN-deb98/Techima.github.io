#!/usr/bin/env python3
"""Build the articles written in the Techima CMS into static pages.

Input : content/articles/*.json   (written by the CMS through the GitHub API)
Output: articles/<slug>/index.html, the card list in articles/index.html and sitemap.xml

Safety rules
- Only pages carrying the GENERATED_MARK comment are ever overwritten or removed,
  so hand-written pages (for example articles/seo-technical-checklist/) are never touched.
- Sitemap entries are only removed when their page no longer exists on disk.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

try:
    import bleach
    import markdown
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependencies. Run: python -m pip install Markdown bleach") from exc

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "articles"
ARTICLES_DIR = ROOT / "articles"
INDEX_PATH = ARTICLES_DIR / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
BASE_URL = "https://nmn-deb98.github.io/Techima.github.io"
SITE_PREFIX = "/Techima.github.io"
GENERATED_MARK = "<!-- techima-cms:generated -->"
MARKER_START = "<!-- CMS_ARTICLES_START -->"
MARKER_END = "<!-- CMS_ARTICLES_END -->"
SM = "http://www.sitemaps.org/schemas/sitemap/0.9"
NS = {"sm": SM}
RESERVED_SLUGS = {"index", "assets", "page", "feed"}
AUTHOR = "نیما مددی نعمتی"

# key -> (label, short label, symbol, caption)
CATEGORIES = {
    "seo": ("سئو و بهینه‌سازی", "SEO", "⌕", "سئو تکنیکال"),
    "web": ("برنامه‌نویسی وب", "WEB", "{ }", "توسعه وب"),
    "content": ("تولید محتوا", "CONTENT", "✎", "تولید محتوا"),
    "learning": ("یادگیری و تجربه", "LEARN", "✦", "یادگیری"),
}
DEFAULT_CATEGORY = "learning"
JALALI_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                 "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "del", "blockquote",
    "ul", "ol", "li", "a", "img", "figure", "figcaption", "pre", "code", "table", "thead",
    "tbody", "tr", "th", "td", "div", "span", "sup", "sub",
}
ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "th": ["align"], "td": ["align"],
    "code": ["class"], "pre": ["class"],
}


# ---------------------------------------------------------------- helpers
def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def safe_text(value: object, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def valid_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value)) and value not in RESERVED_SLUGS


def fa(number: object) -> str:
    return str(number).translate(FA_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy, gy = 979, gy - 1600
    else:
        jy, gy = 0, gy - 621
    gy2 = gy + 1 if gm > 2 else gy
    days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + offsets[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_label(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{fa(jd)} {JALALI_MONTHS[jm - 1]} {fa(jy)}"


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def valid_date(value: str, fallback: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        return fallback


def article_url(slug: str) -> str:
    return f"{BASE_URL}/articles/{quote(slug)}/"


def https_url(value: object) -> str:
    text = safe_text(value, 1000)
    return text if text.startswith("https://") else ""


# ---------------------------------------------------------------- loading
def load_published() -> list[dict]:
    """Return the published articles, newest first."""
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    published = []
    for path in sorted(CONTENT_DIR.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Invalid CMS article JSON in {path.name}: {exc}") from exc
        if not isinstance(item, dict):
            raise SystemExit(f"CMS article must be a JSON object: {path.name}")
        if item.get("status") != "published":
            continue
        slug = safe_text(item.get("slug"), 100)
        title = safe_text(item.get("title"), 180)
        description = safe_text(item.get("description"), 300)
        body = item.get("body", "")
        if not valid_slug(slug):
            raise SystemExit(f"{path.name}: slug must be lowercase English letters, digits and hyphens.")
        if not title or not description or not isinstance(body, str) or not body.strip():
            raise SystemExit(f"{path.name}: a published article needs title, description and body.")
        first = valid_date(safe_text(item.get("datePublished")), today())
        category = safe_text(item.get("category"), 20)
        item.update(
            slug=slug, title=title, description=description, body=body,
            datePublished=first,
            dateModified=valid_date(safe_text(item.get("dateModified")), first),
            category=category if category in CATEGORIES else DEFAULT_CATEGORY,
            tags=[safe_text(t, 60) for t in (item.get("tags") or []) if safe_text(t, 60)][:12],
            image=https_url(item.get("image")), imageAlt=safe_text(item.get("imageAlt"), 180),
        )
        published.append(item)
    slugs = [a["slug"] for a in published]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Two published articles share the same slug.")
    published.sort(key=lambda a: (a["datePublished"], a["title"]), reverse=True)
    return published


# ---------------------------------------------------------------- body
def render_body(md_text: str) -> tuple[str, list[tuple[str, str]], int]:
    """Markdown -> sanitized HTML, table of contents [(id, text)], word count."""
    raw = markdown.markdown(md_text, extensions=["extra", "sane_lists", "fenced_code", "tables"], output_format="html5")
    clean = bleach.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, protocols={"http", "https", "mailto"}, strip=True)
    # The page title is the only <h1>. If the author used "#" inside the body, shift every
    # heading one level down; otherwise "##" stays as the main section heading.
    if re.search(r"<h1[\s>]", clean):
        for level in range(5, 0, -1):
            clean = re.sub(rf"<(/?)h{level}(?=[\s>])", rf"<\1h{level + 1}", clean)
    toc: list[tuple[str, str]] = []

    def add_id(match: re.Match) -> str:
        text = html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
        sid = f"article-section-{len(toc) + 1}"
        toc.append((sid, text))
        return f'<h2 id="{sid}"{match.group(1)}>{match.group(2)}</h2>'

    clean = re.sub(r"<h2([^>]*)>(.*?)</h2>", add_id, clean, flags=re.S)
    clean = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" rel="noopener noreferrer"', clean)
    clean = clean.replace("<img ", '<img loading="lazy" decoding="async" ')
    plain = html.unescape(re.sub(r"<[^>]+>", " ", clean))
    return clean, toc, len(plain.split())


# ---------------------------------------------------------------- shared chrome
def site_chrome() -> tuple[str, str, str]:
    """Reuse header, footer and script tag from the live articles page so they never drift."""
    page = INDEX_PATH.read_text(encoding="utf-8")
    header = re.search(r'<header class="site-header">.*?</header>', page, re.S)
    footer = re.search(r'<footer class="site-footer">.*?</footer>', page, re.S)
    script = re.search(r'<script src="[^"]*assets/js/main\.js"[^>]*></script>', page)
    if not (header and footer and script):
        raise SystemExit("articles/index.html no longer has the expected header/footer/script markup.")
    return header.group(0), footer.group(0), script.group(0)


def csp_meta() -> str:
    page = INDEX_PATH.read_text(encoding="utf-8")
    match = re.search(r'<meta http-equiv="Content-Security-Policy"[^>]*>', page)
    if not match:
        raise SystemExit("articles/index.html has no Content-Security-Policy meta tag.")
    return match.group(0)


# ---------------------------------------------------------------- article page
def cover_html(article: dict) -> str:
    label, short, symbol, caption = CATEGORIES[article["category"]]
    if article["image"]:
        return (f'<div class="article-detail-cover article-detail-cover-photo"><img src="{esc(article["image"])}" '
                f'alt="{esc(article["imageAlt"])}" loading="eager" decoding="async"></div>')
    return (f'<div class="article-detail-cover article-visual-{article["category"]}"><span class="article-visual-label">{esc(label)}</span>'
            f'<span class="article-detail-cover-symbol" aria-hidden="true">{esc(symbol)}</span>'
            f'<span class="article-visual-caption">یادداشت تکیما</span></div>')


def related_html(article: dict, others: list[dict]) -> str:
    pool = [a for a in others if a["slug"] != article["slug"]]
    pool.sort(key=lambda a: (a["category"] != article["category"], ), reverse=False)
    picks = pool[:2]
    if not picks:
        return ""
    cards = "\n".join(
        f'<a class="related-article-card" href="{SITE_PREFIX}/articles/{quote(a["slug"])}/">'
        f'<span class="related-article-card-category">{esc(CATEGORIES[a["category"]][0])}</span>'
        f'<strong>{esc(a["title"])}</strong>'
        f'<span class="related-article-card-link">مطالعه مقاله <span aria-hidden="true">←</span></span></a>'
        for a in picks)
    return (f'<section class="related-articles" aria-labelledby="related-articles-title"><div class="related-articles-heading">'
            f'<div><span class="section-eyebrow">ادامه مسیر</span><h2 id="related-articles-title">مقاله‌های مرتبط</h2></div>'
            f'<a href="{SITE_PREFIX}/articles/">همه مقاله‌ها</a></div><div class="related-articles-grid">{cards}</div></section>')


def render_article(article: dict, others: list[dict]) -> str:
    header, footer, script = site_chrome()
    csp = csp_meta()
    body_html, toc, words = render_body(article["body"])
    minutes = max(1, math.ceil(words / 180))
    url = article_url(article["slug"])
    title, desc = esc(article["title"]), esc(article["description"])
    category_label = CATEGORIES[article["category"]][0]
    og_image = article["image"] or f"{BASE_URL}/assets/images/og-image.png"
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "@id": url + "#article", "mainEntityOfPage": {"@id": url + "#webpage"}, "url": url,
             "headline": article["title"], "description": article["description"], "inLanguage": "fa-IR",
             "author": {"@id": BASE_URL + "/#person"}, "publisher": {"@id": BASE_URL + "/#website"},
             "articleSection": category_label, "keywords": "، ".join(article["tags"]), "image": og_image,
             "datePublished": article["datePublished"], "dateModified": article["dateModified"],
             "isAccessibleForFree": True, "wordCount": words},
            {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": f'{article["title"]} | تکیما',
             "description": article["description"], "inLanguage": "fa-IR", "isPartOf": {"@id": BASE_URL + "/#website"},
             "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#article"},
             "datePublished": article["datePublished"], "dateModified": article["dateModified"]},
            {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "خانه", "item": BASE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": "مقالات", "item": BASE_URL + "/articles/"},
                {"@type": "ListItem", "position": 3, "name": article["title"], "item": url}]},
            {"@type": "WebSite", "@id": BASE_URL + "/#website", "url": BASE_URL + "/", "name": "تکیما",
             "alternateName": "Techima", "inLanguage": "fa", "publisher": {"@id": BASE_URL + "/#person"}},
            {"@type": "Person", "@id": BASE_URL + "/#person", "name": AUTHOR, "url": BASE_URL + "/about/",
             "sameAs": ["https://github.com/NMN-deb98"]},
        ],
    }
    schema_json = json.dumps(graph, ensure_ascii=False, indent=2).replace("</", "<\\/")
    toc_html = ""
    if len(toc) >= 2:
        items = "".join(f'<li><a href="#{sid}">{esc(text)}</a></li>' for sid, text in toc)
        toc_html = f'<aside class="article-detail-toc" aria-label="فهرست مطالب"><strong>در این مقاله می‌خوانید</strong><ol>{items}</ol></aside>'
    tags_html = ""
    if article["tags"]:
        tags_html = '<div class="article-tags" aria-label="برچسب‌ها">' + "".join(f'<span>{esc(t)}</span>' for t in article["tags"]) + "</div>"
    content_class = "article-detail-content" + ("" if toc_html else " article-detail-content-single")
    return f'''<!DOCTYPE html>
{GENERATED_MARK}
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {csp}
  <title>{title} | تکیما</title>
  <meta name="description" content="{desc}">
  <meta name="author" content="{AUTHOR}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="{esc(url)}">
  <meta name="theme-color" content="#0b1d3a">
  <link rel="icon" type="image/png" sizes="192x192" href="{SITE_PREFIX}/favicon.png">
  <link rel="icon" type="image/svg+xml" href="{SITE_PREFIX}/favicon.svg">
  <link rel="shortcut icon" href="{SITE_PREFIX}/favicon.ico">
  <link rel="apple-touch-icon" sizes="192x192" href="{SITE_PREFIX}/favicon.png">
  <link rel="manifest" href="{SITE_PREFIX}/manifest.webmanifest">
  <link rel="preload" href="{SITE_PREFIX}/assets/fonts/Vazirmatn-Variable.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{SITE_PREFIX}/assets/css/style.css">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="تکیما | Techima">
  <meta property="og:locale" content="fa_IR">
  <meta property="og:title" content="{title} | تکیما">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{esc(url)}">
  <meta property="og:image" content="{esc(og_image)}">
  <meta property="article:published_time" content="{article["datePublished"]}">
  <meta property="article:modified_time" content="{article["dateModified"]}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} | تکیما">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{esc(og_image)}">
  <script type="application/ld+json">
{schema_json}
  </script>
</head>
<body>
<a class="skip-link" href="#main">پرش به محتوای اصلی</a>
{header}
<main id="main">
<nav class="breadcrumb-wrap" aria-label="مسیر راهنما"><div class="container"><ol class="breadcrumb"><li><a href="{SITE_PREFIX}/">خانه</a></li><li class="breadcrumb-separator" aria-hidden="true">›</li><li><a href="{SITE_PREFIX}/articles/">مقالات</a></li><li class="breadcrumb-separator" aria-hidden="true">›</li><li aria-current="page"><span class="breadcrumb-current">{title}</span></li></ol></div></nav>
<article class="article-detail"><header class="article-detail-header">{cover_html(article)}<div class="article-detail-heading"><div class="article-feed-meta"><span>{esc(category_label)}</span><span>{fa(minutes)} دقیقه مطالعه</span><time datetime="{article["datePublished"]}" itemprop="datePublished">{jalali_label(article["datePublished"])}</time></div><h1>{title}</h1><p class="article-detail-lead">{desc}</p><div class="article-detail-byline"><span>نویسنده: <a href="{SITE_PREFIX}/about/">{AUTHOR}</a></span></div></div></header>
<div class="{content_class}">{toc_html}<div class="article-detail-prose article-cms-body">{body_html}{tags_html}{related_html(article, others)}<p class="article-detail-credit">این مقاله در تکیما منتشر شده است.</p><div class="article-detail-back"><a href="{SITE_PREFIX}/articles/">مشاهده سایر مقاله‌ها</a><a href="{SITE_PREFIX}/contact/">ارتباط با من</a></div></div></div></article></main>
{footer}
{script}
</body>
</html>
'''


# ---------------------------------------------------------------- articles index
def feed_card(article: dict) -> str:
    label, short, symbol, caption = CATEGORIES[article["category"]]
    thumb = ""
    if article["image"]:
        thumb = (f'<img class="article-feed-thumb" src="{esc(article["image"])}" alt="{esc(article["imageAlt"])}" '
                 f'width="800" height="450" loading="lazy" decoding="async">')
    decoration = "" if article["image"] else (f'<span class="article-visual-label">{esc(short)}</span><span class="article-visual-symbol">{esc(symbol)}</span><span class="article-visual-caption">{esc(caption)}</span>')
    photo_class = " has-photo" if article["image"] else ""
    minutes = max(1, math.ceil(render_body(article["body"])[2] / 180))
    return (
        f'<a class="article-feed-card article-feed-link" href="{SITE_PREFIX}/articles/{quote(article["slug"])}/" '
        f'data-category="{article["category"]}" aria-label="خواندن مقاله {esc(article["title"])}">\n'
        f'<div class="article-feed-visual article-visual-{article["category"]}{photo_class}" aria-hidden="true">{thumb}{decoration}</div>\n'
        f'<div class="article-feed-body"><div class="article-feed-meta"><span>{esc(label)}</span>'
        f'<time datetime="{article["datePublished"]}">{jalali_label(article["datePublished"])}</time></div>'
        f'<h3>{esc(article["title"])}</h3><p>{esc(article["description"])}</p>'
        f'<div class="article-feed-footer"><span class="article-draft-status article-published-status"><span></span>مشاهده مقاله</span>'
        f'<span class="article-read-time">{fa(minutes)} دقیقه مطالعه</span></div></div>\n</a>'
    )


def update_articles_index(articles: list[dict]) -> None:
    page = INDEX_PATH.read_text(encoding="utf-8")
    if MARKER_START not in page or MARKER_END not in page:
        raise SystemExit("articles/index.html is missing the CMS_ARTICLES markers.")
    block = MARKER_START + "\n" + "\n\n".join(feed_card(a) for a in articles) + "\n" + MARKER_END
    before, rest = page.split(MARKER_START, 1)
    _, after = rest.split(MARKER_END, 1)
    INDEX_PATH.write_text(before + block + after, encoding="utf-8")


# ---------------------------------------------------------------- sitemap
def update_sitemap(articles: list[dict]) -> None:
    """Refresh CMS article URLs; drop URLs whose page no longer exists; keep everything else."""
    ET.register_namespace("", SM)
    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()
    published_urls = {article_url(a["slug"]) for a in articles}
    pattern = re.compile(re.escape(BASE_URL) + r"/articles/([a-z0-9]+(?:-[a-z0-9]+)*)/")
    for node in list(root.findall("sm:url", NS)):
        loc = node.find("sm:loc", NS)
        match = pattern.fullmatch(loc.text) if loc is not None and loc.text else None
        if match and (loc.text in published_urls or not (ARTICLES_DIR / match.group(1) / "index.html").exists()):
            root.remove(node)
    for item in articles:
        node = ET.SubElement(root, f"{{{SM}}}url")
        ET.SubElement(node, f"{{{SM}}}loc").text = article_url(item["slug"])
        ET.SubElement(node, f"{{{SM}}}lastmod").text = item["dateModified"]
        ET.SubElement(node, f"{{{SM}}}changefreq").text = "monthly"
        ET.SubElement(node, f"{{{SM}}}priority").text = "0.7"
    if articles:
        newest = max(a["dateModified"] for a in articles)
        for node in root.findall("sm:url", NS):
            loc = node.find("sm:loc", NS)
            last = node.find("sm:lastmod", NS)
            if loc is not None and loc.text == BASE_URL + "/articles/" and last is not None and last.text < newest:
                last.text = newest
    ET.indent(root, space="  ")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    SITEMAP_PATH.write_text(xml, encoding="utf-8")


# ---------------------------------------------------------------- main
def is_generated(path: Path) -> bool:
    try:
        return GENERATED_MARK in path.read_text(encoding="utf-8")[:300]
    except OSError:
        return False


def main() -> None:
    articles = []
    for article in load_published():
        page = ARTICLES_DIR / article["slug"] / "index.html"
        if page.exists() and not is_generated(page):
            # Never overwrite a hand-written page, and never block the other articles because of it.
            print(f"::warning::Skipped CMS article '{article['slug']}': articles/{article['slug']}/ is a hand-written page.")
            continue
        articles.append(article)
    wanted = {a["slug"] for a in articles}

    for article in articles:
        out = ARTICLES_DIR / article["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_article(article, articles), encoding="utf-8")

    # Unpublished or deleted articles: remove only pages this script generated earlier.
    for folder in ARTICLES_DIR.iterdir():
        page = folder / "index.html"
        if folder.is_dir() and folder.name not in wanted and page.exists() and is_generated(page):
            shutil.rmtree(folder)

    update_articles_index(articles)
    update_sitemap(articles)
    print(f"Built {len(articles)} published CMS article(s).")


if __name__ == "__main__":
    main()
