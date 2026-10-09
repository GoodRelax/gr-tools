# conformance-check -- functional correctness

Lens code: `CNF`. Characteristic: `functional-suitability`.
Inputs: `REPORT_DIR/requirements.jsonl`, `REPORT_DIR/map.md`, and in EXTRA your requirement group (mode A) or region (mode B).

---

## Mode A -- requirement to implementation

For **each requirement in your group**, find the code that implements it and decide:

| Status | Meaning |
|---|---|
| `implemented` | The code does what the requirement says, including the cases it names. Cite the implementing location |
| `partial` | Some cases are handled, others not. Name the missing case |
| `divergent` | The code does something different. Give the scenario: input or event sequence -> what the spec says -> what the code does |
| `missing` | No implementation found. Say where you searched (directories, search terms) |
| `undetermined` | Cannot be decided statically (depends on timing, hardware, data you do not have), or the requirement is too ambiguous to judge (cite the SPC finding if one exists) |

Also note, per requirement, whether a test exercises it (cite `file:line`) -- you do not run the tests; you read them.

Write one row per requirement to `REPORT_DIR/conformance/<AGENT_ID>.jsonl`:

```json
{"req":"FR-012","status":"divergent","location":["src/order.c:210"],"test":["tests/order_test.c:55"],"note":"..."}
```

Every `partial`, `divergent` and `missing` is also a finding row in your findings file (severity by the common brief; `spec_ref` = the requirement id) -- **unless an existing finding already has the same root cause**: then cite that finding's id in the row's `note` and do not file it again.

**Reverse direction.** While reading the code for your group, note behaviour that no requirement asks for and that is user-visible or changes stored data. Report it as one `info` or `minor` finding each ("unspecified behaviour"), not as a defect of the code.

If the specification defines state transition tables for your group, check every cell (state x event) against the code, including cells that should produce "no change".

## Mode B -- the code against its own claims

There is no specification; the code's claims are the reference. In your region, check that the code does what these say:

- names of functions and types (a function named as a query must not change state; a name that promises validation must validate),
- comments and documentation comments,
- test names and their assertions,
- user-facing and log messages,
- README or other documents inside CODE_DIR, where they describe behaviour.

Also use `REPORT_DIR/reconstructed/<REGION>.md` and your region's `REC-` rows.

Each mismatch is a finding with its scenario. A comment that is merely stale (describes old behaviour, harmless) is `minor`; a mismatch that would mislead a caller into a wrong result is `major`.

## Checklist

| Item | Check |
|---|---|
| CNF-1 | Every requirement (mode A) / every claim checked (mode B) in scope has a status |
| CNF-2 | No `divergent` or `missing` item |
| CNF-3 | Abnormal and boundary cases named by the requirement are handled |
| CNF-4 | Each requirement weighted by the profile as risky has a test that exercises it |
