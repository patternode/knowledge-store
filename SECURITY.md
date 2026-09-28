# Security

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through GitHub's "Report a vulnerability" on this repository's Security tab. You will get an acknowledgement within a few working days, and a fix or mitigation plan once the report is understood.

## Scope and responsibilities

This project is a kit you deploy into your own AWS account. You are responsible for the account, its IAM, the data you ingest and who you give access to.

Before deploying:

- The stack ships no content filter (such as an Amazon Bedrock guardrail) and no spend budget. Add both to suit your use.
- Document text is untrusted input. It reaches the models during discovery and extraction, and candidate terms are drafted from it. Nothing changes the ontology without a person publishing a version, and extraction results are checked for grounding, but prompt injection through documents remains a risk to weigh.
- Private-scope sources are protected by filtering on the caller's Cognito group, not by separate storage. Content that needs a hard boundary belongs in a separate stack or account.
- Adapters fetch and keep what they are pointed at. Make sure you have the right to.
