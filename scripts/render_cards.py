#!/usr/bin/env python3
"""Render the animated SVG cards for the profile README.

    python scripts/render_cards.py            # animated
    STATIC=1 python scripts/render_cards.py   # final frames, for screenshots

Reads  data/profile.json, data/github.json (written by fetch_github.py),
       data/portrait.txt, fonts/*.woff, fonts/metrics.json
Writes cards/*.svg

Standard library only. README images are shown through <img>, so each SVG is
self-contained: fonts are embedded as base64 WOFF subsets, motion is CSS
keyframes plus SMIL for the name shine and the count-ups.
"""
import base64
import datetime as dt
import json
import os
import pathlib
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "cards"
STATIC = os.environ.get("STATIC") == "1"

PAPER, RULE = "#f7f4ed", "#ddd6c7"
INK, INK2, MUTED = "#1c1b18", "#45413a", "#7d776b"
ACCENT = {"blue": "#2d55c8", "red": "#c8432b", "yellow": "#d29b12"}
BLUE = ACCENT["blue"]
BAR = "#d9d1c0"
LEVELS = ["#ebe6da", "#c9d3ef", "#93a9e4", "#5378d8", "#2347b5"]

METRICS = json.loads((ROOT / "fonts" / "metrics.json").read_text(encoding="utf-8"))
FAMILY = {"serif": "IS", "serif-italic": "ISI", "sans": "GS", "sans-medium": "GSM", "mono": "GM"}
FALLBACK = {
    "serif": "Georgia,'Times New Roman',serif",
    "serif-italic": "Georgia,'Times New Roman',serif",
    "sans": "system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif",
    "sans-medium": "system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif",
    "mono": "ui-monospace,Menlo,Consolas,monospace",
}


def width(text, face, size, spacing=0.0):
    m = METRICS[face]
    return sum(m["widths"].get(ch, m["fallback"]) for ch in text) * size + spacing * max(0, len(text) - 1)


