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


SECTIONS = {
    "landing": ("home-landing-shortcuts", 1), "intro": ("home-intro", 2), "projects": ("home-projects", 3),
    "skills": ("home-skills", 4), "updates": ("home-updates", 5), "video": ("home-video-preview", 6),
    "journey": ("home-journey", 7), "contact": ("home-contact-cta", 8), "comments": ("comments-section", None),
}


def hex_ok(v) -> str:
    v = str(v or "").strip()
    return v if re.fullmatch(r"#[0-9a-fA-F]{6}", v) else ""


def shade(color: str, f: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    if f < 1:
        r, g, b = (int(c * f) for c in (r, g, b))
    else:
        r, g, b = (min(255, int(c + (255 - c) * (f - 1))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def theme_css(theme: dict) -> str:
    rules = []
    acc, navy, bg, txt = (hex_ok(theme.get(k)) for k in ("accent", "navy", "bg", "text"))
    if acc:
        rules += [f"--teal-500:{acc}", f"--teal-600:{shade(acc, .82)}", f"--teal-700:{shade(acc, .65)}", f"--teal-300:{shade(acc, 1.45)}", f"--teal-100:{shade(acc, 1.85)}", f"--teal-50:{shade(acc, 1.93)}"]
    if navy:
        rules += [f"--navy-800:{navy}", f"--navy-900:{shade(navy, .85)}", f"--navy-950:{shade(navy, .66)}", f"--navy-700:{shade(navy, 1.12)}", f"--navy-600:{shade(navy, 1.25)}"]
    if bg:
        rules.append(f"--bg:{bg}")
    if txt:
        rules.append(f"--text:{txt}")
    return ":root{" + ";".join(rules) + "}" if rules else ""


def custom_html(md_text: str) -> str:
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from build_articles import render_body
        return render_body(md_text)[0]
    except Exception:
        return "<p>" + esc(md_text) + "</p>"


def apply_home(text: str, home: dict) -> str:
    for key, (cls, seg) in SECTIONS.items():
        cfg = (home.get("sections") or {}).get(key) or {}
        hide = cfg.get("visible") is False
        text = re.sub(r'(<section class="section ' + cls + r'")(?: hidden)?', lambda m: m.group(1) + (" hidden" if hide else ""), text, count=1)
        if seg:
            text = re.sub(r'(<div class="network-road-segment network-road-segment-' + str(seg) + r'")(?: hidden)?', lambda m: m.group(1) + (" hidden" if hide else ""), text, count=1)
        pat = re.compile(r'<section class="section ' + cls + r'".*?</section>', re.S)
        m = pat.search(text)
        if not m:
            continue
        blk = m.group(0)
        if cfg.get("kicker"):
            blk = re.sub(r'(<span class="home-kicker">).*?(</span>)', lambda x: x.group(1) + esc(cfg["kicker"]) + x.group(2), blk, count=1, flags=re.S)
        if cfg.get("heading"):
            blk = re.sub(r'(<h2 id="[^"]*">).*?(</h2>)', lambda x: x.group(1) + esc(cfg["heading"]) + x.group(2), blk, count=1, flags=re.S)
        if cfg.get("lead"):
            blk = re.sub(r'(</h2>\s*<p>).*?(</p>)', lambda x: x.group(1) + esc(cfg["lead"]) + x.group(2), blk, count=1, flags=re.S)
        if key == "landing":
            for i, t in enumerate((home.get("tiles") or [])[:5]):
                u = link_url(t.get("url"))
                lab = str(t.get("label") or "").strip()
                idx = [0]

                def tile(x, i=i, u=u, lab=lab):
                    n = idx[0]
                    idx[0] += 1
                    if n != i:
                        return x.group(0)
                    out = x.group(0)
                    if u:
                        out = re.sub(r'href="[^"]*"', 'href="' + esc(u) + '"', out, count=1)
                    if lab:
                        out = re.sub(r'(<strong>).*?(</strong>)', lambda y: y.group(1) + esc(lab) + y.group(2), out, count=1, flags=re.S)
                    return out
                blk = re.sub(r'<a class="home-landing-tile".*?</a>', tile, blk, flags=re.S)
        text = text[:m.start()] + blk + text[m.end():]
    text = re.sub(r'<section class="section home-custom".*?</section>\s*', "", text, flags=re.S)
    blocks = []
    for c in (home.get("custom") or [])[:6]:
        title, md = str(c.get("title") or "").strip(), str(c.get("md") or "").strip()
        if not md:
            continue
        head = f'<div class="home-section-heading"><div><h2>{esc(title)}</h2></div></div>' if title else ""
        blocks.append(f'<section class="section home-custom"><div class="container">{head}<div class="article-detail-prose article-cms-body">{custom_html(md)}</div></div></section>\n')
    if blocks:
        text = text.replace('<section class="section comments-section"', "".join(blocks) + '<section class="section comments-section"', 1)
    return text


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
    if path.relative_to(ROOT).as_posix() == "index.html" and cfg.get("home"):
        text = apply_home(text, cfg["home"])
    text = re.sub(r'<style id="cms-theme">.*?</style>\s*', "", text, flags=re.S)
    css = theme_css(cfg.get("theme") or {})
    if css and "</head>" in text:
        text = text.replace("</head>", f'<style id="cms-theme">{css}</style>\n</head>', 1)
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
