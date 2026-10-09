# ORD -- ordering, state and concurrency (priority lens)

Lens code: `ORD`. Characteristic: `reliability` (or `safety` / `security` by profile).

**Code whose correctness depends on events arriving in the expected order is defective code.** Events get reversed, duplicated, dropped, delayed and interleaved in practice. A state machine -- one current state per object, and a defined outcome for every state x event pair -- keeps behaviour correct whatever the order. Ad-hoc `if` / `switch` checks scattered across handlers usually do not.

This lens judges the outcome, not the technique: **every state x event combination must have a defined, correct result.** A small object whose `if` statements achieve that is fine; an unplanned set of flags that fails one perturbation is a FAIL.

## Checklist

| Item | Check |
|---|---|
| ORD-1 | **Event sources are known**: list every source of events in your region -- callbacks, interrupts, signals, messages, asynchronous completions, timers, user input, external notifications, lifecycle calls (init, start, stop, dispose) |
| ORD-2 | **One state per object**: the condition of each event-driven object is held in one enumerated value, not in several booleans or nullable fields whose combinations include impossible ones (`isLoading` and `isDone` both true). Count the representable combinations vs the meaningful ones |
| ORD-3 | **Every state x event cell is defined**: where a state machine exists, every combination has an outcome, including "ignore" or "no change", and the code matches it (mode A: matches the spec's transition table) |
| ORD-4 | **Perturbations are survived** (see below) |
| ORD-5 | **No observable intermediate state**: when several fields change together, no reader, notification or interrupt can observe the half-updated set; notifications are sent after the state is consistent, and whether "before" or "after" is defined |
| ORD-6 | **Re-entrancy**: a callback or notification invoked mid-update cannot re-enter and see or change inconsistent state |
| ORD-7 | **Shared data under concurrency**: check-then-act and read-modify-write on shared data are atomic (lock, atomic operation, single owner, or transaction); lock acquisition order is the same on every path; no long or external call while holding a lock or transaction |
| ORD-8 | **No hidden order dependencies**: results do not depend on iteration order of unordered collections, directory listing order, registration order, initialisation order of modules, or test execution order -- unless that order is guaranteed and stated |
| ORD-9 | **Start-up and shut-down**: calls before initialisation and after disposal are rejected or ignored by design; timers, subscriptions and pending operations are cancelled on disposal |

## Perturbations (ORD-4)

For each event-driven object or flow in your region, try each of these and decide whether the result is still correct:

| Perturbation | Typical breakage |
|---|---|
| Two events in **reverse** order | The second handler assumes the first already ran |
| The same event **twice** | Double effect (charged twice, item added twice), counter off by one |
| An event **missing** | Waits forever; flag never cleared |
| An event **late**: after cancel, time-out, disposal or a newer request | A stale response overwrites newer data; a callback touches a disposed object |
| An event **early**: before initialisation or before a prerequisite | Null access; work done on default values |
| Two flows **interleaved** (two requests in flight, two users, two threads) | Last-writer-wins on stale data; lost update |

Write each failing perturbation as a concrete event sequence in the finding's `scenario`.

## Method

1. List event sources (ORD-1) and the state each one changes.
2. For each piece of state: is it one enumerated value or scattered flags? Where is each transition made?
3. Apply the perturbation table. Read the handlers in the order the perturbation implies.
4. For concurrency, identify shared mutable data and every access to it; check how each access is protected.
5. If the event source or the state lives outside your region, set `cross_region`.

Severity guide: a reachable sequence that corrupts data, double-applies an effect or deadlocks -> `major` or `critical` by profile; impossible combinations representable but not yet reachable -> `minor`.
