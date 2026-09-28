# Third-party notices

This project's own code is licensed under the Apache License 2.0 (see LICENSE). It uses the third-party software below under the licences its authors publish. None of it is bundled in this repository.

## Python dependencies, installed by pip

| Package | Licence |
|---|---|
| boto3, botocore | Apache-2.0 |
| anthropic | MIT |
| rdflib | BSD-3-Clause |
| pyshacl | Apache-2.0 |
| pypdf | BSD-3-Clause |
| strands-agents, bedrock-agentcore (agent image) | Apache-2.0 |
| mcp (agent image) | MIT |
| pydantic (agent image) | MIT |
| aws-opentelemetry-distro (agent image) | Apache-2.0 |

## Loaded by the portal page at run time

| Component | Source | Licence |
|---|---|---|
| D3.js 7 | cdnjs.cloudflare.com | ISC |
| IBM Plex Sans and Mono | Google Fonts | SIL Open Font License 1.1 |

## Container base image

`public.ecr.aws/docker/library/python:3.12-slim`, the Docker Official Image for Python. Its licences are listed at https://github.com/docker-library/python.

## Sample content

- `examples/space-missions/`: original text written for this project, dedicated to the public domain (CC0 1.0).
- `examples/sherlock-holmes/fetch.py` downloads stories by Arthur Conan Doyle from Project Gutenberg. The stories are in the public domain. The script removes Project Gutenberg's header and footer, and the texts are not distributed with this repository.
