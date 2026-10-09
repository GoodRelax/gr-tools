# STR -- structure, maintainability, performance, tests, flexibility

Lens code: `STR`. Characteristics: `maintainability`, `compatibility`, `flexibility`, `interaction-capability`. Efficiency belongs to the `EFF` lens -- do not duplicate it here.

## Checklist

| Item | Check |
|---|---|
| STR-1 | **Size and complexity**: from `REPORT_DIR/tools/complexity.*`, report the distribution for your region (median, 90th percentile, max) of function length and cyclomatic complexity, and the ten worst functions. Read the worst three: is the size essential (a flat dispatch table) or accidental (several jobs in one)? Thresholds are conventions, not standards -- judge by reading |
| STR-2 | **One job, one place**: each decision, calculation or conversion is implemented once and called from elsewhere. Look beyond copy-paste clones (`tools/duplication.*`): renamed or reworded copies of the same rule, validation repeated in several layers, the same constant written in several places. Two copies always drift; say whether these already give different answers for the same input |
| STR-3 | **No magic values**: literals with meaning (limits, time-outs, codes, sizes) are named, with the reason stated where not obvious |
| STR-4 | **One responsibility per unit**: for each large function, class or file, state its responsibility in one sentence. If you can name an event that would require changing one part but not another, it holds two responsibilities |
| STR-5 | **One level of abstraction per function**: a function does not mix the intent ("place the order") with low-level detail (string building for a query) |
| STR-6 | **Computation separated from side effects**: business rules and calculations do not perform I/O, logging, locking or clock reads in their middle; external reads happen first and are passed in, so the logic can be tested with fixed values |
| STR-7 | **Dependency direction inside the region**: stable, central code does not depend on volatile details (frameworks, storage, UI); no reaching into another component's internals |
| STR-8 | **Comments say why, not what**; no commented-out code; no stale comments |
| STR-9 | **Dead code**: unused functions, parameters, flags, configuration and branches (use a dead-code tool if present; confirm by search) |
| STR-10 | **Nesting and control flow**: deep nesting is flattened where early returns would do; no long `if` / `switch` chains that every new variant must extend in several places |
| STR-11 | **Tests -- presence**: the region's behaviour is covered by automated tests. If the whole code has none, SYNTH reports that once; in your region report only which risky behaviour has no test |
| STR-12 | **Tests -- quality**: tests are independent of each other and of execution order; no timing- or randomness-dependent assertions; boundary and error cases are tested, not only the main path; mocks do not replace the very behaviour under test; test names state the condition and the expected result |
| STR-13 | **Compatibility**: stored and exchanged formats and protocols carry a version or are otherwise evolvable; reading older data is handled where the profile implies it |
| STR-14 | **Flexibility**: environment specifics (paths, hosts, devices, sizes) are isolated in configuration or one adapter, not spread through the logic |
| STR-15 | **Interaction capability, as far as code shows it**: user-facing messages say what happened and what to do; long operations can be cancelled; destructive actions are confirmable or undoable. Mark `NA` for code with no user interface |

## Method

Start from the tool outputs, then read. Every tool-derived number in a finding says its tool and command (common brief section 6).

Severity guide: duplicated rules that already disagree -> `major`; a responsibility split that makes a likely change touch many places -> `minor` or `major`; style-level structure issues -> `minor`.
