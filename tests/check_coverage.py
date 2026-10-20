"""Coverage floors per context and layer (docs/engineering-standard.md, section 7 rule 7).

    pytest --cov=knowledge_store --cov-report=json:coverage.json
    python tests/check_coverage.py coverage.json            # fails when a layer is below its floor
    python tests/check_coverage.py coverage.json --raise    # raises each floor to today's figure

A floor only rises: --raise never lowers one. Floors are whole percentages in
tests/coverage-floors.json, keyed "<context>/<layer>" (layer: domain, slices, ports, adapters,
contract), plus "apps" and "kernel".
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

FLOORS = Path(__file__).with_name("coverage-floors.json")
PACKAGE = "knowledge_store"
LAYERS = ("domain", "slices", "adapters")


def key_of(path: str) -> str | None:
    parts = Path(path).as_posix().split(f"/{PACKAGE}/", 1)[-1].split("/")
    if len(parts) == 1:
        return None
    context = parts[0]
    if context in ("apps", "kernel"):
        return context
    if parts[1] in LAYERS:
        return f"{context}/{parts[1]}"
    if parts[1] == "ports.py":
        return f"{context}/ports"
    return f"{context}/contract"


def figures(report: dict) -> dict[str, float]:
    covered, statements = defaultdict(int), defaultdict(int)
    for path, data in report["files"].items():
        key = key_of(path)
        if key is None:
            continue
        summary = data["summary"]
        covered[key] += summary["covered_lines"]
        statements[key] += summary["num_statements"]
    return {k: 100.0 * covered[k] / statements[k] for k in statements if statements[k]}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    now = figures(json.loads(Path(argv[0]).read_text()))
    floors = json.loads(FLOORS.read_text()) if FLOORS.exists() else {}
    if "--raise" in argv:
        raised = {k: max(floors.get(k, 0), math.floor(v)) for k, v in now.items()}
        FLOORS.write_text(json.dumps(dict(sorted(raised.items())), indent=2) + "\n")
        print(f"floors written to {FLOORS}")
        return 0
    failed = False
    for key in sorted(set(floors) | set(now)):
        value, floor = now.get(key), floors.get(key)
        if value is None:
            print(f"  {key:36} not measured (floor {floor}%)")
            continue
        status = "ok" if floor is None or value + 1e-9 >= floor else "BELOW"
        failed |= status == "BELOW"
        print(f"  {key:36} {value:6.1f}%  floor {floor if floor is not None else '-':>3}  {status}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
