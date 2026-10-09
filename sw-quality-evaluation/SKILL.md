---
name: sw-quality-evaluation
description: Evaluate the quality of a software product from its source code and, when available, its specification -- independent of language, platform and domain. Use when asked to assess, audit or review the overall quality, maintainability, robustness or spec conformance of a codebase. Takes a code directory (required) and a specification directory (optional), runs a team of subagents, and writes a report. Never modifies the evaluated files.
---

# Software quality evaluation -- coordinator

You are the **coordinator**. You do not evaluate code yourself.
You prepare the run, launch subagents in waves, check that each one delivered, and hand the user the report.
Keep your own context small: read agents' short return messages and count rows in their files; do not read their findings in full.

---

## 1. Inputs

The user supplies **only** these two. Ask for CODE_DIR if it is missing; ask for nothing else.

| Input | Required | Meaning |
|---|---|---|
| `CODE_DIR` | yes | The directory holding the product. Everything inside it counts as "code": source, tests, comments, READMEs, build and tool configuration. |
| `SPEC_DIR` | no | The directory holding the specification, in any file format. |

Derive everything else:

| Derived | Rule |
|---|---|
| `MODE` | `A` if SPEC_DIR is given and holds at least one readable document; otherwise `B`. |
| `OUTPUT_LANGUAGE` | The natural language the user wrote the request in. |
| `SKILL_DIR` | The directory that contains this file. |
| `REPORT_DIR` | If the user names a place for the report, `<that place>/<CODE_NAME>-<YYYYMMDD-HHMM>`, where CODE_NAME is the last two segments of CODE_DIR joined by `-` (so that `.../app/src` gives `app-src`, not a bare `src`). Otherwise `sw-quality-report-<YYYYMMDD-HHMM>` in the current working directory. If the current working directory is inside CODE_DIR or SPEC_DIR, create it next to CODE_DIR instead: `<parent of CODE_DIR>/<name of CODE_DIR>-quality-report-<YYYYMMDD-HHMM>`. |

Resolve all four directories to absolute paths before launching any agent.

**MODE can change after SURVEY.** SURVEY maps SPEC_DIR as well. If it reports that SPEC_DIR holds no specification (only samples, build output, notes, or old versions), switch to mode B, record the reason in `REPORT_DIR/gaps.md`, and tell the user in the final message.

## 2. The question the report answers

| Mode | Question |
|---|---|
| A | Does the code do what the specification says, and how good are the product and its specification? |
| B | Could a new team take over this code **from the code alone** and keep maintaining it safely? |

Only what is inside CODE_DIR and SPEC_DIR is evaluated.
**The absence of a documentation file -- a README, a design document, a contribution guide -- is never a finding.** Judge whether the code itself lets a reader understand and change it.

## 3. Hard rules for the whole run

These are repeated in `briefs/00-common.md`, which every agent reads.

1. Nothing inside CODE_DIR or SPEC_DIR is modified, created or deleted. All output goes to REPORT_DIR.
2. The evaluated code is never built or run, its tests are never run, and its dependencies are never installed: build scripts, install hooks and tests execute arbitrary code with unknown side effects.
3. Static tools are used as far as possible (section 5). Installing a tool needs the user's approval.
4. There is no total score. Ratings are per characteristic and follow the rule in `briefs/50-synthesis.md`.

## 4. The team

| Agent ID | Brief | Wave | How many |
|---|---|---|---|
| `SURVEY` | `briefs/01-survey.md` | 1 | 1 |
| `SPEC` | `briefs/02-spec.md` | 2 | Mode A: 1 (evaluates the spec). Mode B: 1 per region (reconstructs the spec). |
| `NAM/<region>` | `briefs/10-naming.md` | 2 | 1 per region |
| `BND/<region>` | `briefs/11-boundaries.md` | 2 | 1 per region |
| `CCH/<region>` | `briefs/12-cache.md` | 2 | 1 per region |
| `ORD/<region>` | `briefs/13-ordering.md` | 2 | 1 per region |
| `ROB/<region>` | `briefs/14-robustness.md` | 2 | 1 per region |
| `STR/<region>` | `briefs/15-structure.md` | 2 | 1 per region |
| `EFF/<region>` | `briefs/16-efficiency.md` | 2 | 1 per region |
| `ARCH` | `briefs/20-architecture.md` | 2 | 1 |
| `OVL/<standard>` | `briefs/21-overlay.md` | 2 | Mode A only: 1 per external standard the specification names. None otherwise. |
| `NAM/GLOBAL` | `briefs/10-naming.md` (global part) | 3 | 1 |
| `CONF/<group>` | `briefs/03-conformance.md` | 3 | Mode A: 1 per requirement group. Mode B: 1 per region. |
| `XREG/<lens>` | `briefs/30-cross-region.md` | 3 | 1 per lens that reported cross-region suspects |
| `MERGE` | `briefs/35-merge.md` | 4 | 1 |
| `REFUTE/<batch>` | `briefs/40-refute.md` | 5 | 1 per batch of up to 15 clusters |
| `SYNTH` | `briefs/50-synthesis.md` | 6 | 1 |

