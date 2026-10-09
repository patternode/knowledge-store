"""Architecture briefing for the Knowledge Store.

Eight clips. The picture is a diagram of the flow, drawn in the Patternode brand
(Midnight Terminal, IBM Plex, the mark). Two voice scripts are written from the
same scenes: voice-pro.md for a professional narrator, voice-record.md to read
yourself. Each script is continuous prose for the clip.

  python docs/explainer/build.py --docs
  python docs/explainer/build.py --frames
  python docs/explainer/build.py
"""

from __future__ import annotations

import argparse
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "media"
FONT_DIR = ROOT / "assets" / "fonts"

W, H = 1920, 1080
FPS = 12
WPS = 2.2
HEAD = 0.8
TAIL = 2.4

# Midnight Terminal, dark. DEC-001 option B, from patternode-business
# marketing/brand/tokens.css (the copy the site ships). DEC-003 type is IBM Plex.
BG = (0x1B, 0x20, 0x2C)       # --pn-neutral-950, the brand ground
IVORY = (0xF5, 0xF7, 0xFB)    # --pn-neutral-50
MUTED = (0xB9, 0xC2, 0xD8)    # --pn-neutral-300
DIM = (0x9B, 0xA6, 0xC0)      # --pn-neutral-400
CYAN = (0x00, 0xB8, 0xE6)     # --pn-brand-cyan, the live line
AMBER = (0xE6, 0x9F, 0x00)    # --pn-cat-3
INDIGO = (0x90, 0x9C, 0xFF)   # --pn-secondary-400
ROSE = (0xFF, 0x6D, 0x98)     # --pn-tertiary-400, search hits
DANGER = (0xFF, 0x75, 0x69)   # --pn-danger-400
SURFACE = (0x2C, 0x33, 0x42)  # --pn-neutral-900
RAISED = (0x3E, 0x46, 0x5A)   # --pn-neutral-800
LINE = (0x52, 0x5C, 0x74)     # --pn-neutral-700
TILE = (0x0B, 0x14, 0x37)     # logo tile on the navy ground
INK = SURFACE
CARD = SURFACE

# Diagram roles, named for the scenes.
GOLD = AMBER    # ontology
TEAL = CYAN     # the graph, and a result a passage supports
BLUE = INDIGO   # documents, passages, vectors
CORAL = DANGER  # a result the sources do not support

SANS_WEIGHT = {"reg": b"Regular", "med": b"Medium", "sem": b"SemiBold"}
_fonts: dict = {}


def font(size: int, kind: str = "reg"):
    key = (kind, size)
    if key not in _fonts:
        if kind == "mono":
            face = ImageFont.truetype(FONT_DIR / "IBMPlexMono-Regular.ttf", size)
        else:
            face = ImageFont.truetype(FONT_DIR / "IBMPlexSans[wdth,wght].ttf", size)
            face.set_variation_by_name(SANS_WEIGHT[kind])
        _fonts[key] = face
    return _fonts[key]


def col(rgb, a=1.0):
    return (*rgb, int(max(0.0, min(1.0, a)) * 255))


def ease(t, a, b):
    if b <= a:
        return 1.0 if t >= a else 0.0
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    x = (t - a) / (b - a)
    return x * x * (3 - 2 * x)


def pulse(t, lo=0.55, hi=1.0, speed=0.45):
    s = 0.5 + 0.5 * math.sin(t * speed * math.pi * 2)
    return lo + (hi - lo) * s


def lerp(a, b, p):
    return a + (b - a) * p


def mixpt(a, b, p):
    return (lerp(a[0], b[0], p), lerp(a[1], b[1], p))


def tracked_width(text, fnt, tracking):
    if not text:
        return 0
    return sum(fnt.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(d, xy, text, fnt, fill, tracking=0):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + tracking
    return x


def wrap(text, fnt, width):
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else f"{cur} {word}"
        if fnt.getlength(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_wrapped(d, text, fnt, fill, x, y, width, gap=6):
    lines = wrap(text, fnt, width)
    step = fnt.size + gap
    for i, line in enumerate(lines):
        d.text((x, y + i * step), line, font=fnt, fill=fill)
    return len(lines) * step


def center_text(d, cx, cy, text, fnt, fill):
    box = fnt.getbbox(text)
    tw = box[2] - box[0]
    th = box[3] - box[1]
    d.text((cx - tw / 2, cy - th / 2 - box[1]), text, font=fnt, fill=fill)


def logo_mark(d, x, y, size=36):
    """The mark from logo-lockup.svg: tile, cyan signal, two white nodes."""
    s = size / 64.0
    d.rounded_rectangle((x, y, x + size, y + size), radius=max(2, round(12 * s)), fill=TILE)
    raw = [(8, 44), (20, 30), (30, 38), (44, 16), (56, 24)]
    pts = [(x + px * s, y + py * s) for px, py in raw]
    width = max(2, round(4 * s))
    d.line(pts, fill=CYAN, width=width)
    cap = width / 2
    for px, py in pts:
        d.ellipse((px - cap, py - cap, px + cap, py + cap), fill=CYAN)
    for cx, cy, r in ((20, 30, 3.5), (44, 16, 3.5)):
        rr = r * s
        d.ellipse((x + cx * s - rr, y + cy * s - rr, x + cx * s + rr, y + cy * s + rr), fill=(255, 255, 255, 255))


def chrome(d, kicker):
    logo_mark(d, 64, 26, 36)
    d.text((112, 32), "patternode", font=font(22, "sem"), fill=col(IVORY))
    d.text((244, 36), "Knowledge Store", font=font(16, "med"), fill=col(DIM))
    label = kicker.upper()
    f = font(14, "mono")
    tw = tracked_width(label, f, 1.2)
    draw_tracked(d, (W - 64 - tw, 36), label, f, col(CYAN), tracking=1.2)
    d.line((64, 74, W - 64, 74), fill=col(LINE), width=1)


def footer(d, index, n, global_t, local_t, duration):
    d.line((64, 1020, W - 64, 1020), fill=col(LINE), width=1)
    f = font(14, "mono")
    draw_tracked(d, (64, 1034), f"{index:02d}   /   {n:02d}", f, col(DIM), tracking=1.2)
    stamp = f"{int(global_t) // 60}:{int(global_t) % 60:02d}"
    sf = font(15, "mono")
    d.text((W - 64 - sf.getlength(stamp), 1032), stamp, font=sf, fill=col(DIM))
    if duration > 0:
        x1 = 64 + (W - 128) * max(0.0, min(1.0, local_t / duration))
        d.line((64, 1016, x1, 1016), fill=col(CYAN), width=3)


def heading(d, text, sub=None):
    draw_tracked(d, (64, 92), text, font(40, "sem"), col(IVORY), tracking=-0.8)
    if sub:
        d.text((64, 148), sub, font=font(22), fill=col(MUTED))


def node(d, cx, cy, w, h, title, ring, a=1.0, sub=None, fill=INK):
    if a <= 0.02:
        return
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    d.rounded_rectangle(box, radius=12, fill=col(fill, a), outline=col(ring, a), width=3)
    if sub:
        center_text(d, cx, cy - 14, title, font(22, "sem"), col(IVORY, a))
        center_text(d, cx, cy + 16, sub, font(16), col(MUTED, a))
    else:
        center_text(d, cx, cy, title, font(22, "sem"), col(IVORY, a))


def pill(d, cx, cy, text, ring, a=1.0, fill=INK):
    if a <= 0.02:
        return
    fnt = font(18, "sem")
    tw = fnt.getlength(text)
    w, h = tw + 40, 44
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=22, fill=col(fill, a), outline=col(ring, a), width=2)
    center_text(d, cx, cy, text, fnt, col(IVORY, a))


def page(d, x, y, w, h, title, accent, a=1.0, bars=4, title_size=16):
    if a <= 0.02:
        return
    d.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=col(INK, a), outline=col(accent, a), width=3)
    fold = 22
    d.polygon(
        [(x + w - fold, y + 2), (x + w - 2, y + fold), (x + w - fold, y + fold)],
        fill=col(accent, a * 0.45),
    )
    d.text((x + 16, y + 18), title, font=font(title_size, "sem"), fill=col(IVORY, a))
    top = y + max(58, 26 + title_size)
    for i in range(bars):
        yy = top + i * 18
        span = w - 36 - (10 if i == bars - 1 else 0)
        d.line((x + 16, yy, x + 16 + span * (0.72 if i == bars - 1 else 1), yy), fill=col(LINE, a), width=3)


