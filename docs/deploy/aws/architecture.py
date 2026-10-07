# Generates architecture.svg, the Knowledge Store AWS reference architecture, next to this file.
#   python3 architecture.py
# Render a PNG from it with any browser or SVG tool (the committed PNG is at 2x).
import os
W, H = 1600, 1010
C = {  # role: (fill, stroke, text)
 "store": ("#E6F4F1", "#2E8B7A", "#14463D"),
 "compute": ("#E8EFFB", "#3B6FC9", "#1B3566"),
 "ai": ("#F1EAFB", "#7B4FC9", "#3B2366"),
 "edge": ("#FDF1E2", "#C98A2E", "#5C3D0F"),
 "person": ("#FFFFFF", "#555B66", "#22262E"),
}
out = []
def box(x, y, w, h, role, title, lines=(), svc=None):
    f, s, t = C[role]
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{f}" stroke="{s}" stroke-width="1.6"/>')
    ty = y + 24
    if svc:
        out.append(f'<text x="{x+14}" y="{ty}" class="svc" fill="{s}">{svc}</text>'); ty += 20
    out.append(f'<text x="{x+14}" y="{ty}" class="title" fill="{t}">{title}</text>'); ty += 20
    for l in lines:
        out.append(f'<text x="{x+14}" y="{ty}" class="body" fill="{t}">{l}</text>'); ty += 17
