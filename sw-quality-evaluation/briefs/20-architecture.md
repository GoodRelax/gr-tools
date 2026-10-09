# ARCH -- architecture, quality scenarios and change scenarios

Lens code: `ARC`. Characteristic: as each scenario dictates; `maintainability` for change scenarios.
Region: ALL. You do not read every line: work from `map.md`, `profile.md`, `tools/deps.*` and targeted reading.

**No standard certifies a "clean" architecture.** An architecture is good when its structure lets the product meet the qualities it needs. So this lens asks that question scenario by scenario, in the manner of scenario-based architecture evaluation (ATAM).

## 1. Quality scenarios

From the characteristics weighted `high` (then `medium`) in `profile.md`, write **3 to 7 scenarios**:

| Field | Example |
|---|---|
| Source and stimulus | A burst of 10x the normal request rate |
| Environment | Normal operation, one replica down |
| Response | Requests are queued or rejected with a clear signal; none is lost silently |
| Measure | The quality target from the spec (mode A), or `none stated` |

For each, trace it through the structure: which components take part, where the response is decided, what could break it. Record **risks** (a design choice that may defeat the scenario), **sensitivity points** (one parameter or component the result hinges on) and **trade-offs** (one choice that helps one quality and hurts another).

## 2. Change scenarios (maintainability)

Write **3 to 5 plausible changes** for this product (a new variant of a central concept, a new external interface, a changed rule, a changed limit, a new platform). For each:

- list the places that must change (files and functions),
- count them, and mark those a maintainer would likely miss (nothing points from the obvious place to them),
- say whether the change can be made without touching the stable centre.

A change that must be made in many unconnected places, or that a maintainer would likely make incompletely, is a finding.

## 3. Checklist

| Item | Check |
|---|---|
| ARC-1 | Dependencies point towards the most stable, central code; the centre does not depend on frameworks, storage, transport or UI |
| ARC-2 | No dependency cycles between components (`tools/deps.*`) |
| ARC-3 | Components are used through their public surface, not their internals |
| ARC-4 | The layer or module boundaries put each concept on the right side: what is essential to the product's purpose is in the centre, mere means are at the edge; edge adapters are neither so thin that external details leak inward nor so thick that business rules live in them |
| ARC-5 | Each quality scenario in section 1 is supported by the structure, or its risk is stated |
| ARC-6 | Each change scenario in section 2 touches a small, discoverable set of places |
| ARC-7 | **Minimal configuration**: compared with the simplest structure that would meet the requirements, every extra layer, component, abstraction or technology has a reason visible in the code or spec; abstractions with a single implementation and no stated reason are flagged |
| ARC-8 | The structure reflects the product (a reader can tell from the top-level layout what the product does), not only the frameworks it uses |

## 4. Scope of your findings

File only **structural** findings: dependencies, boundaries, responsibilities, the fit of the structure to a scenario. A code-level defect you meet while tracing (a wrong index, a missing escape, a swallowed error) goes to `REPORT_DIR/handoffs/ARCH.jsonl` (format in the common brief), not to your findings -- the lens agents own it. When the structure *causes* a class of code-level defects (two copies of one rule that already disagree), file the structural cause and cite the example.

## 5. Output

Besides the common files, write `REPORT_DIR/architecture.md`: the scenarios, their traces, risks, sensitivity points, trade-offs, and the change-scenario tables. Keep it under 300 lines.
