# The pipeline image: the knowledge-store CLI. CodeBuild builds it inside the deploying account
# (infra/modules/image-build). The base image comes from ECR Public, not Docker Hub, to avoid
# anonymous pull limits in CodeBuild.
# Pinned to the multi-arch index digest of python:3.12-slim (amd64 and arm64) so that a build
# pulls exactly the image that was reviewed. Update the tag and the digest together.
FROM public.ecr.aws/docker/library/python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# EXTRAS picks the optional dependencies: aws (the default, which CodeBuild uses), plus any
# backends, e.g. aws,mongo,neo4j,age.
ARG EXTRAS="aws"
RUN pip install ".${EXTRAS:+[$EXTRAS]}" && useradd --create-home --uid 10001 lab
USER lab

ENTRYPOINT ["knowledge-store"]
CMD ["run"]
