#!/usr/bin/env python3
"""Run the EnterpriseRAG-Bench questions through a fresh Onyx and write onyx-answers.jsonl.

Runs on the Onyx host under its instance role: the slice is read from S3_BUCKET, answers and status are
written back to it, and Bedrock is reached through the role (no static key). ONYX_URL may be given; otherwise
the host port the installer chose is found from docker.
"""
import io, json, os, pathlib, random, re, string, subprocess, sys, tarfile, time
import boto3, requests, yaml

BUCKET = os.environ["S3_BUCKET"]
MODEL = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
WORK = pathlib.Path("/opt/erb")
LIMIT = int(os.environ.get("QUESTION_LIMIT", "0") or 0)
S3 = boto3.client("s3")
BASE = None


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def find_base():
    global BASE
    if os.environ.get("ONYX_URL"):
        BASE = os.environ["ONYX_URL"].rstrip("/") + "/api"
        return
    cands = []
    try:
        out = subprocess.run(["docker", "ps", "--format", "{{.Names}} {{.Ports}}"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            for m in re.finditer(r"0\.0\.0\.0:(\d+)->(\d+)", line):
                cands.append((0 if "nginx" in line or "web" in line else 1, int(m.group(1))))
    except Exception as e:
        log(f"docker ps failed: {e}")
    ports = [p for _, p in sorted(set(cands))] + [3000, 80, 8080]
    for port in ports:
        try:
            if requests.get(f"http://127.0.0.1:{port}/api/health", timeout=5).status_code == 200:
                BASE = f"http://127.0.0.1:{port}/api"
                log(f"onyx api at {BASE}")
                return
        except Exception:
            pass
    BASE = f"http://127.0.0.1:{ports[0]}/api"
    log(f"no healthy port yet; assuming {BASE}")


def status(**kw):
    kw["when"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        S3.put_object(Bucket=BUCKET, Key="output/status.json", Body=json.dumps(kw).encode())
    except Exception as e:
        log(f"status upload failed: {e}")


def put_answers(path):
    try:
        S3.upload_file(str(path), BUCKET, "output/onyx-answers.jsonl")
    except Exception as e:
        log(f"answers upload failed: {e}")


def fetch_slice():
    if (WORK / "enterprise-rag-bench.yaml").exists():
        return
    WORK.mkdir(parents=True, exist_ok=True)
    body = S3.get_object(Bucket=BUCKET, Key="input/erb-slice.tar.gz")["Body"].read()
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tar:
        tar.extractall(WORK)
    log("slice extracted")


def wait_health(minutes=90):
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        find_base()
        try:
            if requests.get(BASE + "/health", timeout=10).status_code == 200:
                log("api healthy")
                return
        except Exception:
            pass
        time.sleep(20)
    raise SystemExit("api never became healthy")


def imds_credentials():
    tok = requests.put("http://169.254.169.254/latest/api/token", headers={"X-aws-ec2-metadata-token-ttl-seconds": "3600"}, timeout=5).text
    h = {"X-aws-ec2-metadata-token": tok}
    role = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/", headers=h, timeout=5).text.strip()
    c = requests.get(f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role}", headers=h, timeout=5).json()
    return {"AWS_ACCESS_KEY_ID": c["AccessKeyId"], "AWS_SECRET_ACCESS_KEY": c["SecretAccessKey"], "AWS_SESSION_TOKEN": c["Token"]}


def sign_in():
    s = requests.Session()
    email = "admin@example.com"
    pw_file = WORK / "admin.pw"
    pw = pw_file.read_text() if pw_file.exists() else "".join(random.choices(string.ascii_letters + string.digits, k=24))
    pw_file.write_text(pw)
    r = s.post(BASE + "/auth/register", json={"email": email, "password": pw}, timeout=60)
    log(f"register: {r.status_code} {r.text[:120]}")
    r = s.post(BASE + "/auth/login", data={"username": email, "password": pw}, timeout=60)
    log(f"login: {r.status_code}")
    r.raise_for_status()
    return s


def set_up_model(s):
    me = s.get(BASE + "/me", timeout=60)
    log(f"me: {me.status_code} {me.text[:200]}")

    def providers():
        r = s.get(BASE + "/admin/llm/provider", timeout=60)
        log(f"providers: {r.status_code} {r.text[:200]}")
        try:
            data = r.json()
        except ValueError:
            data = []
        return [p for p in data if isinstance(p, dict)] if isinstance(data, list) else []

    def put_provider(custom):
        body = {"name": "bedrock", "provider": "bedrock", "api_key_changed": True, "custom_config_changed": True,
                "custom_config": custom, "is_public": True,
                "model_configurations": [{"name": MODEL, "is_visible": True, "supports_chat": True, "max_input_tokens": 200000}]}
        prior = next((p for p in providers() if p.get("provider") == "bedrock"), None)
        if prior:
            body["id"] = prior["id"]
        r = s.put(BASE + "/admin/llm/provider", params={"is_creation": "false" if prior else "true"}, json=body, timeout=120)
        log(f"provider: {r.status_code} {r.text[:300]}")
        if r.status_code >= 400 and not prior:
            return False
        pid = r.json()["id"] if r.status_code < 400 else prior["id"]
        r = s.post(BASE + "/admin/llm/default", json={"provider_id": pid, "model_name": MODEL}, timeout=60)
        log(f"default model: {r.status_code} {r.text[:200]}")
        r = s.post(BASE + "/admin/llm/test/default", timeout=180)
        log(f"test default llm: {r.status_code} {r.text[:300]}")
        return r.status_code < 400

    if put_provider({"AWS_REGION_NAME": REGION}):
        log("bedrock through the instance role")
        return
    log("role-only config failed; trying instance credentials with a session token")
    custom = {"AWS_REGION_NAME": REGION}
    custom.update(imds_credentials())
    if put_provider(custom):
        log("bedrock through instance credentials")
        return
    log("WARNING: no working bedrock provider; answers will be empty")


def flatten(value, prefix=""):
    lines = []
    if isinstance(value, dict):
        for k, v in value.items():
            lines.extend(flatten(v, f"{prefix}{k}" if not prefix else f"{prefix}.{k}"))
    elif isinstance(value, list):
        if all(not isinstance(v, (dict, list)) for v in value):
            lines.append(f"{prefix}: {', '.join(str(v) for v in value)}")
        else:
            for i, v in enumerate(value, 1):
                lines.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        lines.append(f"{prefix}: {value}" if prefix else str(value))
    return lines


def doc_text(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        return "\n".join(flatten(json.loads(raw)))
    except Exception:
        return raw


def ingest(s, rows):
    done_file = WORK / "ingested.txt"
    done = set(done_file.read_text().split()) if done_file.exists() else set()
    n = 0
    for row in rows:
        if row["doc_id"] in done:
            continue
        path = WORK / "documents" / row["path"]
        text = doc_text(path)
        body = {"document": {"id": row["doc_id"], "semantic_identifier": row["path"], "title": pathlib.Path(row["path"]).stem,
                             "sections": [{"type": "text", "text": text}], "source": "file",
                             "metadata": {"path": row["path"], "folder": row["path"].split("/")[0]},
                             "from_ingestion_api": True}}
        for attempt in range(4):
            try:
                r = s.post(BASE + "/onyx-api/ingestion", json=body, timeout=120)
                if r.status_code < 400:
                    break
                log(f"ingest {row['doc_id']} -> {r.status_code} {r.text[:160]}")
            except Exception as e:
                log(f"ingest {row['doc_id']} error {e}")
            time.sleep(3 * (attempt + 1))
        else:
            continue
        done.add(row["doc_id"])
        n += 1
        if n % 100 == 0:
            done_file.write_text("\n".join(sorted(done)))
            log(f"ingested {len(done)}/{len(rows)}")
            status(phase="ingesting", ingested=len(done), total_docs=len(rows))
    done_file.write_text("\n".join(sorted(done)))
    log(f"ingested {len(done)}/{len(rows)}")


def wait_indexed(s, total, minutes=90):
    deadline = time.time() + minutes * 60
    last = -1
    while time.time() < deadline:
        try:
            info = s.get(BASE + "/manage/admin/cc-pair/1", timeout=60).json()
            num = info.get("num_docs_indexed")
            if num != last:
                log(f"indexed {num}/{total}")
                status(phase="indexing", indexed=num, total_docs=total)
                last = num
            if num is not None and num >= total * 0.98:
                return num
        except Exception as e:
            log(f"index poll: {e}")
        time.sleep(30)
    log("indexing wait timed out; continuing with what is indexed")
    return last


SEARCH_TOOL_ID = None


def find_search_tool(s):
    """The id of Onyx's document search tool, forced on every question so the agent cannot skip retrieval."""
    global SEARCH_TOOL_ID
    try:
        tools = s.get(BASE + "/tool", timeout=60).json()
    except Exception as e:
        log(f"tool list failed: {e}")
        return
    log("tools: " + ", ".join(f"{t.get('id')}={t.get('in_code_tool_id') or t.get('name')}" for t in tools)[:400])
    for t in tools:
        key = f"{t.get('in_code_tool_id') or ''} {t.get('name') or ''}".lower()
        if "search" in key and "web" not in key and "internet" not in key:
            SEARCH_TOOL_ID = t["id"]
            log(f"search tool id {SEARCH_TOOL_ID}")
            return
    log("WARNING: no search tool found; the agent decides whether to search")


def ask(s, question):
    body = {"message": question, "stream": False, "include_citations": True, "chat_session_info": {"persona_id": 0}}
    if SEARCH_TOOL_ID is not None:
        body["forced_tool_id"] = SEARCH_TOOL_ID
    for attempt in range(3):
        try:
            r = s.post(BASE + "/chat/send-chat-message", json=body, timeout=420)
            if r.status_code < 400:
                d = r.json()
                cited = list(dict.fromkeys(c["document_id"] for c in d.get("citation_info") or []))
                top = list(dict.fromkeys(t["document_id"] for t in d.get("top_documents") or []))
                calls = [ (c.get("tool_name") or c.get("name") or "?") for c in d.get("tool_calls") or [] ]
                return {"answer": d.get("answer_citationless") or d.get("answer") or "", "cited_ids": cited,
                        "retrieved_ids": top, "error": d.get("error_msg"), "tool_calls": calls}
            log(f"ask -> {r.status_code} {r.text[:200]}")
        except Exception as e:
            log(f"ask error: {e}")
        time.sleep(10 * (attempt + 1))
    return {"answer": "", "cited_ids": [], "retrieved_ids": [], "error": "no answer after 3 attempts"}


def main():
    status(phase="starting")
    fetch_slice()
    rows = [json.loads(l) for l in (WORK / "documents.jsonl").read_text().splitlines() if l.strip()]
    questions = yaml.safe_load((WORK / "enterprise-rag-bench.yaml").read_text(encoding="utf-8"))["questions"]
    if LIMIT:
        questions = questions[:LIMIT]
    wait_health()
    s = sign_in()
    set_up_model(s)
    status(phase="ingesting", total_docs=len(rows))
    ingest(s, rows)
    indexed = wait_indexed(s, len(rows))
    out = WORK / "onyx-answers.jsonl"
    answered = {}
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                answered[row["question_id"]] = row
    find_search_tool(s)
    if not answered:
        probe = ask(s, questions[0]["question"])
        log(f"probe: tool_calls={probe.get('tool_calls')} top_docs={len(probe['retrieved_ids'])} cited={len(probe['cited_ids'])} "
            f"error={probe.get('error')} answer={probe['answer'][:160]!r}")
        if not probe["retrieved_ids"] and not probe["cited_ids"]:
            status(phase="no-retrieval", indexed=indexed, probe=probe)
            log("the probe answer carried no documents; stopping before the rest")
            return
    status(phase="asking", indexed=indexed, answered=len(answered), total_questions=len(questions))
    started = time.time()
    for i, q in enumerate(questions, 1):
        if q["id"] in answered:
            continue
        reply = ask(s, q["question"])
        ids = reply["cited_ids"] or reply["retrieved_ids"][:5]
        row = {"question_id": q["id"], "answer": reply["answer"], "document_ids": ids,
               "cited_ids": reply["cited_ids"], "retrieved_ids": reply["retrieved_ids"], "error": reply["error"],
               "tool_calls": reply.get("tool_calls"),
               "model": MODEL, "system": "onyx"}
        answered[q["id"]] = row
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        if len(answered) % 10 == 0 or i == len(questions):
            put_answers(out)
            rate = (time.time() - started) / max(1, i)
            log(f"answered {len(answered)}/{len(questions)} ({rate:.0f}s each)")
            status(phase="asking", indexed=indexed, answered=len(answered), total_questions=len(questions),
                   seconds_per_question=round(rate))
    put_answers(out)
    status(phase="done", indexed=indexed, answered=len(answered), total_questions=len(questions))
    log("done")


if __name__ == "__main__":
    main()
