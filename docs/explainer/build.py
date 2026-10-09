"""Conceptual briefing pictures for the Knowledge Store.

Six clips, picture only. Two voice scripts are written from the same scenes:
voice-pro.md for a professional narrator, voice-record.md to read yourself.
Each script is continuous prose for the clip, not a line-by-line cue sheet.

  python docs/explainer/build.py --docs
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
# Measured technical-video pace. Clip length follows the longer of the two reads.
WPS = 2.45
HEAD = 0.8
TAIL = 1.1

BG = (12, 16, 28)
IVORY = (243, 240, 232)
MUTED = (186, 196, 208)
DIM = (140, 152, 168)
GOLD = (224, 177, 90)
TEAL = (78, 214, 162)
CORAL = (232, 118, 104)
BLUE = (148, 180, 255)
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
    draw_tracked(d, (64, 36), "KNOWLEDGE STORE", f, col(GOLD), tracking=2.2)
    label = kicker.upper()
    tw = tracked_width(label, f, 1.6)
    draw_tracked(d, (W - 64 - tw, 36), label, f, col(DIM), tracking=1.6)
    d.line((64, 72, W - 64, 72), fill=col(LINE), width=1)


def footer(d, index, n, global_t, local_t, duration):
    d.line((64, 1020, W - 64, 1020), fill=col(LINE), width=1)
    f = font(15, "med")
    draw_tracked(d, (64, 1036), f"{index:02d}   /   {n:02d}", f, col(DIM), tracking=1.2)
    stamp = f"{int(global_t) // 60}:{int(global_t) % 60:02d}"
    sf = font(16, "mono")
    d.text((W - 64 - sf.getlength(stamp), 1032), stamp, font=sf, fill=col(DIM))
    if duration > 0:
        x1 = 64 + (W - 128) * max(0.0, min(1.0, local_t / duration))
        d.line((64, 1016, x1, 1016), fill=col(GOLD), width=3)


def title(d, text, y=96):
    d.text((64, y), text, font=font(42, "sem"), fill=col(IVORY))


def row_boxes(n, y, h, gap=24, margin=64):
    avail = W - 2 * margin
    cw = (avail - gap * (n - 1)) / n
    out = []
    for i in range(n):
        x0 = margin + i * (cw + gap)
        out.append((x0, y, x0 + cw, y + h))
    return out


def card(d, box, kicker, heading, body, accent):
    panel(d, box, outline=accent, width=2)
    x, y = box[0] + 28, box[1] + 24
    d.text((x, y), kicker, font=font(15, "med"), fill=col(accent))
    d.text((x, y + 36), heading, font=font(28, "sem"), fill=col(IVORY))
    if body:
        draw_wrapped(d, body, font(22), col(MUTED), x, y + 86, box[2] - x - 28, gap=6)


def band(d, y, h, num, heading, body, accent):
    panel(d, (64, y, W - 64, y + h), outline=LINE, width=2)
    d.rectangle((64, y, 72, y + h), fill=col(accent))
    d.text((96, y + 22), num, font=font(18, "mono"), fill=col(accent))
    d.text((168, y + 16), heading, font=font(26, "sem"), fill=col(IVORY))
    draw_wrapped(d, body, font(20), col(MUTED), 168, y + 56, W - 64 - 196, gap=4)


def tc(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def words(paragraphs: list[str]) -> int:
    return sum(len(p.split()) for p in paragraphs)


SECTIONS = [
    {
        "id": "usual",
        "file": "01-usual-path.mp4",
        "kicker": "The usual path",
        "picture": [
            "A wide path: documents, chunks stored as vectors, the agent writes, a citation attached afterwards.",
            "The lower line: enough when the words match; unreliable when the answer is a relationship, a type, or a fact in different words.",
        ],
        "pro": [
            "An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors, so that a question can retrieve the pieces nearest to it in meaning. The agent reads what came back and writes the answer.",
            "That is enough when the question and the source use the same words. It becomes unreliable when the answer depends on a relationship, on what kind of thing something is, or on a fact that was written in different words somewhere else. The model supplies what the chunks did not. The sentence sounds complete. A citation, when there is one, is attached after the sentence has already been written.",
        ],
        "record": [
            "An agent that answers from your own documents usually works like this. The documents are cut into chunks and stored as vectors, so a question can pull back the pieces nearest to it in meaning. The agent reads what came back and writes the answer.",
            "That is enough when the question and the source use the same words. It gets unreliable when the answer depends on a relationship, on what kind of thing something is, or on a fact written in different words somewhere else. The model fills in what the chunks did not say. The sentence sounds finished. If there is a citation, it is attached after the sentence already exists.",
        ],
    },
    {
        "id": "graph",
        "file": "02-ontology-and-graph.mp4",
        "kicker": "Ontology and graph",
        "picture": [
            "Left: an ontology as a shared vocabulary, with three ordinary examples.",
            "Right: a knowledge graph of typed facts, each one able to point at the passage it came from.",
        ],
        "pro": [
            "An ontology is the shared vocabulary for a body of knowledge. It names the kinds of things that matter in that domain, and the relationships that are allowed between them. A contract has parties. A person reports to a role. A case has a client.",
            "A knowledge graph is the facts, written in that vocabulary. Each fact is a small typed statement, and each one can point back to the passage of text it came from. An agent that can see the ontology no longer has to guess which words to search for. It can ask what is connected to what, and of what kind.",
        ],
        "record": [
            "An ontology is a shared vocabulary for a body of knowledge. It names the kinds of things that matter, and the relationships that are allowed between them. A contract has parties. A person reports to a role. A case has a client.",
            "A knowledge graph is those facts, written in that vocabulary. Each fact is a small typed statement, and each one can point back to the passage it came from. An agent that can see the ontology does not have to guess which words to search for. It can ask what is connected to what, and of what kind.",
        ],
    },
    {
        "id": "together",
        "file": "03-graph-and-vectors.mp4",
        "kicker": "Graph and vectors",
        "picture": [
            "Two full columns. A question that names something follows the graph. A question that describes a situation is found by meaning.",
            "Both end at a passage. The graph holds structure. The vectors hold wording the question never used.",
        ],
        "pro": [
            "The graph is the right instrument when a question names things. Many questions do not. They describe a situation, and they share no wording with the page that answers them. Vector search finds that page by meaning.",
            "Used on its own, vector search hands the model a passage and leaves the model to write. Used with the graph, the two stay joined. A search by meaning returns a passage. The facts in the graph cite passages. A hit among the vectors is a way back to the structured facts, and a fact in the graph is a way back to the words. The graph holds the structure. The vectors hold the wording the question never used.",
        ],
        "record": [
            "The graph is what you want when a question names things. Many questions do not. They describe a situation, and they share no words with the page that answers them. Vector search finds that page by meaning.",
            "On its own, vector search hands the model a passage and leaves the model to write. With the graph, the two stay joined. A search by meaning returns a passage. The facts in the graph cite passages. So a hit in the vectors leads back to the structured facts, and a fact in the graph leads back to the words. The graph holds the structure. The vectors hold the wording the question never used.",
        ],
    },
    {
        "id": "improves",
        "file": "04-what-improves.mp4",
        "kicker": "What improves",
        "picture": [
            "Three full-width bands: consistency from the shared vocabulary, accuracy from the tie to a passage, and a decline when nothing remains.",
        ],
        "pro": [
            "Two things improve, and they improve for different reasons. Consistency comes from the ontology. The same types and the same relationships are used when facts are taken from the documents and when a question is asked, so two questions about the same thing follow the same paths.",
            "Accuracy comes from the tie to a source. The model may propose a statement. A person sees that statement only when a passage actually contains it. A statement that cannot be tied to a source is removed. When nothing remains, the agent says that the sources do not answer. The citation is the condition for the sentence being shown.",
        ],
        "record": [
            "Two things get better, and they get better for different reasons. Consistency comes from the ontology. The same types and the same relationships are used when facts are taken from the documents and when a question is asked, so two questions about the same thing follow the same paths.",
            "Accuracy comes from the tie to a source. The model can propose a statement. You see that statement only when a passage actually contains it. A statement that cannot be tied to a source is removed. When nothing is left, the agent says the sources do not answer. The citation is the condition for showing the sentence.",
        ],
    },
    {
        "id": "ingestion",
        "file": "05-on-the-way-in.mp4",
        "kicker": "On the way in",
        "picture": [
            "The lab, conceptually, on the way in: documents kept as they arrived, passages a fact can cite, an ontology you bring or draft and publish, extraction that keeps a fact only when the passage contains it, then the graph and one vector per passage.",
        ],
        "pro": [
            "The knowledge store is one implementation of that idea. On the way in, documents are kept as they arrived. They are divided into passages: stable pieces of text, small enough to cite, and stable enough that the same document produces the same passages again.",
            "An ontology defines the types for that collection. You can bring the ontology with you, or the lab can draft one from the documents for a person to review and publish. Extraction reads each document into those types. A proposed fact has to be present in the passage it cites. Something the ontology has no place for stays out of the graph until a person publishes a version that includes it. From that record the lab builds the two stores the agent will use: the knowledge graph, and a vector index with one vector for each passage.",
        ],
        "record": [
            "This lab is one way of doing that. On the way in, documents are kept as they arrived. They are divided into passages: pieces of text small enough to cite, and stable enough that the same document gives the same passages again.",
            "An ontology defines the types for the collection. You can bring that ontology, or the lab can draft one from the documents and leave it for a person to review and publish. Extraction reads each document into those types. A proposed fact has to appear in the passage it cites. If the ontology has no place for a term, that term stays out of the graph until someone publishes a version that includes it. From that record the lab builds the two stores the agent uses: the knowledge graph, and a vector index with one vector for each passage.",
        ],
    },
    {
        "id": "questions",
        "file": "06-when-someone-asks.mp4",
        "kicker": "When someone asks",
        "picture": [
            "The same ontology plans the question. A named thing follows the graph. A described situation searches by meaning. Both return statements tied to passages.",
            "Two Holmes examples, as concepts: Roylott is answered from the passage that names the swamp adder. Holmes's mother is a decline, because the stories do not say.",
        ],
        "pro": [
            "When a person asks a question, the agent is given that same ontology, and it plans in the collection's own types. A question that names something follows the graph. A question that describes a situation searches the passages by meaning, and returns to the facts that cite what it found. The agent answers in statements. Each statement is tied to a passage. The page is built only from the statements that hold.",
            "In the Sherlock Holmes stories this lab can be loaded with, a question about what killed Dr Grimesby Roylott can be answered from the passage that names the swamp adder. A question about the name of Sherlock Holmes's mother cannot. The stories do not say, and the result is a decline. Ingestion and questions are the same rule, run in opposite directions. A fact enters only when a passage supports it. An answer leaves only when a passage supports it.",
        ],
        "record": [
            "When someone asks a question, the agent is given that same ontology, and it plans in the collection's own types. If the question names something, it follows the graph. If the question describes a situation, it searches the passages by meaning, and comes back to the facts that cite what it found. It answers in statements, and each statement is tied to a passage. The page is built only from the statements that hold.",
            "In the Sherlock Holmes stories loaded here, asking what killed Dr Grimesby Roylott can be answered from the passage that names the swamp adder. Asking for the name of Sherlock Holmes's mother cannot. The stories do not say, and the result is a decline. Putting documents in, and answering questions, are the same rule run in opposite directions. A fact goes in only when a passage supports it. An answer comes out only when a passage supports it.",
        ],
    },
]


def prepare(section):
    n = max(words(section["pro"]), words(section["record"]))
    section["words"] = n
    section["duration"] = HEAD + n / WPS + TAIL
    section["spans"] = [(HEAD, section["duration"] - TAIL, section["record"][0])]


def active_index(section, t):
    return 0, 0.0


# --- frames -----------------------------------------------------------------

def base_frame(bg):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return overlay, ImageDraw.Draw(overlay)


def finish(bg, overlay):
    return Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")


def draw_usual(d, section, t, sent_i):
    title(d, "The usual path")
    steps = [
        ("01", "Documents", "Kept as files and pages.", BLUE),
        ("02", "Chunks", "Stored as vectors, nearest in meaning.", GOLD),
        ("03", "The agent writes", "A finished sentence, from what came back.", IVORY),
        ("04", "Citation, after", "Attached once the sentence exists.", CORAL),
    ]
    boxes = row_boxes(4, 250, 280, gap=22, margin=64)
    for box, (num, heading, body, accent) in zip(boxes, steps):
        card(d, box, num, heading, body, accent)
    panel(d, (64, 600, W - 64, 860), outline=GOLD, width=2)
    d.text((96, 640), "Enough when the words match.", font=font(32, "sem"), fill=col(IVORY))
    draw_wrapped(
        d,
        "Unreliable when the answer is a relationship, a type of thing, or a fact written in different words. The model supplies what the chunks did not.",
        font(26), col(MUTED), 96, 710, W - 220, gap=8,
    )


def draw_graph(d, section, t, sent_i):
    title(d, "A vocabulary, then the facts")
    left, right = row_boxes(2, 220, 640, gap=28, margin=64)
    card(
        d, left, "ONTOLOGY", "The shared vocabulary",
        "The kinds of things that matter, and the relationships allowed between them.\n\n"
        "A contract has parties.\nA person reports to a role.\nA case has a client.",
        GOLD,
    )
    # card() doesn't honour newlines well if wrap splits poorly. Draw the examples ourselves.
    panel(d, right, outline=TEAL, width=2)
    x, y = right[0] + 28, right[1] + 24
    d.text((x, y), "KNOWLEDGE GRAPH", font=font(15, "med"), fill=col(TEAL))
    d.text((x, y + 36), "The facts, in that vocabulary", font=font(28, "sem"), fill=col(IVORY))
    facts = [
        ("Contract", "has party", "Northwind"),
        ("Person", "reports to", "Role"),
        ("Case", "has client", "Hart"),
    ]
    yy = y + 120
    for a, rel, b in facts:
        d.text((x, yy), a, font=font(22, "sem"), fill=col(IVORY))
        d.text((x + 220, yy), rel, font=font(20), fill=col(GOLD))
        d.text((x + 460, yy), b, font=font(22, "sem"), fill=col(IVORY))
        yy += 64
    d.text((x, yy + 24), "Each fact can point back to the passage it came from.", font=font(22), fill=col(MUTED))
    # overwrite left body more cleanly
    panel(d, left, outline=GOLD, width=2)
    x, y = left[0] + 28, left[1] + 24
    d.text((x, y), "ONTOLOGY", font=font(15, "med"), fill=col(GOLD))
    d.text((x, y + 36), "The shared vocabulary", font=font(28, "sem"), fill=col(IVORY))
    draw_wrapped(d, "The kinds of things that matter, and the relationships allowed between them.", font(22), col(MUTED), x, y + 100, left[2] - x - 36, gap=6)
    for i, line in enumerate(["A contract has parties.", "A person reports to a role.", "A case has a client."]):
        d.text((x, y + 230 + i * 52), line, font=font(26, "sem"), fill=col(IVORY))


def draw_together(d, section, t, sent_i):
    title(d, "Why the vectors stay")
    left, right = row_boxes(2, 210, 460, gap=28, margin=64)
    card(d, left, "THE QUESTION NAMES SOMETHING", "Follow the graph",
         "Types and relationships. Each fact carries the passage it came from.", TEAL)
    card(d, right, "THE QUESTION DESCRIBES A SITUATION", "Search by meaning",
         "The wording may not match. One vector is one passage. The hit leads back to the facts that cite it.", BLUE)
    panel(d, (64, 720, W - 64, 960), outline=GOLD, width=2)
    d.text((96, 760), "Both end at a passage.", font=font(32, "sem"), fill=col(IVORY))
    d.text((96, 830), "The graph holds the structure. The vectors hold the wording the question never used.", font=font(24), fill=col(MUTED))


def draw_improves(d, section, t, sent_i):
    title(d, "What gets better")
    rows = [
        ("01", "Consistency", "The same types, when facts are taken from documents and when a question is asked.", GOLD),
        ("02", "Accuracy", "A statement is shown only when a passage actually contains it.", TEAL),
        ("03", "A decline", "When nothing remains, the agent says the sources do not answer.", CORAL),
    ]
    y = 220
    for num, heading, body, accent in rows:
        band(d, y, 150, num, heading, body, accent)
        y += 174
    d.text((64, y + 8), "The citation is the condition for showing the sentence.", font=font(26, "sem"), fill=col(IVORY))


def draw_ingestion(d, section, t, sent_i):
    title(d, "What the lab does on the way in")
    rows = [
        ("01", "Documents", "Kept as they arrived.", BLUE),
        ("02", "Passages", "The pieces a fact can cite. The same document keeps the same passages.", SILVER := (214, 220, 228)),
        ("03", "Ontology", "Bring it, or draft one from the documents for a person to review and publish.", GOLD),
        ("04", "Extraction", "A fact has to be in the passage it cites. A term with no place stays out of the graph.", TEAL),
        ("05", "Two stores", "The knowledge graph, and one vector for each passage.", GOLD),
    ]
    y = 190
    for num, heading, body, accent in rows:
        band(d, y, 118, num, heading, body, accent)
        y += 132


def draw_questions(d, section, t, sent_i):
    title(d, "What the lab does when someone asks")
    left, right = row_boxes(2, 190, 200, gap=22, margin=64)
    card(d, left, "NAMES SOMETHING", "Follow the graph", "", TEAL)
    card(d, right, "DESCRIBES A SITUATION", "Search passages by meaning", "", BLUE)
    # outcome cards
    a, b = row_boxes(2, 430, 340, gap=22, margin=64)
    card(
        d, a, "ANSWERED", "What killed Dr Grimesby Roylott?",
        "From the passage in The Speckled Band that names the swamp adder.",
        TEAL,
    )
    card(
        d, b, "DECLINED", "Holmes's mother's name?",
        "The stories do not say. The result is a decline, not a name borrowed from another mother in the text.",
        CORAL,
    )
    d.text((64, 800), "A fact enters only when a passage supports it.", font=font(26, "sem"), fill=col(IVORY))
    d.text((64, 848), "An answer leaves only when a passage supports it.", font=font(26, "sem"), fill=col(IVORY))


DRAW = {
    "usual": draw_usual,
    "graph": draw_graph,
    "together": draw_together,
    "improves": draw_improves,
    "ingestion": draw_ingestion,
    "questions": draw_questions,
}


def render_frame(bg, section, t, index, n, offset):
    overlay, d = base_frame(bg)
    chrome(d, section["kicker"])
    DRAW[section["id"]](d, section, t, 0)
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
            key = int(offset + t)
            if key != last_key:
                last_bytes = render_frame(bg, section, t, index, n, offset).tobytes()
                last_key = key
            proc.stdin.write(last_bytes)
            if i % (FPS * 8) == 0:
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


def _voice_file(path: Path, heading: str, intro: str, key: str):
    lines = [f"# {heading}", "", intro, ""]
    cursor = 0.0
    for i, section in enumerate(SECTIONS, start=1):
        start = cursor
        end = cursor + section["duration"]
        lines += [
            f"## {i}. {section['kicker']}",
            "",
            f"Clip `{section['file']}`. Assembly {tc(start)} to {tc(end)}.",
            "",
        ]
        lines.append("\n\n".join(section[key]))
        lines.append("")
        cursor = end
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", path)


def write_docs():
    script = [
        "# Knowledge Store briefing",
        "",
        "Six clips. The picture explains the idea. It does not show the product being used.",
        "",
        "Two complete reads, one per clip, in prose:",
        "",
        "- [voice-pro.md](voice-pro.md) for a professional technical narrator.",
        "- [voice-record.md](voice-record.md) to record yourself. Read the paragraphs for that clip straight through.",
        "",
        "The clips are timed to the longer of the two reads, at a measured pace of about 145 words a minute, with a short breath at each end of the clip.",
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
        script += [f"## {i}. {section['kicker']}", "", f"`{section['file']}`, {tc(cursor)} to {tc(cursor + section['duration'])}.", "", "Picture:", ""]
        for line in section["picture"]:
            script.append(f"- {line}")
        script.append("")
        cursor += section["duration"]
    (ROOT / "script.md").write_text("\n".join(script) + "\n", encoding="utf-8")
    _voice_file(
        ROOT / "voice-pro.md",
        "Professional voice",
        "For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs. Do not break it into the sentences on screen.",
        "pro",
    )
    _voice_file(
        ROOT / "voice-record.md",
        "Record yourself",
        "Read each clip straight through, as if explaining it to a room. The paragraphs are the whole read for that picture. Pause between paragraphs. The clip is long enough for this read at a measured pace.",
        "record",
    )
    print(f"total {cursor:.1f}s")


def stills(bg):
    dest = OUT / "stills"
    dest.mkdir(parents=True, exist_ok=True)
    cursor = 0.0
    n = len(SECTIONS)
    for i, section in enumerate(SECTIONS, start=1):
        frame = render_frame(bg, section, 1.0, i, n, cursor)
        name = dest / f"{section['id']}.png"
        frame.save(name)
        print("still", name)
        cursor += section["duration"]


def concat(paths, dest: Path):
    lst = dest.with_suffix(".concat.txt")
    lst.write_text("".join(f"file '{p}'\n" for p in paths), encoding="utf-8")
    try:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dest)]
        subprocess.check_call(cmd)
    finally:
        lst.unlink(missing_ok=True)
    print("wrote", dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", action="store_true")
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()
    for section in SECTIONS:
        prepare(section)
    write_docs()
    if (args.docs and not args.stills) or args.no_video:
        return
    bg = load_bg()
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
