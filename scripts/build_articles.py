#!/usr/bin/env python3
"""Build published CMS articles into GitHub Pages-compatible static HTML."""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

try:
    import markdown
    import bleach
except ImportError as exc:
    raise SystemExit("Missing dependencies: install Markdown and bleach with 'python -m pip install Markdown bleach'") from exc

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "articles"
ARTICLES_DIR = ROOT / "articles"
INDEX_PATH = ARTICLES_DIR / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
BASE_URL = "https://nmn-deb98.github.io/Techima.github.io"
SITE_PREFIX = "/Techima.github.io"
MARKER_START = "<!-- CMS_ARTICLES_START -->"
MARKER_END = "<!-- CMS_ARTICLES_END -->"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def safe_text(value: object, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def valid_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value))


def load_articles() -> list[dict]:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    articles = []
    for path in sorted(CONTENT_DIR.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Invalid CMS article JSON in {path}: {exc}") from exc
        if not isinstance(item, dict):
            raise SystemExit(f"CMS article must be a JSON object: {path}")
        if item.get("status") != "published":
            continue
        slug = safe_text(item.get("slug"), 100)
        title = safe_text(item.get("title"), 180)
        description = safe_text(item.get("description"), 300)
        body = item.get("body", "")
        if not valid_slug(slug):
            raise SystemExit(f"Invalid slug in {path.name}; use lowercase English letters, digits and hyphens.")
        if not title or not description or not isinstance(body, str) or not body.strip():
            raise SystemExit(f"Published article {path.name} needs title, description and body.")
        item["slug"], item["title"], item["description"], item["body"] = slug, title, description, body
        item["datePublished"] = safe_text(item.get("datePublished")) or dt.datetime.now(dt.timezone.utc).date().isoformat()
        item["dateModified"] = safe_text(item.get("dateModified")) or item["datePublished"]
        item["tags"] = [safe_text(tag, 60) for tag in item.get("tags", []) if safe_text(tag, 60)][:12]
        articles.append(item)
    slugs = [item["slug"] for item in articles]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Duplicate published article slug found.")
    return sorted(articles, key=lambda x: (x["datePublished"], x["title"]), reverse=True)


def article_url(article: dict) -> str:
    return f"{BASE_URL}/articles/{quote(article['slug'])}/"


def render_article(article: dict) -> str:
    title = html.escape(article["title"])
    description = html.escape(article["description"], quote=True)
    url = article_url(article)
    escaped_url = html.escape(url, quote=True)
    date_published = html.escape(article["datePublished"], quote=True)
    date_modified = html.escape(article["dateModified"], quote=True)
    tags = "".join(f'<span class="chip">{html.escape(tag)}</span>' for tag in article["tags"])
    rendered_body = markdown.markdown(
        article["body"],
        extensions=["extra", "sane_lists", "tables", "fenced_code"],
        output_format="html5",
    )
    # CMS content is untrusted input. Strip scripts, event handlers and unsafe URL protocols.
    body_html = bleach.clean(
        rendered_body,
        tags={
            "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
            "strong", "em", "del", "blockquote", "ul", "ol", "li",
            "a", "img", "figure", "figcaption", "pre", "code",
            "table", "thead", "tbody", "tr", "th", "td", "div", "span",
        },
        attributes={
            "a": ["href", "title"],
            "img": ["src", "alt", "title", "width", "height", "loading"],
            "th": ["align"], "td": ["align"],
            "code": ["class"], "pre": ["class"],
        },
        protocols={"http", "https", "mailto"},
        strip=True,
    )
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": url + "#article",
                "mainEntityOfPage": {"@type": "WebPage", "@id": url},
                "headline": article["title"],
                "description": article["description"],
                "datePublished": article["datePublished"],
                "dateModified": article["dateModified"],
                "author": {
                    "@type": "Person",
                    "@id": BASE_URL + "/#person",
                    "name": "نیما مددی نعمتی",
                    "url": BASE_URL + "/",
                },
                "publisher": {"@type": "Person", "name": "نیما مددی نعمتی"},
                "inLanguage": "fa",
                **({"image": article["image"]} if isinstance(article.get("image"), str) and article["image"].startswith("https://") else {}),
                "keywords": article["tags"],
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "خانه", "item": BASE_URL + "/"},
                    {"@type": "ListItem", "position": 2, "name": "مقالات", "item": BASE_URL + "/articles/"},
                    {"@type": "ListItem", "position": 3, "name": article["title"], "item": url},
                ],
            },
        ],
    }
    schema_json = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    image_html = ""
    if isinstance(article.get("image"), str) and article["image"].startswith("https://"):
        image_html = f'<figure class="article-hero-thumb"><img src="{html.escape(article["image"], quote=True)}" alt="{html.escape(safe_text(article.get("imageAlt"), 180), quote=True)}" loading="eager" decoding="async"></figure>'
    return f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | تکیما</title>
  <meta name="description" content="{description}">
  <meta name="author" content="نیما مددی نعمتی">
  <link rel="canonical" href="{escaped_url}">
  <meta name="robots" content="index,follow">
  <meta name="theme-color" content="#0b1d3a">
  <link rel="icon" type="image/png" href="{SITE_PREFIX}/favicon.png">
  <link rel="preload" href="{SITE_PREFIX}/assets/fonts/Vazirmatn-Variable.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{SITE_PREFIX}/assets/css/style.css">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="تکیما | Techima">
  <meta property="og:locale" content="fa_IR">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{escaped_url}">
  <meta property="article:published_time" content="{date_published}">
  <meta property="article:modified_time" content="{date_modified}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <script type="application/ld+json">{schema_json}</script>
