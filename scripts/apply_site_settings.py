#!/usr/bin/env python3
"""Apply content/site.json (menu, footer, social links, announcement bar, home hero) to the static pages.

Idempotent: running it twice produces the same files. If content/site.json does not exist nothing changes.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_PREFIX = "/Techima.github.io"
SKIP_PARTS = {"nimacrm", "backend", "node_modules", ".git", "scripts"}
SKIP_FILES = {"admin-comments.html"}
ICONS = {"instagram": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"/><circle cx=\"12\" cy=\"12\" r=\"4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"/><circle cx=\"17.5\" cy=\"6.8\" r=\"1.2\" fill=\"currentColor\"/></svg>", "youtube": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"2.5\" y=\"5\" width=\"19\" height=\"14\" rx=\"4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"m10 9 5 3-5 3z\" fill=\"currentColor\"/></svg>", "aparat": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M4 5.5h16v13H4z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/><path d=\"m9 8 7 4-7 4z\" fill=\"currentColor\"/></svg>", "telegram": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"m21 3-7.4 18-3.7-7.1L3 10.2 21 3Z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/><path d=\"m9.9 13.9 4.8-4.8\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/></svg>", "linkedin": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"M7 10v7M7 7v.1M11 17v-7h3.2a2.8 2.8 0 0 1 2.8 2.8V17M11 13a3 3 0 0 1 6 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/></svg>", "email": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"14\" rx=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"m4 7 8 6 8-6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/></svg>", "x": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M18.9 2H22l-6.8 7.8L23.2 22h-6.3l-5-7.5L5.3 22H2.1l7.3-8.4L1.5 2h6.5l4.5 6.9L18.9 2Zm-1.1 18h1.7L7 3.9H5.2L17.8 20Z\" fill=\"currentColor\"/></svg>", "github": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M9 19c-4.5 1.4-4.5-2.5-6.3-3m12.6 6v-3.5a3 3 0 0 0-.8-2.3c2.7-.3 5.5-1.3 5.5-6A4.7 4.7 0 0 0 18.7 7a4.3 4.3 0 0 0-.1-3.2S17.5 3.5 15 5.2a13 13 0 0 0-6 0C6.5 3.5 5.4 3.8 5.4 3.8A4.3 4.3 0 0 0 5.3 7a4.7 4.7 0 0 0-1.3 3.2c0 4.7 2.8 5.7 5.5 6a3 3 0 0 0-.8 2.3V22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.6\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>", "link": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/></svg>"}


def esc(v) -> str:
    return html.escape(str(v or ""), quote=True)


def link_url(url: str) -> str:
    url = str(url or "").strip()
    if url.startswith("/") and not url.startswith("//"):
        return SITE_PREFIX + url
    if re.match(r"^(https://|mailto:)", url):
        return url
    return ""


def page_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return SITE_PREFIX + "/"
    if rel.endswith("/index.html"):
        return SITE_PREFIX + "/" + rel[: -len("index.html")]
    return SITE_PREFIX + "/" + rel


def current(item_url: str, here: str) -> bool:
    if item_url == here:
        return True
    return item_url != SITE_PREFIX + "/" and item_url.endswith("/") and here.startswith(item_url)


def nav_items(menu: list, here: str, cur: bool) -> str:
    out = []
    for m in menu:
        url = link_url(m.get("url"))
        label = str(m.get("label") or "").strip()
        if not url or not label:
            continue
        aria = ' aria-current="page"' if cur and current(url, here) else ""
        out.append(f'          <li><a href="{esc(url)}"{aria}>{esc(label)}</a></li>')
    return "\n".join(out)


def social_items(items: list) -> str:
    out = []
    for s in items:
        url = link_url(s.get("url"))
        label = str(s.get("label") or "").strip()
        if not url or not label:
            continue
        icon = ICONS.get(s.get("icon"), ICONS["link"])
        ext = "" if url.startswith(SITE_PREFIX) else ' rel="me noopener noreferrer" target="_blank"'
        out.append(f'          <li><a class="footer-social-item" href="{esc(url)}"{ext}>{icon}{esc(label)}</a></li>')
    return "\n".join(out)


def apply_page(path: Path, cfg: dict) -> bool:
    text = path.read_text(encoding="utf-8")
    if '<header class="site-header">' not in text:
        return False
    orig = text
    here = page_url(path)
    menu = cfg.get("menu") or []
    if menu:
        def head(m):
            blk = m.group(0)
            ul = nav_items(menu, here, True)
            return re.sub(r'(<nav class="main-nav"[^>]*>\s*<ul>)(.*?)(</ul>)', lambda x: x.group(1) + "\n" + ul + "\n        " + x.group(3), blk, count=1, flags=re.S)
        text = re.sub(r'<header class="site-header">.*?</header>', head, text, count=1, flags=re.S)

    def foot(m):
        blk = m.group(0)
        if menu:
            ul = nav_items(menu, here, False)
            blk = re.sub(r'(<nav aria-label="پیوندهای فوتر">\s*<h2>[^<]*</h2>\s*<ul>)(.*?)(</ul>)', lambda x: x.group(1) + "\n" + ul + "\n        " + x.group(3), blk, count=1, flags=re.S)
        if cfg.get("footerText"):
            blk = re.sub(r'(<span class="footer-brand">.*?</span>\s*)<p>.*?</p>', lambda x: x.group(1) + "<p>" + esc(cfg["footerText"]) + "</p>", blk, count=1, flags=re.S)
        if cfg.get("social"):
            si = social_items(cfg["social"])
            blk = re.sub(r'(<ul class="footer-social-list">)(.*?)(</ul>)', lambda x: x.group(1) + "\n" + si + "\n        " + x.group(3), blk, count=1, flags=re.S)
        if cfg.get("copyright"):
            blk = re.sub(r'(© <span id="year">[^<]*</span>)[^<]*(</div>)', lambda x: x.group(1) + " " + esc(cfg["copyright"]) + "\n    " + x.group(2), blk, count=1, flags=re.S)
        return blk
    text = re.sub(r'<footer class="site-footer">.*?</footer>', foot, text, count=1, flags=re.S)

    text = re.sub(r'<div class="site-announcement"[^>]*>.*?</div>\s*', "", text, count=1, flags=re.S)
    ann = cfg.get("announcement") or {}
    if ann.get("enabled") and str(ann.get("text") or "").strip():
        au = link_url(ann.get("url"))
        inner = esc(ann["text"].strip())
        if au:
            inner = f'<a href="{esc(au)}">{inner}</a>'
        text = text.replace('<header class="site-header">', f'<div class="site-announcement" role="note">{inner}</div>\n  <header class="site-header">', 1)

    hero = cfg.get("hero") or {}
    if hero and path.relative_to(ROOT).as_posix() == "index.html":
        if hero.get("eyebrow"):
            text = re.sub(r'(<p class="hero-eyebrow">).*?(</p>)', lambda x: x.group(1) + esc(hero["eyebrow"]) + x.group(2), text, count=1, flags=re.S)
        if hero.get("brand") or hero.get("title"):
            text = re.sub(r'(<h1 id="home-title">).*?(</h1>)', lambda x: x.group(1) + "<span>" + esc(hero.get("brand", "")) + "</span>" + esc(hero.get("title", "")) + x.group(2), text, count=1, flags=re.S)
        if hero.get("lead"):
            text = re.sub(r'(<p class="hero-lead">).*?(</p>)', lambda x: x.group(1) + "\n            " + esc(hero["lead"]) + "\n          " + x.group(2), text, count=1, flags=re.S)
        btns = [b for b in (hero.get("buttons") or []) if link_url(b.get("url")) and str(b.get("label") or "").strip()][:2]
        if btns:
            cls = ["btn btn-primary", "btn btn-ghost"]
            row = "\n".join(f'            <a class="{cls[i]}" href="{esc(link_url(b["url"]))}">{esc(b["label"])}</a>' for i, b in enumerate(btns))
            text = re.sub(r'(<div class="btn-row">).*?(</div>)', lambda x: x.group(1) + "\n" + row + "\n          " + x.group(2), text, count=1, flags=re.S)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    cfg_path = ROOT / "content" / "site.json"
    if not cfg_path.exists():
        print("No content/site.json; nothing to apply.")
        return
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if SKIP_PARTS & set(rel.parts[:-1]) or path.name in SKIP_FILES or path.name.startswith("google"):
            continue
        if apply_page(path, cfg):
            changed += 1
    print(f"Applied site settings to {changed} page(s).")


if __name__ == "__main__":
    main()
