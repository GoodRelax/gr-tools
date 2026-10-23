---
name: claim-chart
description: Build an interactive patent claim chart (infringement / freedom-to-operate check) as one offline HTML page plus JSON. Each claim is split into an AND/OR/NOT tree without changing a single character; a person marks every condition True/False/TBD; optional AI provisional checks quote verbatim evidence from the product's spec or code; optional machine translation sits beside the original. Use when the user asks whether a product, specification or code may fall within a patent, asks for a claim chart (クレームチャート, 侵害対比表, 該否判定, 特許に当たらないか調べて), gives patent numbers to analyse, or pastes text that contains patent claims.
---

# claim-chart

Turns patent claims into a checkable tree and writes `claim-chart-<ids>.html` (plus the JSON
the page exports). `SKILL_DIR` below is the folder of this file.

## Rules that always hold

1. **Research results are private.** Write every output (patent texts, trees, AI checks, the HTML)
   only into a folder that git ignores. Before the first write, run
   `git -C <folder> check-ignore -q <folder>/x` (exit 0 = ignored). If it is not ignored, do not
   write; ask the user where to put it. Never commit, push, paste into a PR, issue or public page
   anything about which patent was checked against which product.
2. **The claim text is never changed.** Copy it verbatim from the publication and verify it
   (see `references/sources.md`). The tree only cuts the text; `build.py` refuses any difference.
3. **The AI parses; the person decides.** AI answers go only into `ai.json` as a provisional layer,
   each with verbatim evidence. Something the target does not describe is `tbd`, never `false`.
4. **Not legal advice.** The page says so. Say it again when you report a result.
5. **Ask one question at a time**, in the user's language, with 2–4 options and your recommendation
   first. Take a stated preference as the answer and do not ask again.

## Dialog

First decide the entry from what the user said (ask only if unclear):

| Entry | The user says | You do |
|---|---|---|
| ① from a specification | "does this spec / product / code fall under any patent?" | search → candidate table → the user picks → chart them |
| ② from numbers | "chart US 8,046,721 and JP<number>" | fetch the texts → chart them |
| ③ from text | pastes text with claims | chart the pasted claims (the paste is the original) |

Then ask, one by one, only what is still open:

| Question | Options | Recommend |
|---|---|---|
| What to compare with | path of a spec or code; or none (no AI checks) | the user's spec if one was mentioned |
| Countries (entry ①) | JP, US, EP, CN, IN (several) | JP and US |
| Translation | Japanese, English, none ("none" only when the original is Japanese or English) | the user's language |
| Legal status (entry ①) | in force only / all | in force only |
| Which candidates to chart (entry ①) | pick from the table / top N | pick from the table |
| Output folder | a git-ignored folder | `temp/claim-chart-<date>/` of the repository being compared (after the check-ignore test) |

## Workflow

For each patent, make one source folder `src-<ID>/` in the output folder (`<ID>` = the full
number, e.g. `JP0000000`, `US5946647`; it becomes the tab name):

1. **Text** — `claims.txt` (the claims, each after its header line `【請求項１】` or `1.`) and the
   summary sections (problem / solution / effect, first line = heading), copied and verified as in
   `references/sources.md`. Record where and when in `meta.json` (`schema/meta.schema.json`).
2. **Tree** — write `tree.json` by the rules in `references/tree-rules.md`
   (`schema/tree.schema.json`). Then build; if `build.py` reports a difference, fix the tree, never
   the text.
3. **Translation** (if asked) — `tr.<lang>.json` by `references/translation.md`.
4. **AI provisional checks** (if there is a target) — `ai.json` by `references/ai-checks.md`.
   Record the target's version (repository, branch, `git rev-parse --short HEAD`) in `target`.
5. **Build**:

   ```text
   python -I SKILL_DIR/scripts/build.py <out>/claim-chart-<ids>.html <out>/src-<ID> [<out>/src-<ID2> ...]
   ```

   It prints one line per check and writes nothing if anything is wrong.

Entry ① first writes `candidates.md` in the output folder (see `references/search.md`) and waits
for the user to choose.

## Reporting back

Tell the user, in their language and briefly:

- the path of the HTML (and that it is in a git-ignored folder);
- per patent: claims charted, the AI provisional verdict, and the decisive rows (label, wording,
  evidence) — these are what to look at first;
- what was not checked: countries or sources not searched, applications too recent to be
  published (about 18 months), evidence the target did not have;
- that the final judgment belongs to a patent attorney or another expert.

To revise later: the user can export JSON from the page; an AI may change `check`, `aiCheck`,
`aiReason`, `aiEvidence`, `memo` or `tr` in it and the user imports it back
(`schema/claim-chart-result.schema.json`).

## Files

| Path | Role |
|---|---|
| `scripts/build.py`, `scripts/template.html` | the build and the page |
| `schema/` | formats of every input and of the result |
| `references/` | how to fetch texts, split claims, translate, write AI checks, search |
| `samples/` | two expired US patents compared with a made-up device (`samples/target-sample/`) |
| `tests/` | `python -I tests/test_build.py`; `node tests/ui.test.js` (Playwright, Ajv) |
| `DESIGN.md` | how it works and how to extend it |
