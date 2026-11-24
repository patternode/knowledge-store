"""Numbers in an answer: kept in the kernel (knowledge_store.kernel.numeric), since Answering's
support check and Evaluation's scorer read figures the same way. Re-exported here for the scorer."""

from knowledge_store.kernel.numeric import MAX_ROUNDING, NUMBER, SCALES, matches, stated  # noqa: F401
