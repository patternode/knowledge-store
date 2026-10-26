# Evaluation: enterprise-rag-bench-sample120 (enterprise-rag)

Run 2026-10-25T07:57:52+00:00.

| Measure | Value |
|---|---|
| Correct | 26 of 30 (0.867; 95% interval 0.703 to 0.947) |
| Mean score | 0.867 |
| Grounded (claims that passed the agent's own citation checks) | 1.0 |
| Cited an expected source | 1.0 |
| Citation precision, recall | 0.876, 0.733 |
| False answers: stated a fact for an unanswerable question | 0 |
| False abstentions: declined an answerable question | 4 |
| Unsupported claims: rejected by the claim verifier | 42 of 172 |
| Errors | 0 |
| Tokens (input, output) | 3473517, 65735 |

## By kind

| Kind | Questions | Correct | Mean score | Grounded |
|---|---|---|---|---|
| judged | 25 | 21 | 0.84 | 1.0 |
| list | 5 | 3 | 0.6 | 1.0 |
| multi-hop | 20 | 18 | 0.9 | 1.0 |
| unanswerable | 5 | 5 | 1.0 | None |

## Grader

A model's judgement, reported beside the score and never folded into it.

| Verdict | Questions |
|---|---|
| fail | 2 |
| partial | 6 |
| pass | 17 |
| skipped | 5 |

## Questions

| Id | Kind | Correct | Score | Grounded | Unsupported | Source | Missing or forbidden | Grade |
|---|---|---|---|---|---|---|---|---|
| qst_0313 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0316 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0319 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0321 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0323 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0325 | multi-hop | no | 0.0 | None |  |  |  | fail |
| qst_0330 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0332 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0342 | multi-hop | yes | 1.0 | 1.0 | 4 | yes |  | pass |
| qst_0351 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0352 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0359 | multi-hop | no | 0.0 | 1.0 | 5 | yes |  | partial |
| qst_0366 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | partial |
| qst_0367 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0368 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0369 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0370 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | partial |
| qst_0372 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0376 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0377 | multi-hop | yes | 1.0 | 1.0 | 4 | yes |  | partial |
| qst_0439 | list | yes | 1.0 | 1.0 | 1 | yes |  | partial |
| qst_0442 | list | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0448 | list | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0449 | list | no | 0.0 | None |  |  |  | fail |
| qst_0450 | list | no | 0.0 | 1.0 | 3 | yes |  | partial |
| qst_0484 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
| qst_0488 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
| qst_0489 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
| qst_0492 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
| qst_0500 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