def wrap(text, face, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and width(trial, face, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def font_css(faces):
    css = []
    for f in faces:
        b64 = base64.b64encode((ROOT / "fonts" / f"{f}.woff").read_bytes()).decode()
        style = "italic" if f == "serif-italic" else "normal"
        css.append(f"@font-face{{font-family:'{FAMILY[f]}';font-style:{style};src:url(data:font/woff;base64,{b64}) format('woff')}}")
        css.append(f".{f}{{font-family:'{FAMILY[f]}',{FALLBACK[f]}{';font-style:italic' if style == 'italic' else ''}}}")
    return "".join(css)


KEYFRAMES = """
.fb{transform-box:fill-box}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{0%{opacity:0;transform:scale(.2)}70%{opacity:1;transform:scale(1.12)}100%{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes draw{from{stroke-dashoffset:var(--len)}to{stroke-dashoffset:0}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.25;transform:scale(1.9)}}
@keyframes ring{0%{opacity:.5;transform:scale(.15)}100%{opacity:0;transform:scale(1.5)}}
@keyframes swing{0%{opacity:0;transform:translateY(36px) rotate(-3.5deg)}62%{opacity:1;transform:translateY(-4px) rotate(.8deg)}82%{transform:translateY(1px) rotate(-.2deg)}100%{opacity:1;transform:none}}
@keyframes nudge{0%,70%,100%{transform:translate(0,0)}82%{transform:translate(3px,-3px)}}
@keyframes sweep{0%{transform:translateX(40px) skewX(-18deg)}28%,100%{transform:translateX(720px) skewX(-18deg)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def anim(name, dur, delay=0.0, ease="cubic-bezier(.2,.8,.2,1)", loop=False, origin=None, extra=""):
    s = f"animation:{name} {dur}s {ease} {delay:.3f}s {'infinite' if loop else 'both'}"
    if origin:
        s += f";transform-origin:{origin}"
    return f'style="{s}{extra}"'


def svg(w, h, body, faces, defs="", extra_css="", title=""):
    css = font_css(faces) + KEYFRAMES + extra_css + ("*{animation:none!important}" if STATIC else "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="{escape(title)}"><title>{escape(title)}</title><defs>{defs}</defs><style>{css}</style>{body}</svg>'
    )


def frame(w, h, r=16):
    return f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="{PAPER}" stroke="{RULE}"/>'


def text(x, y, s, face, size, fill, anchor="start", spacing=0.0, attrs=""):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text class="{face}" x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{ls} '
            f'{attrs}>{escape(s)}</text>')


def countup(total, x, y, fmt, face, size, fill, start, anchor="start", n=20, step=0.055):
    if STATIC or not isinstance(total, int) or total <= 0:
        return text(x, y, fmt(total), face, size, fill, anchor)
    out = []
    for i in range(n):
        v = total if i == n - 1 else round(total * (1 - (1 - (i + 1) / n) ** 3))
        keep = "freeze" if i == n - 1 else "remove"
        out.append(
            f'<text class="{face}" x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" opacity="0">'
            f'{escape(fmt(v))}<set attributeName="opacity" to="1" begin="{start + i*step:.3f}s" dur="{step:.3f}s" fill="{keep}"/></text>'
        )
    return "".join(out)


# ------------------------------------------------------------------ hero
def hero(cfg):
    W, H = 900, 460
    portrait = (ROOT / "data" / "portrait.txt")
    rows = portrait.read_text(encoding="utf-8").split("\n") if portrait.exists() else []
    text_w = 420 if rows else 800
    x0 = 52

    l1, l2 = cfg["name_lines"]
    size = 80
    while max(width(l1, "serif", size), width(l2, "serif-italic", size)) > text_w and size > 40:
        size -= 2

    defs = (
        f'<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="260" y2="0" gradientTransform="translate(-400 0)">'
        f'<stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}"/>'
        f'<stop offset=".5" stop-color="{BLUE}"/><stop offset=".58" stop-color="{INK}"/><stop offset="1" stop-color="{INK}"/>'
        + ("" if STATIC else '<animateTransform attributeName="gradientTransform" type="translate" values="-300 0;700 0;700 0" '
           'keyTimes="0;.45;1" dur="6s" begin="2.4s" repeatCount="indefinite"/>')
        + "</linearGradient>"
    )
    b = [frame(W, H, 18)]
    b.append(f'<g {anim("fade", .7, .1)}>' + text(x0, 70, cfg["kicker"], "mono", 11, MUTED, spacing=2.2) + "</g>")
    y1, y2 = 70 + size * 1.25, 70 + size * 2.15
    b.append(f'<g {anim("rise", .9, .35)}>' + text(x0 - 3, round(y1), l1, "serif", size, INK, spacing=-1) + "</g>")
    b.append(f'<g {anim("rise", .9, .55)}>' + text(x0 - 3, round(y2), l2, "serif-italic", size, "url(#shine)", spacing=-1) + "</g>")

    ry = round(y2 + 36)
    rule_len = text_w
    b.append(f'<line x1="{x0}" x2="{x0 + rule_len}" y1="{ry}" y2="{ry}" stroke="{RULE}" stroke-dasharray="{rule_len}" '
             f'{anim("draw", 1.1, 1.0, extra=f";--len:{rule_len}")}/>')

    sy = ry + 38
    b.append(f'<g {anim("fade", .7, 1.3)}>'
             f'<circle class="fb" cx="{x0 + 5}" cy="{sy - 5}" r="4" fill="{BLUE}" {anim("pulse", 2.4, 0, "ease-in-out", True, "50% 50%")}/>'
             + text(x0 + 20, sy, cfg["status"], "sans-medium", 16, INK) + "</g>")
    for i, line in enumerate(wrap(cfg["blurb"], "sans", 14.5, text_w)):
        b.append(f'<g {anim("fade", .7, 1.5 + i*.12)}>' + text(x0, sy + 34 + i * 23, line, "sans", 14.5, INK2) + "</g>")
    b.append(f'<g {anim("fade", .8, 1.9)}>' + text(x0, H - 46, "  ·  ".join(cfg["stack"]).upper(), "mono", 10.5, MUTED, spacing=1.6) + "</g>")

    if rows:
        lh = 4.15
        cw = METRICS["mono"]["widths"]["a"] * lh
        cols = max(len(r) for r in rows)
        pw, ph = cols * cw, len(rows) * lh
        px, py = W - 30 - pw, (H - ph) / 2
        ramp = " .:-=+*#%@"
        tone = lambda ch: "#a39b8a" if ramp.find(ch) <= 2 else INK2 if ramp.find(ch) <= 5 else INK
        out = [f'<g class="mono" font-size="{lh}">']
        for i, r in enumerate(rows):
            if not r.strip():
                continue
            spans, run, col = [], "", None
            for ch in r:
                c = col if ch == " " and col else tone(ch)
                if c != col and run:
                    spans.append(f'<tspan fill="{col}">{escape(run)}</tspan>')
                    run = ""
                col, run = c, run + ch
            spans.append(f'<tspan fill="{col}">{escape(run)}</tspan>')
            out.append(f'<text xml:space="preserve" x="{px:.1f}" y="{py + (i+1)*lh:.2f}" {anim("fade", .25, .5 + i*.018, "linear")}>{"".join(spans)}</text>')
        out.append("</g>")
        b.append("".join(out))
    return svg(W, H, "".join(b), ["serif", "serif-italic", "sans", "sans-medium", "mono"], defs,
               title=f'{cfg["name"]}. {cfg["status"]}. {cfg["blurb"]}')


# ------------------------------------------------------------------ tiles
def tile(t, idx, gh):
    W, H = 300, 236
    color = ACCENT[t["accent"]]
    value = t.get("value")
    if t.get("value_from") == "repos":
        value = gh.get("repos") if gh else None
    delay = .3 + idx * .16

    defs = (
        f'<clipPath id="c{idx}"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
        f'<linearGradient id="s{idx}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
    )
    b = [frame(W, H, 16), f'<g clip-path="url(#c{idx})">']
    for k in range(2):
        b.append(f'<circle class="fb" cx="{W}" cy="0" r="120" fill="none" stroke="{color}" stroke-width="1.2" opacity="0" '
                 f'{anim("ring", 4, delay + 1 + k*2, "ease-out", True, "50% 50%")}/>')
    b.append(f'<circle cx="{W}" cy="0" r="38" fill="{color}" fill-opacity=".09"/>')
    b.append(f'<rect class="fb" x="-200" y="0" width="90" height="{H}" fill="url(#s{idx})" '
             f'{anim("sweep", 7, delay + 2.2 + idx*.8, "ease-in-out", True)}/>')
    b.append("</g>")

    b.append(text(24, 40, f'{idx+1:02d} — {t["kicker"]}', "mono", 10.5, color, spacing=1.8))
    b.append(f'<g class="fb" {anim("nudge", 3.2, 2 + idx*.4, "ease-in-out", True)}>' + text(W - 24, 41, "↗", "sans", 16, INK2, "end") + "</g>")

    if isinstance(value, int):
        b.append(countup(value, 22, 122, lambda v: f"{v:,}", "serif", 66, INK, delay + .7))
    else:
        face = "serif-italic" if t.get("italic") else "serif"
        b.append(text(22, 122, value if value is not None else "—", face, 66 if len(str(value or "-")) < 6 else 54, INK, spacing=-.5))
    b.append(text(24, 150, t["label"], "sans-medium", 13, INK))
    for i, line in enumerate(wrap(t["caption"], "sans", 12.5, W - 48)[:3]):
        b.append(text(24, 177 + i * 19, line, "sans", 12.5, MUTED))

    body = f'<g class="fb" {anim("swing", 1.05, delay, origin="50% 100%")}>{"".join(b)}</g>'
    return svg(W, H, body, ["serif", "serif-italic", "sans", "sans-medium", "mono"], defs,
               title=f'{t["kicker"]}: {value if value is not None else ""} {t["label"]}. {t["caption"]}')


# ------------------------------------------------------------------ activity
def load_github():
    p = ROOT / "data" / "github.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d if d.get("weeks") else None


def days(gh):
    return [d for wk in gh["weeks"] for d in wk] if gh else []


def streaks(ds):
    longest = cur = 0
    for d in ds:
        cur = cur + 1 if d["c"] > 0 else 0
        longest = max(longest, cur)
    current = 0
    tail = list(ds)
    if tail and tail[-1]["c"] == 0:  # today not counted yet is fine
        tail = tail[:-1]
    for d in reversed(tail):
        if d["c"] > 0:
            current += 1
        else:
            break
    return current, longest


def activity(gh):
    W, H = 900, 290
    ds = days(gh)
    today = dt.date.today()
    keys, y, m = [], today.year, today.month
    for _ in range(12):
        keys.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    keys.reverse()
    sums = {k: 0 for k in keys}
    for d in ds:
        dd = dt.date.fromisoformat(d["d"])
        if (dd.year, dd.month) in sums:
            sums[(dd.year, dd.month)] += d["c"]
    best = max(keys, key=lambda k: sums[k]) if gh else None
    mx = max(sums.values()) or 1

    b = [frame(W, H, 16)]
    b.append(text(40, 52, "LAST 12 MONTHS", "mono", 10.5, MUTED, spacing=2))
    b.append(text(40, 92, "Activity", "serif", 40, INK, spacing=-.5))

    x0, base, top, bw, step = 40, 248, 138, 30, 46.5
    b.append(f'<line x1="{x0}" x2="{x0 + step*12 - (step-bw)}" y1="{base}" y2="{base}" stroke="{RULE}"/>')
    for i, k in enumerate(keys):
        v = sums[k]
        h = max(3, v / mx * (base - top)) if gh else 3
        bx = x0 + i * step
        fill = BLUE if k == best and v > 0 else BAR
        b.append(f'<rect class="fb" x="{bx}" y="{base - h:.1f}" width="{bw}" height="{h:.1f}" rx="3" fill="{fill}" '
                 f'{anim("grow", .9, .4 + i*.06, origin="50% 100%")}/>')
        if k == best and v > 0:
            b.append(f'<g class="fb" {anim("pop", .5, 1.4, origin="50% 100%")}>'
                     + text(bx + bw / 2, base - h - 9, f"{v:,}", "mono", 11, BLUE, "middle") + "</g>")
        b.append(text(bx + bw / 2, base + 22, dt.date(k[0], k[1], 1).strftime("%b").upper(), "mono", 9.5, MUTED, "middle", 1))

    sx = 640
    b.append(f'<line x1="{sx - 28}" x2="{sx - 28}" y1="40" y2="{H - 40}" stroke="{RULE}"/>')
    cur, longest = streaks(ds)
    stats = [
        ("CURRENT STREAK", cur if gh else None, "days"),
        ("LONGEST STREAK", longest if gh else None, "days"),
        ("BEST MONTH", sums[best] if gh and best else None, dt.date(best[0], best[1], 1).strftime("%B") if best else ""),
    ]
    for i, (label, val, unit) in enumerate(stats):
        y = 66 + i * 76
        b.append(text(sx, y, label, "mono", 10, MUTED, spacing=1.8))
        if val is None:
            b.append(text(sx, y + 40, "—", "serif", 38, INK))
        else:
            b.append(countup(val, sx, y + 40, lambda v: f"{v:,}", "serif", 38, INK, 1.0 + i * .2))
            b.append(f'<g {anim("fade", .6, 2.2 + i*.15)}>'
                     + text(sx + width(f"{val:,}", "serif", 38) + 8, y + 40, "day" if unit == "days" and val == 1 else unit, "serif-italic", 20, MUTED) + "</g>")
    if not gh:
        b.append(text(x0, 186, "Fills in with live GitHub data on the first Action run.", "sans", 13, MUTED))
    return svg(W, H, "".join(b), ["serif", "serif-italic", "sans", "mono"], title="Contribution activity over the last 12 months")


def graph(gh):
    W, H = 900, 262
    weeks = gh["weeks"][-53:] if gh else [[] for _ in range(53)]
    allc = [d["c"] for wk in weeks for d in wk]
    mx = max(allc) if allc else 0
    x0, y0, cell, step = 40, 112, 12, 15.5

    def lv(c):
        if c <= 0 or not mx:
            return 0
        r = c / mx
        return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4

    css = "".join(f".w{i}{{animation:pop .45s cubic-bezier(.2,.8,.2,1) {.6 + i*.03:.2f}s both;transform-origin:50% 50%}}" for i in range(53))
    b = [frame(W, H, 16)]
    b.append(text(40, 52, "IN THE LAST YEAR", "mono", 10.5, MUTED, spacing=2))
    if gh:
        b.append(countup(gh["total"], 40, 92, lambda v: f"{v:,} contributions", "serif", 40, INK, .3))
    else:
        b.append(text(40, 92, "Contributions", "serif", 40, INK, spacing=-.5))
    prev = None
    for wi, wk in enumerate(weeks):
        if wk:
            mo = dt.date.fromisoformat(wk[0]["d"]).month
            if mo != prev and wi < 51 and wi > 0 or (wi == 0 and wk):
                b.append(text(x0 + wi * step, y0 - 10, dt.date(2000, mo, 1).strftime("%b").upper(), "mono", 9, MUTED, spacing=1))
            prev = mo
        cells = {d["w"]: d for d in wk}
        for r in range(7):
            d = cells.get(r)
            if wk and d is None:
                continue
            b.append(f'<rect class="fb w{wi}" x="{x0 + wi*step:.1f}" y="{y0 + r*step:.1f}" width="{cell}" height="{cell}" rx="2.5" '
                     f'fill="{LEVELS[lv(d["c"]) if d else 0]}"/>')
    ly = y0 + 7 * step + 22
    lx = W - 40 - (5 * step + 66)
    b.append(text(lx, ly + 10, "LESS", "mono", 9, MUTED, spacing=1))
    for i, c in enumerate(LEVELS):
        b.append(f'<rect x="{lx + 34 + i*step:.1f}" y="{ly}" width="{cell}" height="{cell}" rx="2.5" fill="{c}"/>')
    b.append(text(lx + 34 + 5 * step + 4, ly + 10, "MORE", "mono", 9, MUTED, spacing=1))
    return svg(W, H, "".join(b), ["serif", "mono"], extra_css=css, title="GitHub contribution graph for the last year")


# ------------------------------------------------------------------ repos
def repo(r, idx):
    W, H = 444, 178
    color = ACCENT[r.get("accent", "blue")]
    b = [frame(W, H, 16)]
    b.append(text(26, 40, "REPOSITORY", "mono", 10, MUTED, spacing=1.8))
    b.append(f'<circle cx="{W - 26 - width(r["language"], "mono", 10.5, 1) - 12}" cy="36.5" r="4" fill="{color}"/>')
    b.append(text(W - 26, 40, r["language"], "mono", 10.5, INK2, "end", 1))
    ns = 34
    while width(r["name"], "serif", ns) > W - 90 and ns > 24:
        ns -= 1
    b.append(text(25, 82, r["name"], "serif", ns, INK, spacing=-.4))
    nx = 25 + width(r["name"], "serif", ns) - .4 * len(r["name"]) + 10
    b.append(f'<g class="fb" {anim("nudge", 3.2, 1.5 + idx*.5, "ease-in-out", True)}>' + text(nx, 78, "↗", "sans", 17, MUTED) + "</g>")
    for i, line in enumerate(wrap(r["description"], "sans", 13, W - 52)[:2]):
        b.append(text(26, 110 + i * 20, line, "sans", 13, INK2))
    b.append(text(26, H - 24, "  ·  ".join(r["tags"]).upper(), "mono", 9.5, MUTED, spacing=1.4))
    body = f'<g class="fb" {anim("rise", .8, .2 + idx*.15)}>{"".join(b)}</g>'
    return svg(W, H, body, ["serif", "sans", "mono"], title=f'{r["name"]}: {r["description"]}')


def main():
    cfg = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))
    gh = load_github()
    OUT.mkdir(exist_ok=True)
    files = {"hero.svg": hero(cfg), "activity.svg": activity(gh), "graph.svg": graph(gh)}
    for i, t in enumerate(cfg["tiles"]):
        files[f'tile-{t["slug"]}.svg'] = tile(t, i, gh)
    for i, r in enumerate(cfg["repos"]):
        files[f'repo-{r["slug"]}.svg'] = repo(r, i)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
    print(f"wrote {len(files)} cards (static={STATIC}, github data={'yes' if gh else 'not yet'})")


if __name__ == "__main__":
    main()
