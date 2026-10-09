# synthesis -- merge, score, report

Lens code: `SYN`. Region: ALL. You read the files other agents wrote; you do not re-evaluate the code, except to settle a contradiction between two agents (read the cited lines only).

**Scores are computed, not judged.** You prepare the inputs, run `scripts/score_axes.py`, and write the report around its numbers. Never adjust a score by hand; if a score looks wrong, the inputs are wrong -- fix the inputs and run the script again.

## 1. Final findings -- `REPORT_DIR/findings/final.jsonl` and `findings/final.csv`

1. Load `clusters.jsonl` (the `merge` agent already grouped findings by root cause), every `refute/result-*.jsonl`, and any new findings the refuters wrote.
2. Apply refute outcomes to clusters: drop `rejected` ones (keep their count and ids for the appendix); apply new severity / confidence of `downgraded` and `upgraded` ones; where a refuter corrected a cluster's scenario, use the corrected one; clusters that were not refuted keep their values.
3. Add the refuters' new findings as clusters of their own -- unless the refuter says it shares the root cause of an existing cluster, in which case add it to that cluster's members.
4. **Tests absent.** If CODE_DIR contains no automated tests at all, add one finding for the whole code (`maintainability`, items `["STR-11"]`; `major` if the profile weights reliability or maintainability `high`, otherwise `minor`). Do not add one per region.
5. Renumber the result `F-001`, `F-002`, ... ordered by severity, then confidence, then the profile weight of the characteristic.

Every final row keeps everything a reader needs to check it -- **never drop the evidence**:

```json
{"id":"F-004","severity":"major","confidence":"confirmed",
 "characteristics":["reliability","interaction-capability"],"items":["CCH-2","CCH-4"],
 "title":"...","what":"...","scenario":"...","fix_direction":"...",
 "location":["src/rooms/availability_cache.py:15"],
 "evidence":"what was seen at the location","verified_by":"how it was confirmed (traced / probe on synthetic input / outside-scope evidence / refuter could not break it)",
 "independent_reports":2,"sources":{"cluster":"C-007","members":["CCH-R01-003","ORD-R01-005"]}}
```

`independent_reports` is the number of distinct lenses among the cluster's members. `items` is the union of the members' checklist items -- the scoring script uses it to place the finding on the design and hard-spot axes, so it must not be empty for a finding that a checklist item covers. Write the text fields in OUTPUT_LANGUAGE.

## 2. Scoring inputs, then run the script

Write these files in REPORT_DIR, then run `python <SKILL_DIR>/scripts/score_axes.py <REPORT_DIR> <SKILL_DIR>`:

| File | Content |
|---|---|
| `profile.json` | `{"weights": {...}}` -- copy the nine weights from `profile.md` (the `survey` agent may already have written it) |
| `verdict-overrides.jsonl` | One row `{"agent","item","verdict"}` for each PASS verdict a refuter overturned (`rejected`), with the verdict the counter-example supports (`MOSTLY`, `PARTIAL` or `FAIL`) |
| `axis-overrides.json` | `{"cannot_judge": {"<axis id>": "<reason>"}}` for each axis whose items were read on less than half of the in-scope code. **The naming axis is mandatory and may never appear here**: if naming coverage is short, tell the coordinator, who has the missing files read before you continue |
| `labels.json` | Translations into OUTPUT_LANGUAGE: `{"axes": {"<axis id>": "..."}, "charts": {"<chart id>": {"title": "...", "subtitle": "..."}}, "cannot_judge": "...", "not_applicable": "..."}`. Axis ids and English labels are in `<SKILL_DIR>/axes.json` |

Coverage for an axis counts only the files that axis applies to: for naming, every file with identifiers (source and tests, not stylesheets or data); for the other axes, the source files of the lenses that feed it. Lines an agent proved identical to lines it read fully (a diff) count as read.

The script writes `scores.json` (every axis score with how it was computed), `charts/product.svg`, `charts/design.svg` and `charts/hard-spots.svg`. It exits with an error if a mandatory axis could not be scored -- do not write the report until it runs clean.

How the script scores an axis (so you can explain it in the report):

1. **Checklist level**: verdicts score `PASS` 2, `MOSTLY` 1.5, `PARTIAL` 1, `FAIL` 0; the rate maps to a level (95% and no FAIL -> 10, 88% -> 9, 80% -> 8, 70% -> 7, 60% -> 6, 50% -> 5, 40% -> 4, 30% -> 3, 20% -> 2, below -> 1).
2. **Defect level**: from the axis's final findings, a `plausible` finding counted one severity lower. Two or more critical -> 2; one critical -> 3; majors -> 4 when there are 4 or more per 5,000 lines, 5 when 1 to 3 per 5,000 lines, 6 when fewer than one per 5,000 lines; otherwise by minor findings per 5,000 lines: none -> 10, 1-3 -> 9, 4-9 -> 8, 10-19 -> 7, 20 or more -> 6; an unconfirmed major (counted as minor) keeps the axis at 6 or below.
3. **Axis score** = the lower of the two. Both directions are fair: few defects cannot hide a design that ignores the principles, and good checklist results cannot hide confirmed defects.
4. **Design score** = the same calculation over all items and findings of the design chart together.

