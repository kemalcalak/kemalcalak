"""Builds the README's SVG cards in the kemalcalak.com "Ember Cut" language.

Every card is written twice: a Paper stock for GitHub's light theme and a
Darkroom stock for its dark theme; the README picks one with <picture>.
Fonts are subset to the glyphs each card uses and embedded as base64 WOFF2,
because an SVG loaded through <img> cannot fetch anything.

    python3 tools/build.py
"""

import base64
import functools
import io
import math
import random
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

STOCKS = {
    "paper": {
        "bg": "#f0eae0", "gaffer": "#e6decd", "hairline": "#d5ccb9",
        "ink": "#241c12", "soft": "#3a332a", "ember": "#c93a10",
    },
    "darkroom": {
        "bg": "#0b0a09", "gaffer": "#161311", "hairline": "#292420",
        "ink": "#eae3d6", "soft": "#b4aca4", "ember": "#ff4a1c",
    },
}

# family name -> (file, pinned variation axes)
FACES = {
    "Fraunces Display": ("Fraunces-latin.woff2", {"opsz": 144, "wght": 380}),
    "Fraunces Text": ("Fraunces-latin.woff2", {"opsz": 28, "wght": 400}),
    "Switzer": ("Switzer-Variable.woff2", {"wght": 420}),
    "Fragment Mono": ("FragmentMono-latin.woff2", None),
}

EXPO = "cubic-bezier(0.16, 1, 0.3, 1)"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load(family):
    file, axes = FACES[family]
    font = TTFont(FONTS / file)
    if axes:
        font = instancer.instantiateVariableFont(font, axes)
    return font


@functools.cache
def metrics_font(family):
    return load(family)


def text_width(family, s, size):
    font = metrics_font(family)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    units = sum(hmtx[cmap[ord(ch)]][0] for ch in s)
    return units * size / font["head"].unitsPerEm


def font_face(family, text):
    font = load(family)
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
        self.css = []

    def text(self, family, s, x, y, size, fill, cls="", anchor="start", extra=""):
        self.used[family] = self.used.get(family, "") + s
        c = f' class="{cls}"' if cls else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.body.append(
            f'<text{c} x="{x}" y="{y}" font-family="\'{family}\'" font-size="{size}" fill="{fill}"{a}{extra}>{esc(s)}</text>'
        )

    def typed(self, family, s, x, y, size, fill, start, step):
        """Monospace line that types itself one glyph at a time."""
        self.used[family] = self.used.get(family, "") + s
        spans = []
        for i, ch in enumerate(s):
            if ch == " ":
                spans.append(" ")
                continue
            spans.append(f'<tspan class="k" style="animation-delay:{start + i * step:.2f}s">{esc(ch)}</tspan>')
        self.body.append(
            f'<text x="{x}" y="{y}" font-family="\'{family}\'" font-size="{size}" fill="{fill}" xml:space="preserve">{"".join(spans)}</text>'
        )

    def add(self, raw):
        self.body.append(raw)

    def render(self, bg):
        faces = "".join(font_face(f, t) for f, t in self.used.items())
        base = (
            ".k{animation:k .01s linear backwards}"
            "@keyframes k{from,to{opacity:0}}"
            f".in{{animation:in .9s {EXPO} backwards}}"
            "@keyframes in{from{opacity:0;transform:translateY(14px)}}"
            ".fade{animation:fade .8s ease-out backwards}"
            "@keyframes fade{from{opacity:0}}"
            ".caret{animation:blink 1.1s steps(1) infinite}"
            "@keyframes blink{50%{opacity:0}}"
        )
        reduced = (
            "@media (prefers-reduced-motion:reduce){"
            ".k,.in,.fade,.draw{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}"
            ".caret{animation:none}.loop{display:none}}"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img" aria-label="{esc(self.title)}">'
            f"<title>{esc(self.title)}</title>"
            f"<style>{faces}{base}{''.join(self.css)}{reduced}</style>"
            f'<rect width="{self.w}" height="{self.h}" fill="{bg}"/>'
            + "".join(self.body)
            + "</svg>"
        )