def stage(d, cx, y, text, accent, a=1.0):
    if a <= 0.02:
        return
    fnt = font(14, "mono")
    tw = tracked_width(text, fnt, 1.2)
    draw_tracked(d, (cx - tw / 2, y), text, fnt, col(accent, a), tracking=1.2)


def arrow(d, start, end, fill, width=4, head=13, prog=1.0):
    if prog <= 0.03:
        return
    tip = mixpt(start, end, min(1.0, prog))
    d.line((*start, *tip), fill=fill, width=width)
    if prog < 0.96:
        return
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    p1 = (end[0] + head * math.cos(ang + 2.6), end[1] + head * math.sin(ang + 2.6))
    p2 = (end[0] + head * math.cos(ang - 2.6), end[1] + head * math.sin(ang - 2.6))
    d.polygon([end, p1, p2], fill=fill)


def dashed(d, start, end, fill, width=3, dash=14, gap=10):
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length < 1:
        return
    vx, vy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    dist = 0.0
    while dist < length:
        a = dist
        b = min(length, dist + dash)
        d.line((start[0] + vx * a, start[1] + vy * a, start[0] + vx * b, start[1] + vy * b), fill=fill, width=width)
        dist += dash + gap


def poly_arrow(d, pts, fill, width=4, head=13, prog=1.0):
    if prog <= 0.03 or len(pts) < 2:
        return
    segs = []
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append(seg)
        total += seg
    if total <= 0:
        return
    budget = total * min(1.0, prog)
    walked = 0.0
    for (a, b), seg in zip(zip(pts, pts[1:]), segs):
        if seg <= 0:
            continue
        if walked + seg < budget - 0.5:
            d.line((*a, *b), fill=fill, width=width)
            walked += seg
            continue
        tip = mixpt(a, b, max(0.0, min(1.0, (budget - walked) / seg)))
        d.line((*a, *tip), fill=fill, width=width)
        return
    end = pts[-1]
    prev = pts[-2]
    ang = math.atan2(end[1] - prev[1], end[0] - prev[0])
    p1 = (end[0] + head * math.cos(ang + 2.6), end[1] + head * math.sin(ang + 2.6))
    p2 = (end[0] + head * math.cos(ang - 2.6), end[1] + head * math.sin(ang - 2.6))
    d.polygon([end, p1, p2], fill=fill)


def bead(d, start, end, p, color, r=7):
    x, y = mixpt(start, end, p % 1.0)
    d.ellipse((x - r, y - r, x + r, y + r), fill=col(color))


def dots(d, cx, cy, rx, ry, n, a, hot, ring=BLUE, hot_color=CYAN):
    if a <= 0.02:
        return
    for i in range(n):
        ang = i * 2.399963
        rad = math.sqrt((i + 0.5) / n)
        x = cx + math.cos(ang) * rx * rad
        y = cy + math.sin(ang) * ry * rad
        on = i in hot
        r = 7 if on else 4
        shade = hot_color if on else ring
        d.ellipse((x - r, y - r, x + r, y + r), fill=col(shade, a if on else a * 0.8))


def schema(d, origin, a=1.0, scale=1.0):
    """Three-type ontology: Person, Story, Place."""
    if a <= 0.02:
        return
    ox, oy = origin
    person = (ox, oy)
    story = (ox - 170 * scale, oy + 168 * scale)
    place = (ox + 170 * scale, oy + 168 * scale)
    nw, nh = 168 * scale, 64 * scale
    arrow(d, (person[0] - 20, person[1] + nh / 2), (story[0] + 30, story[1] - nh / 2), col(GOLD, a), width=3, prog=a)
    arrow(d, (person[0] + 20, person[1] + nh / 2), (place[0] - 30, place[1] - nh / 2), col(GOLD, a), width=3, prog=a)
    node(d, *person, nw, nh, "Person", GOLD, a)
    node(d, *story, nw, nh, "Story", GOLD, a)
    node(d, *place, nw, nh, "Place", GOLD, a)
    if a > 0.7:
        center_text(d, (person[0] + story[0]) / 2 - 28, (person[1] + story[1]) / 2, "appears in", font(15, "med"), col(GOLD, a))
        center_text(d, (person[0] + place[0]) / 2 + 36, (person[1] + place[1]) / 2, "meets at", font(15, "med"), col(GOLD, a))


