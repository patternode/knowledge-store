"""Poll the baseline host's S3 channel; print new log lines; exit on a phase change, a runner exit, or the cap."""
import boto3, json, pathlib, sys, time
HERE=pathlib.Path(__file__).parent
B=json.load(open(HERE/"launch.json"))["bucket"]; s3=boto3.client("s3"); ec2=boto3.client("ec2")
stop_phases=set(sys.argv[1].split(",")) if len(sys.argv)>1 else {"ingesting","asking","done"}
cap=int(sys.argv[2]) if len(sys.argv)>2 else 25
seen={"boot.log":0,"runner.log":0}; last_phase=None; t0=time.time()
def get(key):
    try: return s3.get_object(Bucket=B,Key=key)["Body"].read().decode(errors="replace")
    except Exception: return None
while time.time()-t0 < cap*60:
    for k in seen:
        txt=get("output/"+k)
        if txt and len(txt)>seen[k]:
            new=txt[seen[k]:]; seen[k]=len(txt)
            lines=[l for l in new.splitlines() if l.strip() and not l.startswith("+ sleep") and "aws s3 cp" not in l]
            print(f"--- {k} (+{len(lines)} lines)"); print("\n".join(lines[-40:]), flush=True)
    st=get("output/status.json")
    if st:
        ph=json.loads(st).get("phase")
        if ph!=last_phase: print("STATUS", st, flush=True); last_phase=ph
        if ph in stop_phases: sys.exit(0)
    b=get("output/boot.log") or ""
    if "runner exit" in b: print("runner exited"); sys.exit(0)
    try:
        inst=ec2.describe_instances(InstanceIds=[json.load(open(HERE/"instance.json"))["instance_id"]])["Reservations"][0]["Instances"][0]
        if inst["State"]["Name"] not in ("pending","running"): print("instance state", inst["State"]["Name"]); sys.exit(0)
    except Exception as e: print("describe:", str(e)[:100])
    time.sleep(90)
print("watch cap reached; last phase", last_phase)
