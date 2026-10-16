<!--
The title is this change's line in CHANGELOG.md and the GitHub Release, and its type sets the next version (CONTRIBUTING.md, "Releases"): `feat(scope): what changed` bumps the minor version, `fix(scope): what changed` the patch, and a `!` after the type marks a breaking change. `docs`, `build`, `ci`, `chore`, `refactor`, `test` and `style` never bump. Write it for someone reading the release notes.
The description is the change record: a squash merge copies it into the commit. Update it before merging so it says what merged. Delete any section that does not apply.
-->

## Summary

<!-- One or two sentences: what changes, and for whom. -->

## Why

Refs <!-- Required: the issue (#n, fixes #n, refs #n, or owner/repo#n), thread (t-xxx), improvement (IMP-NNN) or ADR (ADR-NNN) this serves. If there is none, write a line "No reference:" followed by the reason. The Change reference check fails a pull request into main that cites none of these. -->

## What changed

<!-- By component. The choices made, and the options rejected where that matters later. -->

## How it was verified

<!-- Tests, runs, measurements, screenshots. Say what was not verified. -->

## The lab

<!-- Patternode's lab runs a pinned release, not main (AGENTS.md). Say whether this change should reach the lab with the next release, and whether it changes the agent image (anything the Runtime container runs, including src/knowledge_store/agent/). "Nothing for the lab" is an answer. -->
