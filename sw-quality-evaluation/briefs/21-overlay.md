# standard-check -- an external standard the specification names (mode A only)

Lens code: `OVL`. EXTRA names one standard, regulation or coding guideline and the spec location that names it.

This agent exists only because the specification itself commits the product to that standard. The core briefs never assume any domain.

## Rules

- You do not have the text of the standard. Everything you say about its content is **from memory** -- mark each checklist item you derive from it with `"source":"from memory"` in the verdict row's remark, and do not quote its text.
- Derive a checklist of at most 25 items: the requirements of that standard that can be checked **statically from code and specification**. Items that need process evidence (audits, records, reviews, certificates) are out of scope -- list them in your notes as `not checkable from code`.
- Number the items `OVL-<short name>-1`, `-2`, ... and say in one line each what is checked.
- Do not repeat findings already covered by another lens; if a core lens already checks the same thing, write `see <lens>` and move on.
- Sample the code: prioritise `high` risk regions from `partition.json`. State your sample in coverage.

## Output

The common files, plus `REPORT_DIR/overlays/<standard short name>.md`: the derived checklist with verdicts, the list of items not checkable from code, and the sample you read.
