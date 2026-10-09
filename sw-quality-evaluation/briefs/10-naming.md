# NAM -- naming (priority lens)

Lens code: `NAM`. Characteristic: `maintainability` (and `functional-suitability` when a misleading name causes a wrong call).

**A name is the main interface of the code. "The name tells what it denotes" is a MUST, not a style preference.**

**Naming is a mandatory axis of the report: it must always be scored.** Read every file of your region that declares identifiers -- source and tests; stylesheets and data files are not in scope. If you cannot cover them all, say exactly which files you missed in your return message, so the coordinator can have them read; never leave the axis to "cannot judge".

## 1. The four steps

| Step | Question | Judged? | Example |
|---|---|---|---|
| 1 | Which convention did the author choose? | **No** -- the choice is the author's | `lowerCamel` for variables and `UpperCamel` for types; `UPPER_SNAKE` for globals |
| 2 | Is one convention applied consistently to each kind of identifier? | Yes | FAIL: globals spelled `GLOBAL_TASK` and `Global_schedule` side by side |
| 3 | Is every word spelled correctly? | Yes | FAIL: `GOBAL_TASK` |
| 4 | **Does the name tell what it denotes?** | Yes -- MUST | FAIL: a variable named just `Task` -- which task, in what role? |

## 2. What "tells what it denotes" means

**The wider the scope, the more specific the name must be.** `i` is fine for a three-line loop; a module-level or global name must stand on its own when read far from its definition.

| Item | Check |
|---|---|
| NAM-1 | No generic names at wider than local scope: `data`, `info`, `tmp`, `obj`, `value`, `item`, `result`, `manager`, `handler`, `helper`, `util`, or a bare type name used as a variable name (`Task`, `Order`) when its role is not evident -- a role or qualifier is missing (`pendingTask`, `taskBeingEdited`) |
| NAM-2 | Names match behaviour: a name that reads as a query does not change state; a name promising an action performs exactly that action; no hidden side effect behind an innocent name |
| NAM-3 | Operations that read mutable or external state, or that can be slow or fail (clock, random, file, network, database, device), are named as actions, not as plain nouns, so callers do not treat them as cheap and stable |
| NAM-4 | Booleans read as predicates (`isReady`, `hasStock`, `canRetry`, or the language's idiom); no negated or double-negated booleans (`isNotInvalid`) |
| NAM-5 | Collections are distinguishable from single items (plural, or the codebase's consistent idiom) |
| NAM-6 | Types and components are noun phrases; commands are verb + object; events (things that already happened) are in the past tense, so a reader can tell a request that may be refused from a notification that cannot |
| NAM-7 | Quantities with a fixed unit carry the unit in the name (`timeoutMs`, `lengthMm`) unless the unit is carried by the value's type -- unit mix-ups pass type checks |
| NAM-8 | Abbreviations are used consistently (not `usr` here and `user` there) |
| NAM-9 | Step 2: each kind of identifier (type, function, variable, constant, global, file, module) follows one convention throughout the region |
| NAM-10 | Step 3: no misspellings in identifiers (use `REPORT_DIR/tools/spelling.*` if present; it splits identifiers into words) |
| NAM-11 | One concept, one name; one name, one concept -- within the region |
| NAM-12 | State machines, if any: the name of the definition (the rules) differs from the name of the current state (the value), so the two cannot be confused |

## 3. Method (region agents)

1. Start from `REPORT_DIR/tools/identifiers.txt` filtered to your region, if present. Otherwise list declarations with a search.
2. Sort identifiers by kind and scope. Look first at globals, public API, module-level names and type names; then function names; then locals in long functions.
3. For each suspect, read its uses before deciding: a name is bad if a reader at the use site cannot tell what it denotes.
4. For NAM-2, read the body of every function whose name reads as a query or getter.
5. Group findings: one finding per pattern with up to 10 representative locations, plus the count of all occurrences.

Severity guide: a name that leads a caller into a wrong result -> `major`; a generic or misleading name on public API or global state -> `minor` at least, `major` if the region is high risk; a misspelling -> `minor`.

## 4. Global part (agent `NAM/GLOBAL`, wave 3)

You run after all regions. Inputs: `REPORT_DIR/tools/identifiers.txt` (whole code), all `findings/NAM-*.jsonl`, and in mode A `REPORT_DIR/glossary.json`.

| Item | Check |
|---|---|
| NAM-G1 | Each kind of identifier follows one convention across the whole code (step 2, cross-region) |
| NAM-G2 | One concept, one name across components; one name, one concept across components |
| NAM-G3 | Mode A: names of domain concepts match the specification's vocabulary; a concept the spec names is not called something else in the code |
| NAM-G4 | Abbreviation and spelling consistency across components |

Do not repeat region findings; reference them by id in your notes if you build on them.
