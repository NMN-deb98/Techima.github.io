#!/usr/bin/env python3
"""Rebuilds the performance-optimised static assets of the Techima site.

  python scripts/optimize_assets.py css    -> assets/css/style.src.css  ->  assets/css/style.css (minified)
  python scripts/optimize_assets.py font   -> assets/fonts/Vazirmatn-Full.woff2 -> Vazirmatn-Variable.woff2 (subset)
  python scripts/optimize_assets.py sw     -> stamps sw.js with a hash of the static files (run after css/font/js changes)
  python scripts/optimize_assets.py        -> all three

Edit style.src.css (readable) — never style.css directly. Nothing visible is removed: the font keeps every
Persian/Arabic letter, digit, punctuation mark and the Latin range; the CSS minifier only drops comments/whitespace.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def minify_css(src: str) -> str:
    out, i, n = [], 0, len(src)
    keep = []  # strings and url() bodies are protected from whitespace changes
    while i < n:
        c = src[i]
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            keep.append(src[i:j + 1]); out.append("\x00%d\x00" % (len(keep) - 1)); i = j + 1
        elif src.startswith("url(", i):
            j = src.find(")", i)
            keep.append(src[i:j + 1]); out.append("\x00%d\x00" % (len(keep) - 1)); i = j + 1
        else:
            out.append(c); i += 1
    css = "".join(out)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    css = css.replace(";}", "}")
    css = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], css)
    return css.strip() + "\n"


def build_css():
    src_path = os.path.join(ROOT, "assets/css/style.src.css")
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    css = minify_css(src)
    with open(os.path.join(ROOT, "assets/css/style.css"), "w", encoding="utf-8") as f:
        f.write(css)
    print("css", len(src), "->", len(css))


def build_font():
    from fontTools import subset
    full = os.path.join(ROOT, "assets/fonts/Vazirmatn-Full.woff2")
    out = os.path.join(ROOT, "assets/fonts/Vazirmatn-Variable.woff2")
    opts = subset.Options()
    opts.layout_features = ["ccmp", "locl", "init", "medi", "fina", "isol", "rlig", "liga", "calt", "rclt", "curs",
                            "mark", "mkmk", "kern", "dist", "numr", "dnom", "frac", "case", "zero", "tnum", "pnum", "lnum", "onum",
                            "ss01", "ss02", "ss03"]
    opts.flavor = "woff2"; opts.notdef_outline = True; opts.name_IDs = [1, 2, 3, 4, 6]; opts.hinting = False
    unis = [*range(0x20, 0x7F), *range(0xA0, 0x180), *range(0x600, 0x700), *range(0x750, 0x780), *range(0x8A0, 0x900),
            *range(0x2000, 0x2070), *range(0x20A0, 0x20C0), *range(0x2190, 0x21A0), 0x2200,
            0x2212, 0x2022, 0x2026, 0x2190, 0x2192, 0x25CF, 0x2713]
    font = subset.load_font(full, opts)
    s = subset.Subsetter(opts); s.populate(unicodes=unis); s.subset(font)
    subset.save_font(font, out, opts)
    print("font", os.path.getsize(full), "->", os.path.getsize(out))


def build_sw():
    """Stamps sw.js with a hash of the static files, so every changed file reaches visitors on their next visit."""
    import hashlib
    h = hashlib.sha1()
    for rel in ["assets/css/style.css", "assets/js/main.js", "assets/js/comments.js", "assets/fonts/Vazirmatn-Variable.woff2"]:
        with open(os.path.join(ROOT, rel), "rb") as f:
            h.update(f.read())
    path = os.path.join(ROOT, "sw.js")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    new = re.sub(r'const VERSION = "[^"]*";', 'const VERSION = "%s";' % h.hexdigest()[:10], src, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print("sw version", h.hexdigest()[:10])


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what == "all":
        build_css(); build_font(); build_sw()
    else:
        {"css": build_css, "font": build_font, "sw": build_sw}[what]()
