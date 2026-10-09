# Agent notes

Patternode's live lab does not follow this repository. It runs the module pin in
patternode-platform `deployments/knowledge-store/main.tf` (`source` `ref=`) from the last
applied `deploy` revision. A merge to `main` here does not change the lab, and neither does
merging that pin, until the revision is promoted and Dermot applies it. The lab keeps the old
pages until then. This has been missed repeatedly, and the lab has looked broken each time.

When you merge a user-visible change to `main`, open that platform pull request in the same
piece of work. If the agent image changed, the platform change leaves `agent.runtime = false`
for one apply, then a following change sets it `true` once the image is in ECR
(`knowledge-store-agent`). The steps are in that deployment's README, under "For agents".
