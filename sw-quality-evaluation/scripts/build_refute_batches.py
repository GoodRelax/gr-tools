"""Build refute batches from MERGE output.

Usage: python build_refute_batches.py <REPORT_DIR> [batch_size]

Selects every cluster of severity critical or major, every cluster kept below a
higher severity vote (upgrade candidate), plus every PASS verdict on a
priority-lens item, and writes REPORT_DIR/refute/batch-NN.jsonl files of at most
batch_size rows (default 15). Clusters come first so that the most severe rows are
refuted by the earliest batches.
"""
import json
import pathlib
import sys

# Items that feed the hard-spot axes of axes.json; their PASS verdicts are refuted.
PRIORITY_LENS_PREFIXES = ("NAM-", "BND-", "CCH-", "ORD-", "EFF-", "ROB-")


def read_jsonl(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main():
    report_dir = pathlib.Path(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    clusters = read_jsonl(report_dir / "clusters.jsonl")
    selected = [dict(c, refute_kind="cluster") for c in clusters
                if c.get("severity") in ("critical", "major")]
    # A cluster kept below a member's higher (but unconfirmed) vote is refuted as an
    # upgrade candidate, so that the higher severity is either traced or dropped.
    rank = {"info": 0, "minor": 1, "major": 2, "critical": 3}
    for c in clusters:
        votes = (c.get("severity_votes") or {}).values()
        top = max((rank.get(v, 0) for v in votes), default=0)
        if c.get("severity") not in ("critical", "major") and top >= rank["major"] > rank.get(c.get("severity"), 0):
            selected.append(dict(c, refute_kind="upgrade-candidate"))

    for findings_file in sorted((report_dir / "findings").glob("*.jsonl")):
        for row in read_jsonl(findings_file):
            if (row.get("kind") == "verdict" and row.get("verdict") == "PASS"
                    and str(row.get("item", "")).startswith(PRIORITY_LENS_PREFIXES)):
                selected.append(dict(row, refute_kind="pass", source_file=findings_file.name))

    out_dir = report_dir / "refute"
    out_dir.mkdir(exist_ok=True)
    batches = [selected[i:i + batch_size] for i in range(0, len(selected), batch_size)]
    for number, batch in enumerate(batches, 1):
        path = out_dir / f"batch-{number:02d}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in batch),
                        encoding="utf-8")
    kinds = {}
    for r in selected:
        kinds[r["refute_kind"]] = kinds.get(r["refute_kind"], 0) + 1
    print(f"selected by kind: {kinds}, batches: {len(batches)}")


if __name__ == "__main__":
    main()
