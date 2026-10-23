# claim-chart

**Interactive patent claim charts in one offline HTML file.**

Each claim is split into a tree of conditions (AND / OR / NOT) without changing a single character
of the claim. You mark each condition True, False or TBD against your product, and the verdict of
every branch, claim and patent follows. An AI agent can add provisional answers, each with a
verbatim quote from your specification as evidence, and a machine translation can sit beside the
original. The page saves itself with your marks, and exports / imports JSON for AI tools.

> This tool only assists in judging whether a product falls within a patent. Translations are
> machine translations (for reference). Ask a patent attorney or another expert for the final judgment.

Sample: open [`samples/sample-claim-chart.html`](samples/sample-claim-chart.html) in a browser —
two expired US patents (US 5,946,647 and US 8,046,721) compared with a made-up device
([`samples/target-sample/device-spec.md`](samples/target-sample/device-spec.md)).

## What the page does

- Tabs: an overview, then one tab per patent (full number). Clicking a verdict in the overview opens that claim.
- Each claim: the original text on one side, the tree on the other; clicking either one finds the other.
- Colours: True pink, False green, TBD orange, No need grey ("No need" = TBD that can no longer change the result).
- Filters: TBD / True / False / No need, branches only or from the trunk, AI reasons on/off.
- Two layers: the person's answers and the AI's provisional answers; "Adopt" copies the AI's where you still have TBD.
- Original / translation / both; Japanese or English menus; light and dark; font sizes; resizable panes.
- Save as `.html` (opens where you left it), export / import JSON (`schema/claim-chart-result.schema.json`).

## Use with an AI agent (Claude Code skill)

Copy this folder to `~/.claude/skills/claim-chart/`. Then ask, for example:

- "Does this specification fall under any patent?" (searches, lists candidates, you pick)
- "Make a claim chart of US 8,046,721 and JP<number> against `docs/spec`."
- Paste text that contains claims and ask for a claim chart.

`SKILL.md` describes the dialog and the workflow; `references/` holds the procedures.
Outputs are written only to a git-ignored folder: research results should not be published.

## Build by hand

```text
python -I scripts/build.py OUT.html samples/src-US5946647 samples/src-US8046721
```

A patent folder holds `claims.txt`, `meta.json`, `tree.json`, summary files, and optionally
`tr.<lang>.json` and `ai.json`; see `schema/` and `DESIGN.md`. The build refuses any tree that does
not join back to the exact claim text, any translation that drops a branch, and any AI evidence
quote that is not in its file.

## Tests

```text
python -I tests/test_build.py
CC_NODE_MODULES=<node_modules with playwright and ajv> node tests/ui.test.js
```

## Platform / Requirements

- Python 3.9+ (standard library only) to build
- Any modern browser to view (no server, no network)
- Playwright and Ajv only for the page tests
