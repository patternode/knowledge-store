# Generates architecture.drawio, an editable draw.io (diagrams.net) version of the Knowledge Store
# AWS reference architecture, next to this file. Same layout and content as architecture.py (the
# SVG and PNG); open the .drawio file in diagrams.net or the draw.io desktop app or VS Code
# extension to change it.
#   python3 architecture_drawio.py
import os
from xml.sax.saxutils import escape

W, H = 1600, 1010
C = {  # role: (fill, stroke, text), as architecture.py
    "store": ("#E6F4F1", "#2E8B7A", "#14463D"),
    "compute": ("#E8EFFB", "#3B6FC9", "#1B3566"),
    "ai": ("#F1EAFB", "#7B4FC9", "#3B2366"),
    "edge": ("#FDF1E2", "#C98A2E", "#5C3D0F"),
    "person": ("#FFFFFF", "#555B66", "#22262E"),
}
FONT = "fontFamily=Helvetica;"
cells = []
n = [1]


def nid(prefix):
    n[0] += 1
    return f"{prefix}{n[0]}"


def attr(s: str) -> str:
    return escape(s, {'"': "&quot;"})


def vertex(x, y, w, h, style, value="", ident=None, parent="1"):
    ident = ident or nid("v")
    cells.append(f'<mxCell id="{ident}" value="{attr(value)}" style="{style}" vertex="1" parent="{parent}">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return ident


def box(x, y, w, h, role, title, lines=(), svc=None, ident=None):
    """A component: the AWS service on top, then its name and what it does."""
    f, s, t = C[role]
    parts = []
    if svc:
        parts.append(f'<font style="font-size:12px" color="{s}"><b>{escape(svc)}</b></font>')
    parts.append(f'<font style="font-size:16px"><b>{escape(title)}</b></font>')
    if lines:
        parts.append('<font style="font-size:13px">' + "<br>".join(escape(l) for l in lines) + "</font>")
    style = (f"rounded=1;arcSize=6;absoluteArcSize=1;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};"
             f"strokeWidth=1.6;fontColor={t};align=left;verticalAlign=top;spacingLeft=12;spacingTop=6;{FONT}")
    return vertex(x, y, w, h, style, "<br>".join(parts), ident)


def chip(x, y, w, text, role, ident=None):
    f, s, t = C[role]
    style = (f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor={s};strokeWidth=1.2;"
             f"fontColor={t};fontStyle=1;fontSize=13;{FONT}")
    return vertex(x, y, w, 24, style, escape(text), ident)


def text(x, y, w, h, html, size=13, color="#3A3F48", bold=False, align="left"):
    style = (f"text;html=1;whiteSpace=wrap;fontSize={size};fontColor={color};align={align};verticalAlign=top;"
             f"fontStyle={1 if bold else 0};{FONT}")
    return vertex(x, y, w, h, style, html)


def edge(src, tgt, label="", points=(), dashed=False, color="#4A505C", width=1.8, exit=None, entry=None):
    style = (f"edgeStyle=none;html=1;rounded=0;endArrow=block;endFill=1;strokeColor={color};strokeWidth={width};"
             f"fontSize=12;fontColor=#3A3F48;labelBackgroundColor=#F7F8FA;{FONT}")
    if dashed:
        style += "dashed=1;"
    if exit:
        style += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
    if entry:
        style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
    arr = f'<Array as="points">{pts}</Array>' if pts else ""
    label = "<br>".join(escape(p) for p in label.split("\n")) if label else ""
    cells.append(f'<mxCell id="{nid("e")}" value="{attr(label)}" style="{style}" edge="1" parent="1" '
                 f'source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>')


# --- title and lanes -----------------------------------------------------------------------------
text(40, 22, 1500, 34, "Knowledge Store on AWS: minimal GraphRAG", 26, "#1D2129", True)
text(40, 58, 1500, 22, "Ingestion fills a knowledge graph and a passage index; chat answers from both, and every "
     "claim shown is checked against a cited passage.", 15, "#505663")
for x, w, name in [(28, 440, "INGESTION"), (548, 424, "SHARED: GRAPH, PASSAGES, MODELS"), (1068, 504, "CHAT")]:
    vertex(x, 96, w, 736, f"rounded=1;arcSize=2;absoluteArcSize=1;fillColor=#F7F8FA;strokeColor=#DDE1E7;"
           f"html=1;connectable=0;{FONT}")
    text(x + 14, 102, w - 28, 20, escape(name), 11.5, "#7A8190", True)

# --- ingestion -----------------------------------------------------------------------------------
lake = box(40, 132, 400, 95, "store", "Lake: landing/<collection>/",
           ["Uploads, parsed text, passages, gold RDF,", "ontology versions"], "Amazon S3")
sweep = box(40, 270, 400, 546, "compute", "The sweep (idempotent)", [], "Amazon ECS Fargate · public subnets, no NAT")
edge(lake, sweep, "upload event or schedule\nEventBridge · SQS · Pipes · Scheduler")
y0 = 336
ingest, refine = chip(60, y0, 110, "ingest", "compute"), chip(190, y0, 110, "refine", "compute")
text(60, y0 + 38, 360, 20, "Ontology, one of two ways:", 13, C["compute"][2])
discover = chip(60, y0 + 64, 110, "discover", "compute")
review = chip(190, y0 + 64, 110, "review", "compute")
publish = chip(320, y0 + 64, 100, "publish", "compute")
text(60, y0 + 100, 360, 40, "or the one you provide (ontology_dir),<br>published by its owl:versionInfo", 13,
     C["compute"][2])
extract = chip(60, y0 + 150, 170, "extract (SHACL)", "compute")
project = chip(250, y0 + 150, 110, "project", "compute")
for a, b in [(ingest, refine), (discover, review), (review, publish), (extract, project)]:
    edge(a, b, color=C["compute"][1], width=1.4)
text(60, y0 + 198, 360, 40, "Images for the pipeline and the agent are<br>built in your account by CodeBuild into ECR.",
     13, C["compute"][2])

# --- shared: Bedrock, the VPC with Neptune and the graph tools, the Knowledge Base -----------------
bedrock = box(572, 140, 376, 150, "ai", "Models and screening",
              ["Claude: discovery, review, extraction,", "and the chat agent", "Titan Text Embeddings V2: passages",
               "Guardrails: questions and grounding"], "Amazon Bedrock")
vertex(560, 352, 400, 318, f"rounded=1;arcSize=3;absoluteArcSize=1;fillColor=none;strokeColor=#8A919E;"
       f"strokeWidth=1.4;dashed=1;dashPattern=7 5;html=1;connectable=0;{FONT}")
text(574, 358, 380, 20, "VPC · PRIVATE SUBNETS · NO ROUTE OUT", 11.5, "#5A6170", True)
neptune = box(580, 386, 360, 112, "store", "Knowledge graph",
              ["Gold RDF: one named graph per document,", "plus the ontology itself · IAM auth",
               "db.t3.medium ≈ 60 USD/month (can be off)"], "Amazon Neptune · SPARQL")
graph_tools = box(580, 560, 360, 95, "compute", "Graph tools",
                  ["Fixed, read-only SPARQL built from", "the ontology: entities, facts, paths"], "AWS Lambda")
edge(graph_tools, neptune, "read-only")
kb = box(572, 704, 376, 112, "store", "Passage index",
         ["One vector per passage, so a hit is", "a passage id · filtered to collection", "and the caller's scope"],
         "Bedrock Knowledge Base · S3 Vectors")

edge(sweep, bedrock, "model calls", exit=(1, 0.055), entry=(0, 1.0))
edge(sweep, neptune, "gold RDF", exit=(1, 0.31), entry=(0, 0.48))
edge(sweep, kb, "every passage", exit=(1, 0.91), entry=(0, 0.57))

# --- chat ------------------------------------------------------------------------------------------
person = box(1084, 132, 220, 62, "person", "A person", ["asks in the chat page"])
signin = box(1336, 132, 220, 88, "edge", "Sign-in", ["Cognito (private-readers), or", "a host website's grant"],
             "Amazon Cognito · or site_sign_in")
edge(person, signin, exit=(1, 0.5), entry=(0, 0.4))
page = box(1084, 226, 472, 66, "edge", "Chat and ontology pages (static, from S3)", [], "Amazon CloudFront")
edge(person, page, exit=(0.5, 1), entry=(0.233, 0))
api = box(1084, 324, 472, 112, "compute", "Chat API",
          ["Token or website grant checked · daily quota (30) · concurrency (20)",
           "asks the agent as the person, or as a service client by scope",
           "conversation and quota state in DynamoDB"], "API Gateway · Lambda · DynamoDB")
edge(page, api, "/api/*", exit=(0.233, 1), entry=(0.233, 0))
agent = box(1084, 460, 472, 112, "ai", "The chat agent",
            ["Released ontology in its system prompt", "Answers as claims, each citing a passage + quote",
             "Code checks every citation; failed claims removed"], "Amazon Bedrock AgentCore Runtime")
edge(api, agent, exit=(0.233, 1), entry=(0.233, 0))
edge(agent, bedrock, "model, guardrail", points=[(1010, 500), (1010, 230)], exit=(0, 0.357), entry=(1, 0.6))
gateway = box(1084, 600, 472, 95, "compute", "Tool gateway",
              ["Interceptor writes the caller's scope into every", "call from the verified token"],
              "AgentCore Gateway (MCP)")
edge(agent, gateway, "MCP, as the caller", exit=(0.233, 1), entry=(0.233, 0))
edge(gateway, graph_tools, "graph tools", exit=(0, 0.316), entry=(1, 0.737))
passages = box(1084, 720, 472, 96, "compute", "Passage tools",
               ["Search by meaning, then read passages", "from the lake · outside the VPC"], "AWS Lambda")
edge(gateway, passages, exit=(0.233, 1), entry=(0.233, 0))
edge(passages, kb, "Retrieve", exit=(0, 0.5), entry=(1, 0.571))

# --- footer notes ------------------------------------------------------------------------------------
notes = [
    ("Grounding", ["No statement without a source: a claim survives only if its quote is",
                   "in a passage the caller may read, is ≥ 12 characters, and the",
                   "guardrail scores it grounded. One repair turn, then it is removed."]),
    ("Valves", ["Per question: 16 tool calls, 14 model calls, 4000 output tokens",
                "per call, 1 repair turn. Optional monthly budget alert."]),
    ("Sign-in, networking and cost", ["Cognito, or a host website that frames the pages (site_sign_in).",
                                      "No NAT gateway; Neptune and the graph tools reach S3 through a",
                                      "gateway endpoint. Neptune is the main fixed cost (can be off)."]),
]
for i, (head, lines) in enumerate(notes):
    x = 28 + i * 520
    text(x + 4, 850, 500, 20, escape(head), 14, "#1D2129", True)
    text(x + 4, 872, 500, 60, "<br>".join(escape(l) for l in lines), 13)
text(28, 976, 1540, 20, "Design: docs/architectures/aws.md · Terraform: infra/modules/knowledge-store · "
     "Deployment guide: docs/deploy/aws · Generated by architecture_drawio.py", 12, "#7A8190")

doc = f'''<mxfile host="Electron" type="device">
  <diagram id="knowledge-store-aws" name="Knowledge Store on AWS">
    <mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" background="#FFFFFF" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        {chr(10).join("        " + c for c in cells).lstrip()}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "architecture.drawio"), "w").write(doc)
