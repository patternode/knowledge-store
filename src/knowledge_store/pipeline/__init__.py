"""The pipeline steps. Each is idempotent: rerunning it does no work for content already
processed, so the one scheduled or event-triggered sweep (run.py) is also the recovery path."""
