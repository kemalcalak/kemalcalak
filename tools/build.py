"""Builds the README's SVG cards in kemalcalak.com's direction B identity.

Every card is written twice: a Day stock for GitHub's light theme and a
Night stock for its dark theme; the README picks one with <picture>. The
colours and type follow the site's BRAND.md: IBM Plex Sans for sentences,
IBM Plex Mono for what a machine says, one cobalt accent, nothing moves.
Fonts are subset to the glyphs each card uses and embedded as base64 WOFF2,
because an SVG loaded through <img> cannot fetch anything.

    python3 tools/build.py
"""

import base64
import functools
import io
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

STOCKS = {
    "day": {
        "page": "#F6F7F9", "raised": "#FFFFFF", "line": "#DFE3E9", "ink": "#11151B",
        "soft": "#434A55", "muted": "#5B636F", "accent": "#2049C9", "chip": "#E7EDFC",
    },
    "night": {
        "page": "#0E1116", "raised": "#161A21", "line": "#252B34", "ink": "#E9ECF1",
        "soft": "#AAB1BC", "muted": "#8D95A1", "accent": "#86B0FF", "chip": "#18233A",
    },
}

# family name -> file
FACES = {
    "Plex Sans": "IBMPlexSans-Regular.ttf",
    "Plex Sans Semi": "IBMPlexSans-SemiBold.ttf",
    "Plex Mono": "IBMPlexMono-Regular.ttf",
    "Plex Mono Medium": "IBMPlexMono-Medium.ttf",
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@functools.cache
def metrics_font(family):
    return TTFont(FONTS / FACES[family])


def text_width(family, s, size):
    font = metrics_font(family)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    units = sum(hmtx[cmap[ord(ch)]][0] for ch in s)
    return units * size / font["head"].unitsPerEm


def wrap(family, s, size, width):
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if line and text_width(family, trial, size) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def font_face(family, text):
    font = TTFont(FONTS / FACES[family])
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = []
    sub = subset.Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{data}) format('woff2')}}"


class Card:
    """Collects text per family so each card embeds only the glyphs it draws."""

    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.used = {}
        self.body = []

    def text(self, family, s, x, y, size, fill, anchor="start"):
        self.used[family] = self.used.get(family, "") + s
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.body.append(
            f'<text x="{x:g}" y="{y:g}" font-family="\'{family}\'" font-size="{size}" fill="{fill}"{a}>{esc(s)}</text>'
        )

    def spans(self, family, parts, x, y, size):
        """One line in several colours: parts is [(text, fill), ...]."""
        self.used[family] = self.used.get(family, "") + "".join(t for t, _ in parts)
        inner = "".join(f'<tspan fill="{f}">{esc(t)}</tspan>' for t, f in parts)
        self.body.append(
            f'<text x="{x:g}" y="{y:g}" font-family="\'{family}\'" font-size="{size}" xml:space="preserve">{inner}</text>'
        )

    def add(self, raw):
        self.body.append(raw)

    def render(self):
        faces = "".join(font_face(f, t) for f, t in self.used.items())
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img" aria-label="{esc(self.title)}">'
            f"<title>{esc(self.title)}</title>"
            f"<style>{faces}</style>"
            + "".join(self.body)
            + "</svg>"
        )


def box(s, w, h, fill, radius):
    return (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{radius}" '
            f'fill="{fill}" stroke="{s["line"]}"/>')


def chips(c, s, items, x, y, size=12):
    """Stack chips: fully round, accent text on the chip colour."""
    for item in items:
        w = text_width("Plex Mono", item, size) + 20
        c.add(f'<rect x="{x:g}" y="{y:g}" width="{w:.1f}" height="24" rx="12" fill="{s["chip"]}"/>')
        c.text("Plex Mono", item, x + 10, y + 16, size, s["accent"])
        x += w + 8
    return x


def mark(c, s, x, y, scale=1.0):
    """The akç monogram: Plex Mono 500 in a 1.5px outlined rounded rectangle."""
    w, h = 64 * scale, 40 * scale
    c.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{8 * scale:g}" '
          f'fill="none" stroke="{s["ink"]}" stroke-width="1.5"/>')
    c.spans("Plex Mono Medium", [("ak", s["ink"]), ("ç", s["accent"])], x + 13 * scale, y + 26.5 * scale, 20 * scale)


INTRO = "I build agent systems and the web apps that use them."
NOW = ("now", "Full-stack AI Engineer at SeriAI")


