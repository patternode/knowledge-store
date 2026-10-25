#!/bin/bash
# Onyx EnterpriseRAG baseline host, third form: installs Onyx, switches the deployment to Standard (the
# installer's non-interactive default is Lite, which has no vector index), ingests the slice and asks the
# 120-question sample, with Bedrock in us-west-2 (its own daily token allowance). No secrets: the instance role reaches S3 and Bedrock. Logs ship to s3://$B/output/.
# Control channel s3://$B/control/command: stop (shut down, terminates), sh (run control/run.sh as root).
set -x
B=__BUCKET__   # launch.py substitutes the bucket from launch.json
ONYX_TAG=v4.9.4
MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
MAX_HOURS=8
exec > >(tee -a /var/log/erb-boot.log) 2>&1
mkdir -p /opt/erb
dnf install -y docker git python3-pip
systemctl enable --now docker
pip3 install -q boto3 requests pyyaml
ship() { aws s3 cp /var/log/erb-boot.log s3://$B/output/boot.log --quiet; [ -f /var/log/erb-runner.log ] && aws s3 cp /var/log/erb-runner.log s3://$B/output/runner.log --quiet; }
( while true; do ship; sleep 60; done ) &
( sleep $((MAX_HOURS*3600)); echo "max hours reached"; ship; shutdown -h now ) &
control() {
  while true; do
    cmd=$(aws s3 cp s3://$B/control/command - 2>/dev/null)
    if [ -n "$cmd" ]; then echo -n | aws s3 cp - s3://$B/control/command --quiet; fi
    case "$cmd" in
      stop) echo "stop requested"; ship; shutdown -h now ;;
      sh) aws s3 cp s3://$B/control/run.sh /opt/erb/run.sh --quiet && echo "=== run.sh begins" && bash /opt/erb/run.sh; echo "=== run.sh exit $?" ;;
    esac
    sleep 30
  done
}
control &
export HOME=/root
curl -fsSL https://onyx.app/install_onyx.sh | bash -s -- --tag $ONYX_TAG --no-prompt --dir /opt/onyx --no-wait
echo "=== switching to Standard"
sysctl -w vm.max_map_count=262144
cd /opt/onyx/deployment && docker compose -p onyx down && docker compose -p onyx -f docker-compose.yml up -d
for i in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:80/api/health && break; sleep 20; done
docker ps --format '{{.Names}} {{.Status}}'
echo "=== search tool availability"
# Onyx hides its SearchTool from /api/tool and skips it in chat unless a connector other than the built-in
# ingestion connector (id 0) exists (SearchTool.is_available, check_connectors_exist). Documents sent through
# the ingestion API land on connector 0 only, so add an inert connector: no cc pair, so nothing indexes.
docker exec onyx-relational_db-1 psql -U postgres -At -c "insert into connector (name, source, input_type, connector_specific_config, indexing_start, refresh_freq, prune_freq, time_created, time_updated, kg_processing_enabled, kg_coverage_days) select 'erb-placeholder-for-search-tool', source, input_type, connector_specific_config, indexing_start, refresh_freq, prune_freq, now(), now(), kg_processing_enabled, kg_coverage_days from connector where id=0 and not exists (select 1 from connector where id > 0)"
echo "=== slice and sample"
aws s3 cp s3://$B/input/erb-slice.tar.gz /opt/erb/erb-slice.tar.gz --quiet && tar -xzf /opt/erb/erb-slice.tar.gz -C /opt/erb && rm /opt/erb/erb-slice.tar.gz
aws s3 cp s3://$B/input/enterprise-rag-bench.sample.yaml /opt/erb/enterprise-rag-bench.yaml --quiet && grep -c "^- id:" /opt/erb/enterprise-rag-bench.yaml
aws s3 cp s3://$B/runner/onyx_baseline.py /opt/erb/onyx_baseline.py --quiet
echo "=== runner"
S3_BUCKET=$B MODEL_ID=$MODEL_ID BEDROCK_REGION=us-west-2 python3 /opt/erb/onyx_baseline.py >> /var/log/erb-runner.log 2>&1
echo "runner exit $?"; ship
echo "runner finished; host kept up until a stop command (for diagnosis and reruns)"
wait
