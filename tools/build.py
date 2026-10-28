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


# The site's AKÇ mark, copied from components/site/Mark.tsx: IBM Plex Sans 700 outlined
# on a 32 unit grid, so it is drawn exactly as on kemalcalak.com.
MARK_PATH = "M13.21 19.05H11.69L11.21 17.46H8.97L8.49 19.05H7.01L9.22 12.35H11.03ZM10.85 16.22 10.44 14.83 10.11 13.68H10.06L9.73 14.83L9.32 16.22Z M17.67 19.05 15.89 16.13 15.02 17.19V19.05H13.56V12.35H15.02V15.54H15.08L16.03 14.24L17.54 12.35H19.19L16.93 15.11L19.39 19.05Z M22.37 13.53Q21.73 13.53 21.34 13.95Q20.95 14.37 20.95 15.16V16.24Q20.95 17.03 21.34 17.45Q21.73 17.87 22.37 17.87Q22.91 17.87 23.23 17.58Q23.56 17.29 23.71 16.87L24.9 17.56Q24.52 18.32 23.92 18.74Q23.31 19.17 22.42 19.17L22.34 19.58L22.37 19.62Q22.49 19.59 22.6 19.57Q22.72 19.55 22.84 19.55Q23.12 19.55 23.33 19.7Q23.54 19.86 23.54 20.21Q23.54 20.54 23.35 20.73Q23.17 20.92 22.88 21.01Q22.6 21.09 22.27 21.09Q21.77 21.09 21.49 20.95Q21.2 20.81 21.08 20.66L21.52 20.13Q21.62 20.24 21.77 20.32Q21.93 20.41 22.15 20.41Q22.34 20.41 22.46 20.35Q22.58 20.29 22.58 20.17Q22.58 20.06 22.44 19.94Q22.31 19.82 21.86 19.78L21.65 19.76L21.79 19.12Q21.06 19 20.52 18.59Q19.98 18.18 19.7 17.47Q19.41 16.76 19.41 15.75Q19.41 14.62 19.77 13.83Q20.14 13.05 20.8 12.64Q21.47 12.24 22.37 12.24Q23.3 12.24 23.91 12.62Q24.52 13 24.88 13.81L23.62 14.46Q23.5 14.04 23.2 13.79Q22.91 13.53 22.37 13.53Z"


def mark(c, s, x, y, size=48):
    """The AKÇ mark: frame and letters in ink, the line under them in the accent."""
    k = size / 32
    c.add(f'<g transform="translate({x:g} {y:g}) scale({k:g})">'
          f'<rect x="0.5" y="0.5" width="31" height="31" rx="6.54" fill="none" stroke="{s["ink"]}" stroke-width="1"/>'
          f'<path fill="{s["ink"]}" d="{MARK_PATH}"/>'
          f'<rect x="6.82" y="20.35" width="13.25" height="1" rx="0.5" fill="{s["accent"]}"/></g>')


INTRO = "I build agent systems and the web apps that use them."
NOW = ("now", "Full-stack AI Engineer at SeriAI")


def hero(stock):
    s = STOCKS[stock]
    W, H = 900, 260
    c = Card(W, H, f"Ali Kemal Çalak, Full-stack Agentic AI Engineer. {INTRO}")
    c.add(box(s, W, H, s["page"], 10))
    mark(c, s, 48, 40, 56)
    c.text("Plex Sans Semi", "Ali Kemal Çalak", 46, 152, 48, s["ink"])
    c.text("Plex Sans", "Full-stack Agentic AI Engineer", 48, 188, 20, s["soft"])
    c.text("Plex Sans", INTRO, 48, 220, 16, s["muted"])
    label, role = NOW
    c.spans("Plex Mono", [(f"{label}  ", s["muted"]), (role, s["ink"])], W - 48 - text_width("Plex Mono", f"{label}  {role}", 13), 70, 13)
    c.add(f'<circle cx="{W - 48 - text_width("Plex Mono", f"{label}  {role}", 13) - 12:.1f}" cy="65.5" r="3.5" fill="{s["accent"]}"/>')
    return c


def link(stock, label):
    s = STOCKS[stock]
    W, H = max(132, round(text_width("Plex Mono", label, 13) + 56)), 36
    c = Card(W, H, label)
    c.add(box(s, W, H, s["raised"], 6))
    c.text("Plex Mono", label, 14, 23, 13, s["ink"])
    c.text("Plex Mono", "↗", W - 14, 23, 13, s["accent"], anchor="end")
    return c


ABOUT = ("I work at SeriAI as a Full-stack AI Engineer. I build every layer of a product, from the interface "
         "down to the database, and the agent systems that run on top of it: several agents working together, "
         "MCP integrations and workflow automation. I graduated in software engineering from KTÜ in 2026.")


def about(stock):
    s = STOCKS[stock]
    W = 900
    lines = wrap("Plex Sans", ABOUT, 17, W - 64)
    H = 70 + len(lines) * 28 + 14
    c = Card(W, H, ABOUT)
    c.add(box(s, W, H, s["page"], 10))
    c.text("Plex Mono Medium", "About", 32, 44, 13, s["muted"])
    for i, ln in enumerate(lines):
        c.text("Plex Sans", ln, 32, 80 + i * 28, 17, s["soft"])
    return c


def section(stock, name):
    """A section label as the site draws it: mono, muted, then a hairline."""
    s = STOCKS[stock]
    W, H = 900, 44
    c = Card(W, H, name)
    c.text("Plex Mono Medium", name, 2, 27, 13, s["muted"])
    x = text_width("Plex Mono Medium", name, 13) + 16
    c.add(f'<line x1="{x:.0f}" y1="22.5" x2="{W}" y2="22.5" stroke="{s["line"]}"/>')
    return c


CONTACT = ("Write to me about a project or a job.", "I usually reply within two days.", "kemalcalak@gmail.com")


def contact(stock):
    s = STOCKS[stock]
    W, H = 900, 150
    lead, note, email = CONTACT
    c = Card(W, H, f"{lead} {note} {email}")
    c.add(box(s, W, H, s["page"], 10))
    c.text("Plex Mono Medium", "Contact", 32, 44, 13, s["muted"])
    c.text("Plex Sans Semi", lead, 31, 84, 24, s["ink"])
    c.text("Plex Sans", note, 32, 116, 16, s["muted"])
    bw = text_width("Plex Mono", email, 14) + 60
    c.add(f'<rect x="{W - 32 - bw:.1f}" y="62" width="{bw:.1f}" height="40" rx="6" fill="{s["accent"]}"/>')
    c.text("Plex Mono", f"{email}  ↗", W - 32 - bw / 2, 87, 14, s["page"], anchor="middle")
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

LINKS = ["Website", "LinkedIn", "Medium", "X", "Email", "All projects", "Latest writing"]
LABELS = ["Projects"]


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for stock in STOCKS:
        cards = {"hero": hero(stock), "tools": tools(stock), "about": about(stock), "contact": contact(stock)}
        for name in LABELS:
            cards[f"label-{name.lower()}"] = section(stock, name)
        for slug, args in PROJECTS.items():
            cards[f"project-{slug}"] = project(stock, *args)
        for label in LINKS:
            cards[f"link-{label.lower().replace(' ', '-')}"] = link(stock, label)
        for name, card in cards.items():
            (OUT / f"{name}-{stock}.svg").write_text(card.render(), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.glob("*.svg"))
    print(f"wrote {len(list(OUT.glob('*.svg')))} files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