def splatter(w, h, ink, ember, seed, avoid):
    """Ink-and-ember dust like the site's hero: dense at the left, thinning out."""
    rnd = random.Random(seed)
    dots = {ink: [], ember: []}
    ax0, ay0, ax1, ay1 = avoid
    for _ in range(9000):
        x = rnd.random() * w
        y = rnd.random() * h
        # density falls off left to right, and is thin inside the text block
        keep = 0.55 * math.exp(-x / (w * 0.3)) + 0.035
        if ax0 < x < ax1 and ay0 < y < ay1:
            keep *= 0.12
        if rnd.random() > keep:
            continue
        r = rnd.choice([0.5, 0.6, 0.7, 0.8, 0.9, 1.1, 1.3, 1.6, 2.1]) * (0.8 + rnd.random() * 0.4)
        o = 0.2 + rnd.random() * 0.6
        tone = ember if rnd.random() < 0.26 else ink
        dots[tone].append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" opacity="{o:.1f}"/>')
    return "".join(f'<g fill="{tone}">{"".join(d)}</g>' for tone, d in dots.items())


def hero(stock):
    s = STOCKS[stock]
    W, H = 900, 420
    c = Card(W, H, "Ali Kemal Çalak, Agentic AI Engineer")
    c.add(splatter(W, H, s["ink"], s["ember"], 7, (40, 78, 600, 372)))

    c.typed("Fragment Mono", "> run: introduce(ali_kemal_calak)", 58, 104, 17, s["ember"], 0.2, 0.035)
    c.text("Fraunces Display", "Ali Kemal", 52, 200, 100, s["ink"], "in", extra=' style="animation-delay:1.3s"')
    c.text("Fraunces Display", "Çalak", 52, 294, 100, s["ink"], "in", extra=' style="animation-delay:1.45s"')
    c.text("Fragment Mono", "Agentic AI Engineer · Agents, LLM Systems & Fullstack", 58, 352, 17, s["soft"], "fade",
           extra=' style="animation-delay:2s"')

    # the agent loop: plan -> build -> verify -> plan, with an ember pulse running it
    nodes = {"plan": (690, 112), "build": (826, 214), "verify": (668, 300)}
    order = ["plan", "build", "verify"]
    path = "M{} {} L{} {} L{} {} Z".format(*nodes["plan"], *nodes["build"], *nodes["verify"])
    perim = sum(math.dist(nodes[order[i]], nodes[order[(i + 1) % 3]]) for i in range(3))
    c.css.append(
        f".draw{{stroke-dasharray:{perim:.0f};animation:draw 1.6s {EXPO} 2.3s backwards}}"
        f"@keyframes draw{{from{{stroke-dashoffset:{perim:.0f}}}}}"
    )
    c.add(f'<path class="draw" d="{path}" fill="none" stroke="{s["soft"]}" stroke-opacity=".55" stroke-width="1"/>')
    for i, name in enumerate(order):
        x, y = nodes[name]
        w = 22 + len(name) * 9.6
        d = 2.2 + i * 0.25
        c.add(f'<g class="fade" style="animation-delay:{d:.2f}s">'
              f'<rect x="{x - w / 2:.1f}" y="{y - 14}" width="{w:.1f}" height="28" fill="{s["bg"]}" stroke="{s["soft"]}" stroke-opacity=".6"/>'
              f'<circle cx="{x - w / 2 + 11:.1f}" cy="{y}" r="2.6" fill="{s["ember"]}"/>')
        c.text("Fragment Mono", name, round(x - w / 2 + 20, 1), y + 5, 14, s["ink"])
        c.add("</g>")
    c.add(f'<circle class="loop" r="4" fill="{s["ember"]}" opacity="0">'
          f'<animateMotion dur="5.4s" begin="3.9s" repeatCount="indefinite" path="{path}"/>'
          f'<set attributeName="opacity" to="1" begin="3.9s"/></circle>')

    c.typed("Fragment Mono", "→ delegate: plan · build · verify · ok", 560, 388, 13, s["soft"], 3.9, 0.03)
    return c


def link(stock, label):
    s = STOCKS[stock]
    c = Card(150, 40, label)
    c.add(f'<rect x=".5" y=".5" width="149" height="39" fill="none" stroke="{s["hairline"]}"/>')
    c.text("Fragment Mono", label, 16, 25, 15, s["ink"])
    c.text("Fragment Mono", "↗", 134, 25, 15, s["ember"], anchor="end")
    return c