def instance_graph(d, origin, a=1.0):
    if a <= 0.02:
        return
    ox, oy = origin
    moriarty = (ox - 170, oy)
    story = (ox + 190, oy)
    falls = (ox + 190, oy + 150)
    arrow(d, (moriarty[0] + 90, moriarty[1]), (story[0] - 140, story[1]), col(TEAL, a), width=3, prog=min(1, a * 1.3))
    arrow(d, (story[0], story[1] + 36), (falls[0], falls[1] - 36), col(TEAL, a), width=3, prog=min(1, a * 1.3))
    node(d, *moriarty, 170, 58, "Moriarty", TEAL, a)
    node(d, *story, 270, 58, "The Final Problem", TEAL, a)
    node(d, *falls, 250, 58, "Reichenbach", TEAL, a)
    if a > 0.65:
        center_text(d, (moriarty[0] + story[0]) / 2, moriarty[1] - 28, "appears in", font(15, "med"), col(TEAL, a))
        center_text(d, story[0] - 64, (story[1] + falls[1]) / 2, "meets at", font(15, "med"), col(TEAL, a))


def passage_mark(d, x, y, a, label="Final Problem"):
    if a <= 0.02:
        return
    page(d, x, y, 150, 92, label, BLUE, a, bars=2)


def tc(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def words(paragraphs: list[str]) -> int:
    return sum(len(p.split()) for p in paragraphs)


SECTIONS = [
    {
        "id": "purpose",
        "file": "00-purpose.mp4",
        "kicker": "The purpose",
        "picture": [
            "One line: an agent that does not invent what the documents never said.",
            "Three beats: the usual way, a graph with vectors, then how to try the open-source store.",
        ],
        "pro": [
            "This briefing shows how an agent can answer from documents without inventing what they never said. The usual way fails. A graph and a vector search belong together. Then, how to try this open-source store on your own documents.",
        ],
        "record": [
            "This briefing shows how an agent can answer from your own documents without inventing what they never said. The usual way fails. A graph and a vector search belong together. Then, how to try this open-source store yourself.",
        ],
    },
    {
        "id": "collection",
        "file": "00-the-collection.mp4",
        "kicker": "The collection",
        "picture": [
            "Three story pages: Adventures, Memoirs, and Return, labeled as the collection used in this briefing.",
            "A short line: a collection, also called a corpus, is the set of documents an agent answers from.",
            "A quieter mark: this set is a stand-in, and the same pictures apply to any documents.",
        ],
        "pro": [
            "The examples that follow use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.",
            "It is a stand-in for any documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.",
        ],
        "record": [
            "These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.",
            "It is a stand-in for your own documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.",
        ],
    },
    {
        "id": "usual",
        "file": "01-usual-path.mp4",
        "kicker": "The usual path",
        "picture": [
            "Three story collections become a field of vectors. The question is where Professor Moriarty was born.",
            "The lit chunk says he is a man of good birth. A sentence is written from it, and a citation is pinned on afterwards.",
        ],
        "pro": [
            "An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the nearest chunks, and the agent writes a sentence.",
            "The question is where Professor Moriarty was born. The stories never say. The nearest chunk calls him a man of good birth and excellent education. The model can still write that phrase, and attach a citation afterwards. The words were there. They do not name a place.",
        ],
        "record": [
            "An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the nearest chunks, and the agent writes a sentence.",
            "Ask where Professor Moriarty was born. The stories never say. The nearest chunk calls him a man of good birth. From those words the model can write that phrase, and a citation gets attached afterwards. The words were there. They do not name a place.",
        ],
    },
    {
        "id": "graph",
        "file": "02-ontology-and-graph.mp4",
        "kicker": "Ontology and graph",
        "picture": [
            "Left, an ontology draws itself: Person, Story, Place, and the two links that are allowed.",
            "Right, the same picture filled in. Moriarty appears in The Final Problem, and meets Holmes at the Reichenbach Falls. A passage sits on the fact.",
        ],
        "pro": [
            "An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A story. A place. A person appears in a story. A person meets someone at a place.",
            "A knowledge graph is that picture, filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Each fact points at a passage.",
        ],
        "record": [
            "An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A story. A place. A person appears in a story. A person meets someone at a place.",
            "The knowledge graph is that picture filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Every fact points at a passage.",
        ],
    },
    {
        "id": "together",
        "file": "03-graph-and-vectors.mp4",
        "kicker": "Graph and vectors",
        "picture": [
            "A question that names Moriarty walks the graph to The Final Problem and the passage.",
            "A question that only describes the waterfall searches the vectors, lands on the same passage, and returns to the same fact.",
        ],
        "pro": [
            "When a question names things, the graph is the path. Where does Professor Moriarty appear walks from the person, along appears in, to the story, and on to the falls. The passage comes with the fact.",
            "Instead, two rivals fall together at a waterfall. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.",
        ],
        "record": [
            "Ask where Professor Moriarty appears, and the graph is enough. Person, appears in, story, meets at the falls, and the passage is already on the fact.",
            "Instead, two rivals fall together at a waterfall. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.",
        ],
    },
    {
        "id": "bring",
        "file": "04-bring-ontology.mp4",
        "kicker": "Bring the ontology",
        "picture": [
            "Normal ingestion. Documents are divided into passages. An ontology you bring drops into extraction.",
            "A fact enters the graph only when the passage contains it. One vector is stored for each passage.",
        ],
        "pro": [
            "If you already have the vocabulary, you bring the ontology with the documents. They are divided into passages. Extraction reads each passage through the ontology you brought.",
            "A fact is kept only when the passage contains it. The Final Problem names Moriarty and the Reichenbach Falls, so that fact stays. The lab builds the graph, and one vector for each passage.",
        ],
        "record": [
            "This is the path when you bring the ontology. Documents stay as they arrived and are split into passages to cite. Extraction reads each passage in the types you brought.",
            "A fact is kept only when the passage contains it. The Final Problem names Moriarty and the falls, so that fact stays. One vector is stored for each passage.",
        ],
    },
    {
        "id": "derive",
        "file": "05-derive-ontology.mp4",
        "kicker": "Derive the ontology",
        "picture": [
            "The other ingestion. Documents arrive with no ontology. A sample proposes Person, Story, and Place.",
            "The proposals become a draft, a person publishes it, and that ontology drops into the same extraction. The graph and the vectors are built the same way.",
        ],
        "pro": [
            "If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they mention, and the links that should be allowed. A person publishes that draft.",
            "Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.",
        ],
        "record": [
            "This is the path when you do not bring an ontology. The documents come in. A sample is read, and the lab proposes the kinds of things they talk about. You publish that draft.",
            "Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.",
        ],
    },
    {
        "id": "questions",
        "file": "06-when-someone-asks.mp4",
        "kicker": "The chat",
        "picture": [
            "A chat message, Where does Professor Moriarty appear, enters an agent that holds the ontology. The agent walks the graph, reads the cited passage, and a check keeps the statement because the quote is in the passage.",
            "The result returns in the chat: The Final Problem, with that passage.",
            "A second message, where he was born, takes the same path. Nothing survives the check. The result in the chat is a decline.",
        ],
        "pro": [
            "A person types a message in the chat. Where does Professor Moriarty appear walks from the person to the story, and the cited passage is read. It is in The Final Problem, so the statement stays. The result is that story, with the passage beside it.",
            "Where he was born takes the same path. It meets the phrase a man of good birth, and nothing that names a place. The result is a decline. The sources do not say.",
        ],
        "record": [
            "Someone types in the chat. Where does Professor Moriarty appear goes from the person to the story, and the passage on that fact is read. The Final Problem does name him, so the statement stays. You see that story, with the passage beside it.",
            "Ask where he was born. It meets a man of good birth, not a place. The chat declines. The sources do not say.",
        ],
    },
    {
        "id": "close",
        "file": "07-what-is-better.mp4",
        "kicker": "What is better",
        "picture": [
            "Left, the kept result: The Final Problem, with that passage, in cyan.",
            "Beside it, the declined result: the sources do not say, in danger.",
            "One line: the graph is for the connection, and the vectors are for the wording.",
        ],
        "pro": [
            "A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The Final Problem stays, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place. A sentence no longer receives a citation after it has been written.",
        ],
        "record": [
            "A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The Final Problem stays, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place. A sentence no longer gets a citation after it has been written.",
        ],
    },
    {
        "id": "tryit",
        "file": "08-try-it.mp4",
        "kicker": "Try it",
        "picture": [
            "A one-line recap: Moriarty appears in The Final Problem. His birthplace is not in the sources.",
            "Three steps: the public repository, clone it, your own AWS account.",
        ],
        "pro": [
            "Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say.",
            "To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.",
        ],
        "record": [
            "Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say.",
            "To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.",
        ],
    },
]


def prepare(section):
    n = max(words(section["pro"]), words(section["record"]))
    section["words"] = n
    section["duration"] = HEAD + n / WPS + TAIL


# --- scenes -----------------------------------------------------------------

def draw_purpose(d, t):
    heading(d, "Why listen", "An agent that does not invent what the documents never said.")
    a1 = ease(t, 0.6, 2.4)
    a2 = ease(t, 3.2, 5.2)
    a3 = ease(t, 6.0, 8.2)
    beats = [
        (a1, "The usual way", CORAL),
        (a2, "Graph and vectors", TEAL),
        (a3, "Try it on your documents", GOLD),
    ]
    gap = 48
    widths = []
    fnt = font(22, "sem")
    for _, text, _ in beats:
        widths.append(fnt.getlength(text) + 48)
    group = sum(widths) + gap * (len(beats) - 1)
    x = (W - group) / 2
    y = 520
    for (a, text, ring), w in zip(beats, widths):
        pill(d, x + w / 2, y, text, ring, a)
        if a > 0.7 and text != beats[-1][1]:
            pass
        x += w + gap
    # Arrows between the beats, once each pair is visible.
    x = (W - group) / 2
    for i, ((a, _, ring), w) in enumerate(zip(beats, widths)):
        if i < len(beats) - 1 and min(a, beats[i + 1][0]) > 0.4:
            arrow(
                d,
                (x + w + 6, y),
                (x + w + gap - 6, y),
                col(MUTED, min(a, beats[i + 1][0])),
                width=3,
                prog=min(a, beats[i + 1][0]),
            )
        x += w + gap


def draw_collection(d, t):
    heading(d, "One collection", "Named before any example.")
    a_pages = ease(t, 0.4, 3.2)
    a_def = ease(t, 4.2, 8.5)
    a_stand = ease(t, 18.5, 23.5)

    titles = ["Adventures", "Memoirs", "Return"]
    w, h, gap = 270, 300, 56
    x0 = (W - (3 * w + 2 * gap)) / 2
    y0 = 250
    for i, name in enumerate(titles):
        page(d, x0 + i * (w + gap), y0, w, h, name, BLUE, a_pages, bars=4, title_size=28)
    stage(d, W / 2, y0 + h + 28, "THIS BRIEFING", BLUE, a_pages)

    if a_def > 0.02:
        center_text(d, W / 2, 700, "A collection, also called a corpus.", font(26, "med"), col(IVORY, a_def))
        center_text(d, W / 2, 744, "The documents an agent answers from.", font(22), col(MUTED, a_def))
    if a_stand > 0.02:
        center_text(d, W / 2, 830, "A stand-in for any documents.", font(20), col(MUTED, a_stand))


def draw_usual(d, t):
    heading(d, "The usual path", "Chunks nearest in meaning. A sentence written from them.")
    a_docs = ease(t, 0.4, 2.2)
    a_field = ease(t, 2.4, 5.5)
    a_hit = ease(t, 6.0, 9.0)
    a_answer = ease(t, 9.5, 13.0)
    a_cite = ease(t, 14.0, 17.0)

    titles = ["Adventures", "Memoirs", "Return"]
    for i, name in enumerate(titles):
        page(d, 90, 280 + i * 175, 210, 155, name, BLUE, a_docs, bars=3)
    stage(d, 195, 820, "DOCUMENTS", BLUE, a_docs)

    arrow(d, (330, 520), (470, 520), col(BLUE, a_field), prog=a_field)
    dots(d, 680, 520, 150, 120, 36, a_field, hot={2, 7, 11, 18} if a_hit > 0.2 else set(), hot_color=ROSE)
    if a_hit > 0.2:
        pill(d, 680, 700, "a man of good birth", ROSE, a_hit)
        stage(d, 680, 820, "VECTORS", BLUE, a_field)

    arrow(d, (860, 520), (1040, 470), col(CORAL, a_answer), prog=a_answer)
    if a_answer > 0.05:
        d.rounded_rectangle((1060, 300, 1820, 760), radius=12, fill=col(INK, a_answer), outline=col(CORAL, a_answer), width=3)
        d.text((1100, 340), "QUESTION", font=font(14, "mono"), fill=col(DIM, a_answer))
        d.text((1100, 372), "Where was Moriarty born?", font=font(28, "sem"), fill=col(IVORY, a_answer))
        d.text((1100, 460), "WRITTEN ANSWER", font=font(14, "mono"), fill=col(CORAL, a_answer))
        d.text((1100, 500), "Of good birth", font=font(48, "sem"), fill=col(IVORY, a_answer))
        if a_cite > 0.05:
            pill(d, 1360, 660, "Citation attached afterwards", CORAL, a_cite, fill=RAISED)
            dashed(d, (820, 700), (1060, 620), col(CORAL, a_cite), width=3)


def draw_graph(d, t):
    heading(d, "A vocabulary, then the facts", "What the collection is allowed to say, and what it actually says.")
    a_left = ease(t, 0.5, 4.5)
    a_right = ease(t, 6.0, 11.0)
    a_page = ease(t, 12.0, 15.0)
    d.line((960, 230, 960, 900), fill=col(LINE, max(a_left, a_right)), width=2)
    stage(d, 480, 230, "ONTOLOGY", GOLD, a_left)
    schema(d, (480, 420), a_left, scale=1.15)
    stage(d, 1440, 230, "KNOWLEDGE GRAPH", TEAL, a_right)
    instance_graph(d, (1400, 430), a_right)
    if a_page > 0.05:
        passage_mark(d, 1580, 760, a_page)
        arrow(d, (1570, 640), (1640, 760), col(BLUE, a_page), width=3, prog=a_page)
        stage(d, 1655, 870, "PASSAGE", BLUE, a_page)


def draw_together(d, t):
    heading(d, "Why the vectors stay", "A named thing walks the graph. A situation is found by meaning.")
    a_top = ease(t, 0.4, 3.0)
    a_walk = ease(t, 3.2, 8.5)
    a_page = ease(t, 8.5, 11.0)
    a_bot = ease(t, 11.5, 14.5)
    a_back = ease(t, 15.5, 19.5)

    pill(d, 250, 340, "Where does Moriarty appear?", TEAL, a_top)
    stage(d, 250, 392, "NAMES SOMETHING", TEAL, a_top)
    arrow(d, (460, 340), (540, 340), col(TEAL, a_walk), prog=a_walk)
    node(d, 640, 340, 180, 64, "Moriarty", TEAL, a_walk)
    arrow(d, (740, 340), (860, 340), col(TEAL, a_walk), prog=max(0.0, (a_walk - 0.25) / 0.75))
    center_text(d, 800, 308, "appears in", font(15, "med"), col(TEAL, max(0.0, a_walk - 0.3)))
    node(d, 1020, 340, 280, 64, "The Final Problem", TEAL, max(0.0, (a_walk - 0.4) / 0.6))
    arrow(d, (1170, 340), (1320, 360), col(BLUE, a_page), prog=a_page)
    passage_mark(d, 1330, 300, a_page, "Final Problem")
    stage(d, 1405, 268, "SAME PASSAGE", BLUE, a_page)

    d.line((80, 520, 1840, 520), fill=col(LINE, 0.9), width=1)

    pill(d, 320, 700, "Two rivals fall at a waterfall", BLUE, a_bot)
    stage(d, 340, 752, "DESCRIBES A SITUATION", BLUE, a_bot)
    arrow(d, (640, 700), (760, 730), col(BLUE, a_bot), prog=a_bot)
    dots(d, 980, 760, 150, 80, 28, a_bot, hot={4, 9, 15, 21})
    poly_arrow(
        d,
        [(1140, 760), (1540, 760), (1540, 430), (1440, 400)],
        col(BLUE, a_back),
        width=3,
        prog=a_back,
    )


def draw_bring(d, t):
    heading(d, "Bring the ontology", "Documents in. The vocabulary comes with you. A graph comes out.")
    a_docs = ease(t, 0.3, 2.2)
    a_pass = ease(t, 2.6, 5.0)
    a_ont = ease(t, 5.2, 8.5)
    a_ext = ease(t, 8.0, 10.5)
    a_out = ease(t, 11.0, 15.0)
    live = t > 15

    page(d, 80, 430, 170, 200, "Stories", BLUE, a_docs, bars=4)
    page(d, 110, 460, 170, 200, "Stories", BLUE, a_docs * 0.95, bars=4)
    stage(d, 195, 700, "DOCUMENTS", BLUE, a_docs)

    arrow(d, (300, 540), (400, 540), col(BLUE, a_pass), prog=a_pass)
    for i in range(4):
        yy = 470 + i * 36
        d.rounded_rectangle((420, yy, 620, yy + 26), radius=8, fill=col(INK, a_pass), outline=col(BLUE, a_pass), width=2)
    stage(d, 520, 700, "PASSAGES", BLUE, a_pass)

    # Ontology brought in from above.
    for name, x in (("Person", 700), ("Story", 860), ("Place", 1020)):
        pill(d, x, 214, name, GOLD, a_ont)
    node(d, 860, 330, 250, 84, "Ontology", GOLD, a_ont, sub="you bring this")
    arrow(d, (860, 378), (860, 475), col(GOLD, a_ont), prog=a_ont)

    arrow(d, (640, 540), (740, 520), col(BLUE, a_ext), prog=a_ext)
    node(d, 860, 530, 200, 100, "Extract", TEAL, a_ext, sub="fact in the passage")

    arrow(d, (970, 500), (1240, 300), col(TEAL, a_out), prog=a_out)
    arrow(d, (970, 580), (1380, 770), col(BLUE, a_out), prog=a_out)

    node(d, 1280, 280, 180, 56, "Moriarty", TEAL, a_out)
    node(d, 1640, 280, 280, 56, "The Final Problem", TEAL, a_out)
    arrow(d, (1380, 280), (1490, 280), col(TEAL, a_out), prog=a_out, width=3)
    if a_out > 0.4:
        center_text(d, 1435, 248, "appears in", font(14, "med"), col(TEAL, a_out))
    stage(d, 1530, 348, "KNOWLEDGE GRAPH", TEAL, a_out)
    arrow(d, (1700, 314), (1700, 418), col(BLUE, a_out), width=3, prog=a_out)
    passage_mark(d, 1560, 418, a_out, "Final Problem")

    dots(d, 1500, 780, 170, 72, 26, a_out, hot={3, 8, 14})
    stage(d, 1500, 880, "ONE VECTOR PER PASSAGE", BLUE, a_out)

    if live:
        bead(d, (300, 540), (740, 520), (t - 15) / 3.5, GOLD)
        bead(d, (860, 378), (860, 475), (t - 15) / 3.5, GOLD)


def draw_derive(d, t):
    heading(d, "Derive the ontology", "Documents in. A vocabulary is proposed and published. Extraction is the same step.")
    a_docs = ease(t, 0.4, 2.2)
    a_sample = ease(t, 2.4, 5.0)
    a_terms = ease(t, 5.2, 8.8)
    a_draft = ease(t, 9.0, 12.0)
    a_pub = ease(t, 12.2, 15.0)
    a_join = ease(t, 15.2, 18.2)
    a_out = ease(t, 18.4, 22.0)

    page(d, 70, 470, 160, 180, "Stories", BLUE, a_docs, bars=4)
    stage(d, 150, 670, "DOCUMENTS", BLUE, a_docs)

    arrow(d, (150, 470), (150, 338), col(GOLD, a_sample), prog=a_sample, width=3)
    page(d, 80, 200, 140, 130, "Sample", GOLD, a_sample, bars=2)
    stage(d, 300, 230, "SAMPLE", GOLD, a_sample)

    arrow(d, (230, 265), (330, 265), col(GOLD, a_terms), prog=a_terms)
    for name, x in (("Person", 430), ("Story", 600), ("Place", 770)):
        pill(d, lerp(300, x, a_terms), 265, name, GOLD, a_terms)

    arrow(d, (860, 265), (960, 265), col(GOLD, a_draft), prog=a_draft)
    node(d, 1120, 265, 260, 84, "Draft ontology", GOLD, a_draft, sub="a person reviews")
    arrow(d, (1260, 265), (1380, 265), col(TEAL, a_pub), prog=a_pub)
    node(d, 1520, 265, 210, 84, "Published", TEAL, a_pub)

    arrow(d, (1520, 312), (1520, 520), col(GOLD, a_join), prog=a_join)
    node(d, 1520, 575, 220, 100, "Extract", TEAL, a_join, sub="same step")

    arrow(d, (240, 560), (350, 560), col(BLUE, a_join), prog=a_join)
    arrow(d, (600, 572), (1400, 575), col(BLUE, a_join), prog=a_join)
    for i in range(3):
        d.rounded_rectangle((370, 520 + i * 38, 590, 548 + i * 38), radius=8, fill=col(INK, a_join), outline=col(BLUE, a_join), width=2)
    stage(d, 480, 660, "PASSAGES", BLUE, a_join)

    arrow(d, (1440, 630), (730, 820), col(TEAL, a_out), prog=a_out)
    arrow(d, (1600, 630), (1660, 800), col(BLUE, a_out), prog=a_out)
    node(d, 760, 820, 180, 56, "Moriarty", TEAL, a_out)
    node(d, 1160, 820, 280, 56, "The Final Problem", TEAL, a_out)
    arrow(d, (860, 820), (1010, 820), col(TEAL, a_out), prog=a_out, width=3)
    if a_out > 0.35:
        center_text(d, 935, 788, "appears in", font(14, "med"), col(TEAL, a_out))
    stage(d, 990, 888, "KNOWLEDGE GRAPH", TEAL, a_out)
    dots(d, 1680, 840, 120, 52, 18, a_out, hot={2, 6, 11})
    stage(d, 1680, 920, "VECTORS", BLUE, a_out)


def chat_bubble(d, box, who, text, accent, a, size=26):
    if a <= 0.02:
        return
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=12, fill=col(INK, a), outline=col(accent, a), width=3)
    d.text((x0 + 18, y0 + 14), who, font=font(13, "mono"), fill=col(accent, a))
    draw_wrapped(d, text, font(size, "sem"), col(IVORY, a), x0 + 18, y0 + 42, x1 - x0 - 36, gap=4)


