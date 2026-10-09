# Coordinator check: parse findings, count by severity, flag FAIL verdicts without a finding, count cross-region suspects.
import json, sys, pathlib, collections
rd = pathlib.Path(sys.argv[1])
total = collections.Counter(); xreg = 0
# A FAIL may cite a finding filed by another agent (same root cause, not re-filed); collect every finding id first.
known_ids = set()
for f in (rd / "findings").glob("*.jsonl"):
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            if r.get("kind") == "finding": known_ids.add(r.get("id"))
        except Exception: pass
for f in sorted((rd / "findings").glob("*.jsonl")):
    rows = []
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except Exception as e: print(f"PARSE ERROR {f.name}:{n} {e}")
    fnd = [r for r in rows if r.get("kind") == "finding"]
    ver = [r for r in rows if r.get("kind") == "verdict"]
    sev = collections.Counter(r.get("severity") for r in fnd); total.update(sev)
    cited = set()
    for r in fnd:
        it = r.get("item") or r.get("items") or []
        cited.update(it if isinstance(it, list) else [it])
    def cites_known(v):
        text = json.dumps(v, ensure_ascii=False)
        return any(i and i in text for i in known_ids)
    orphan = [v["item"] for v in ver if v.get("verdict") == "FAIL" and v["item"] not in cited and not cites_known(v)]
    nopass = [v["item"] for v in ver if v.get("verdict") == "PASS" and not v.get("evidence")]
    x = sum(1 for r in fnd if r.get("cross_region")); xreg += x
    print(f"{f.name}: verdicts={len(ver)} findings={len(fnd)} {dict(sev)} xreg={x}" + (f" FAIL-without-finding={orphan}" if orphan else "") + (f" PASS-without-evidence={nopass}" if nopass else ""))
print("TOTAL", dict(total), "cross_region suspects:", xreg)
