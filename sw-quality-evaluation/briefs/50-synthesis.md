# SYNTH -- merge, rate, report

Lens code: `SYN`. Region: ALL. You read the files other agents wrote; you do not re-evaluate the code, except to settle a contradiction between two agents (read the cited lines only).

## 1. Merge -- `REPORT_DIR/findings/final.jsonl` and `findings/final.csv`

1. Load `clusters.jsonl` (MERGE already grouped findings by root cause), every `refute/result-*.jsonl`, and any new findings the refuters wrote (`findings/REF-*.jsonl`).
2. Apply refute outcomes to clusters: drop `rejected` ones (keep their count and ids for the appendix); apply new severity / confidence of `downgraded` and `upgraded` ones; where a refuter corrected a cluster's scenario, use the corrected one; clusters that were not refuted (minor, info) keep their values.
3. Add the refuters' new findings as clusters of their own -- unless the refuter says it shares the root cause of an existing cluster, in which case add it to that cluster's members.
4. Renumber the result `F-001`, `F-002`, ... ordered by severity, then confidence, then the profile weight of the characteristic. Keep the cluster id and member finding ids in a `sources` field.
5. **Tests absent.** If CODE_DIR contains no automated tests at all, add one finding for the whole code (`maintainability`; `major` if the profile weights reliability or maintainability `high`, otherwise `minor`). Do not add one per region.

## 2. Coverage per characteristic

Map lenses to characteristics:

| Characteristic | Lenses |
|---|---|
| functional suitability | CNF |
| performance efficiency | EFF, CCH |
| compatibility | STR |
| interaction capability | STR |
| reliability | BND, CCH, ORD, ROB |
| security | ROB, BND |
| maintainability | NAM, STR, ARC, SPC (mode B) |
| flexibility | STR, ARC |
| safety | ROB, ORD |

Coverage of a characteristic = in-scope lines that at least one of its lenses `read_fully`, divided by all in-scope lines (from `coverage/*.json` and `partition.json`). Lines an agent marked `read_partially` because it proved them identical to lines it read fully (a diff) count as read. State the method in the report.

## 3. Rating per characteristic -- by rule, not by impression

Apply the first rule that matches, using findings after refutation. **A finding counts toward its first characteristic only** (the one most directly harmed); its other characteristics are shown as "also affects" in the tables but do not lower their ratings -- otherwise one defect lowers several ratings at once.

| Rating | Rule |
|---|---|
| `not evaluated` | The profile weights the characteristic `n/a` |
| `poor` | At least one `critical` finding with confidence `confirmed` |
| `weak` | At least one `major` `confirmed`, or at least one `critical` `plausible` |
| `undetermined` | Coverage below 50%, or every checklist verdict for it is `UNDETERMINED` or `NA` |
| `good` | No finding above `info`, coverage at least 80%, and every checklist item for it is `PASS` or `NA` |
| `fair` | Otherwise |

Rate the five priority lenses (naming, boundaries, cache, ordering, efficiency) the same way, using the findings in which that lens is among the cluster's `lenses`, at the cluster's final severity (the defect's severity, not the lens's own vote), and that lens's verdicts.

There is **no total score.** Do not average ratings.

## 4. Report -- `REPORT_DIR/REPORT.md`, in OUTPUT_LANGUAGE

1. **Summary** -- mode; what was evaluated; the top risks (at most 5, each one sentence with its finding id); the rating table (nine characteristics with weight, rating, coverage; then the five priority lenses).
2. **Product profile and weights** -- from `profile.md`, with `stated` / `inferred` marks.
3. **Scope and coverage** -- regions evaluated and not evaluated, excluded paths, tools run and missing (from `tools/index.md`), measurements that are estimates, gaps (`gaps.md`).
4. **Priority lenses** -- naming, boundaries, cache, ordering, efficiency: for each, the checklist verdict table (aggregated over regions: PASS / FAIL / NA / UNDETERMINED counts per item) and its main findings.
5. **Functional correctness** -- mode A: the conformance table summarised by status, the list of `divergent` and `missing` requirements, unspecified behaviour. Mode B: mismatches between the code and its own claims.
6. **Other characteristics** -- per characteristic: rating, main findings.
7. **Architecture** -- summary of `architecture.md`: scenarios, risks, trade-offs, change scenarios.
8. **Specification** -- mode A: specification quality (SPC items, characteristics lacking measurable targets). Mode B: how much of the intent could be recovered from the code, and where it could not.
9. **External standards** -- mode A, if any overlays ran: each standard's derived checklist summary, marked `from memory`.
10. **Undetermined items** -- what static reading could not settle, and what would settle each (run a test, measure on the target, ask a stakeholder).
11. **Limitations** -- what this evaluation cannot show, and every piece of outside-scope evidence the agents used (from their notes), so the reader knows what was consulted beyond CODE_DIR and SPEC_DIR.

**Appendix A** -- all findings: id, characteristic, severity, confidence, location, title.
**Appendix B** -- refuted clusters: count and ids, by lens. **Appendix C** -- cross-confirmation: for each finding, how many independent agents reported it (from cluster members); a defect found by several lenses independently is stronger evidence.

Each finding in the body shows: id, severity, confidence, location(s), what, scenario, fix direction. **Keep REPORT.md readable: the body details every critical and major finding; minor and info findings appear only in Appendix A (one line each), with their full text in `final.csv`.** Aim for under 500 lines. The number of findings stated in the summary must equal the number of rows in `final.jsonl`.

Return message: the counts by severity, the rating table in one line per characteristic, and any contradiction you could not settle.
