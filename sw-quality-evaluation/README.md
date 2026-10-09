# sw-quality-evaluation

A Claude Code prompt (usable as a skill) that evaluates the quality of a software product **from its source code and, when available, its specification** -- independent of language, platform and application domain.

It runs a team of subagents, each with one narrow job, and writes a report. It never modifies, builds or runs the evaluated code.

## What it answers

| You give | Mode | Question |
|---|---|---|
| code directory + specification directory | A | Does the code do what the specification says, and how good are the product and its specification? |
| code directory only | B | Could a new team take over this code from the code alone and keep maintaining it safely? |

Everything inside the code directory counts as code: source, tests, comments, READMEs, build configuration. The absence of a documentation file is never held against the code.

## How to run

In Claude Code, either:

- install the folder as a skill (copy it to `~/.claude/skills/sw-quality-evaluation/` or to a project's `.claude/skills/`) and ask: *"Evaluate the software quality. Code: `<dir>`. Spec: `<dir>`."*, or
- without installing, ask: *"Follow `<path to this folder>/SKILL.md`. Code: `<dir>`. Spec: `<dir>`."*

Leave out the spec directory for mode B. The report is written in the language you ask in.

Before starting, the coordinator lists the open-source static tools that are missing and would help, and asks whether to install them. For large code it tells you how many agents it plans to launch and asks before fanning out.

## What it looks at

- **Five priority lenses**, each with its own agents: **naming** (does the name tell what it denotes; is one convention applied consistently), **boundaries** (off-by-one), **caches** (any copy that must stay in sync with a source of truth), **ordering** (does the code stay correct when events arrive reversed, duplicated, late or interleaved), **efficiency** (is heavy work done in the complexity class it could be -- no O(N^2) where O(N log N) or O(log N) is at hand).
- **The nine product quality characteristics of ISO/IEC 25010:2023**, weighted per product from a profile the first agent derives (what the product is, its runtime, the worst harm a defect could cause).
- **Functional correctness**: requirement-by-requirement against the specification (mode A), or the code against its own names, comments and tests (mode B).
- **Architecture** by quality scenarios and change scenarios.
- **The specification itself** (mode A), by the properties of good requirements; or how much intent can be recovered from the code (mode B).
- **External standards** only when the specification names them.

## How it keeps the evaluation honest

- A PASS needs the location that honours the check; "found nothing" is `UNDETERMINED`, not PASS.
- Findings reported by several lenses are merged by root cause first; the number of agents that found each one independently is kept as cross-confirmation.
- Every serious finding and every priority-lens PASS is then re-checked once by a different agent that tries to refute it; a finding held below a higher, unconfirmed vote is re-checked for an upgrade.
- Ratings follow a fixed rule from the findings and the coverage; there is no total score.
- Every number states how it was measured; numbers not measured by a tool are marked as estimates.

## Files

| File | Role |
|---|---|
| `SKILL.md` | Coordinator: inputs, team, waves, checks |
| `briefs/00-common.md` | Rules, verdicts, severities and file formats every agent follows |
| `briefs/01-survey.md` | Map, product profile, partition into regions, tool runs |
| `briefs/02-spec.md` | Specification evaluation (A) or reconstruction (B) |
| `briefs/03-conformance.md` | Functional correctness |
| `briefs/10-naming.md` ... `13-ordering.md`, `16-efficiency.md` | The five priority lenses |
| `briefs/14-robustness.md`, `15-structure.md` | The remaining characteristics |
| `briefs/20-architecture.md` | Quality and change scenarios |
| `briefs/21-overlay.md` | External standards named by the specification |
| `briefs/30-cross-region.md` | Defects that cross region borders |
| `briefs/35-merge.md` | Group findings by root cause before refutation |
| `briefs/40-refute.md` | Independent refutation |
| `briefs/50-synthesis.md` | Merge, rating rule, report outline |
| `tools.md` | Open-source static tools and the rules for running them |
| `scripts/check_wave.py` | Coordinator's check after each wave: parse, counts, FAIL without a finding, PASS without evidence |
| `scripts/build_refute_batches.py` | Builds refutation batches from the merged clusters |
| `trial-runs/` | Reports from trial runs of this prompt; `trial-runs/.tools/` (locally installed tools) is git-ignored |

## Limits

- Static reading cannot prove the absence of defects, and cannot measure run-time performance; those items come out as `UNDETERMINED` with what would settle them.
- Statements about external standards come from the model's memory, not from the standards' text, and are marked so.
- Cost grows with the code: roughly seven lens agents per region of about 5,000 lines, plus fixed agents.