def draw_questions(d, t):
    heading(d, "A message, then a result", "Typed in the chat. Returned only when a passage supports it.")
    a_msg = ease(t, 0.4, 2.4)
    a_agent = ease(t, 2.6, 5.2)
    a_find = ease(t, 5.4, 9.5)
    a_keep = ease(t, 9.8, 13.0)
    a_out = ease(t, 13.2, 16.5)
    a_msg2 = ease(t, 18.0, 20.5)
    a_find2 = ease(t, 20.8, 24.5)
    a_drop = ease(t, 24.8, 28.0)
    a_out2 = ease(t, 28.2, 32.0)

    # Both messages enter the left side of the agent, above its caption.
    chat_bubble(d, (64, 230, 460, 370), "MESSAGE", "Where does Moriarty appear?", IVORY, a_msg, size=22)
    arrow(d, (460, 300), (480, 300), col(GOLD, a_agent), prog=a_agent, width=3)

    d.rounded_rectangle((480, 220, 850, 450), radius=12, fill=col(INK, a_agent), outline=col(GOLD, a_agent), width=3)
    if a_agent > 0.1:
        center_text(d, 665, 278, "Agent", font(26, "sem"), col(IVORY, a_agent))
        for name, x in (("Person", 559), ("Story", 668), ("Place", 774)):
            pill(d, x, 358, name, GOLD, a_agent)
        stage(d, 665, 466, "HOLDS THE ONTOLOGY", GOLD, a_agent)

    # Named lookup: the fact, the passage under it, then the check.
    arrow(d, (850, 300), (940, 300), col(TEAL, a_find), prog=a_find, width=3)
    node(d, 1000, 300, 170, 56, "Moriarty", TEAL, a_find)
    arrow(d, (1090, 300), (1160, 300), col(TEAL, a_find), width=3, prog=a_find)
    if a_find > 0.45:
        center_text(d, 1125, 248, "appears in", font(14, "med"), col(TEAL, a_find))
    node(d, 1310, 300, 260, 56, "Final Problem", TEAL, a_find)
    passage_mark(d, 1185, 350, a_find, "Final Problem")
    stage(d, 1285, 492, "GRAPH AND PASSAGE", TEAL, a_find)

    arrow(d, (1450, 300), (1470, 300), col(TEAL, a_keep), prog=a_keep, width=3)
    node(d, 1540, 300, 140, 56, "Kept", TEAL, a_keep)
    arrow(d, (1540, 328), (1540, 515), col(TEAL, a_out), prog=a_out, width=3)

    # Result in the chat. The passage sits clear of the sentence.
    chat_bubble(d, (1220, 515, 1856, 675), "RESULT", "The Final Problem.", TEAL, a_out, size=26)
    if a_out > 0.4:
        passage_mark(d, 1682, 555, a_out, "Final Problem")

    # Second message. The path steps down beside the agent, not across its caption.
    chat_bubble(d, (64, 720, 420, 845), "MESSAGE", "Where was he born?", IVORY, a_msg2, size=22)
    arrow(d, (420, 782), (480, 400), col(GOLD, a_find2), prog=a_find2, width=3)
    poly_arrow(
        d,
        [(850, 400), (930, 400), (930, 782), (990, 782)],
        col(CORAL, a_find2),
        width=3,
        prog=a_find2,
    )
    node(d, 1095, 782, 210, 64, "Good birth", CORAL, a_find2, sub="not a place")
    arrow(d, (1200, 782), (1270, 782), col(CORAL, a_drop), prog=a_drop, width=3)
    node(d, 1350, 782, 160, 58, "Removed", CORAL, a_drop)
    arrow(d, (1430, 782), (1500, 782), col(CORAL, a_out2), prog=a_out2, width=3)
    chat_bubble(d, (1500, 720, 1856, 845), "RESULT", "The sources do not say.", CORAL, a_out2, size=22)