## 3. Rating words

Print every score with its word from `axes.json` (`scale`): 10 Outstanding, 9 Excellent, 8 Great, 7 Good, 6 Standard, 5 Tolerable, 4 Inadequate, 3 Poor, 2 Bad, 1 Unacceptable. When OUTPUT_LANGUAGE is Japanese, use the `ja` words of `axes.json` exactly -- they are fixed terms, not to be paraphrased; for other languages translate the English words. Always show the number next to the word. Print the scale table (score, word, English, guide) and the severity definitions near the end of page one.

## 4. The verdict on page one

### 4.1 Three headline answers

| Headline | Answer | Rule |
|---|---|---|
| **Design score** | 1-10 with its word | `design_score` from `scores.json` |
| **Can it be used now** | `Yes` | No critical finding and no major finding on a main function |
| | `With care` | No critical finding; every major finding occurs only under conditions users can avoid or will notice -- name the conditions |
| | `No` | A confirmed critical finding reachable in ordinary use, or a major finding on a main function that users cannot avoid |
| **Can it be maintained** | `Easily` | Maintainability scores 7 or more; risky behaviour is guarded by tests; change scenarios touch few, discoverable places |
| | `With effort` | Neither `Easily` nor `Hard` |
| | `Hard` | Maintainability scores 3 or less; or it scores 5 or less and at least two of: no tests on risky behaviour, one rule implemented in several places that already disagree, change scenarios touching many places a maintainer would miss |

### 4.2 Consistency check -- before you write

For each risk you will list on page one, ask: **would a user of this product meet it in ordinary use, with no way to avoid or notice it?** If yes for any risk, "Can it be used now" must be `No`, whatever else the page says. Then read your verdict paragraph against the risk table: a page that says "usable" above a risk that makes the product unusable is wrong. Fix the answer, not the risk.

### 4.3 The verdict paragraph

4 to 7 sentences in OUTPUT_LANGUAGE that a non-developer can follow:

1. The design score and its word, and whether it can be used now, as one plain statement.
2. What is good about it -- only strengths backed by evidence.
3. The main weakness and what it means for a user or a maintainer, in everyday words, with finding ids.
4. Whether it can be maintained, and why.
5. What it would take to improve the headline answers (which findings to fix).

Be frank: say plainly when the software is not fit for use. Never soften what the rules give, never make it harsher than the evidence. **Judge the code, not the people**: describe the code ("well structured", "prototype quality"), never the author's skill or experience.

### 4.4 Strengths

Up to five, each with its evidence (file:line, verdict, tool result or test). A report that lists only risks misleads as much as one that lists only praise. If the evidence supports no strength, say so.

## 5. Report -- `REPORT_DIR/REPORT.md`, in OUTPUT_LANGUAGE

**Follow the layout of `<SKILL_DIR>/briefs/report-sample.md`.** It shows a fictional product: copy its structure, never its numbers, findings or wording.

Page one, in this order:

1. Title: the product as the profile describes it (no internal codes).
2. **Three headline cards** -- design score, can it be used now, can it be maintained -- each with a one-line basis that names the rule that applied and the finding ids.
3. **The three radar charts side by side** (`charts/product.svg`, `charts/design.svg`, `charts/hard-spots.svg`) in one table row, each with its title and subtitle.
4. **Overall verdict** (4.3) and **strengths** (4.4).
5. **Main risks with evidence**: at most five rows -- finding id and severity, what happens in everyday words, location, how it was verified, how many lenses found it independently.

Then:

6. **Breakdown** -- one table per chart. Columns: the axis with the plain question it answers; (product chart only) importance for this product; score and word; one sentence saying what the score means here; how the score was computed (checklist counts and rate, defect counts, which one decided); the finding ids.
7. **How scores are computed** (section 2 in plain words), the **scale**, and the **severity definitions**.
8. Product profile; scope and coverage; functional correctness (conformance summary); architecture (scenarios and change scenarios); specification (mode A) or how much intent could be recovered (mode B); external standards (if any); items that could not be settled statically and what would settle them; limitations, including every piece of outside-scope evidence.
9. **Appendix A** -- all findings, one line each. **Appendix B** -- refuted clusters. **Appendix C** -- cross-confirmation counts.

Each critical and major finding is detailed in the body (what, scenario, location, evidence, how verified, fix direction). Minor and info findings appear only in Appendix A, with their full text in `final.csv`. Aim for under 500 lines. The number of findings stated must equal the rows of `final.jsonl`.

**Words in the report.** Use plain words only. Lens codes, item codes as headings, agent names and internal file names do not appear in the text a reader reads: say "the naming review" or "naming", not `NAM`; say "finding F-004", not `CCH-R01-003`. Item ids may appear only inside the "how computed" column and the appendices.

Return message: the three headline answers, the scores of every axis in one line per chart, the counts by severity, and any contradiction you could not settle.