</head>
<body>
  <a class="skip-link" href="#main">پرش به محتوای اصلی</a>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="{SITE_PREFIX}/" aria-label="تکیما، بازگشت به صفحهٔ اصلی">
        <svg class="brand-mark" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><rect width="64" height="64" rx="14" fill="#14b8a6"/><rect x="15" y="15" width="34" height="8" rx="4" fill="#0b1d3a"/><rect x="28" y="15" width="8" height="30" rx="4" fill="#0b1d3a"/><circle cx="32" cy="47" r="5" fill="#fff"/></svg>
        <span class="brand-text">تکیما<small>TECHIMA</small></span>
      </a>
      <nav class="main-nav" aria-label="منوی اصلی"><ul>
        <li><a href="{SITE_PREFIX}/">خانه</a></li>
        <li><a href="{SITE_PREFIX}/about/">درباره من</a></li>
        <li><a href="{SITE_PREFIX}/projects/">پروژه‌ها</a></li>
        <li><a href="{SITE_PREFIX}/articles/" aria-current="page">مقالات</a></li>
        <li><a href="{SITE_PREFIX}/contact/">تماس با من</a></li>
      </ul></nav>
    </div>
  </header>
  <main id="main">
    <section class="page-hero" aria-labelledby="article-title"><div class="container">
      <nav aria-label="مسیر راهنما"><ol class="breadcrumb">
        <li><a href="{SITE_PREFIX}/">خانه</a></li>
        <li><a href="{SITE_PREFIX}/articles/">مقالات</a></li>
        <li aria-current="page">{title}</li>
      </ol></nav>
      <h1 id="article-title">{title}</h1>
      <p>{description}</p>
      <p class="article-meta"><time datetime="{date_published}">{date_published}</time></p>
    </div></section>
    <section class="section" style="padding-top:0"><div class="container">
      <article class="article-content">
        {image_html}
        {body_html}
        {f'<div class="article-tags">{tags}</div>' if tags else ''}
      </article>
    </div></section>
  </main>
  <footer class="site-footer"><div class="container footer-inner">
    <div><span class="footer-brand">تکیما</span><p>وب‌سایت شخصی نیما مددی نعمتی</p></div>
    <nav aria-label="پیوندهای فوتر"><h2>صفحه‌ها</h2><ul>
      <li><a href="{SITE_PREFIX}/">خانه</a></li><li><a href="{SITE_PREFIX}/about/">درباره من</a></li>
      <li><a href="{SITE_PREFIX}/projects/">پروژه‌ها</a></li><li><a href="{SITE_PREFIX}/articles/">مقالات</a></li>
      <li><a href="{SITE_PREFIX}/contact/">تماس با من</a></li>
    </ul></nav>
    <div><h2>ارتباط</h2><ul><li><a href="https://github.com/NMN-deb98" rel="me noopener noreferrer" target="_blank">گیت‌هاب (GitHub)</a></li></ul></div>
  </div><div class="container footer-bottom">© <span id="year">۱۴۰۵</span> تکیما — نیما مددی نعمتی</div></footer>
  <script src="{SITE_PREFIX}/assets/js/main.js" defer></script>
</body>
</html>
'''


def update_articles_index(articles: list[dict]) -> None:
    current = INDEX_PATH.read_text(encoding="utf-8")
    cards = [MARKER_START, '<section class="section" aria-labelledby="cms-articles-title"><div class="container">',
             '<h2 id="cms-articles-title">نوشته‌های منتشرشده</h2>',
             '<div class="card-grid">']
    for item in articles:
        cards.append(
            f'<a class="card card-link" href="{SITE_PREFIX}/articles/{quote(item["slug"])}/">'
            f'<h3>{html.escape(item["title"])}</h3><p>{html.escape(item["description"])}</p>'
            f'<span class="article-card-date">{html.escape(item["datePublished"])}</span></a>'
        )
    cards.extend(['</div></div></section>', MARKER_END])
    block = "\n".join(cards)
    if MARKER_START in current and MARKER_END in current:
        before, rest = current.split(MARKER_START, 1)
        _, after = rest.split(MARKER_END, 1)
        current = before + block + after
    else:
        current = current.replace("</main>", block + "\n</main>", 1)
    INDEX_PATH.write_text(current, encoding="utf-8")


def update_sitemap(articles: list[dict]) -> None:
    if SITEMAP_PATH.exists():
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
    else:
        root = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
        tree = ET.ElementTree(root)
    # Remove stale URLs generated by this CMS, but preserve all unrelated site URLs.
    generated_url_pattern = re.compile(re.escape(BASE_URL) + r"/articles/[a-z0-9]+(?:-[a-z0-9]+)*/")
    for node in list(root.findall("sm:url", NS)):
        loc = node.find("sm:loc", NS)
        if loc is not None and loc.text and generated_url_pattern.fullmatch(loc.text):
            root.remove(node)
    existing = {el.text for el in root.findall("sm:url/sm:loc", NS)}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    for item in articles:
        url = article_url(item)
        if url in existing:
            continue
        node = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = url
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = today
    ET.indent(root, space="  ")
    tree.write(SITEMAP_PATH, encoding="utf-8", xml_declaration=True)


def main() -> None:
    articles = load_articles()
    for article in articles:
        out = ARTICLES_DIR / article["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_article(article), encoding="utf-8")
    update_articles_index(articles)
    update_sitemap(articles)
    print(f"Built {len(articles)} published CMS article(s).")


if __name__ == "__main__":
    main()
