# Security

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through GitHub's "Report a vulnerability" on this repository's Security tab. You will get an acknowledgement within a few working days, and a fix or mitigation plan once the report is understood.

## Scope and responsibilities

How the design itself keeps people, data and spend safe, boundary by boundary, is
[docs/architecture/security.md](docs/architecture/security.md). This page is what you are
responsible for around it.

This project is a kit you deploy into your own AWS account. You are responsible for the account, its IAM, the data you ingest and who you give access to.

Before deploying:

- The chat's Bedrock guardrail is on by default (`guardrail.enabled`); tune it to suit your use. There is no spend
  budget unless you set one: set `budget.monthly_usd` (mailed to `admin_email`, or `budget.email`).
- Document text is untrusted input. It reaches the models during discovery and extraction, and candidate terms are drafted from it. Nothing changes the ontology without a person publishing a version, and extraction results are checked for grounding, but prompt injection through documents remains a risk to weigh.
- Private-scope sources are protected by filtering on the caller's Cognito group, not by separate storage. Content that needs a hard boundary belongs in a separate stack or account.
- Adapters fetch and keep what they are pointed at. Make sure you have the right to.

## The launch stack (CloudFormation)

[`infra/launch/knowledge-store.yaml`](infra/launch/knowledge-store.yaml) runs the project's
Terraform in a CodeBuild project, `<DeploymentName>-deploy`, whose service role has
`AdministratorAccess`. The role trusts only CodeBuild, and only for that project in your account
(`aws:SourceAccount` and `aws:SourceArn`). A Lambda function (`Starter`) starts the project for
each CloudFormation request.

**Treat the deploy project and the Starter function as administrator-equivalent.** CodeBuild's
`StartBuild` accepts a different buildspec, source and environment for one build, and Starter
passes on whatever source URL it is invoked with, so anyone who may start or change either one can
run any code as administrator. Nothing inside the template can prevent that; IAM in your account
must. Allow these actions on these resources to administrators only:

| Resource | Actions |
|---|---|
| the project `<DeploymentName>-deploy` | `codebuild:StartBuild`, `codebuild:StartBuildBatch`, `codebuild:RetryBuild`, `codebuild:RetryBuildBatch`, `codebuild:UpdateProject` |
| the Starter function (`<stack>-Starter-*`) | `lambda:InvokeFunction`, `lambda:UpdateFunctionCode`, `lambda:UpdateFunctionConfiguration` |
| the roles `<stack>-DeployerRole-*` and `<stack>-StarterRole-*` | `iam:PassRole` (and changes to the roles themselves) |

CloudFormation names the function and roles after the stack, with a random suffix (and shortens
long names); take the exact names from the stack's Resources tab.

CloudFormation invokes Starter with the credentials of whoever creates, updates or deletes the
stack, and Starter's own role starts the build, so leave both of those allowed. A service control
policy (or a permissions-boundary or identity-policy statement) such as this one, with your
administrator roles and the stack's name filled in, does it:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "KnowledgeStoreDeployerIsAdminOnly",
    "Effect": "Deny",
    "Action": [
      "codebuild:StartBuild", "codebuild:StartBuildBatch", "codebuild:RetryBuild",
      "codebuild:RetryBuildBatch", "codebuild:UpdateProject",
      "lambda:InvokeFunction", "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration",
      "iam:PassRole"
    ],
    "Resource": [
      "arn:aws:codebuild:*:*:project/<DeploymentName>-deploy",
      "arn:aws:lambda:*:*:function:<stack>-Starter-*",
      "arn:aws:iam::*:role/<stack>-DeployerRole-*",
      "arn:aws:iam::*:role/<stack>-StarterRole-*"
    ],
    "Condition": {
      "ArnNotLike": {
        "aws:PrincipalArn": [
          "arn:aws:iam::*:role/<your administrator role>",
          "arn:aws:iam::*:role/<stack>-StarterRole-*"
        ]
      }
    }
  }]
}
```

Also:

- **Set `SourceSha256`.** `SourceUrl` must be an `https://` or `s3://` URL, and the build refuses
  anything else, but without a hash the build runs whatever that URL serves at the time. With an
  `s3://` URL, only administrators should be able to write that object.
- **Known limitation:** the deploy role keeps `AdministratorAccess`. Terraform creates and deletes
  IAM roles, CloudFront, Cognito, Lambda, ECS, CodeBuild, Neptune, Bedrock and AgentCore resources,
  and a narrower policy has not been validated against a real deploy and destroy. If your
  organisation requires one, deploy with Terraform directly under your own role
  ([docs/deploy/aws](docs/deploy/aws/README.md)) instead of the launch stack.

## Hardening a deployment

- **Image builds.** Any object written under `source/` in the build bucket (`<name>-build-<account>`)
  starts a privileged CodeBuild build that pushes to the stack's ECR repositories, and so changes
  the code the pipeline and agent run. Only the identity that applies Terraform should hold
  `s3:PutObject` there. The bucket requires TLS; it cannot name the applying identity itself
  without breaking applies by anyone else, so restrict writes in IAM. The repositories' tags are
  mutable because the pipeline and the agent run `:latest`, which every build moves.
- **Sign-in.** The Cognito pool allows (does not require) an authenticator app as a second factor.
  Requiring it would stop existing users at their next sign-in, as the portal has no set-up flow
  for it. Deletion protection on the pool is off by default so that `terraform destroy` and
  deleting the launch stack keep working; the identity module's `deletion_protection` input turns it on.
- **The API.** CloudFront forwards `/api/*` to the HTTP API's own `execute-api` endpoint, which is
  also reachable directly. API Gateway still checks the Cognito token on every route (or, with
  `site_sign_in`, the Lambda checks the website's grant), so going around CloudFront skips only
  CloudFront's web ACL and caching, not authentication. Each request is logged to
  `/aws/vendedlogs/apigateway/<name>-portal`.
- **CI.** The example deployment's workflow plans with a read-only role and applies with a second
  role that only the protected `production` environment can assume; see
  [examples/deployment](examples/deployment/README.md#ci).