def film(stock, kind, title, lines, stack):
    s = STOCKS[stock]
    W, H = 440, 270
    c = Card(W, H, f"{title}: {' '.join(lines)}")
    # viewfinder corners instead of a boxed card
    L, m = 18, 10
    corners = [
        f"M{m} {m + L}V{m}H{m + L}", f"M{W - m - L} {m}H{W - m}V{m + L}",
        f"M{m} {H - m - L}V{H - m}H{m + L}", f"M{W - m - L} {H - m}H{W - m}V{H - m - L}",
    ]
    c.add(f'<path d="{" ".join(corners)}" fill="none" stroke="{s["soft"]}" stroke-opacity=".7"/>')
    c.text("Fragment Mono", kind, 34, 50, 14, s["ember"])
    c.text("Fragment Mono", "↗", W - 34, 50, 16, s["ink"], anchor="end")
    c.text("Fraunces Display", title, 32, 112, 46, s["ink"])
    for i, ln in enumerate(lines):
        assert text_width("Switzer", ln, 20) < W - 68, f"tagline too wide: {ln}"
        c.text("Switzer", ln, 34, 152 + i * 28, 20, s["soft"])
    c.text("Fragment Mono", stack, 34, 240, 14, s["soft"])
    return c


CREDITS = [
    ("Languages", "Python, TypeScript, JavaScript"),
    ("Agentic AI", "Agno, MCP, multi-agent systems"),
    ("Backend", "FastAPI, Node.js"),
    ("Frontend & mobile", "React, Next.js, React Native"),
    ("Data", "PostgreSQL, MongoDB, Redis"),
]


def credits(stock):
    s = STOCKS[stock]
    W, H = 900, 330
    c = Card(W, H, "Credits: " + "; ".join(f"{a}: {b}" for a, b in CREDITS))
    c.text("Fraunces Display", "Credits", W / 2, 78, 44, s["ink"], anchor="middle")
    gutter = W / 2
    for i, (role, names) in enumerate(CREDITS):
        y = 140 + i * 40
        c.text("Switzer", role, gutter - 20, y, 18, s["soft"], anchor="end")
        c.text("Fraunces Text", names, gutter + 20, y, 25, s["ink"])
    return c


def closing(stock):
    s = STOCKS[stock]
    W, H = 900, 250
    c = Card(W, H, "Let's build systems that act.")
    c.add(f'<line x1="52" y1="34" x2="{W - 52}" y2="34" stroke="{s["hairline"]}"/>')
    c.text("Fraunces Display", "Let’s build", 52, 112, 62, s["ink"])
    c.text("Fraunces Display", "systems that act.", 52, 180, 62, s["ink"])
    caret_x = 52 + text_width("Fraunces Display", "systems that act.", 62) + 10
    c.add(f'<rect class="caret" x="{caret_x:.0f}" y="138" width="14" height="42" fill="{s["ember"]}"/>')
    c.text("Fragment Mono", "Shot on code · no cameras were used", W - 52, 224, 13, s["soft"], anchor="end")
    c.text("Fragment Mono", "© 2026 Ali Kemal Çalak", 52, 224, 13, s["soft"])
    return c


FILMS = {
    "design-editor": ("Design tool", "Design Editor", ["AI agents design on a live canvas", "over MCP. Local-first, in Rust."],
                      "Rust · Skia · MCP"),
    "warroom": ("Agentic AI", "Warroom", ["One URL in. Out: an evidence-linked", "report and your rival’s next move."],
                "FastAPI · TypeScript · Docker"),
    "nextjs-template": ("Fullstack", "Next.js Starter", ["The boring 20% of every SaaS", "frontend, solved once and properly."],
                        "Next.js 16 · React 19 · TypeScript"),
    "fastapi-template": ("Fullstack", "FastAPI Starter", ["Layered async backend with auth,", "RBAC, jobs and tracing built in."],
                         "FastAPI · PostgreSQL · Redis"),
}

LINKS = ["Website", "LinkedIn", "Medium", "Email"]


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for stock in STOCKS:
        bg = STOCKS[stock]["bg"]
        cards = {"hero": hero(stock), "credits": credits(stock), "closing": closing(stock)}
        for slug, args in FILMS.items():
            cards[f"film-{slug}"] = film(stock, *args)
        for label in LINKS:
            cards[f"link-{label.lower()}"] = link(stock, label)
        for name, card in cards.items():
            (OUT / f"{name}-{stock}.svg").write_text(card.render(bg), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.glob("*.svg"))
    print(f"wrote {len(list(OUT.glob('*.svg')))} files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
