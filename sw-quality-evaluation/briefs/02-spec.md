# SPEC -- evaluate the specification (mode A) or reconstruct it (mode B)

Lens code: `SPC`. Characteristic for findings: `specification` (mode A) or `maintainability` (mode B).

---

## Mode A -- evaluate the specification

Read every document that `map.md` classifies as `current specification` or `test specification`. Do not evaluate old versions, notes or samples; you may consult them only to understand a term. If a file cannot be read (format, encoding), list it in your notes and in coverage as `not_read`.

### A.1 Requirement list -- `REPORT_DIR/requirements.jsonl`

One row per requirement:

```json
{"id":"FR-012","location":"spec:requirements.md:140","kind":"functional","summary":"...","group":"G03"}
```

- Use the specification's own IDs. If requirements have none, assign `SPEC-0001`, `SPEC-0002`, ... in document order and give the location of each.
- `kind`: `functional`, `quality` (a target for one of the nine characteristics), `constraint`, `interface`, `state` (a state or transition definition).
- `summary`: at most 200 characters, in the specification's language.
- `group`: cut the list into groups of 30 to 60 requirements that belong together (same feature or component); merge smaller groups with a neighbour. Each group becomes one conformance agent.

Also write `REPORT_DIR/glossary.json`: the specification's defined terms, each with its location -- `{"term":"...","location":"spec:..."}`. Empty list if there is no glossary or defined vocabulary.

### A.2 Checklist

| Item | Check |
|---|---|
| SPC-1 | Each requirement is **unambiguous**: no untestable wording ("appropriately", "fast", "as needed", "user-friendly") without a measurable criterion; the actor and the action are explicit; no double negatives |
| SPC-2 | Each requirement is **verifiable**: a test or inspection could decide pass/fail |
| SPC-3 | Each requirement is **singular**: one requirement per statement |
| SPC-4 | The set is **consistent**: no two requirements give different results for the same situation; no requirement's precondition conflicts with another's behaviour |
| SPC-5 | **Single source**: the same requirement is not stated in two places that could drift; repeated content refers to one owner |
| SPC-6 | **Abnormal and boundary cases** are specified, as relevant to the product: time-out, interruption or cancellation, concurrent operation, missing permission, invalid or inconsistent data, resource exhaustion, minimum / maximum / empty / absent values |
| SPC-7 | **Quality requirements are measurable**: for every characteristic weighted `high` or `medium` in `profile.md`, there is a target with a number or a decidable condition. List each characteristic that lacks one -- later agents mark target-based checks for it `UNDETERMINED` |
| SPC-8 | **State behaviour is complete**: where the specification defines states, every state x event combination has a defined outcome (including "no change"), in a table or equivalent |
| SPC-9 | **Vocabulary**: one concept has one name, one name one concept; terms and abbreviations are defined |
| SPC-10 | **Traceable**: requirements have stable identifiers that code, tests and other requirements can cite; dependencies between requirements are stated |
| SPC-11 | **Negative requirements** ("must not ...") say what happens instead |
| SPC-12 | **Notation**: where the specification declares a notation for requirements or scenarios (listed as `spec notation` in `profile.md`), the requirements follow it |

Write verdict rows per item (region `ALL`). For FAIL, cite representative requirement locations; merge repeated instances of one problem into one finding with several locations.

---

## Mode B -- reconstruct the specification from the code (one agent per region)

The question is: **could a newcomer recover what this code is meant to do?** Write `REPORT_DIR/reconstructed/<REGION>.md`:

- Purpose of the region; the behaviours it provides; the data it owns; the states it tracks; its external interfaces; constraints it enforces (limits, timings, formats).
- Tag every statement with its source: `name`, `comment`, `test`, `structure` (evident from the code's shape), or `inferred` (your guess).

Also write `REPORT_DIR/requirements.jsonl` rows for the behaviours you recovered (append; ids `REC-<REGION>-NNN`, `kind` as in mode A, `group` = your region id).

| Item | Check |
|---|---|
| SPC-B1 | The purpose of each component is recoverable from names, comments or tests |
| SPC-B2 | Each non-obvious constant, limit or rule has a stated reason (a comment, a name, a test) |
| SPC-B3 | Intended behaviour at boundaries and in error cases can be told from tests or comments |
| SPC-B4 | Comments, test names and messages do not contradict the code |
| SPC-B5 | A newcomer can find where a given behaviour is implemented without reading everything (structure and naming lead there) |

Each place where intent cannot be recovered -- you can see what the code does but not what it is meant to do -- is a finding (`maintainability`, usually `minor`; `major` when the unclear code is on a path the profile rates risky).
A defect you trace while reconstructing -- the code produces a wrong result -- is not an intent finding: grade it by the common severity table, or put it in `REPORT_DIR/handoffs/SPEC-<REGION>.jsonl` if another lens owns it.
