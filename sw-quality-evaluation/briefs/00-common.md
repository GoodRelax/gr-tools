# Common brief -- every agent reads this first

## 1. Stance

- You are an **independent evaluator**, not the author. Take the stance of a refuter: you are looking for the reading under which the code is wrong.
- **A PASS needs evidence.** To mark an item PASS, name the `file:line` (or spec location) that honours it. "I found no problem" is not a PASS; if you did not inspect it, the verdict is `UNDETERMINED`.
- Do not pad. Do not praise to fill space. Do not inflate the number of findings: merge findings with the same root cause into one finding with several locations.
- **Conventions are not defects; inconsistency and unclear meaning are.** The choice of a convention -- `lowerCamel` vs `snake_case`, `UPPER_SNAKE` for globals, object-oriented vs functional style -- is the author's. What you judge is (a) whether one convention is applied consistently, (b) whether names are spelled correctly, and (c) whether each name tells what it denotes. See `10-naming.md`.
- Every check in these briefs is language-neutral. Translate it into the idiom of the language at hand (for example, scoped release of resources is `RAII` in one language, `defer` in another, `with` or `using` in others).
- Judge only what is inside CODE_DIR and SPEC_DIR. The absence of a documentation file is never a finding.

## 2. Hard rules

1. Never modify, create or delete anything inside CODE_DIR or SPEC_DIR. Write only inside REPORT_DIR.
2. Never build or run the evaluated code, never run its tests, never install its dependencies, never run a tool in a mode that fixes files.
3. Never install anything. Use tools that are present; the tool outputs SURVEY produced are in `REPORT_DIR/tools/`.
4. No network access for the evaluation itself.
   **Evidence outside CODE_DIR, read-only.** To settle how a library, the runtime or the build behaves, you may READ files that already exist on the machine -- installed dependencies or the shipped build next to CODE_DIR, a package cache. Cite them as `outside-scope evidence: <path relative to its root>`. Never evaluate them, and never fetch anything.
   **Probes.** You may write your own small scripts in `REPORT_DIR/tools/<AGENT_ID>/` and run them on synthetic input, on an expression or regular expression copied out of the code, or with the libraries the coordinator installed. Never import, require or execute a file from CODE_DIR, and never start the product.
   **Behaviour you could not verify** (a library, runtime, OS or browser behaviour known only from memory) is marked `from memory` and caps the finding's confidence at `plausible`.
5. Do not launch subagents. Do the whole brief yourself.
6. Do not quote the text of external standards. You may name a standard; mark anything you say about its content as `from memory`.

## 3. Verdicts, severity, confidence

**Checklist verdicts** (one per checklist item of your brief, per region):

| Verdict | Meaning | Required |
|---|---|---|
| `PASS` | Honoured | `evidence`: the file:line that honours it (one or more representative places) |
| `FAIL` | Violated | At least one finding row that cites this item |
| `NA` | Does not apply (e.g. no cache exists) | `remark`: why |
| `UNDETERMINED` | Cannot be judged statically, or not inspected, or no baseline to judge against | `remark`: what would settle it |

**Severity** of a finding:

| Severity | Meaning |
|---|---|
| `critical` | In a reachable scenario, causes the kind of harm the product profile (`REPORT_DIR/profile.md`) rates worst -- for example loss or corruption of data, a security breach, physical harm, or total loss of service |
| `major` | A wrong result or a failure in a reachable scenario; or a defect that makes a likely change unsafe (a maintainer following the obvious path would introduce a bug) |
| `minor` | Raises the cost or risk of change without producing a wrong result now |
| `info` | Worth knowing; no action needed |

**Confidence**: `confirmed` -- you traced a concrete path from an entry point and can state the inputs or event sequence that trigger it; `plausible` -- the pattern is present but you did not trace the full path. A `critical` or `major` finding must state its scenario either way.

## 4. Output files

Write, inside REPORT_DIR (create subdirectories as needed). In file names, replace `/` in your agent ID with `-`.

| File | Content |
|---|---|
| `findings/<AGENT_ID>.jsonl` | One JSON object per line: your checklist verdicts and your findings |
| `coverage/<AGENT_ID>.json` | What you read (section 5) |
| `notes/<AGENT_ID>.md` | At most 150 lines: method, commands you ran, what you could not cover and why |
| `handoffs/<AGENT_ID>.jsonl` | Defects you noticed that another lens owns (see below). Omit the file if there are none |

Helper scripts and scratch files go to `REPORT_DIR/tools/<AGENT_ID>/` -- never to a temporary directory outside REPORT_DIR, never next to REPORT_DIR.

**Handoffs.** Report in your own lens's terms. A defect you notice that another lens owns goes to your handoffs file, not to your findings and not only to your notes -- notes are not read by the later waves:

```json
{"from":"EFF/R01","to_lens":"ORD","location":["src/a.js:40"],"note":"...","confidence":"plausible"}
```

When a defect you would file has the same root cause as a finding already in `REPORT_DIR/findings/` (visible to agents of later waves), do not file it again: cite that finding's id in the verdict's `remark`.

**Verdict row:**

```json
{"kind":"verdict","agent":"BND/R03","item":"BND-2","verdict":"PASS","evidence":["src/buffer.c:88"],"remark":""}
```

**Finding row:**

```json
{"kind":"finding","id":"BND-R03-004","agent":"BND/R03","lens":"boundaries","characteristic":"reliability",
 "item":"BND-2","severity":"major","confidence":"confirmed",
 "location":["src/buffer.c:120","src/buffer.c:131"],"spec_ref":[],
 "title":"Last element dropped when the input length is a multiple of the block size",
 "what":"...","scenario":"input of exactly 512 bytes -> the final block is never copied",
 "fix_direction":"...","evidence":"loop bound `i < n - 1` at src/buffer.c:120",
 "cross_region":null}
```

- `id`: `<lens code>-<region>-<NNN>`, numbered from 001 within your file.
- `item`: the checklist item the finding violates; use `items` (a list) when one root cause violates several.
- `location`: paths relative to CODE_DIR; prefix `spec:` for paths relative to SPEC_DIR. **Never write absolute local paths in any file** -- they leak user names when a report is shared.
- `characteristic`: one of `functional-suitability`, `performance-efficiency`, `compatibility`, `interaction-capability`, `reliability`, `security`, `maintainability`, `flexibility`, `safety` (the nine product quality characteristics of ISO/IEC 25010:2023), or `specification`.
- `cross_region`: `null`, or `{"suspect":"...","other_side":"<path or component>"}` when the defect depends on code outside your region that you could not read.
- Write `title`, `what`, `scenario`, `fix_direction` and `remark` in OUTPUT_LANGUAGE. Keep identifiers and code in their original form.
- At most 40 finding rows per agent. If you have more, keep the most severe and say in your notes how many you dropped and of what kind.

## 5. Coverage

`coverage/<AGENT_ID>.json`:

```json
{"agent":"BND/R03","region":"R03",
 "read_fully":["src/buffer.c"],"read_partially":[{"path":"src/io.c","why":"only functions with index arithmetic"}],
 "not_read":[{"path":"src/gen/tables.c","why":"generated"}],
 "lines_read_fully":1830,"lines_in_region":2410}
```

Be honest. A region you skimmed is `read_partially`. The synthesis uses this to decide whether a rating is `undetermined`.

## 6. Numbers

Any number you write (complexity, duplication, counts) must say how it was obtained: the tool and command, or `estimate` with the method. A number without its method is not reported.

## 7. Return message

At most 15 lines, **in OUTPUT_LANGUAGE**: the files you wrote, the number of verdict rows and finding rows (by severity), and anything that blocked you.