def draw_close(d, t):
    heading(d, "What is better", "A fact the documents support.")
    a_keep = ease(t, 0.4, 2.6)
    a_page = ease(t, 2.0, 4.6)
    a_drop = ease(t, 3.8, 6.4)
    a_line = ease(t, 7.6, 10.4)
    a_bring = ease(t, 11.6, 14.4)
    a_ask = ease(t, 13.8, 16.6)

    if a_keep > 0.02:
        d.rounded_rectangle((80, 220, 920, 530), radius=12, fill=col(INK, a_keep), outline=col(TEAL, a_keep), width=3)
        d.text((112, 246), "RESULT", font=font(14, "mono"), fill=col(TEAL, a_keep))
        d.text((112, 292), "The Final Problem.", font=font(40, "sem"), fill=col(IVORY, a_keep))
    page(d, 112, 380, 280, 116, "Final Problem", TEAL, a_page, bars=2, title_size=18)

    if a_drop > 0.02:
        d.rounded_rectangle((1000, 220, 1840, 530), radius=12, fill=col(INK, a_drop), outline=col(CORAL, a_drop), width=3)
        d.text((1032, 246), "RESULT", font=font(14, "mono"), fill=col(CORAL, a_drop))
        d.text((1032, 340), "The sources do not say.", font=font(36, "sem"), fill=col(IVORY, a_drop))

    line = "Graph for the connection. Vectors for the wording."
    fnt = font(26, "med")
    d.text(((W - fnt.getlength(line)) / 2, 590), line, font=fnt, fill=col(IVORY, a_line))

    left = "Bring or publish an ontology"
    right = "Ask. Keep only what a passage supports."
    pf = font(18, "sem")
    gap = 100
    lw, rw = pf.getlength(left) + 40, pf.getlength(right) + 40
    group = lw + gap + rw
    x0 = (W - group) / 2
    c1 = x0 + lw / 2
    c2 = x0 + lw + gap + rw / 2
    y = 760
    pill(d, c1, y, left, GOLD, a_bring)
    pill(d, c2, y, right, TEAL, a_ask)
    arrow(
        d,
        (c1 + lw / 2 + 10, y),
        (c2 - rw / 2 - 10, y),
        col(MUTED, min(a_bring, a_ask)),
        width=3,
        prog=min(a_bring, a_ask),
    )