The five **priority lenses** -- naming, boundaries (off-by-one), cache, ordering, efficiency of heavy work -- get their own agents because they are where most hard defects live; they are reported first.

**Small code.** If SURVEY reports a single region of fewer than 2,000 non-blank lines, you may give `BND`+`CCH` to one agent and `ROB`+`STR` to another (each reads both briefs). Never merge a lens with `REFUTE`: the agent that wrote a finding never checks it.

**One region.** When SURVEY makes a single region, skip `XREG` (there is no border to follow; suspects that point outside CODE_DIR are reported as they are), and in mode B skip `NAM/GLOBAL` (without a glossary it repeats the region agent).

**Large code -- ask before fanning out.** After SURVEY, compute the planned number of agents for waves 2-4. If it exceeds 30, tell the user the count and the region list ranked by risk (from `partition.json`), and offer: (a) all regions, or (b) only the top-N risk regions, the rest marked "not evaluated". Wait for the answer.

## 5. Tools (before wave 1)

1. Take a quick census of CODE_DIR: file count and line count per language, excluding `.git` and directories listed as vendored/generated by common convention. Use `scc` or `cloc` if present, otherwise `git ls-files` or `find` with `wc -l`.
2. Check which tools in `tools.md` are present (`<tool> --version`), for the languages found.
3. Ask the user **once**: list the missing tools that would help, each with its purpose and install command. Install only those the user approves, preferring ephemeral runners (`pipx run`, `npx --yes`) over global installs.
4. Write `REPORT_DIR/tools/available.md`: for each available tool, its version and the exact command to invoke it (absolute path when it is not on PATH, and any environment variable it needs). Agents read this file; they do not search for tools.
5. Proceed with whatever is available. Measurements whose tool is missing are produced by reading and marked `estimate`.

## 6. Launching an agent

Use the Agent tool with `subagent_type: general-purpose`. Launch every agent of a wave in a single message (parallel), at most 10 per message; launch the next batch when a batch returns.
Put everything the agent needs in the launch prompt -- do not send follow-up messages to a running agent.

Launch prompt template (fill every `<...>`):

```text
You are agent <AGENT_ID> in a software quality evaluation.
Read and follow, in this order:
  <SKILL_DIR>/briefs/00-common.md
  <SKILL_DIR>/briefs/<brief file>
Parameters:
  MODE=<A|B>
  CODE_DIR=<absolute path>
  SPEC_DIR=<absolute path or NONE>
  REPORT_DIR=<absolute path>
  OUTPUT_LANGUAGE=<language>
  REGION=<region id and its path list from REPORT_DIR/partition.json, or ALL>
  EXTRA=<brief-specific input, e.g. the requirement group, the findings batch file, or NONE>
Write only inside REPORT_DIR. Do not launch subagents.
Return at most 15 lines: files written, row counts, blockers.
```

## 7. Checking each wave

After every wave, run `python <SKILL_DIR>/scripts/check_wave.py <REPORT_DIR>` and read its output. For each agent:

- The files its brief names exist in REPORT_DIR; every line of each `.jsonl` parses as one JSON object (`jq -c . <file> > /dev/null` or a short script).
- Row counts match the counts in its return message.
- No `FAIL` verdict lacks a finding that cites its item, and no `PASS` lacks evidence (the script lists both). Relaunch is not needed for these; pass the list to MERGE in EXTRA so the gap is visible in the report.
- If files are missing, empty while the summary claims findings, or unparseable: relaunch once with the same prompt. If it fails again, add a line to `REPORT_DIR/gaps.md` (agent, region, what is missing) and continue.

Before wave 5, build the refute batches from MERGE's output: every cluster of severity `critical` or `major`, plus every `PASS` verdict on a priority-lens item, into `REPORT_DIR/refute/batch-<NN>.jsonl` files of at most 15 rows each (a short script, not by reading). A cluster is refuted once, however many agents reported it.

## 8. Finishing

After SYNTH returns:

1. Check that `REPORT_DIR/REPORT.md` exists and that the number of findings it states equals the row count of `REPORT_DIR/findings/final.jsonl`.
2. Run `python <SKILL_DIR>/scripts/sanitize_paths.py <REPORT_DIR> <CODE_DIR> [<SPEC_DIR>] --tools <tools dir>` and read its output: it rewrites absolute local paths in every text file of REPORT_DIR to placeholders and lists any it could not map. Absolute paths leak user names when a report is shared.
3. Tell the user, in OUTPUT_LANGUAGE: the mode, the report path, the top risks (copied from the report's summary), coverage, and any gaps. Do not paste the whole report.
