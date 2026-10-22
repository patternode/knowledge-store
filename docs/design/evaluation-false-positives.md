---
sidebar_label: False positives in evaluation
last_modified: 2026-10-20
---

# False positives in evaluation: what changed since 18 October 2026

This note compares how Knowledge Store's evaluation judges answers today with how it judged them on 18 October 2026 (the baseline, `main` at `097658e`, release 0.4.0). It covers Knowledge Store only. The decision behind the changes is patternode-architecture ADR-048; this repository's record of it is [ADR-012](../architecture/decisions/ADR-012-evaluation-counts-false-answers-and-unsupported-claims-and-gates-releases.md).

A false positive here is an evaluation passing something it should fail: a wrong answer scored right, a guess scored as a right decline, or an unsupported claim scored as supported. The aim was to remove them without failing right answers and right declines (false negatives), so every change below was checked in both directions.

## Summary

| Measured on the labelled corpus | Baseline (18 Oct) | This branch before the review | Now |
|---|---|---|---|
| Wrong replies scored right (false positives), of 9 | 3 | 4 | 0 |
| Right replies and declines scored wrong (false negatives), of 13 | 7 | 2 | 0 |
| Unsupported claims passed as supported, of 4 | not measured | 2 | 0 |
| Supported claims rejected, of 3 | not measured | 0 | 0 |

The corpus is `tests/evaluation/unit/test_false_positives.py`: 22 hand-labelled replies across lookups, comparisons, figures and unanswerable questions, and 7 claims against one source passage. It runs with every `pytest`, so a change that brings a false positive back fails the build. It is a fixed set of the failure modes found, not a sample of live answers: it shows which mistakes each scorer makes, not how often a live run meets them. That rate needs a live run of the shipped sets, which costs model spend and has not been done.

## What the baseline did

The baseline scorer (`src/knowledge_store/evals/score.py` at `097658e`) had three sources of false positives and several of false negatives.

1. A required fact counted wherever its spelling appeared, so "It was not an Atlas V" stated "Atlas V". The same rule failed right answers: "An Atlas V, not a Delta II" broke the question's `must_not` and scored zero.
2. Figures were written as spellings ("2.4 billion"). A year could stand for a figure ("In 2025 revenue rose" stated 2025), and a right figure in another form ("$94.9 billion" for 94.93 billion, "$2.00 billion") was missed.
3. An unanswerable question was right only when the reply carried the `abstained` flag. A cited hedge ("The sources do not say who funded the probe") scored as an answered unanswerable question, which the report counted as a false positive, so the false positive count was itself inflated by right declines.
4. Claims were not checked. The report used the agent's own citation checks (`grounded`), which test that a quote appears in the passage, not that the passage supports the claim, and it never counted a wrong claim on an answerable question.

## What changed, and why

| Change | Where | Stops | Keeps right |
|---|---|---|---|
| Figures are numbers, matched at the rounding the answer states them at; a year is never a figure | `evaluation/domain/numeric.py` | "In 2025 revenue rose" passing for 2025 | "$94.9 billion", "$95 billion" and "$2.00 billion" for their figures |
| However coarse the rounding, a figure may be at most 5% off | `numeric.MAX_ROUNDING` | "$2 billion" passing for 2.4 billion (the answer's own rounding allowed half a billion either way) | "$2 billion" for 2.0 or 2.04 billion, "$95 billion" for 94.93 billion |
| A fact counts only where the answer asserts it: a mention inside a negated clause neither states a fact nor breaks a `must_not`, and the same holds for a comparison's order | `evaluation/domain/score.py`, `asserted` and `negated` | "It was not an Atlas V", "Juno didn't fly on an Atlas V" | "An Atlas V, not a Delta II", "Not a Delta II but an Atlas V", "There is no doubt it was an Atlas V", "Not only an Atlas V…" |
| A decline is the reply saying what the sources lack (its gaps, or the words), not only the `abstained` flag | `score.declined` | none directly; it removes the false "false positives" the baseline reported | cited hedges, declines that show the context they did find |
| A decline that goes on to make a claim the verifier rejects is a false answer | `score.score` | "The sources do not say. It was probably NASA." | a decline whose extra claims the verifier supports |
| Without a verifier, a decline that still shows claims is flagged (`hedged`), not failed | `score.score`, `summarise` | nothing is passed silently: the report counts them for review | declines that show context, which would otherwise fail |
| Every claim is checked by a claim verifier, the same port Answering uses in production | `evaluation/slices/run_set.py`, `evaluation/adapters/verifiers.py` | unsupported claims on any question, now counted as their own measure | |
| The lexical verifier checks years, and the source sentence that best matches a claim must agree with it on negation | `verifiers.LexicalVerifier` | "Juno was not launched on an Atlas V", "launched … in 2016" against a source that says 2011 | supported claims, figures and years |
| The report counts false answers, false abstentions and unsupported claims separately, with 95% intervals | `score.summarise` | the old single "false positive" that mixed right declines in | |
| A model grader (DeepEval's G-Eval and faithfulness, ADR-013), when a run asks for one, is reported beside the score and never changes it | `run_set.run` | a lenient judge passing a wrong answer | |

Two of the changes made in this branch before the review let false positives in, and the review found them with the corpus. Matching a figure at the answer's own rounding passed "$2 billion" for 2.4 billion until the 5% cap. Treating any decline as right passed a decline followed by a guess until verified claims were counted against it. The lexical verifier ignored "not" (a stop word) and never checked years until the review.

## What did not change

- The agent's own citation checks in Answering (`answering/domain/grounding.py`) are as they were: they test that a quote appears in its passage. The evaluation now measures what gets through them with a claim verifier, but production answers are not filtered by meaning. The Bedrock Guardrail adapter is the production route for that, behind the same ClaimVerifier port.
- The lexical verifier is a floor, not a judge of meaning: a paraphrase that swaps two entities named in the same passage can pass it. HHEM (`HhemVerifier`, the `verify` extra) is the meaning-level check. Its threshold should be calibrated on hand-labelled claims before it gates a release, and that has not been done.
- Negation is read from the clause before a mention, a deliberate trade. A negation after the mention ("Atlas V was not used") is not caught, and a negation that does not deny the fact ("no one doubts it was an Atlas V") can fail a right answer. The corpus pins the common phrasings both ways.

## How to check it

```
pytest tests/evaluation/unit/test_false_positives.py -v
```

Each case's name says what it guards. To add a failure mode, add a labelled case first, watch it fail, then change the scorer.
