# Deploying Knowledge Store into your own infrastructure

This directory is a template for a deployment repository: a private repository of your own that
holds your configuration and your curated ontologies, and uses this repository as a pinned module.
Nothing of yours ever needs to live in a copy of this repository, and upgrading is a one-line change.

```
your-deployment/
  main.tf              # provider, backend and the module, pinned to a release; your whole configuration
  outputs.tf           # the same outputs as infra/stack, so the example tools work against it
  backend.hcl          # where the state lives (from backend.hcl.example)
  ontology/<id>/       # the curated master of each collection's ontology
  .github/workflows/   # optional: plan on pull requests, apply by hand from main
```

The quick start's `infra/stack` is the same module with a minimal root around it. Use it to try
Knowledge Store; use this template when you run it for real.

## Set it up

1. Copy this directory into a new private repository (or a directory of an infrastructure
   repository you already have).
2. State: if you have no state bucket, run `infra/bootstrap` from this repository once, and write
   what it prints to `backend.hcl`. Otherwise point `backend.hcl` at the bucket you use.
3. Edit `main.tf`: region, `admin_email`, `name`, your collections, and the release in `ref`.
4. Apply:

   ```bash
   terraform init -backend-config=backend.hcl
   terraform plan
   terraform apply
   ```

5. Upload to the `upload_to` output, then curate and publish each collection's first ontology
   (see [ontology/README.md](ontology/README.md)).

Credentials: prefer `AWS_PROFILE` in the environment over a `profile` in the files. The S3
backend does not use the provider's profile, so a profile set only on the provider sends the
state to whatever account the default credentials belong to. With `AWS_PROFILE`, both use the
same account, and the same files work in CI.

## What goes where

| Here, in your repository | In Knowledge Store (upstream) |
|---|---|
| region, account guard, tags, state location | the module and everything it creates |
| collections, their profiles and sources | the pipeline, portal, agent and their images |
| model choices, agent switches | defaults that work for anyone |
| curated ontologies and their history | the ontology tooling and the core vocabulary |

If you need something the module does not offer, such as an existing VPC or user pool, add it
upstream as an input with a default that keeps today's behaviour, rather than patching a copy.
Then everyone can use it, and your deployment keeps following releases.

## Upgrade

Read the release notes, change `ref` in `main.tf` to the new tag, and plan. Refactors inside the
module carry `moved` blocks, so a plan should show only real changes. To try an unreleased change,
point `ref` at a branch, or at a local checkout with `source = "../knowledge-store/infra/modules/knowledge-store"`.

## The example agent

The agent needs two applies: first with `agent = { enabled = true }`, which builds its image in
CodeBuild; then, once the image is in ECR, with `runtime = true`. To call it:

```bash
python <knowledge-store checkout>/examples/agent/invoke.py --stack-dir . dossier <collection> "<entity>"
```
