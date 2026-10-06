# The Knowledge Store module

Everything in one apply: the lake, the image build, the network, the pipeline, Cognito sign-in and
the portal. A root calls it with its own provider and backend. [`infra/stack`](../../stack) is the
reference root and [`examples/deployment`](../../../examples/deployment) a template for your own.
Only `admin_email` is required; [`variables.tf`](variables.tf) describes every input.

## Edge protection

The portal is one CloudFront distribution: the static page from S3, and `/api/*` from an API
Gateway HTTP API behind a Cognito JWT authorizer. Out of the box nothing filters traffic at the
edge, and CloudFront, API Gateway and Lambda bill per request and per GB. A public portal should
turn on the web ACL below and subscribe the distribution to a CloudFront flat-rate pricing plan.

### Inputs

| Input | Default | What it does |
|---|---|---|
| `waf.enabled` | `false` | Create an AWS WAF web ACL (scope `CLOUDFRONT`) and attach it to the portal's distribution |
| `waf.managed_rules_action` | `"block"` | `block` or `count` for the AWS managed common rule set (`AWSManagedRulesCommonRuleSet`); use `count` first to watch for false positives |
| `waf.managed_rules_count_overrides` | `["SizeRestrictions_BODY"]` | Rules of that set that only count. A chat question carries recent history and can pass the rule's 8 KB body limit |
| `waf.rate_limit` | `500` | Requests per IP in any 5 minutes, all paths, before the IP is blocked |
| `waf.api_rate_limit` | `300` | Requests per IP in any 5 minutes to `/api/*`. The chat polls every 1.5 seconds while it answers, so keep room for several questions |
| `waf.allowed_methods` | `GET`, `HEAD`, `POST`, `OPTIONS` | Any other method is blocked. The portal sends only `GET` and `POST` |
| `web_acl_arn` | `""` | Attach an existing `CLOUDFRONT`-scope web ACL instead of creating one. It takes precedence over `waf.enabled` |
| `api_throttle` | `{ rate_limit = 20, burst_limit = 50 }` | The HTTP API stage's throttling, for the whole API, in requests per second |

Outputs: `portal_distribution_id` (for the console steps below) and `portal_web_acl_arn`.

A `CLOUDFRONT` web ACL must be created in us-east-1. The module sets that region on the web ACL
itself (the AWS provider 6.x takes a per-resource region), so it works whatever region your
provider uses, and you pass no provider alias.

```hcl
module "knowledge_store" {
  source      = "git::https://github.com/patternode/knowledge-store.git//infra/modules/knowledge-store?ref=<release>"
  admin_email = "you@example.org"

  waf = { enabled = true }                     # or: web_acl_arn = "arn:aws:wafv2:us-east-1:..."
}
```

AWS WAF bills per web ACL, per rule and per million requests inspected, unless a flat-rate plan
covers the distribution.

### CloudFront flat-rate pricing plans (console only)

CloudFront's flat-rate pricing plans charge a fixed monthly price per distribution, include AWS
WAF and DDoS protection, and do not bill overage for requests or data transfer beyond the plan's
allowance. That puts a ceiling on what a request flood can cost. Recommended for any public
deployment.

Terraform cannot subscribe a distribution to a plan. Do it in the CloudFront console, per
distribution: open the distribution named by `portal_distribution_id` and choose a pricing plan.

Keep the Terraform configuration in step with the web ACL that ends up on the distribution. If
the plan attaches a web ACL of its own, set `web_acl_arn` to its ARN; with neither `waf.enabled`
nor `web_acl_arn` set, the next apply detaches it.

### The API's own endpoint stays enabled

The HTTP API's default `execute-api` endpoint is CloudFront's origin for `/api/*`, so it cannot
be disabled (`disable_execute_api_endpoint`) without breaking the portal. Disabling it would need
a custom domain name on the API, with its own certificate, as the origin instead. So the API can
also be called directly, where the web ACL does not apply. Two things bound that path:

- The JWT authorizer. A request without a valid Cognito ID token for the portal's client is
  rejected by API Gateway and never runs the Lambda, so it cannot reach the lake or a model.
- The stage throttling (`api_throttle`), which caps the request rate for the whole API. Signed-in
  users' model spend is further bounded by `daily_questions`.
