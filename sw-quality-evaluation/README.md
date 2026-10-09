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

The report opens with three headline answers and three radar charts side by side:

| Headline | Meaning |
|---|---|
| Design score | 1-10, computed from the design chart |
| Can it be used now? | Yes / With care (conditions named) / No |
| Can it be maintained? | Easily / With effort / Hard |

| Chart | Axes |
|---|---|
| Product quality: can it be used? | The nine characteristics of ISO/IEC 25010:2023 |
| Design and construction: is it well engineered? | Responsibility, API and boundaries, layers and dependencies, no duplication, state handling, tests, simplicity |
| Hard spots: are the error-prone parts right? | Naming (mandatory), boundaries (off-by-one), caches and copies, ordering, efficiency, error paths and clean-up, string boundaries, numbers and units, time and dates, sharing and mutability |

Behind them: functional correctness (requirement by requirement in mode A; the code against its own names, comments and tests in mode B), architecture by quality and change scenarios, the specification itself (mode A) or how much intent the code reveals (mode B), and external standards only when the specification names them.

## How it keeps the evaluation fair and honest

- **Scores are computed, not judged.** Agents decide each checklist verdict (PASS / MOSTLY / PARTIAL / FAIL) and each finding's severity; `scripts/score_axes.py` turns them into 1-10 scores with the rules in `axes.json`. An axis scores the lower of its checklist level and its defect level; defect counts are taken per 5,000 lines so that size alone does not lower a score; an unconfirmed finding counts one severity lower. Both 10 and 1 are reachable.
- **The ten-level scale** (`axes.json`): 10 Outstanding, 9 Excellent, 8 Great, 7 Good, 6 Standard, 5 Tolerable, 4 Inadequate, 3 Poor, 2 Bad, 1 Unacceptable, with fixed Japanese terms for Japanese reports.
- **Severity**: minor -- no real harm; major -- leads to a defect or a large maintenance burden; critical -- leads to an outage, data corruption or a security incident, including a main function that silently gives wrong results.
- A PASS needs the location that honours the check; "found nothing" is `UNDETERMINED`, not PASS.
- Findings reported by several lenses are merged by root cause first; the number of lenses that found each one independently is kept as cross-confirmation.
- Every serious finding and every PASS on a hard-spot item is re-checked once by a different agent that tries to refute it; a finding held below a higher, unconfirmed vote is re-checked for an upgrade.
- Page one is checked for consistency: it cannot say "usable" above a risk that users meet in ordinary use.
- The report judges the code, never the people who wrote it, and lists strengths as well as risks.

## Files

| File | Role |
|---|---|
| `SKILL.md` | Coordinator: inputs, team, waves, checks |
| `briefs/00-common.md` | Rules, verdicts, severities and file formats every agent follows |
| `briefs/01-survey.md` | Map, product profile, partition into regions, tool runs |
| `briefs/02-spec.md` | Specification evaluation (A) or reconstruction (B) |
| `briefs/03-conformance.md` | Functional correctness |
| `briefs/10-naming.md` ... `13-ordering.md`, `16-efficiency.md` | The five priority lenses |
| `briefs/14-robustness.md`, `15-structure.md` | Error paths, time, numbers, strings, security; structure and tests |
| `briefs/17-component-design.md` | Design of each component: responsibility, name, interface |
| `briefs/20-architecture.md` | Quality and change scenarios |
| `briefs/21-overlay.md` | External standards named by the specification |
| `briefs/30-cross-region.md` | Defects that cross region borders |
| `briefs/35-merge.md` | Group findings by root cause before refutation |
| `briefs/40-refute.md` | Independent refutation |
| `briefs/50-synthesis.md` | Final findings, scoring inputs, headline answers, report layout |
| `briefs/report-sample.md` | Page-one layout sample on a fictional product (format only) |
| `axes.json` | The three charts, their axes, the checklist items behind each axis, the scale and the counting rules |
| `tools.md` | Open-source static tools and the rules for running them |
| `scripts/check_wave.py` | Coordinator's check after each wave: parse, counts, FAIL without a finding, PASS without evidence |
| `scripts/build_refute_batches.py` | Builds refutation batches from the merged clusters |
| `scripts/score_axes.py` | Computes every axis score and the design score, and draws the charts |
| `scripts/radar_chart.py` | Draws one radar chart as SVG (no third-party packages) |
| `scripts/sanitize_paths.py` | Removes absolute local paths from a report directory |
| `trial-runs/` | Reports from trial runs of this prompt; `trial-runs/.tools/` (locally installed tools) is git-ignored |

## Limits

- Static reading cannot prove the absence of defects, and cannot measure run-time performance; those items come out as `UNDETERMINED` with what would settle them.
- Statements about external standards come from the model's memory, not from the standards' text, and are marked so.
- Cost grows with the code: roughly eight lens agents per region of about 5,000 lines, plus fixed agents.
