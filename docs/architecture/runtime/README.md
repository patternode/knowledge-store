# Runtime

What runs where. A service is the deployable unit, the C4 container: built, versioned, released and deployed on its own. A node is where a service runs. A store is a database, bucket, prefix, table, index or secret, owned by one context whatever writes it.

| Register | Rows |
|---|---|
| [services.csv](services.csv) | SV-001 to SV-009, each with a page under [services/](services/) naming its code, its role and its findings against the continuum |
| [nodes.csv](nodes.csv) | DN-001 to DN-016 |
| [stores.csv](stores.csv) | ST-001 to ST-018, with the context that owns each and the services that write and read it |
| [deployable-units.md](deployable-units.md) | The C4 container view: every deployable unit and store with the SBB that realises it, and how the C4 levels sit on the continuum |

## Services

| Service | Context (composes) | Realises | Node |
|---|---|---|---|
| [SV-001 Pipeline (the sweep)](services/SV-001-pipeline/index.md) | BC-001 (BC-001, BC-002, BC-003, BC-004) | SBB-002 | DN-004 |
| [SV-002 Chat agent](services/SV-002-chat-agent/index.md) | BC-005 (BC-005, BC-004) | SBB-006 | DN-005 |
| [SV-003 Portal API](services/SV-003-portal-api/index.md) | BC-006 (BC-006, BC-004, BC-005) | SBB-007 | DN-007, DN-008 |
| [SV-004 Graph tools](services/SV-004-tools-graph/index.md) | BC-004 (BC-004) | SBB-005 | DN-007, DN-006 |
| [SV-005 Passage tools](services/SV-005-tools-passages/index.md) | BC-004 (BC-004) | SBB-015 | DN-007 |
| [SV-006 Gateway interceptor](services/SV-006-agent-interceptor/index.md) | BC-006 (BC-006) | SBB-017 | DN-007 |
| [SV-007 Chat page](services/SV-007-chat-page/index.md) | BC-006 (BC-006) | SBB-018 | DN-009 |
| [SV-008 Command line](services/SV-008-knowledge-store-cli/index.md) | BC-008 (BC-001, BC-002, BC-003, BC-004, BC-008) | SBB-013 | DN-004, DN-014 |
| [SV-009 Evaluation runner](services/SV-009-evaluation-runner/index.md) | BC-007 (BC-007) | SBB-019 | DN-014 |

Three rules of the continuum are checked here: a service serves one bounded context (SV-001 and SV-003 compose several today, CN-006); a store is owned by one context (every row of stores.csv names one; the sweep writes most of them, by the security rule that it is the only writer); every unit is provisioned from code (two log groups are not).
