# Evaluation: enterprise-rag-bench-sample120 (enterprise-rag)

Run 2026-10-25T00:31:03+00:00.

| Measure | Value |
|---|---|
| Correct | 105 of 120 (0.875; 95% interval 0.804 to 0.923) |
| Mean score | 0.875 |
| Grounded (claims that passed the agent's own citation checks) | 0.996 |
| Cited an expected source | 0.99 |
| Citation precision, recall | 0.912, 0.928 |
| False answers: stated a fact for an unanswerable question | 0 |
| False abstentions: declined an answerable question | 2 |
| Unsupported claims: rejected by the claim verifier | 132 of 386 |
| Errors | 13 |
| Tokens (input, output) | 14319712, 186028 |

## By kind

| Kind | Questions | Correct | Mean score | Grounded |
|---|---|---|---|---|
| judged | 115 | 103 | 0.896 | 0.996 |
| lookup | 90 | 83 | 0.922 | 0.994 |
| list | 5 | 1 | 0.2 | 1.0 |
| multi-hop | 20 | 19 | 0.95 | 1.0 |
| unanswerable | 5 | 2 | 0.4 | None |

## Grader

A model's judgement, reported beside the score and never folded into it.

| Verdict | Questions |
|---|---|
| fail | 1 |
| partial | 10 |
| pass | 94 |
| skipped | 2 |

## Questions

| Id | Kind | Correct | Score | Grounded | Unsupported | Source | Missing or forbidden | Grade |
|---|---|---|---|---|---|---|---|---|
| qst_0011 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0020 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0026 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0027 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0035 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0038 | lookup | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0039 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0054 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0056 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0066 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0067 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0073 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0075 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0078 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0081 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0086 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0089 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0090 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0092 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0095 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0097 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0100 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0101 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0104 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0107 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0110 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0114 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0119 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0121 | lookup | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0123 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0131 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0144 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0145 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0147 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0148 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0150 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0152 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0163 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0170 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0179 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0180 | lookup | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0181 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0192 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0198 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0199 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0204 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | partial |
| qst_0208 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0211 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0212 | lookup | yes | 1.0 | 0.529 | 5 | yes |  | pass |
| qst_0214 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0216 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0222 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0224 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0228 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0229 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0231 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | partial |
| qst_0234 | lookup | no | 0.0 | 1.0 | 1 | no |  | partial |
| qst_0238 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0241 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0244 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0248 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0251 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0252 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0257 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0262 | lookup | no | 0.0 | None |  |  | error: The question could not be answered. Try again later. |  |
| qst_0263 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0268 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0270 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0273 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0276 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0282 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0285 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0291 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0292 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0295 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0297 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0299 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0300 | lookup | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0313 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0316 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0319 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0321 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0323 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0325 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | partial |
| qst_0330 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0332 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0342 | multi-hop | yes | 1.0 | 1.0 | 6 | yes |  | pass |
| qst_0351 | multi-hop | yes | 1.0 | 1.0 | 5 | yes |  | pass |
| qst_0352 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0359 | multi-hop | no | 0.0 | 1.0 | 6 | yes |  | partial |
| qst_0366 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0367 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | pass |
| qst_0368 | multi-hop | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0369 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0370 | multi-hop | yes | 1.0 | 1.0 | 1 | yes |  | partial |
| qst_0372 | multi-hop | yes | 1.0 | 1.0 | 3 | yes |  | partial |
| qst_0376 | multi-hop | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0377 | multi-hop | yes | 1.0 | 1.0 | 6 | yes |  | pass |
| qst_0384 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0404 | lookup | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0406 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0409 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | fail |
| qst_0411 | lookup | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0420 | lookup | yes | 1.0 | 1.0 | 2 | yes |  | partial |
| qst_0423 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | partial |
| qst_0428 | lookup | yes | 1.0 | 1.0 | 1 | yes |  | pass |
| qst_0439 | list | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0442 | list | no | 0.0 | None |  |  | error: The question could not be answered. Try again later. |  |
| qst_0448 | list | yes | 1.0 | 1.0 | 2 | yes |  | pass |
| qst_0449 | list | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0450 | list | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0459 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0460 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0462 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | pass |
| qst_0470 | lookup | yes | 1.0 | 1.0 | 0 | yes |  | partial |
| qst_0484 | unanswerable | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0488 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
| qst_0489 | unanswerable | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
| qst_0492 | unanswerable | yes | 1.0 | None |  |  |  | skipped |
| qst_0500 | unanswerable | no | 0.0 | None |  |  | error: The model call budget for this question was spent before an answer. |  |
