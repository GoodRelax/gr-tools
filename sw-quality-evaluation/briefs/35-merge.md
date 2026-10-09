# merge -- group findings by root cause before refutation

Lens code: `MRG`. Region: ALL. You run after every agent that writes findings (waves 1-3) and before refutation.

Several lenses look at the same code from different sides, so one defect is often reported by several agents -- under different titles, severities and characteristics. That cross-confirmation is useful, but refuting and reporting each copy is waste and inflates the counts. You collapse them.

## Inputs

- `REPORT_DIR/findings/*.jsonl` (every agent's verdicts and findings)
- `REPORT_DIR/handoffs/*.jsonl` (observations agents made outside their own lens; may be absent)
- `REPORT_DIR/conformance/*.jsonl` (mode A: notes that cite existing finding ids)

You read the cited code lines only to decide whether two findings share a root cause. You do not evaluate anything new.

## Steps

1. **Cluster.** Two findings belong together when fixing one root cause in one place would fix both -- the same mechanism at the same location(s), whatever the lens, title or wording. Findings that merely sit in the same file, or that share a symptom with different causes, stay apart.
2. **Handoffs.** For each handoff: if a finding already covers it, add the handoff to that cluster's `members`. Otherwise make it a cluster of its own with `confidence: "plausible"` and `"origin":"handoff"` -- it will be refuted like any other.
3. **Severity and confidence of a cluster.** Take the highest severity that some member supports with a `confirmed` trace; if no member is confirmed, take the highest severity and set confidence `plausible`. When members disagree, record each member's severity in `severity_votes` and say in one line why the chosen one stands.
4. **Characteristics.** List every characteristic the members name; the first is the one most directly harmed.
5. Every finding id appears in exactly one cluster. Singletons are clusters too.

## Output -- `REPORT_DIR/clusters.jsonl`

```json
{"cluster":"C-001","title":"...","root_cause":"...","severity":"critical","confidence":"confirmed",
 "severity_votes":{"ORD-R01-001":"critical","NAM-R01-001":"major"},"severity_reason":"...",
 "characteristics":["functional-suitability","reliability"],"lenses":["ORD","NAM","ARC"],
 "members":["ORD-R01-001","NAM-R01-001","ARC-ALL-001"],"origin":"findings",
 "location":["node/reintegrate_to_html.js:208"],"scenario":"...","fix_direction":"...","items":["ORD-4","NAM-2"]}
```

Order by severity, then confidence. Write `title`, `root_cause`, `scenario`, `fix_direction`, `severity_reason` in OUTPUT_LANGUAGE.

Also write `REPORT_DIR/merge-summary.md` (at most 60 lines): finding count in, cluster count out, the five largest clusters with their member counts, and every severity disagreement.

Return: findings in, clusters out by severity, number of handoff-only clusters.
