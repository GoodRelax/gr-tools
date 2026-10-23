# Claim chart — design

A claim chart breaks each patent claim into a tree of conditions (AND / OR / NOT) and lets a
person mark every condition True, False or TBD against a product. The verdict of every branch,
claim and patent follows from those marks. The output is one self-contained `.html` page that
works offline and can be saved with its marks, plus a JSON form of the same result for AI tools.

> This tool only assists in judging whether a product falls within a patent. Translations are
> machine translations (for reference). The final judgment belongs to a patent attorney or
> another expert. (The page shows this once, in the disclaimer line, and nowhere else.)

## 1. Principles

| Principle | How it is enforced |
|---|---|
| The claim text is never reworded. | `build.py` joins every tree back and compares it with the claim, character for character. |
| The AI only parses; it does not decide. | The tree is structure only. AI answers are a separate, provisional layer (`ai.json`) that a person adopts or not. |
| Every AI answer shows where it came from. | Each piece of evidence is a verbatim quote; `build.py` finds it in the cited file and computes its line. |
| A description that is missing is not a "no". | AI rule: what the target does not describe is TBD, never False. |
| Translations are references only. | They sit next to the original, in a different colour; `build.py` checks that they keep the tree's holes. |
| Research results stay private. | Outputs go to a git-ignored folder (`temp/`); nothing about a real product is published. |

## 2. Files

```text
SKILL.md                 how an AI agent runs the whole job (dialog, workflow, rules)
DESIGN.md                this file
scripts/build.py         the build (Python 3, standard library only)
scripts/template.html    the page; build.py embeds the data into it
schema/                  JSON Schemas of every input and of the result
  meta.schema.json         meta.json        bibliographic data
  tree.schema.json         tree.json        the claim trees
  translation.schema.json  tr.<lang>.json   machine translation (optional)
  ai.schema.json           ai.json          AI provisional checks (optional)
  claim-chart-result.schema.json            export / import format of the page
references/              fetching texts, splitting rules, translation, AI checks, searching
samples/                 two expired US patents compared with a made-up device, and the built page
tests/test_build.py      build tests: the samples build; each kind of broken input is refused
tests/ui.test.js         page tests in headless Chromium (Playwright, Ajv)
tests/fixtures/          a made-up claim with a NOT, a reference and an optional clause
temp/                    git-ignored; real research results live here or in another ignored folder
```

A patent source folder `src-<ID>/` holds `claims.txt` (the claims, verbatim, each after a header
line such as `【請求項１】` or `1.`), `meta.json`, `tree.json`, the summary text files that
`meta.json` names (first line = heading), and optionally `tr.<lang>.json` and `ai.json`.

Build: `python -I scripts/build.py OUT.html src-A src-B ...` (one page, one tab per patent).

## 3. The build pipeline

| Step | Function | What it guarantees |
|---|---|---|
| read | `split_claims`, `expand` | claims split at header lines; the short JSON form becomes full nodes |
| verify | `verify_text`, `verify_shape` | tree text == claim text; references point to earlier claims; a NOT wraps one plain list of leaves |
| annotate | `annotate` | labels (`1`, `1A`, `1A.2`, ...) and spans `[s, e)` in the claim text |
| explain | `explain_negations` | each leaf under a NOT gets `ie`: the negation with only that leaf filled in |
| check | `load_translations`, `load_ai` | translation holes, line and paragraph counts match; every AI quote exists |
| write | `write_html` | data and result schema embedded; `<` escaped so JSON cannot end its `<script>` |

Any problem raises `BuildError`; the build prints it and writes nothing.

## 4. Splitting a claim into a tree

These rules keep the split mechanical (anyone applying them gets the same tree):

1. A claim is an AND. A preamble ("…であって、", "…, comprising:") is a leaf.
2. Elements are the clauses separated by "と、", "し、", "であり、", ";" and the like; each is a child of the AND.
3. Inside a clause, a list joined by "又は / 若しくは / or / at least one of" is an OR; one joined by "及び / 並びに / and" is an AND.
   If the clause has wording of its own besides the list, that node is `own` and takes a check too.
   Two items that are the object of one act ("selection of a structure and an action") stay in one leaf.
