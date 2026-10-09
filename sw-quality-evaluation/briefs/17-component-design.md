# CMP -- design of each component

Lens code: `CMP`. Characteristic: `maintainability` (or `functional-suitability` when a misleading interface causes a wrong call).

You judge the code the way a designer would, **one component at a time**: does each part have one job, does its name say that job, and can someone use it from its interface alone? "Component" here means the unit the code is organised into -- a module, a package, a class, a file with a clear role. Use the component list in `REPORT_DIR/map.md`; inside your region, also judge each class or module that other parts call.

## 1. Responsibility sentence (for D1 and D2)

For each component, write **one sentence** saying what it is responsible for, as seen from outside. Then test the sentence:

1. Split it into clauses.
2. Pick the main clause -- what the component is called for.
3. Fold the other clauses into it when they are (a) a step of that one operation, (b) the range it acts on, or (c) a condition, default or limit on it.
4. If more than one clause remains, ask: **can you name one event that would change one clause but not the other?** If yes, the component has two reasons to change -- two responsibilities.
5. Record the sentence and the outcome in your notes. A component whose sentence can only be a list of what it contains ("utilities", "helpers", "manager of X, Y and Z") has no responsibility of its own.

A higher-level component's sentence must **summarise** its parts, not list them.

## 2. Checklist

| Item | Check |
|---|---|
| CMP-1 | **One responsibility**: each component passes the sentence test of section 1 |
| CMP-2 | **The name says the responsibility**: the component's name matches its sentence. Names that hide the job (`Manager`, `Helper`, `Util`, `Service` used for unrelated operations, `Common`) or promise something else fail |
| CMP-3 | **Cohesion**: everything inside serves that one responsibility; no member would sit more naturally in another component |
| CMP-4 | **A minimal, sufficient public surface**: the component exposes what callers need and nothing more; internal types, mutable state and helper functions are not exposed; callers do not need to reach past the interface |
| CMP-5 | **Usable from the interface alone**: inputs, outputs, errors, units, preconditions and side effects can be read from types, names and the interface's own comments. **If you had to read the implementation to call it correctly, it fails** -- say what you had to look up |
| CMP-6 | **Hard to misuse**: no hidden call order (`init()` before `use()` without the type enforcing it), no rows of unexplained boolean or numeric arguments, no ambiguity about whether a value may be absent, no partially constructed objects handed out |
| CMP-7 | **State in one place**: a component that holds state keeps it in one value per thing it tracks (for example one enumerated status), with the transitions defined in one place -- not spread over several flags that callers update |

## 3. Method

1. From `map.md` and the code, list the components in your region and their public surface (exports, public classes and functions, endpoints).
2. For each component: write the sentence (section 1), then read the public surface as a caller would -- before reading the implementation. Note every question the interface does not answer (CMP-5).
3. Then read the implementation and check CMP-1 to CMP-4, CMP-6 and CMP-7.
4. Small components can be judged together; say so in your notes.

## 4. Scope

File **design** findings only. A code-level defect you meet (a wrong index, a missing escape) goes to `REPORT_DIR/handoffs/<AGENT_ID>.jsonl`. When a design flaw causes defects (two flags that drift apart; an interface that invites a wrong call), file the design flaw and cite the example.

Severity guide: an interface that leads callers into wrong results, or state spread so that it already drifts -> `major`; a component with two responsibilities or a name that hides its job -> `major` when it is central and likely to change, otherwise `minor`; an undocumented unit or error on a single function -> `minor`.