def arrow(pts, label=None, lx=None, ly=None, anchor="middle", dashed=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    da = ' stroke-dasharray="6 4"' if dashed else ''
    out.append(f'<path d="{d}" fill="none" stroke="#4A505C" stroke-width="1.8"{da} marker-end="url(#ah)"/>')
    if label:
        for i, part in enumerate(label.split("|")):
            out.append(f'<text x="{lx}" y="{ly + i*15}" class="lbl" text-anchor="{anchor}">{part}</text>')
def chip(x, y, w, text, role):
    f, s, t = C[role]
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="12" fill="#fff" stroke="{s}" stroke-width="1.2"/>')
    out.append(f'<text x="{x+w/2}" y="{y+16.5}" class="chip" fill="{t}" text-anchor="middle">{text}</text>')

# Title and lanes
out.append('<text x="40" y="48" class="h1">Knowledge Store on AWS — minimal GraphRAG</text>')
out.append('<text x="40" y="74" class="sub">Ingestion fills a knowledge graph and a passage index; chat answers from both, and every claim shown is checked against a cited passage.</text>')
for x, w, name in [(28, 440, "INGESTION"), (548, 424, "SHARED: GRAPH, PASSAGES, MODELS"), (1068, 504, "CHAT")]:
    out.append(f'<rect x="{x}" y="96" width="{w}" height="736" rx="14" fill="#F7F8FA" stroke="#DDE1E7"/>')
    out.append(f'<text x="{x+14}" y="118" class="lane">{name}</text>')

# Ingestion
box(40, 132, 400, 95, "store", "Lake: landing/&lt;collection&gt;/", ["Uploads, parsed text, passages, gold RDF,", "ontology versions"], "Amazon S3")
arrow([(240, 227), (240, 266)], "upload event or schedule|EventBridge · SQS · Pipes · Scheduler", 252, 243, "start")
box(40, 270, 400, 546, "compute", "The sweep (idempotent)", [], "Amazon ECS Fargate · public subnets, no NAT")
steps = [("ingest", 0), ("refine", 1)]
y0 = 336
for i, s in enumerate(["ingest", "refine"]):
    chip(60 + i*130, y0, 110, s, "compute")
out.append(f'<text x="60" y="{y0+52}" class="body" fill="#1B3566">Ontology, one of two ways:</text>')
chip(60, y0+64, 110, "discover", "compute"); chip(190, y0+64, 110, "review", "compute"); chip(320, y0+64, 100, "publish", "compute")
out.append(f'<text x="60" y="{y0+114}" class="body" fill="#1B3566">or the one you provide (ontology_dir),</text>')
out.append(f'<text x="60" y="{y0+131}" class="body" fill="#1B3566">published by its owl:versionInfo</text>')
chip(60, y0+150, 170, "extract (SHACL)", "compute"); chip(250, y0+150, 110, "project", "compute")
for (x1, x2, yy) in [(170, 190, y0+12), (170, 190, y0+76), (300, 320, y0+76), (230, 250, y0+162)]:
    out.append(f'<path d="M{x1},{yy} L{x2-2},{yy}" stroke="#3B6FC9" stroke-width="1.4" marker-end="url(#ahs)"/>')
out.append(f'<text x="60" y="{y0+212}" class="body" fill="#1B3566">Images for the pipeline and the agent are</text>')
out.append(f'<text x="60" y="{y0+229}" class="body" fill="#1B3566">built in your account by CodeBuild into ECR.</text>')

# Middle: Bedrock, VPC with Neptune and graph tools, KB
box(572, 140, 376, 150, "ai", "Models and screening", ["Claude: discovery, review, extraction,", "and the chat agent", "Titan Text Embeddings V2: passages", "Guardrails: questions and grounding"], "Amazon Bedrock")
out.append('<rect x="560" y="352" width="400" height="318" rx="12" fill="none" stroke="#8A919E" stroke-width="1.4" stroke-dasharray="7 5"/>')
out.append('<text x="574" y="372" class="lane" fill="#5A6170">VPC · PRIVATE SUBNETS · NO ROUTE OUT</text>')
box(580, 386, 360, 112, "store", "Knowledge graph", ["Gold RDF: one named graph per document,", "plus the ontology itself · IAM auth", "db.t3.medium ≈ 60 USD/month (can be off)"], "Amazon Neptune · SPARQL")
box(580, 560, 360, 95, "compute", "Graph tools", ["Fixed, read-only SPARQL built from", "the ontology: entities, facts, paths"], "AWS Lambda")
arrow([(760, 560), (760, 502)], "read-only", 770, 536, "start")
box(572, 704, 376, 112, "store", "Passage index", ["One vector per passage, so a hit is", "a passage id · filtered to collection", "and the caller's scope"], "Bedrock Knowledge Base · S3 Vectors")

# Ingestion -> stores / Bedrock
arrow([(440, 300), (568, 300)], "model calls", 504, 292)
arrow([(440, 440), (576, 440)], "gold RDF", 508, 432)
arrow([(440, 768), (568, 768)], "every passage", 504, 760)

# Chat column
box(1084, 132, 220, 62, "person", "A person", ["asks in the chat page"])
box(1336, 132, 220, 78, "edge", "Sign-in", ["group private-readers"], "Amazon Cognito")
arrow([(1304, 163), (1332, 163)])
arrow([(1194, 194), (1194, 222)])
box(1084, 226, 472, 66, "edge", "Chat page (static, from S3)", [], "Amazon CloudFront")
arrow([(1194, 292), (1194, 320)], "/api/*", 1206, 310, "start")
box(1084, 324, 472, 112, "compute", "Chat API", ["JWT check · daily quota (30) · concurrency cap (20)", "passes the person's own token, never stored", "conversation and quota state in DynamoDB"], "API Gateway (JWT) · Lambda · DynamoDB")
arrow([(1194, 436), (1194, 456)])
box(1084, 460, 472, 112, "ai", "The chat agent", ["Released ontology in its system prompt", "Answers as claims, each citing a passage + quote", "Code checks every citation; failed claims removed"], "Amazon Bedrock AgentCore Runtime")
arrow([(1084, 500), (1010, 500), (1010, 230), (952, 230)])
out.append('<text x="1002" y="370" class="lbl" text-anchor="middle" transform="rotate(-90 1002 370)">model, guardrail</text>')
arrow([(1194, 572), (1194, 596)], "MCP, as the person", 1206, 589, "start")
box(1084, 600, 472, 95, "compute", "Tool gateway", ["Interceptor writes the caller's scope into every", "call from the verified token"], "AgentCore Gateway (MCP)")
arrow([(1084, 630), (944, 630)], "graph tools", 1012, 622)
arrow([(1194, 695), (1194, 716)])
box(1084, 720, 472, 96, "compute", "Passage tools", ["Search by meaning, then read passages", "from the lake · outside the VPC"], "AWS Lambda")
arrow([(1084, 768), (952, 768)], "Retrieve", 1018, 760)

# Footer notes
notes = [
 ("Grounding", ["No statement without a source: a claim survives only if its quote is", "in a passage the caller may read, is ≥ 12 characters, and the", "guardrail scores it grounded. One repair turn, then it is removed."]),
 ("Valves", ["Per question: 16 tool calls, 14 model calls, 4000 output tokens", "per call, 1 repair turn. Optional monthly budget alert."]),
 ("Networking and cost", ["No NAT gateway. Neptune and the graph tools reach S3 through a", "gateway endpoint. Neptune is the main fixed cost; set", "knowledge_graph.enabled = false to remove it."]),
]
for i, (h, ls) in enumerate(notes):
    x = 28 + i*520
    out.append(f'<text x="{x+4}" y="866" class="nh">{h}</text>')
    for j, l in enumerate(ls):
        out.append(f'<text x="{x+4}" y="{888+j*18}" class="note">{l}</text>')
out.append('<text x="28" y="990" class="foot">Design: docs/architectures/aws.md · Terraform: infra/modules/knowledge-store · Deployment guide: docs/deploy/aws</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4A505C"/></marker>
<marker id="ahs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#3B6FC9"/></marker>
<style>
text {{ font-family: Inter, 'DejaVu Sans', sans-serif; }}
.h1 {{ font-size: 26px; font-weight: 700; fill: #1D2129; }}
.sub {{ font-size: 15px; fill: #505663; }}
.lane {{ font-size: 11.5px; font-weight: 700; letter-spacing: 1.2px; fill: #7A8190; }}
.svc {{ font-size: 12px; font-weight: 600; }}
.title {{ font-size: 16px; font-weight: 700; }}
.body {{ font-size: 13px; }}
.chip {{ font-size: 13px; font-weight: 600; }}
.lbl {{ font-size: 12px; fill: #3A3F48; font-weight: 500; paint-order: stroke; stroke: #F7F8FA; stroke-width: 4px; }}
.nh {{ font-size: 14px; font-weight: 700; fill: #1D2129; }}
.note {{ font-size: 13px; fill: #3A3F48; }}
.foot {{ font-size: 12px; fill: #7A8190; }}
</style></defs>
<rect width="100%" height="100%" fill="#FFFFFF"/>
{chr(10).join(out)}
</svg>'''
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "architecture.svg"), "w").write(svg)