def hero(stock):
    s = STOCKS[stock]
    W, H = 900, 260
    c = Card(W, H, f"Ali Kemal Çalak, Full-stack Agentic AI Engineer. {INTRO}")
    c.add(box(s, W, H, s["page"], 10))
    mark(c, s, 48, 44)
    c.text("Plex Sans Semi", "Ali Kemal Çalak", 46, 152, 48, s["ink"])
    c.text("Plex Sans", "Full-stack Agentic AI Engineer", 48, 188, 20, s["soft"])
    c.text("Plex Sans", INTRO, 48, 220, 16, s["muted"])
    label, role = NOW
    c.spans("Plex Mono", [(f"{label}  ", s["muted"]), (role, s["ink"])], W - 48 - text_width("Plex Mono", f"{label}  {role}", 13), 70, 13)
    c.add(f'<circle cx="{W - 48 - text_width("Plex Mono", f"{label}  {role}", 13) - 12:.1f}" cy="65.5" r="3.5" fill="{s["accent"]}"/>')
    return c


def link(stock, label):
    s = STOCKS[stock]
    W, H = 132, 36
    c = Card(W, H, label)
    c.add(box(s, W, H, s["raised"], 6))
    c.text("Plex Mono", label, 14, 23, 13, s["ink"])
    c.text("Plex Mono", "↗", W - 14, 23, 13, s["accent"], anchor="end")
    return c


def project(stock, meta, title, tagline, stack):
    s = STOCKS[stock]
    W, H = 440, 236
    c = Card(W, H, f"{title}: {tagline}")
    c.add(box(s, W, H, s["raised"], 10))
    c.text("Plex Mono", meta, 28, 42, 12, s["muted"])
    c.text("Plex Mono", "↗", W - 28, 42, 14, s["accent"], anchor="end")
    c.text("Plex Sans Semi", title, 27, 84, 26, s["ink"])
    lines = wrap("Plex Sans", tagline, 16, W - 56)
    assert len(lines) <= 3, f"tagline too long: {title}"
    for i, ln in enumerate(lines):
        c.text("Plex Sans", ln, 28, 116 + i * 25, 16, s["soft"])
    end = chips(c, s, stack, 28, H - 52)
    assert end < W - 20, f"stack too wide: {title}"
    return c


TOOLS = [
    ("AI and agents", ["Multi-agent systems", "MCP", "RAG", "Agno", "n8n", "Claude Code"]),
    ("Languages", ["Python", "TypeScript", "JavaScript"]),
    ("Frontend", ["React", "Next.js"]),
    ("Backend and data", ["FastAPI", "PostgreSQL", "MongoDB", "Redis"]),
]


def tools(stock):
    s = STOCKS[stock]
    W = 900
    H = 56 + len(TOOLS) * 44 + 20
    c = Card(W, H, "Tools I use. " + " ".join(f"{g}: {', '.join(i)}." for g, i in TOOLS))
    c.add(box(s, W, H, s["page"], 10))
    c.text("Plex Mono Medium", "Tools I use", 32, 44, 13, s["muted"])
    for i, (group, items) in enumerate(TOOLS):
        y = 66 + i * 44
        c.text("Plex Sans", group, 32, y + 17, 15, s["soft"])
        end = chips(c, s, items, 220, y)
        assert end < W - 20, f"tool row too wide: {group}"
    return c


PROJECTS = {
    "ivralo": ("2026 · AI", "ivralo",
               "Reads the alert and the logs when production breaks and shows the cause with proof. Runs on the company's own servers.",
               ["Python", "Agno", "PostgreSQL", "MCP"]),
    "design-editor": ("2026 · AI", "Design Editor",
                      "A vector editor on your own machine, where you design together with AI agents over MCP.",
                      ["Rust", "Skia", "MCP"]),
    "sponsorhub": ("2026 · Full-stack", "SponsorHub",
                   "A platform that brings competition teams, student clubs and sponsors together.",
                   ["Next.js", "FastAPI", "PostgreSQL", "Redis"]),
    "saas-starter": ("2026 · Full-stack", "SaaS Starter",
                     "The auth, i18n and testing setup every SaaS ends up rewriting, done once and done properly.",
                     ["Next.js", "FastAPI", "PostgreSQL", "Redis"]),
}

LINKS = ["Website", "LinkedIn", "Medium", "X", "Email"]


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for stock in STOCKS:
        cards = {"hero": hero(stock), "tools": tools(stock)}
        for slug, args in PROJECTS.items():
            cards[f"project-{slug}"] = project(stock, *args)
        for label in LINKS:
            cards[f"link-{label.lower()}"] = link(stock, label)
        for name, card in cards.items():
            (OUT / f"{name}-{stock}.svg").write_text(card.render(), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.glob("*.svg"))
    print(f"wrote {len(list(OUT.glob('*.svg')))} files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
