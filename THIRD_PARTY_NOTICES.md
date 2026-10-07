# Third-party notices

This project's own code is licensed under the Apache License 2.0 (see LICENSE). It uses the third-party software below under the licences its authors publish. Only D3.js is bundled in this repository, in `chat/vendor/`.

## Python dependencies, installed by pip

| Package | Licence |
|---|---|
| anthropic | MIT |
| rdflib | BSD-3-Clause |
| pyshacl | Apache-2.0 |
| pypdf | BSD-3-Clause |
| strands-agents, bedrock-agentcore (agent image) | Apache-2.0 |
| mcp (agent image) | MIT |
| pydantic (agent image) | MIT |
| aws-opentelemetry-distro (agent image) | Apache-2.0 |

Optional, installed only with the extra that names them (see the README's Install section):

| Package | Extra | Licence |
|---|---|---|
| boto3, botocore | aws | Apache-2.0 |
| azure-storage-blob, azure-storage-queue, azure-identity | azure | MIT |
| azure-functions (the Azure Function App) | azure host | MIT |
| google-cloud-storage, google-auth | gcp | Apache-2.0 |
| PyJWT | azure, gcp | MIT |
| cryptography (through PyJWT) | azure, gcp | Apache-2.0 or BSD-3-Clause |
| pymongo | mongo | Apache-2.0 |
| neo4j | neo4j | Apache-2.0 (parts under the Python Software Foundation License) |
| psycopg, psycopg-binary | age | LGPL-3.0-only. It is installed by pip as an unmodified, separate library and imported at run time; this project does not include or change its code |

## Bundled with the chat page

| Component | File | Licence |
|---|---|---|
| D3.js 7.9.0, Copyright 2010-2023 Mike Bostock | `chat/vendor/d3.min.js`, unmodified from the `d3` npm package | ISC (the notice is in the file's first line and in `chat/vendor/README.md`) |

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
