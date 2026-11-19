#!/usr/bin/env python3
"""One-time: subset the fonts and save them as WOFF plus a metrics file.

    pip install fonttools
    python scripts/build_fonts.py /path/to/ttf/folder

Needs InstrumentSerif-Regular.ttf, InstrumentSerif-Italic.ttf, Geist.ttf
(variable) and GeistMono.ttf (variable) from Google Fonts. Writes fonts/*.woff
and fonts/metrics.json. The renderer reads only those, so the daily Action
needs nothing but the Python standard library.
"""
import io
import json
import pathlib
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
CHARS = "".join(chr(c) for c in range(0x20, 0x7F)) + "·—–’“”↗→●"

FACES = {
    "serif": ("InstrumentSerif-Regular.ttf", None),
    "serif-italic": ("InstrumentSerif-Italic.ttf", None),
    "sans": ("Geist.ttf", 400),
    "sans-medium": ("Geist.ttf", 500),
    "mono": ("GeistMono.ttf", 400),
}

metrics = {}
for key, (fname, wght) in FACES.items():
    font = TTFont(SRC / fname)
    if wght is not None:
        font = instantiateVariableFont(font, {"wght": wght})
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = ["*"]
    sub = subset.Subsetter(opts)
    sub.populate(text=CHARS)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff"
    font.save(buf)
    (ROOT / "fonts" / f"{key}.woff").write_bytes(buf.getvalue())

    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    widths = {ch: hmtx[cmap[ord(ch)]][0] / upm for ch in CHARS if ord(ch) in cmap}
    metrics[key] = {"widths": widths, "fallback": widths.get("n", 0.5)}
    print(f"{key:13s} {len(buf.getvalue())/1024:5.1f} KB")

(ROOT / "fonts" / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
