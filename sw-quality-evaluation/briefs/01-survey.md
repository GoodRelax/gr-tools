# survey -- map, profile, partition, tool runs

You run first and alone. Every later agent starts from what you write, so be accurate rather than fast.

## 1. Map -- `REPORT_DIR/map.md`

- Languages and line counts (non-blank), per top-level directory.
- **Excluded from evaluation**, each with its reason: version-control metadata, vendored third-party code, generated code, build output, dependency caches, binary assets, and REPORT_DIR itself if it lies inside CODE_DIR. Name how you recognised each (a generator header, a lock file, a directory convention).
- Components: the units the code is organised into (by directory, package, module or build target), one line each saying what it does.
- Entry points: where control enters (main functions, request handlers, interrupt or event handlers, scheduled jobs, public library API, UI event handlers).
- External interfaces: files, databases, network protocols, devices, other processes, environment variables, configuration.
- Dependency directions between components (from a tool if available, otherwise from imports/includes), and any cycles.
- Tests: where they are, roughly what they cover, what framework.

### 1.1 Specification map (mode A) -- in `map.md`

Classify every document in SPEC_DIR: `current specification`, `test specification` (expected behaviour stated as tests -- counts as specification), `old version` (superseded; give the evidence: a dated file name, an `old` folder, a newer file with the same title), `note or review`, `sample or build output`, `unreadable`. Only `current specification` and `test specification` are evaluated.
**If no document is a current specification or a test specification, write `NO_SPEC` on the first line of `map.md` with the reason.** The coordinator then switches to mode B.

## 2. Product profile -- `REPORT_DIR/profile.md`

Mode A: derive from the specification (read its overview, scope and quality requirements; you need not read every requirement). Mode B: infer from the code. Mark every statement `stated (<location>)` or `inferred (<from what>)`.

- What the product is and who uses it.
- Runtime environment: resource limits, real-time or latency constraints, connectivity, concurrency model, single or multi-user.
- **Harm class**: the worst plausible consequence of a defect -- inconvenience, financial loss, exposure of personal data, data loss, physical harm. Say why.
- Expected life and how updates reach users (continuous deployment, store release, field update, never).
- Mode A: **external standards the specification names** (any standard, regulation or coding guideline). List each with the spec location. These start overlay agents; do not list standards the spec does not name. Classify each before listing it:
  - `external standard` -- a document outside the specification that the product must comply with. **Only these start overlay agents.**
  - `own rule` -- a rule the specification writes out itself (naming rules, design principles, a language or character-set rule), even when it cites a well-known principle by name. It is a requirement: it goes to `requirements.jsonl` and is checked by conformance, not by an overlay.
  - `spec notation` -- a syntax used to write the specification (a requirement template, a scenario language). The `spec-review` agent checks that the specification follows it.
  - `withdrawn` -- named but stated elsewhere in the specification to be dropped. No overlay; the `spec-review` agent reports the contradiction if both statements stand.

**Weights.** Give each of the nine ISO/IEC 25010:2023 characteristics a weight -- `high`, `medium`, `low` or `n/a` -- with a one-line reason tied to the profile:
functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility, safety.

Also write the weights to `REPORT_DIR/profile.json` for the scoring script, using the axis ids of `axes.json`:

```json
{"weights": {"functional-suitability": "high", "performance-efficiency": "low", "compatibility": "medium", "interaction-capability": "medium", "reliability": "high", "security": "medium", "maintainability": "medium", "flexibility": "low", "safety": "n/a"}}
```

## 3. Partition -- `REPORT_DIR/partition.json`

Cut the in-scope code into **regions** that one agent can read thoroughly: about 5,000 non-blank lines each, never splitting a file, keeping a component together where possible. Tests go with the code they test.

```json
{"regions":[
  {"id":"R01","paths":["src/core/"],"lines":4210,"components":["core"],
   "risk":"high","risk_reasons":["parses external input","holds shared mutable state"]}
 ],
 "excluded":[{"path":"vendor/","reason":"vendored third-party"}]}
```

Rank risk `high` / `medium` / `low` from: handling of external input, shared or long-lived state, concurrency or event handling, resource handling, complexity hot spots (from the tool output), and relevance to the worst harm class.

## 4. Tool runs -- `REPORT_DIR/tools/`

Run the tools from `tools.md` that are present and relevant, once, for the whole in-scope code, and save their raw output here, so that the lens agents do not rerun them. Never use a fixing mode. Typical set:

| Output file | Purpose |
|---|---|
| `tools/size.*` | Lines per file and language |
| `tools/complexity.*` | Per-function complexity and length |
| `tools/duplication.*` | Copy-paste clones |
| `tools/spelling.*` | Misspelled words, including inside identifiers |
| `tools/secrets.*` | Credentials and keys committed in the code |
| `tools/identifiers.txt` | Every identifier with its kind, scope and location (tags generator or AST tool; else a regex approximation, marked as such) |
| `tools/deps.*` | Component or module dependency graph |
| `tools/lint-<tool>.*` | Language linters and pattern scanners that run without the project's dependencies |

Write `tools/index.md`: for each run, the tool, version, exact command, exit status, and whether the output is complete. List the tools you wanted but did not have.

In every file you write, give paths relative to CODE_DIR, SPEC_DIR or REPORT_DIR -- never absolute local paths, which leak user names. Tool outputs that contain absolute paths are rewritten after the run.

## 5. Findings

You are not a lens agent; write findings only for things nobody else will see -- for example committed secrets (from the secrets scan) or a dependency cycle between components. Use lens code `SRV`. No verdict rows are required of you.

## 6. Return

Also state in your return message: the number of regions, how many are `high` risk, the mode-A standards list, and any tool that failed.
