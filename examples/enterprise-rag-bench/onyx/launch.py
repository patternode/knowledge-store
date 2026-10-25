"""Launch the Onyx baseline host in the labs account. Run with the labs profile; refuses to run until the role exists."""
import boto3, json, pathlib, sys, time
cfg = json.load(open(pathlib.Path(__file__).with_name("launch.json")))
iam, ec2 = boto3.client("iam"), boto3.client("ec2")
try:
    iam.get_instance_profile(InstanceProfileName=cfg["role"])
except Exception as e:
    sys.exit(f"instance profile {cfg['role']} not found: {e}")
s3 = boto3.client("s3")
s3.upload_file(str(pathlib.Path(__file__).with_name("onyx_baseline.py")), cfg["bucket"], "runner/onyx_baseline.py")
try: s3.delete_object(Bucket=cfg["bucket"], Key="control/command")
except Exception: pass
itype = sys.argv[1] if len(sys.argv) > 1 else "m7i.2xlarge"
r = ec2.run_instances(
    ImageId=cfg["ami_x86"], InstanceType=itype, MinCount=1, MaxCount=1,
    SubnetId=cfg["subnet"], SecurityGroupIds=[cfg["sg"]],
    IamInstanceProfile={"Name": cfg["role"]},
    UserData=pathlib.Path(__file__).with_name("boot.sh").read_text().replace("__BUCKET__", cfg["bucket"]),
    BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 120, "VolumeType": "gp3", "DeleteOnTermination": True}}],
    MetadataOptions={"HttpTokens": "required", "HttpPutResponseHopLimit": 2},
    InstanceInitiatedShutdownBehavior="terminate",
    TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "onyx-erb-baseline"}, {"Key": "purpose", "Value": "EnterpriseRAG baseline, self-terminating"}]}],
)
inst = r["Instances"][0]
info = {"instance_id": inst["InstanceId"], "type": itype, "launched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(info, open(pathlib.Path(__file__).with_name("instance.json"), "w"), indent=1)
print(info)
