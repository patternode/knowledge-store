# Evaluation: enterprise-rag-bench-sample120 (enterprise-rag)

Run 2026-10-25T06:48:13+00:00.

| Measure | Value |
|---|---|
| Correct | 115 of 120 (0.958; 95% interval 0.906 to 0.982) |
| Mean score | 0.958 |
| Grounded (claims that passed the agent's own citation checks) | None |
| Cited an expected source | 0.904 |
| Citation precision, recall | 0.885, 0.88 |
| False answers: stated a fact for an unanswerable question | 5 |
| False abstentions: declined an answerable question | 0 |
| Unsupported claims: rejected by the claim verifier | 0 of 0 |
| Errors | 0 |
| Tokens (input, output) | 0, 0 |

## By kind

| Kind | Questions | Correct | Mean score | Grounded |
|---|---|---|---|---|
| judged | 115 | 115 | 1.0 | None |
| lookup | 90 | 90 | 1.0 | None |
| list | 5 | 5 | 1.0 | None |
| multi-hop | 20 | 20 | 1.0 | None |
| unanswerable | 5 | 0 | 0.0 | None |

## Grader

A model's judgement, reported beside the score and never folded into it.

| Verdict | Questions |
|---|---|
| fail | 4 |
| partial | 10 |
| pass | 106 |

## Questions

| Id | Kind | Correct | Score | Grounded | Unsupported | Source | Missing or forbidden | Grade |
|---|---|---|---|---|---|---|---|---|
| qst_0011 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0020 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0026 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0027 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0035 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0038 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0039 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0054 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0056 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0066 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0067 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0073 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0075 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0078 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0081 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0086 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0089 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0090 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0092 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0095 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0097 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0100 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0101 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0104 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0107 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0110 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0114 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0119 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0121 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0123 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0131 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0144 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0145 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0147 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0148 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0150 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0152 | lookup | yes | 1.0 | None | 0 | yes |  | partial |
| qst_0163 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0170 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0179 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0180 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0181 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0192 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0198 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0199 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0204 | lookup | yes | 1.0 | None | 0 | no |  | partial |
| qst_0208 | lookup | yes | 1.0 | None | 0 | no |  | partial |
| qst_0211 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0212 | lookup | yes | 1.0 | None | 0 | no |  | pass |
| qst_0214 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0216 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0222 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0224 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0228 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0229 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0231 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0234 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0238 | lookup | yes | 1.0 | None | 0 | no |  | pass |
| qst_0241 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0244 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0248 | lookup | yes | 1.0 | None | 0 | yes |  | partial |
| qst_0251 | lookup | yes | 1.0 | None | 0 | no |  | partial |
| qst_0252 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0257 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0262 | lookup | yes | 1.0 | None | 0 | no |  | fail |
| qst_0263 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0268 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0270 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0273 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0276 | lookup | yes | 1.0 | None | 0 | no |  | pass |
| qst_0282 | lookup | yes | 1.0 | None | 0 | no |  | partial |
| qst_0285 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0291 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0292 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0295 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0297 | lookup | yes | 1.0 | None | 0 | no |  | partial |
| qst_0299 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0300 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0313 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0316 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0319 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0321 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0323 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0325 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0330 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0332 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0342 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0351 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0352 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0359 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0366 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0367 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0368 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0369 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0370 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0372 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0376 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0377 | multi-hop | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0384 | lookup | yes | 1.0 | None | 0 | yes |  | partial |
| qst_0404 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0406 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0409 | lookup | yes | 1.0 | None | 0 | no |  | fail |
| qst_0411 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0420 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0423 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0428 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0439 | list | yes | 1.0 | None | 0 | yes |  | partial |
| qst_0442 | list | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0448 | list | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0449 | list | yes | 1.0 | None | 0 | no |  | fail |
| qst_0450 | list | yes | 1.0 | None | 0 | yes |  | partial |
| qst_0459 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0460 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0462 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0470 | lookup | yes | 1.0 | None | 0 | yes |  | pass |
| qst_0484 | unanswerable | no | 0.0 | None | 0 |  | false answer | pass |
| qst_0488 | unanswerable | no | 0.0 | None | 0 |  | false answer | fail |
| qst_0489 | unanswerable | no | 0.0 | None | 0 |  | false answer | pass |
| qst_0492 | unanswerable | no | 0.0 | None | 0 |  | false answer | pass |
| qst_0500 | unanswerable | no | 0.0 | None | 0 |  | false answer | pass |