def draw_try(d, t):
    heading(d, "Try it", "The public repository. Your own documents.")
    a_line = ease(t, 0.4, 2.2)
    a1 = ease(t, 3.0, 5.0)
    a2 = ease(t, 5.4, 7.4)
    a3 = ease(t, 7.8, 10.0)
    line = "Moriarty appears in The Final Problem. His birthplace is not in the sources."
    fnt = font(22, "med")
    d.text(((W - fnt.getlength(line)) / 2, 250), line, font=fnt, fill=col(IVORY, a_line))

    steps = [
        (a1, "1", "Public repo", "patternode/knowledge-store"),
        (a2, "2", "Clone it", "It is open source"),
        (a3, "3", "Your AWS account", "Your own documents"),
    ]
    w, gap = 420, 48
    x0 = (W - (3 * w + 2 * gap)) / 2
    for i, (a, num, title, sub) in enumerate(steps):
        x = x0 + i * (w + gap)
        if a <= 0.02:
            continue
        d.rounded_rectangle((x, 380, x + w, 620), radius=12, fill=col(INK, a), outline=col(CYAN if i == 2 else GOLD, a), width=3)
        d.text((x + 24, 410), num, font=font(18, "mono"), fill=col(CYAN, a))
        d.text((x + 24, 460), title, font=font(28, "sem"), fill=col(IVORY, a))
        d.text((x + 24, 520), sub, font=font(18), fill=col(MUTED, a))
        if i < 2 and min(a, steps[i + 1][0]) > 0.3:
            arrow(
                d,
                (x + w + 6, 500),
                (x + w + gap - 6, 500),
                col(MUTED, min(a, steps[i + 1][0])),
                width=3,
                prog=min(a, steps[i + 1][0]),
            )


