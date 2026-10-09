"""Motion-graphics cut for the Knowledge Store briefing.

Picture only, plus a silent audio track so players report duration. The voice is recorded
separately; see voice-script.md, which this file writes from the same cues it animates.

  python docs/explainer/build.py --docs
  python docs/explainer/build.py --stills
  python docs/explainer/build.py
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BG_PATH = ROOT / "assets" / "bg-network.jpg"
OUT = ROOT / "media"

W, H = 1920, 1080
FPS = 12
WORD_SEC = 0.35
PAUSE = 0.20
MIN_SENT = 1.05
HEAD = 0.45
TAIL = 0.35

BG = (12, 16, 28)
IVORY = (243, 240, 232)
MUTED = (176, 186, 200)
DIM = (132, 144, 162)
GOLD = (224, 177, 90)
TEAL = (78, 214, 162)
CORAL = (232, 118, 104)
BLUE = (148, 180, 255)
BRONZE = (206, 146, 88)
SILVER = (214, 220, 228)
CARD = (18, 26, 44)
LINE = (62, 78, 108)
SOFT = (28, 38, 60)

FONTS = {
    "reg": "/usr/share/fonts/truetype/macos/Inter-Regular.ttf",
    "med": "/usr/share/fonts/truetype/macos/Inter-Medium.ttf",
    "sem": "/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf",
    "mono": "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
}

_fonts: dict = {}


def font(size: int, kind: str = "reg"):
    key = (kind, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONTS[kind], size)
    return _fonts[key]


def col(rgb, a=1.0):
    return (*rgb, int(max(0.0, min(1.0, a)) * 255))


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def appear(t, start, dur=0.4):
    if t <= start:
        return 0.0
    return ease((t - start) / dur)


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


def draw_wrapped(d, text, fnt, fill, x, y, width, gap=8):
    lines = wrap(text, fnt, width)
    step = fnt.size + gap
    for i, line in enumerate(lines):
        d.text((x, y + i * step), line, font=fnt, fill=fill)
    return len(lines) * step


def panel(d, box, fill=CARD, outline=LINE, radius=18, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def chrome(d, kicker):
    f = font(15, "med")
    draw_tracked(d, (88, 40), "KNOWLEDGE STORE", f, col(GOLD), tracking=2.4)
    label = kicker.upper()
    tw = tracked_width(label, f, 1.8)
    draw_tracked(d, (W - 88 - tw, 40), label, f, col(DIM), tracking=1.8)
    d.line((88, 76, W - 88, 76), fill=col(LINE), width=1)


def footer(d, index, n, global_t, local_t, duration):
    d.line((88, 1012, W - 88, 1012), fill=col(LINE), width=1)
    f = font(15, "med")
    draw_tracked(d, (88, 1032), f"{index:02d}   /   {n:02d}", f, col(DIM), tracking=1.4)
    stamp = f"{int(global_t) // 60}:{int(global_t) % 60:02d}"
    sf = font(16, "mono")
    sw = sf.getlength(stamp)
    d.text((W - 88 - sw, 1028), stamp, font=sf, fill=col(DIM))
    # recording aid: how far through this section
    if duration > 0:
        x1 = 88 + (W - 176) * max(0.0, min(1.0, local_t / duration))
        d.line((88, 1008, x1, 1008), fill=col(GOLD), width=3)


def stepper(d, names, active):
    f = font(15, "med")
    y = 100
    widths = [tracked_width(name.upper(), f, 1.15) + 26 for name in names]
    gap = 36
    total = sum(widths) + gap * (len(names) - 1)
    x = (W - total) / 2
    for i, name in enumerate(names):
        cur = int(active + 0.001) == i
        done = i < active
        color = GOLD if cur else TEAL if done else DIM
        d.ellipse((x, y + 4, x + 12, y + 16), fill=col(color))
        draw_tracked(d, (x + 20, y), name.upper(), f, col(color), tracking=1.15)
        if i < len(names) - 1:
            lx = x + widths[i] + 4
            d.line((lx, y + 10, lx + gap - 16, y + 10), fill=col(TEAL if done else LINE), width=2)
        x += widths[i] + gap


def headline(d, text, y=168, size=54, width=1600, fill=IVORY):
    f = font(size, "sem")
    return draw_wrapped(d, text, f, col(fill), 160, y, width, gap=6)


def subline(d, text, y, width=1500, size=26, fill=MUTED):
    return draw_wrapped(d, text, font(size), col(fill), 160, y, width, gap=6)


def row_boxes(n, y, h, gap=28, margin=140):
    avail = W - 2 * margin
    cw = (avail - gap * (n - 1)) / n
    boxes = []
    for i in range(n):
        x0 = margin + i * (cw + gap)
        boxes.append((x0, y, x0 + cw, y + h))
    return boxes


def card(d, box, title, body, accent, title_size=22, body_size=20):
    panel(d, box)
    d.rectangle((box[0], box[1], box[0] + 6, box[3]), fill=col(accent))
    x, y = box[0] + 28, box[1] + 22
    d.text((x, y), title, font=font(title_size, "sem"), fill=col(IVORY))
    if body:
        draw_wrapped(d, body, font(body_size), col(MUTED), x, y + title_size + 16, box[2] - x - 24, gap=6)


def mono_chip(d, xy, text, accent=GOLD):
    f = font(20, "mono")
    tw = f.getlength(text)
    x, y = xy
    box = (x, y, x + tw + 28, y + 40)
    panel(d, box, fill=SOFT, outline=accent, radius=8, width=1)
    d.text((x + 14, y + 8), text, font=f, fill=col(accent))
    return box[2]


def tc(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def tc_tenth(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:04.1f}"


# --- cues -------------------------------------------------------------------

SECTIONS = [
    {
        "id": "open",
        "file": "01-open.mp4",
        "kicker": "The failure",
        "record": "Voice only. The picture is the generated open.",
        "steps": [],
        "narration": [
            "A retrieval system can still invent.",
            "It finds nearby text, and then the model writes the answer.",
            "That sentence is a paraphrase.",
            "A figure shifts.",
            "A relation appears that no passage stated.",
            "If a citation is added, it is attached afterwards.",
            "Knowing the model does not remove that step.",
            "The failure is the order of operations.",
        ],
        "picture": [
            "Title lockup, then the line: the model writes the answer.",
            "Three failures arrive with the voice: a figure shifts, a relation appears, a citation is attached afterwards.",
            "The section ends on: the failure is the order of operations.",
        ],
    },
    {
        "id": "rule",
        "file": "02-rule.mp4",
        "kicker": "The rule",
        "record": "Voice only. The picture is the generated rule.",
        "steps": ["Propose", "Check", "Remove"],
        "narration": [
            "Knowledge Store keeps the statement and the source together.",
            "A result is shown only when a passage contains it.",
            "The model proposes.",
            "Code checks that proposal against the text, and against the ontology.",
            "What fails is removed.",
            "If nothing remains, the system says so.",
        ],
        "picture": [
            "The rule, in one line: shown only when a passage contains it.",
            "Three columns land with the voice: Propose, Check, Remove.",
            "The last line adds the decline: if nothing remains, the system says so.",
        ],
    },
    {
        "id": "ingestion",
        "file": "03-ingestion.mp4",
        "kicker": "Ingestion",
        "record": "Voice only. The picture is the generated pipeline.",
        "steps": ["Landing", "Bronze", "Silver", "Ontology", "Extract", "Record"],
        "phases": [
            (0, 1, 0),
            (2, 4, 1),
            (5, 7, 2),
            (8, 16, 3),
            (17, 22, 4),
            (23, 24, 5),
        ],
        "narration": [
            "Documents arrive as documents.",
            "An adapter lists them and fetches the bytes. It does not parse them, and it leaves the upload unchanged.",
            "Ingest stores each distinct file once, under the hash of its bytes.",
            "Two names for the same file are one object, and a version that has not changed is skipped.",
            "That copy is bronze, the immutable source.",
            "Refine writes silver: passages cut on a fixed rule, about eighteen hundred characters.",
            "The identifier is the document hash plus the hash of the passage, so a rerun keeps the same identifiers.",
            "Every fact cites one of those passages. That passage is the unit of evidence.",
            "What the documents are about is a separate ontology.",
            "A core vocabulary, shared by every collection, records only where a fact came from: the document, the passage, and the extraction run.",
            "You bring the domain ontology as Turtle, or the system drafts one once five documents are refined.",
            "It asks for classes, relations, and attributes, and each example has to be copied from a passage.",
            "An example that is not in the text is dropped.",
            "A person edits the draft and publishes it. Published versions are immutable.",
            "A label change does not re-extract.",
            "A new term is extracted only where it is likely to apply.",
            "A change of meaning is a major version, and the documents are extracted again.",
            "Extraction is a tool call whose schema comes from the ontology, so a missing type cannot be recorded.",
            "Each entity, attribute, and relation names its passages.",
            "Code checks shape, domain and range, and grounding: the name and the value occur in the cited passage.",
            "SHACL requires every assertion to cite at least one passage and exactly one run.",
            "After a short repair, what still fails is dropped one item at a time.",
            "A term with no place in the ontology stays a candidate, outside the graph, until a person publishes it.",
            "The record is the RDF for that document at that ontology version.",
            "The graph database, the passage index, and the portal are projections rebuilt from it.",
        ],
        "picture": [
            "Landing: uploads, pages, and an adapter. The bytes are fetched. Nothing is parsed, and nothing uploaded is rewritten.",
            "Bronze: two names, one object, addressed by the sha256 of the bytes. An unchanged version is skipped.",
            "Silver: passages with stable identifiers. About 1,800 characters. The passage is the unit of evidence.",
            "Ontology: the core vocabulary records provenance only. The domain ontology is brought as Turtle, or drafted once five documents are refined. Examples not in the passage are dropped. A person publishes. Patch, minor, and major versions decide whether anything is extracted again.",
            "Extract: a tool call whose schema comes from the ontology. Shape, domain and range, grounding, and SHACL. A short repair, then drop the item. Candidates stay outside the graph.",
            "Record: the RDF is the record. The graph database, the passage index, and the portal are projections.",
        ],
    },
    {
        "id": "chat",
        "file": "04-chat.mp4",
        "kicker": "Chat",
        "record": "Voice only. The picture is the generated chat mechanism.",
        "steps": ["Ontology", "Tools", "Routes", "Scope", "Claims", "Check"],
        "phases": [
            (0, 0, 0),
            (1, 2, 1),
            (3, 4, 2),
            (5, 5, 3),
            (6, 6, 4),
            (7, 10, 5),
        ],
        "narration": [
            "A question comes back under the same rule. The released ontology is in the prompt, so the agent plans in those types, relations, and attributes.",
            "The tools are fixed and read-only: search for an entity, read its facts, walk a neighbourhood, find a path, search passages, read passages.",
            "The model cannot write a query of its own.",
            "A named thing follows the graph. Each fact brings the passage it was extracted from, and that passage is read before the fact is used.",
            "A question that describes a situation searches passages by meaning. One vector is one passage, so the hit leads back to the facts which cite it.",
            "Private sources follow the caller's token. The model cannot widen that.",
            "The agent returns claims: one statement, a passage identifier, and a quote copied from that passage.",
            "Code then reads the passage again. The quote has to be in it. Too short, or not actually there, it fails. A claim with no citation left is removed.",
            "Failed citations are sent back once. A guardrail can also reject a claim that does not follow from its quotes.",
            "The page is built only from what passed.",
            "If nothing passed, the answer declines and names what was missing.",
        ],
        "picture": [
            "The released ontology sits in the prompt. The agent plans in those terms.",
            "Six read-only tools. No query language for the model to write.",
            "Two routes. A named thing follows the graph, and every fact carries passage ids. A described situation searches by meaning: one vector is one passage.",
            "Private sources follow the caller's token.",
            "A claim is a statement, a passage id, and a quote copied from that passage.",
            "Code reads the passage back. The quote must be in it. Too short fails. No citation left, the claim is removed. Failed citations go back once. A guardrail can reject a claim that does not follow from its quotes. Nothing left: the decline.",
        ],
    },
    {
        "id": "lab-answer",
        "file": "05-lab-answer.mp4",
        "kicker": "On the lab",
        "record": "Record this picture on the lab, and record this voice with it. Replace 05-lab-answer.mp4 in the cut.",
        "steps": [],
        "lab": True,
        "shots": [
            "Window wider than 1,100 pixels, so the workbench sits beside the chat.",
            "Ask a question the collection can answer. Do not read the answer out before it arrives.",
            "Leave the workbench visible: a search, a read, then the citation check.",
            "When the answer lands, open source 1. The highlight in the passage is the quote.",
        ],
        "suggestion": "If the space-missions collection is loaded, ask: “What launched Voyager 1, and when?” The source card should highlight words from that document. On another collection, pick a fact you can point at in one passage.",
        "narration": [
            "On the lab, ask a question the collection can answer.",
            "Leave the workbench open.",
            "The steps are the tool calls: a type searched, an entity read, then the citation check.",
            "The answer that lands is a set of statements.",
            "Each one carries a number.",
            "Open the number.",
            "That is the passage, and the words highlighted in it are the quote taken from it.",
            "It is the same identifier that was written when the document was extracted.",
            "The source was required when the claim was made, and the page kept only the ones that matched.",
        ],
        "picture": [
            "This slot is a caption guide. Replace it with the portal recording.",
            "The on-screen sentence follows the voice, so the slot can be watched before the lab picture exists.",
        ],
    },
    {
        "id": "lab-decline",
        "file": "06-lab-decline.mp4",
        "kicker": "The decline",
        "record": "Record this picture on the lab, and record this voice with it. Replace 06-lab-decline.mp4 in the cut.",
        "steps": [],
        "lab": True,
        "shots": [
            "Ask something the documents do not contain. Let the answer finish.",
            "Show the decline, and the list under “What the sources don't cover”.",
            "Do not rephrase until the model guesses. The decline is the result.",
        ],
        "suggestion": "If the space-missions collection is loaded, ask: “Who is the current project manager for Voyager 1?” That is not in the documents. The line on screen should be: I can't answer that from the sources in this collection.",
        "narration": [
            "Now ask something the sources do not contain.",
            "The result on screen is a decline.",
            "It names what is missing.",
            "There is no unchecked sentence beside it.",
            "The passages do not move, and the ontology is versioned, so the same question meets the same record.",
            "What reaches a person has already been tied to a passage.",
            "A result that cannot be tied to one is not shown.",
        ],
        "picture": [
            "This slot is a caption guide. Replace it with the decline on the portal.",
        ],
    },
]


def prepare(section):
    t = HEAD
    spans = []
    for sentence in section["narration"]:
        dur = max(MIN_SENT, len(sentence.split()) * WORD_SEC + PAUSE)
        spans.append((t, t + dur, sentence))
        t += dur
    section["spans"] = spans
    section["duration"] = t + TAIL
    return section["duration"]


def active_index(section, t):
    if t < HEAD:
        return -1, 0.0
    for i, (a, b, _) in enumerate(section["spans"]):
        if a <= t < b:
            return i, (t - a) / max(0.001, b - a)
    return len(section["spans"]) - 1, 1.0


def phase_index(section, sent_i):
    phases = section.get("phases") or []
    if sent_i < 0:
        return 0
    for a, b, p in phases:
        if a <= sent_i <= b:
            return p
    return phases[-1][2] if phases else 0


# --- frames -----------------------------------------------------------------

def base_frame(bg):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return overlay, ImageDraw.Draw(overlay)


def finish(bg, overlay):
    return Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")


def draw_open_clean(d, section, t, sent_i):
    """Open, drawn in order so early frames stay quiet."""
    if sent_i < 0:
        d.text((160, 420), "A result has to name its source.", font=font(48, "sem"), fill=col(IVORY))
        return
    headline(d, "The model writes the answer." if sent_i < 6 else "The failure is the order of operations.",
             y=190, size=58, fill=GOLD if sent_i >= 6 else IVORY)
    if sent_i < 2:
        subline(d, "It finds nearby text, and then the model writes the answer.", y=290)
    elif sent_i < 6:
        subline(d, "That sentence is a paraphrase.", y=290)
    else:
        subline(d, "Knowing the model does not remove that step.", y=290)
    items = [
        (3, "01", "A figure shifts", "A number or a date moves off the words in the passage."),
        (4, "02", "A relation appears", "The sentence joins two things no passage joined."),
        (5, "03", "A citation, afterwards", "The source is chosen once the sentence already exists."),
    ]
    boxes = row_boxes(3, 460, 280)
    for i, (need, num, title, body) in enumerate(items):
        if sent_i >= need:
            card(d, boxes[i], f"{num}     {title}", body, CORAL, 26, 22)


def draw_rule(d, section, t, sent_i):
    if sent_i < 0:
        headline(d, "Shown only when a passage contains it.", y=360, size=52)
        return
    headline(d, "Shown only when a passage contains it.", y=180, size=46)
    cols = [
        (2, "Propose", "The model names entities, facts, and claims.", GOLD),
        (3, "Check", "Code tests them against the passage and the ontology.", TEAL),
        (4, "Remove", "What the passage does not contain is dropped.", CORAL),
    ]
    boxes = row_boxes(3, 380, 340)
    for i, (need, title, body, accent) in enumerate(cols):
        if sent_i >= need:
            panel(d, boxes[i])
            d.rectangle((boxes[i][0], boxes[i][1], boxes[i][0] + 6, boxes[i][3]), fill=col(accent))
            d.text((boxes[i][0] + 32, boxes[i][1] + 36), f"0{i + 1}", font=font(20, "mono"), fill=col(accent))
            d.text((boxes[i][0] + 32, boxes[i][1] + 90), title, font=font(40, "sem"), fill=col(IVORY))
            draw_wrapped(d, body, font(22), col(MUTED), boxes[i][0] + 32, boxes[i][1] + 170, boxes[i][2] - boxes[i][0] - 64, gap=6)
    if sent_i >= 5:
        d.text((160, 780), "If nothing remains, the system says so.", font=font(32, "sem"), fill=col(GOLD))


def _phase_title(d, text, y=176):
    d.text((140, y), text, font=font(36, "sem"), fill=col(IVORY))


def draw_landing(d, sent_i):
    _phase_title(d, "Documents arrive unchanged.")
    items = [
        ("Upload", "A file in the landing folder."),
        ("Web page", "An address the adapter is allowed to fetch."),
        ("Your adapter", "Anything that can list items and return bytes."),
    ]
    boxes = row_boxes(3, 280, 220, margin=140)
    for box, (title, body) in zip(boxes, items):
        card(d, box, title, body, BLUE, 28, 22)
    panel(d, (140, 560, 1780, 760), fill=SOFT, outline=LINE)
    d.text((180, 600), "The adapter lists and fetches.", font=font(28, "sem"), fill=col(IVORY))
    d.text((180, 656), "It does not parse. What was uploaded is left as it arrived.", font=font(24), fill=col(MUTED))


def draw_bronze(d, sent_i):
    sent_i = 99
    _phase_title(d, "One object for one set of bytes.")
    # two names
    d.text((160, 280), "report.pdf", font=font(26, "med"), fill=col(MUTED))
    d.text((160, 340), "copies / report.pdf", font=font(26, "med"), fill=col(MUTED))
    d.line((520, 300, 700, 420), fill=col(BRONZE), width=2)
    d.line((520, 360, 700, 450), fill=col(BRONZE), width=2)
    panel(d, (720, 300, 1760, 560), outline=BRONZE)
    d.text((760, 330), "BRONZE", font=font(16, "med"), fill=col(BRONZE))
    d.text((760, 370), "sha256 of the bytes", font=font(28, "sem"), fill=col(IVORY))
    d.text((760, 440), "9f2c1ab0 … e41d", font=font(28, "mono"), fill=col(GOLD))
    notes = []
    if sent_i >= 4:
        notes.append("The same file under two names is one object.")
    if sent_i >= 5:
        notes.append("A version that has not changed is skipped, and not read again.")
    if sent_i >= 6:
        notes.append("This copy is the immutable source.")
    y = 620
    for note in notes:
        d.text((160, y), note, font=font(26), fill=col(MUTED))
        y += 48


def draw_silver(d, sent_i):
    sent_i = 99
    _phase_title(d, "The passage is the unit of evidence.")
    panel(d, (140, 270, 560, 860))
    d.text((172, 300), "SILVER", font=font(16, "med"), fill=col(SILVER))
    d.text((172, 340), "Parsed text", font=font(28, "sem"), fill=col(IVORY))
    d.text((172, 410), "Cut on a fixed rule.", font=font(22), fill=col(MUTED))
    d.text((172, 460), "About 1,800 characters.", font=font(22), fill=col(MUTED))
    rows = [
        ("01", "9f2c… / a91e…"),
        ("02", "9f2c… / b33c…"),
        ("03", "9f2c… / c70a…"),
    ]
    for i, (seq, pid) in enumerate(rows):
        y = 280 + i * 160
        panel(d, (620, y, 1760, y + 130), outline=TEAL if sent_i >= 9 else LINE)
        d.text((660, y + 28), seq, font=font(22, "mono"), fill=col(TEAL))
        d.text((760, y + 28), pid, font=font(22, "mono"), fill=col(GOLD))
        d.text((660, y + 74), "passage text, kept verbatim for citation", font=font(20), fill=col(MUTED))
    if sent_i >= 9:
        d.text((620, 790), "Identifier = document hash + hash of the passage text.", font=font(22), fill=col(IVORY))
    if sent_i >= 11:
        d.text((620, 834), "Every later fact cites one of these passages.", font=font(22), fill=col(MUTED))


def draw_ontology(d, sent_i):
    sent_i = 99
    _phase_title(d, "What it is about, and where it came from.")
    panel(d, (140, 250, 820, 560))
    d.text((172, 274), "CORE VOCABULARY", font=font(16, "med"), fill=col(GOLD))
    d.text((172, 312), "Shared by every collection.", font=font(24, "sem"), fill=col(IVORY))
    for i, line in enumerate(["ks:Document", "ks:Passage", "ks:Assertion"]):
        d.text((172, 370 + i * 40), line, font=font(22, "mono"), fill=col(TEAL))
    if sent_i >= 13:
        d.text((172, 500), "Where a fact came from.", font=font(20), fill=col(MUTED))
    panel(d, (860, 250, 1780, 560))
    d.text((892, 274), "DOMAIN ONTOLOGY", font=font(16, "med"), fill=col(BLUE))
    if sent_i >= 14:
        d.text((892, 316), "Bring it as Turtle, or draft it.", font=font(24, "sem"), fill=col(IVORY))
        d.text((892, 358), "A draft waits for five refined documents.", font=font(20), fill=col(MUTED))
    steps = []
    if sent_i >= 15:
        steps.append("Examples copied from the passage")
    if sent_i >= 16:
        steps.append("An example not in the text is dropped")
    if sent_i >= 17:
        steps.append("A person edits the draft and publishes it")
    for i, step in enumerate(steps):
        d.text((892, 410 + i * 36), step, font=font(20), fill=col(IVORY))
    if sent_i >= 18:
        d.text((160, 590), "A published version is immutable.", font=font(22, "sem"), fill=col(GOLD))
    if sent_i >= 19:
        boxes = row_boxes(3, 660, 250, margin=140)
        versions = [
            (19, "Patch", "A label change. Nothing is extracted again.", GOLD),
            (20, "Minor", "A new term, extracted only where it is likely to apply.", TEAL),
            (21, "Major", "The meaning changed. The documents are extracted again.", CORAL),
        ]
        for box, (need, title, body, accent) in zip(boxes, versions):
            if sent_i >= need:
                card(d, box, title, body, accent, 24, 20)


def draw_extract(d, sent_i):
    sent_i = 99
    _phase_title(d, "The model proposes. Code keeps what passes.")
    panel(d, (140, 260, 780, 520), outline=GOLD)
    d.text((172, 292), "TOOL CALL", font=font(16, "med"), fill=col(GOLD))
    d.text((172, 340), "Schema from the ontology.", font=font(28, "sem"), fill=col(IVORY))
    if sent_i >= 23:
        d.text((172, 410), "A type the ontology does not have", font=font(22), fill=col(MUTED))
        d.text((172, 448), "cannot be recorded.", font=font(22), fill=col(MUTED))
    checks = [
        (25, "Shape", "The fields the schema requires."),
        (25, "Domain and range", "The types the ontology allows."),
        (25, "Grounding", "The name and the value are in the passage."),
        (26, "SHACL", "At least one passage, and exactly one run."),
    ]
    y = 260
    for need, title, body in checks:
        if sent_i >= need:
            d.ellipse((830, y + 8, 846, y + 24), fill=col(TEAL))
            d.text((866, y), title, font=font(22, "sem"), fill=col(IVORY))
            d.text((1100, y), body, font=font(20), fill=col(MUTED))
            y += 56
    outcomes = []
    if sent_i >= 27:
        outcomes.append((TEAL, "Kept", "A short repair first. What passes stays."))
    if sent_i >= 28:
        outcomes.append((CORAL, "Dropped", "One item at a time. The rest of the document stays."))
    if sent_i >= 29:
        outcomes.append((DIM, "Candidate", "Outside the graph, until a person publishes a version that contains it."))
    y = 640
    for accent, title, body in outcomes:
        d.rectangle((160, y, 172, y + 64), fill=col(accent))
        d.text((196, y), title, font=font(22, "sem"), fill=col(accent))
        d.text((420, y + 2), body, font=font(20), fill=col(MUTED))
        y += 80


def draw_record(d, sent_i):
    _phase_title(d, "The RDF is the record.")
    panel(d, (140, 280, 1780, 560), outline=GOLD, width=2)
    d.text((180, 320), "GOLD", font=font(16, "med"), fill=col(GOLD))
    d.text((180, 364), "RDF for this document, at this ontology version.", font=font(32, "sem"), fill=col(IVORY))
    d.text((180, 440), "Every assertion cites the passage it was stated in, and the run that extracted it.", font=font(22), fill=col(MUTED))
    boxes = row_boxes(3, 640, 220, margin=140)
    for box, (title, body) in zip(boxes, [
        ("Graph database", "A projection of the RDF."),
        ("Passage index", "One vector per passage. A hit is a passage id."),
        ("Portal", "The chat, the sources, the workbench. Rebuilt from the record."),
    ]):
        card(d, box, title, body, GOLD, 24, 20)


def draw_ingestion(d, section, t, sent_i):
    p = phase_index(section, max(sent_i, 0))
    stepper(d, section["steps"], p if sent_i >= 0 else -1)
    drawers = [draw_landing, draw_bronze, draw_silver, draw_ontology, draw_extract, draw_record]
    if sent_i < 0:
        _phase_title(d, "From documents to a record.", y=420)
        return
    drawers[p](d, sent_i)


def draw_chat_ontology(d, sent_i):
    _phase_title(d, "The ontology is in the prompt.")
    panel(d, (140, 280, 1780, 700), outline=GOLD)
    d.text((180, 320), "SYSTEM PROMPT", font=font(16, "med"), fill=col(GOLD))
    d.text((180, 380), "Plan every query in the released types,", font=font(32, "sem"), fill=col(IVORY))
    d.text((180, 432), "relations, and attributes.", font=font(32, "sem"), fill=col(IVORY))
    d.text((180, 530), "The agent reads the ontology before it searches.", font=font(24), fill=col(MUTED))


def draw_chat_tools(d, sent_i):
    sent_i = 99
    _phase_title(d, "Fixed tools. Read-only.")
    names = [
        ("Search entities", "By name, and by type."),
        ("Read an entity", "Facts, each with its passage ids."),
        ("Neighbourhood", "What is one to three relations away."),
        ("Paths", "The shortest chains between two entities."),
        ("Search passages", "By what the text says."),
        ("Read passages", "The full text, before a citation."),
    ]
    boxes = []
    for r in range(2):
        boxes += row_boxes(3, 270 + r * 200, 170, margin=140)
    for i, (box, (title, body)) in enumerate(zip(boxes, names)):
        show = sent_i >= 4 or (sent_i >= 3 and i < 4)
        if show:
            card(d, box, title, body, TEAL if i < 4 else BLUE, 22, 18)
    if sent_i >= 5:
        d.text((160, 700), "There is no query language for the model to write.", font=font(26, "sem"), fill=col(GOLD))


def draw_chat_routes(d, sent_i):
    sent_i = 99
    _phase_title(d, "Two ways in. Both end at a passage.")
    boxes = row_boxes(2, 270, 520, gap=40, margin=140)
    left, right = boxes
    panel(d, left, outline=TEAL)
    d.text((left[0] + 32, left[1] + 28), "THE QUESTION NAMES SOMETHING", font=font(16, "med"), fill=col(TEAL))
    lines = ["Follow the graph."]
    if sent_i >= 7:
        lines.append("Each fact returns the passage it was extracted from.")
        lines.append("Read that passage before using the fact.")
    for i, line in enumerate(lines):
        d.text((left[0] + 32, left[1] + 100 + i * 56), line, font=font(24), fill=col(IVORY))
    panel(d, right, outline=BLUE)
    d.text((right[0] + 32, right[1] + 28), "THE QUESTION DESCRIBES A SITUATION", font=font(16, "med"), fill=col(BLUE))
    lines = ["Search passages by meaning."]
    if sent_i >= 9:
        lines.append("One vector is one passage. A hit is an identifier.")
        lines.append("That identifier leads back to the facts which cite it.")
    for i, line in enumerate(lines):
        draw_wrapped(d, line, font(24), col(IVORY), right[0] + 32, right[1] + 100 + i * 80, right[2] - right[0] - 64, gap=4)


def draw_chat_scope(d, sent_i):
    sent_i = 99
    _phase_title(d, "Scope comes from the caller.")
    panel(d, (140, 300, 1780, 680), outline=GOLD)
    d.text((180, 360), "The caller's token", font=font(40, "sem"), fill=col(IVORY))
    d.text((180, 450), "decides who may read a private source.", font=font(28), fill=col(MUTED))
    if sent_i >= 11:
        d.text((180, 540), "The model cannot widen that.", font=font(28, "sem"), fill=col(GOLD))


def draw_chat_claims(d, sent_i):
    sent_i = 99
    _phase_title(d, "A claim is three parts.")
    rows = [
        (0, "A statement", "One sentence that answers part of the question.", IVORY),
        (0, "A passage id", "An identifier of a passage read in this conversation.", GOLD),
        (0, "A quote", "Words copied from that passage.", TEAL),
    ]
    y = 270
    for need, title, body, accent in rows:
        if sent_i >= need:
            panel(d, (160, y, 1760, y + 110), outline=accent, width=2)
            d.text((200, y + 22), title, font=font(22, "sem"), fill=col(accent))
            d.text((520, y + 24), body, font=font(22), fill=col(MUTED))
            y += 130


def draw_chat_check(d, sent_i):
    sent_i = 99
    _phase_title(d, "Code reads the passage again.")
    checks = [
        (15, "The quote is in the passage."),
        (16, "Too short, or not actually there: it fails."),
        (17, "No citation left: the claim is removed."),
        (18, "Failed citations are sent back once."),
        (19, "A guardrail can reject a claim that does not follow from its quotes."),
        (20, "The page is built only from what passed."),
    ]
    y = 250
    for need, text in checks:
        if sent_i >= need:
            d.ellipse((160, y + 10, 176, y + 26), fill=col(TEAL if need < 25 else GOLD))
            draw_wrapped(d, text, font(26), col(IVORY), 200, y, 1500, gap=4)
            y += 70
    if sent_i >= 21:
        panel(d, (140, 760, 1780, 940), outline=CORAL, width=2)
        d.text((180, 800), "If nothing passed", font=font(18, "med"), fill=col(CORAL))
        d.text((180, 844), "I can't answer that from the sources in this collection.", font=font(28, "sem"), fill=col(IVORY))


def draw_chat(d, section, t, sent_i):
    p = phase_index(section, max(sent_i, 0))
    stepper(d, section["steps"], p if sent_i >= 0 else -1)
    drawers = [draw_chat_ontology, draw_chat_tools, draw_chat_routes, draw_chat_scope, draw_chat_claims, draw_chat_check]
    if sent_i < 0:
        _phase_title(d, "The same rule, from the question back.", y=420)
        return
    drawers[p](d, sent_i)


def draw_lab(d, section, t, sent_i):
    # badge
    f = font(14, "med")
    badge = "REPLACE WITH LAB PICTURE"
    tw = tracked_width(badge, f, 1.4)
    panel(d, (W - 120 - tw - 28, 96, W - 100, 136), fill=SOFT, outline=GOLD, radius=8, width=1)
    draw_tracked(d, (W - 112 - tw - 8, 104), badge, f, col(GOLD), tracking=1.4)
    if sent_i < 0:
        headline(d, section["kicker"], y=240, size=56)
        subline(d, "Record the portal. The voice for this slot is below, timed.", y=340)
    else:
        sentence = section["spans"][sent_i][2]
        # previous, dim
        if sent_i > 0:
            prev = section["spans"][sent_i - 1][2]
            draw_wrapped(d, prev, font(24), col(DIM), 140, 200, 1500, gap=6)
        draw_wrapped(d, sentence, font(40, "sem"), col(IVORY), 140, 300, 1500, gap=8)
    y = 640
    d.text((140, y), "SHOOT", font=font(14, "med"), fill=col(GOLD))
    y += 36
    for shot in section["shots"]:
        h = draw_wrapped(d, shot, font(20), col(MUTED), 140, y, 1600, gap=4)
        y += h + 8


DRAW = {
    "open": draw_open_clean,
    "rule": draw_rule,
    "ingestion": draw_ingestion,
    "chat": draw_chat,
    "lab-answer": draw_lab,
    "lab-decline": draw_lab,
}


def render_frame(bg, section, t, index, n, offset):
    overlay, d = base_frame(bg)
    chrome(d, section["kicker"])
    sent_i, _ = active_index(section, t)
    DRAW[section["id"]](d, section, t, sent_i)
    footer(d, index, n, offset + t, t, section["duration"])
    return finish(bg, overlay)


def encode(path: Path, section, bg, index, n, offset):
    path.parent.mkdir(parents=True, exist_ok=True)
    nframes = int(round(section["duration"] * FPS))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "32k",
        "-movflags", "+faststart",
        str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    last_key = None
    last_bytes = b""
    try:
        for i in range(nframes):
            t = i / FPS
            sent_i, _frac = active_index(section, t)
            # The picture holds within a sentence. Timecode and the progress
            # hairline move once a second, so those frames are redrawn.
            key = (sent_i, int(offset + t))
            if key != last_key:
                last_bytes = render_frame(bg, section, t, index, n, offset).tobytes()
                last_key = key
            proc.stdin.write(last_bytes)
            if i % (FPS * 5) == 0:
                print(f"  {section['id']} {t:6.1f}s / {section['duration']:.1f}s", flush=True)
    finally:
        proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise SystemExit(f"ffmpeg failed for {path} ({code})")
    print(f"wrote {path}")


def load_bg():
    im = Image.open(BG_PATH).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    veil = Image.new("RGB", (W, H), BG)
    return Image.blend(veil, im, 0.42)


def write_docs(offsets):
    script = ["# Knowledge Store — five-minute briefing", "",
              "Picture and voice for one cut of about five minutes. The generated picture covers the failure, the rule, the ingestion pipeline, and the chat check. Two slots are left for a recording of the portal on the lab.",
              "",
              "The voice is not in the picture files. Record it from [voice-script.md](voice-script.md). Speak at about 160 words a minute, with a short breath at each sentence. The cues are timed to that pace.",
              "",
              "Assembly timecode is burned into the bottom right of every frame. A gold hairline along the footer shows progress through the current section.",
              "",
              "## Timeline", "",
              "| In | Out | Section | Picture | You record |",
              "|---|---|---|---|---|"]
    voice = ["# Voice script", "",
             "Record each section as its own take. The picture files have no narration.",
             "",
             "Pace is about 160 words a minute. Each line is one sentence. Start the line at the cue. If you finish a line early, wait for the next cue rather than rushing the next sentence.",
             "",
             "Say sha-256 as “sha two fifty-six”. Say SHACL as “shackle”. Say RDF as “R D F”. Say Turtle as the word for the format. Say the layer names bronze, silver, and gold as the metals: they are the names in the system, and the picture says what each one holds.",
             "",
             "Leave the room tone at the start of each file for the half-second before the first cue.",
             ""]
    cursor = 0.0
    n = len(SECTIONS)
    for i, section in enumerate(SECTIONS, start=1):
        dur = section["duration"]
        start, end = cursor, cursor + dur
        script.append(f"| {tc(start)} | {tc(end)} | {section['kicker']} | `{section['file']}` | {section['record']} |")
        cursor = end
    script += ["", f"Total picture: {tc(cursor)} ({cursor:.1f} seconds).", ""]
    cursor = 0.0
    for i, section in enumerate(SECTIONS, start=1):
        start = cursor
        script += [f"## {i}. {section['kicker']}", "",
                   f"Picture `{section['file']}`, from {tc(start)} to {tc(start + section['duration'])}.",
                   "",
                   section["record"],
                   "",
                   "### Picture", ""]
        for line in section["picture"]:
            script.append(f"- {line}")
        script.append("")
        if section.get("shots"):
            script += ["", "### Lab shots", ""]
            for shot in section["shots"]:
                script.append(f"- {shot}")
            script += ["", section["suggestion"], ""]
        script += ["### Voice", ""]
        for a, b, sentence in section["spans"]:
            script.append(f"- `{tc_tenth(start + a)}` {sentence}")
        script.append("")
        voice += [f"## {i}. {section['kicker']}", "",
                  f"File: `{section['file']}`",
                  f"Assembly: {tc(start)} to {tc(start + section['duration'])}.",
                  "",
                  section["record"],
                  ""]
        if section.get("suggestion"):
            voice += ["Director, not spoken:", "", section["suggestion"], ""]
            voice.append("Shots, while this voice plays:")
            voice.append("")
            for shot in section["shots"]:
                voice.append(f"- {shot}")
            voice.append("")
        voice.append("Read:")
        voice.append("")
        for a, b, sentence in section["spans"]:
            voice.append(f"`{tc_tenth(a)}` {sentence}")
            voice.append("")
        cursor = start + section["duration"]
    (ROOT / "script.md").write_text("\n".join(script) + "\n", encoding="utf-8")
    (ROOT / "voice-script.md").write_text("\n".join(voice) + "\n", encoding="utf-8")
    print(f"total {cursor:.1f}s")
    print(f"wrote {ROOT / 'script.md'}")
    print(f"wrote {ROOT / 'voice-script.md'}")


def stills(bg, offsets):
    dest = OUT / "stills"
    dest.mkdir(parents=True, exist_ok=True)
    n = len(SECTIONS)
    cursor = 0.0
    for i, section in enumerate(SECTIONS, start=1):
        # head, a mid sentence, and the last sentence
        times = [0.2]
        phases = section.get("phases") or []
        if phases:
            for a, b, _p in phases:
                times.append(section["spans"][b][0] + 0.25)
        elif section["spans"]:
            times.append(section["spans"][min(2, len(section["spans"]) - 1)][0] + 0.2)
            times.append(section["spans"][-1][0] + 0.3)
        for t in times:
            frame = render_frame(bg, section, t, i, n, cursor)
            name = dest / f"{section['id']}-{t:.1f}.png"
            frame.save(name)
            print("still", name)
        cursor += section["duration"]


def concat(paths, dest: Path):
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in paths), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dest)]
    subprocess.check_call(cmd)
    print("wrote", dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", action="store_true")
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--section", action="append", default=[])
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()
    offsets = []
    cursor = 0.0
    for section in SECTIONS:
        offsets.append(cursor)
        cursor += prepare(section)
    write_docs(offsets)
    docs_only = args.docs and not args.stills and not args.section
    if docs_only or args.no_video:
        return
    bg = load_bg()
    if args.stills:
        stills(bg, offsets)
        return
    wanted = set(args.section) or {s["id"] for s in SECTIONS}
    n = len(SECTIONS)
    paths = []
    for i, section in enumerate(SECTIONS, start=1):
        path = OUT / section["file"]
        paths.append(path)
        if section["id"] not in wanted:
            continue
        encode(path, section, bg, i, n, offsets[i - 1])
    if not args.section:
        concat(paths, OUT / "assembly.mp4")


if __name__ == "__main__":
    main()
