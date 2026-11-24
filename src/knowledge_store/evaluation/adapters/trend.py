"""A static trend page across evaluation runs: the quality dashboard, with no service behind it.

One row per run, oldest first, with accuracy and its interval, false answers, unsupported claims
and retrieval recall, and a small line for accuracy and recall at 10. It reads the runs the run
store kept and writes one HTML file, which can be published on the repository's Pages site.
"""

from __future__ import annotations

import html


def _line(values: list[float | None], width: int = 240, height: int = 48) -> str:
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(pts) < 2:
        return ""
    step = width / max(1, len(values) - 1)
    coords = " ".join(f"{i * step:.1f},{height - v * height:.1f}" for i, v in pts)
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">'
            f'<polyline fill="none" stroke="currentColor" stroke-width="2" points="{coords}"/></svg>')


def trend_html(runs: list[dict], title: str = "Evaluation trend") -> str:
    runs = sorted(runs, key=lambda r: r.get("when", ""))
    rows, acc, rec = [], [], []
    for r in runs:
        s = (r.get("summary") or {}).get("all") or {}
        acc.append(s.get("accuracy"))
        rec.append(s.get("recall_at_10"))
        ci = s.get("accuracy_ci95")
        rows.append("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in (
            r.get("when", "")[:19], r.get("set", ""), s.get("accuracy"),
            f"{ci[0]} to {ci[1]}" if ci else "", s.get("false_answers"), s.get("unsupported_claims"),
            s.get("recall_at_10"), s.get("reciprocal_rank"))) + "</tr>")
    head = "".join(f"<th>{h}</th>" for h in ("Run", "Set", "Accuracy", "95% interval", "False answers",
                                              "Unsupported claims", "Recall at 10", "Reciprocal rank"))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:.4rem;text-align:left}}
.lines{{display:flex;gap:2rem;margin:1rem 0}}</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="lines"><div>Accuracy<br>{_line(acc)}</div><div>Recall at 10<br>{_line(rec)}</div></div>
<table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>
<p>Deterministic scores only; a model-graded score, where one ran, is in each run's own report.</p>
</body></html>
"""