DRAW = {
    "purpose": draw_purpose,
    "collection": draw_collection,
    "usual": draw_usual,
    "graph": draw_graph,
    "together": draw_together,
    "bring": draw_bring,
    "derive": draw_derive,
    "questions": draw_questions,
    "close": draw_close,
    "tryit": draw_try,
}


def render_frame(bg, section, t, index, n, offset):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    chrome(d, section["kicker"])
    DRAW[section["id"]](d, t)
    footer(d, index, n, offset + t, t, section["duration"])
    return Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")


def encode(path: Path, section, bg, index, n, offset):
    path.parent.mkdir(parents=True, exist_ok=True)
    nframes = int(round(section["duration"] * FPS))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "32k",
        "-movflags", "+faststart",
        str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for i in range(nframes):
            t = i / FPS
            proc.stdin.write(render_frame(bg, section, t, index, n, offset).tobytes())
            if i % (FPS * 10) == 0:
                print(f"  {section['id']} {t:6.1f}s / {section['duration']:.1f}s", flush=True)
    finally:
        proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise SystemExit(f"ffmpeg failed for {path} ({code})")
    print(f"wrote {path}")


def load_bg():
    """Brand ground, with a quiet signal field kept to the sides."""
    base = Image.new("RGBA", (W, H), (*BG, 255))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rng = random.Random(7)
    for _ in range(12):
        if rng.random() < 0.5:
            lo, hi = 20, 300
        else:
            lo, hi = W - 300, W - 20
        x, y = rng.randint(lo, hi), rng.randint(150, 960)
        pts = [(x, y)]
        for _step in range(rng.randint(2, 3)):
            x = max(lo, min(hi, x + rng.randint(-110, 110)))
            y = max(130, min(990, y + rng.randint(-55, 55)))
            pts.append((x, y))
        shade = CYAN if rng.random() < 0.62 else INDIGO
        d.line(pts, fill=(*shade, 32), width=2)
        for px, py in pts:
            r = 3 if rng.random() < 0.28 else 2
            d.ellipse((px - r, py - r, px + r, py + r), fill=(*shade, 64))
    return Image.alpha_composite(base, overlay).convert("RGB")


