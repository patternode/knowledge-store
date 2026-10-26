# Evaluation: enterprise-rag-bench-sample120 (enterprise-rag)

Run 2026-10-26T03:04:26+00:00.

| Measure | Value |
|---|---|
| Correct | 21 of 23 (0.913; 95% interval 0.732 to 0.976) |
| Mean score | 0.913 |
| Grounded (claims that passed the agent's own citation checks) | 0.997 |
| Cited an expected source | 1.0 |
| Citation precision, recall | 0.827, 0.696 |
| False answers: stated a fact for an unanswerable question | 0 |
| False abstentions: declined an answerable question | 2 |
| Unsupported claims: rejected by the claim verifier | 57 of 173 |
| Errors | 0 |
| Tokens (input, output) | 4359422, 76497 |

## By kind

| Kind | Questions | Correct | Mean score | Grounded |
|---|---|---|---|---|
| judged | 23 | 21 | 0.913 | 0.997 |
| lookup | 6 | 5 | 0.833 | 1.0 |
| list | 5 | 5 | 1.0 | 1.0 |
| multi-hop | 12 | 11 | 0.917 | 0.995 |

## Grader

A model's judgement, reported beside the score and never folded into it.

| Verdict | Questions |
|---|---|
| fail | 1 |
| partial | 6 |
| pass | 16 |

## Questions

| Id | Kind | Correct | Score | Grounded | Unsupported | Source | Missing or forbidden | Grade |
|---|---|---|---|---|---|---|---|---|
| qst_0342 | multi-hop | yes | 1.0 | 1.0 | 5 | yes |  | pass |
| qst_0351 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | partial |
| qst_0352 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0359 | multi-hop | no | 0.0 | 1.0 | 7 | yes |  | pass |
| qst_0366 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0367 | multi-hop | yes | 1.0 | 1.0 | 4 | yes |  | pass |
| qst_0368 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0369 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0370 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0372 | multi-hop | yes | 1.0 | 0.941 | 1 | yes |  | pass |
| qst_0376 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0377 | multi-hop | yes | 1.0 | 1.0 | 5 | yes |  | pass |
| qst_0384 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0404 | lookup | no | 0.0 | None |  |  |  | fail |
| qst_0411 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | partial |
| qst_0420 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | partial |
| qst_0423 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0428 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0439 | list | yes | 1.0 | 1.0 | 1 | yes |  | partial |
| qst_0442 | list | yes | 1.0 | 1.0 | 6 | yes |  | pass |
| qst_0448 | list | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0449 | list | yes | 1.0 | 1.0 | 3 | yes |  | partial |
| qst_0450 | list | yes | 1.0 | 1.0 | 1 | yes |  | partial |