4. A negation that wraps one list is a NOT over that list; its leaves are read as negated sentences
   (shown as "i.e., …") and the list flips (De Morgan). A negation over two or more lists stays one leaf.
5. A clause with a condition ("…場合に限り", "if …", "when …") is one leaf, lists included. Exception:
   when the condition is only a list of events ("detects at least one of A, B and C"), it is an OR marked
   `alt` (its scope reads two ways), and the person can switch it to AND.
6. An optional clause ("…てもよく", "may …") is `P`: always True.
7. "請求項 n に記載の / of claim n" is `R`: it mirrors claim n.
8. Not one character changes.

## 5. Evaluation

| Node | True | False | otherwise |
|---|---|---|---|
| AND | all children True | any child False | TBD |
| OR | any child True | all children False | TBD |
| NOT | its list (with the gate flipped) is True | … False | TBD |
| `own` node | its own check AND its gate | | |
| `P` optional | always True | | |
| `R` reference | the cited claim's value | | |
| patent | any claim True | all claims False | TBD |

**No need** is a display category, not a value: a TBD whose ancestors are already decided by a
sibling (an AND with a False child, an OR with a True child, a patent with a True claim).
`markRelevant` computes it top-down; the filter treats it as a fourth category.

There are two layers of answers, computed independently: the person's (`S.checks`) and the
AI's (`ai.json`, or AI fields read from JSON). `S.ui.view` picks the one that colours the page;
"adopt" copies AI answers into the person's layer where the person still has TBD.

## 6. The page (`template.html`)

The script is split into numbered sections; each has one job.

| Section | Content |
|---|---|
| 1 boot and state | `DATA` (embedded by the build), `S` (saved state, with every key of `S.ui` documented), `UI` (not saved) |
| 2 texts | every visible word, Japanese and English (`t(key)`) |
| 3 helpers | escaping, `act()` for controls, badges |
| 4 index | `P[id]`: patents with `byId`, `byN`, `nodes`; nodes get `parent`, `depth`, `kids`, `text` |
| 5 evaluation | `answer`, `val`, `markRelevant`, `cat`, `worth`, `counts`, filters, translation lookup |
| 6 rendering | `render()` redraws everything from `S`; one function per part of the page |
| 7 actions | every control has `data-act="name"`; `ON_CLICK`, `ON_CHANGE`, `ON_INPUT` map the name to its effect |
| 8 bars | resizing the claim text pane and the claim boxes |
| 9 save and JSON | save the page with its state; export and import `claim-chart-result/1` |

Rendering is a pure function of `S` and `UI`, so any change is "update `S`, call `render()`".
Saving writes the page captured at load time (`PRISTINE`) with only the state block replaced.

### Extending

| To add | Do |
|---|---|
| a control | add its words to `TXT` (both languages), draw it in `controlsHtml` with `act("name")`, handle `name` in `ON_CLICK` / `ON_CHANGE`; if it must persist, give it a documented default in `S.ui` |
| a node kind | `expand` and `verify_shape` in `build.py`, `schema/tree.schema.json`, `val` and `gateHtml` in the page, section 5 of this file |
| a translation language | a `tr.<lang>.json` per patent; add the language name to `LANG_NAMES` |
| a menu language | a new key in `TXT` and in the menu select |
| a field in the result JSON | `exportJson`, `importJson` (if it may be read back), `schema/claim-chart-result.schema.json` |
| a test | `tests/ui.test.js` (`check(name, ok, detail)`) or `tests/test_build.py` (`broken(name, edit, expect)`) |

## 7. Result JSON

`claim-chart-result/1` lists every node of every claim with its verbatim `text`, the person's
`check`, the AI's `aiCheck` / `aiReason` / `aiEvidence`, computed `value` / `aiValue`,
`worthChecking`, `memo` and `tr`. On import the page reads back only `check`, `reading`, `memo`,
the AI fields and `tr`, and skips a node whose `text` differs from the claim, so an answer cannot
land on the wrong words. AI quotes and translations read from JSON are shown as not verified,
because only the build can check them against their sources.

## 8. Tests

```text
python -I tests/test_build.py
CC_NODE_MODULES=<folder with playwright and ajv> node tests/ui.test.js
```

Both exit non-zero on any failure. Run them after every change.