def _voice_file(path: Path, heading_text: str, intro: str, key: str):
    lines = [f"# {heading_text}", "", intro, ""]
    cursor = 0.0
    for i, section in enumerate(SECTIONS, start=1):
        start = cursor
        end = cursor + section["duration"]
        lines += [
            f"## {i}. {section['kicker']}",
            "",
            f"Clip `{section['file']}`. Assembly {tc(start)} to {tc(end)}.",
            "",
            "\n\n".join(section[key]),
            "",
        ]
        cursor = end
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", path)


def write_docs():
    script = [
        "# Knowledge Store briefing",
        "",
        f"{['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'][len(SECTIONS)]} clips. The picture is an architecture diagram of the flow.",
        "",
        "Two complete reads, one per clip, in prose:",
        "",
        "- [voice-pro.md](voice-pro.md) for a professional technical narrator.",
        "- [voice-record.md](voice-record.md) to record yourself. Read the paragraphs for that clip straight through.",
        "",
        "The clips are timed to the longer of the two reads, at about 130 words a minute, with a short breath at each end.",
        "",
        "## Timeline",
        "",
        "| In | Out | Clip | Picture |",
        "|---|---|---|---|",
    ]
    cursor = 0.0
    for section in SECTIONS:
        start, end = cursor, cursor + section["duration"]
        script.append(f"| {tc(start)} | {tc(end)} | `{section['file']}` | {section['kicker']} |")
        cursor = end
    script += ["", f"Total picture: {tc(cursor)} ({cursor:.1f} seconds).", ""]
    cursor = 0.0
    for i, section in enumerate(SECTIONS, start=1):
        script += [
            f"## {i}. {section['kicker']}",
            "",
            f"`{section['file']}`, {tc(cursor)} to {tc(cursor + section['duration'])}.",
            "",
            "Picture:",
            "",
        ]
        for line in section["picture"]:
            script.append(f"- {line}")
        script.append("")
        cursor += section["duration"]
    (ROOT / "script.md").write_text("\n".join(script) + "\n", encoding="utf-8")
    _voice_file(
        ROOT / "voice-pro.md",
        "Professional voice",
        "For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.",
        "pro",
    )
    _voice_file(
        ROOT / "voice-record.md",
        "Record yourself",
        "Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.",
        "record",
    )
    print(f"total {cursor:.1f}s")


def load_ready_bg():
    for section in SECTIONS:
        prepare(section)
    return load_bg()


def stills(bg):
    dest = OUT / "stills"
    dest.mkdir(parents=True, exist_ok=True)
    cursor = 0.0
    n = len(SECTIONS)
    for i, section in enumerate(SECTIONS, start=1):
        # Late in the clip, once the diagram has assembled.
        frame = render_frame(bg, section, max(1.0, section["duration"] - 2.5), i, n, cursor)
        name = dest / f"{section['id']}.png"
        frame.save(name)
        print("still", name)
        cursor += section["duration"]


def frames(bg):
    dest = Path("/tmp/ks-qa")
    dest.mkdir(parents=True, exist_ok=True)
    cursor = 0.0
    n = len(SECTIONS)
    for i, section in enumerate(SECTIONS, start=1):
        for frac in (0.25, 0.55, 0.92):
            t = section["duration"] * frac
            frame = render_frame(bg, section, t, i, n, cursor)
            name = dest / f"{section['id']}-{int(frac * 100)}.png"
            frame.save(name)
            print("frame", name)
        cursor += section["duration"]


def concat(paths, dest: Path):
    lst = dest.with_suffix(".concat.txt")
    lst.write_text("".join(f"file '{p}'\n" for p in paths), encoding="utf-8")
    try:
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dest)])
    finally:
        lst.unlink(missing_ok=True)
    print("wrote", dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", action="store_true")
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--frames", action="store_true")
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()
    for section in SECTIONS:
        prepare(section)
    write_docs()
    if args.docs and not args.stills and not args.frames:
        return
    if args.no_video and not args.stills and not args.frames:
        return
    bg = load_bg()
    if args.frames:
        frames(bg)
        return
    if args.stills:
        stills(bg)
        return
    n = len(SECTIONS)
    cursor = 0.0
    paths = []
    for i, section in enumerate(SECTIONS, start=1):
        path = OUT / section["file"]
        paths.append(path)
        encode(path, section, bg, i, n, cursor)
        cursor += section["duration"]
    concat(paths, OUT / "assembly.mp4")


if __name__ == "__main__":
    main()
