# The pipeline image: the knowledge-store CLI. CodeBuild (AWS) or ACR Tasks (Azure) builds it inside
# the deploying account (infra/modules/image-build, infra/azure/modules/knowledge-store); the base
# image comes from ECR Public, not Docker Hub, to avoid anonymous pull limits in CodeBuild.
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# EXTRAS adds optional dependencies for a cloud and its backends, e.g. azure,mongo,neo4j,age.
ARG EXTRAS=""
RUN pip install ".${EXTRAS:+[$EXTRAS]}" && useradd --create-home --uid 10001 lab
USER lab

ENTRYPOINT ["knowledge-store"]
CMD ["run"]
