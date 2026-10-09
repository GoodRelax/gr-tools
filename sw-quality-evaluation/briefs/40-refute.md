# REFUTE -- try to break each finding and each PASS

Lens code: `REF`. EXTRA names your batch file: `REPORT_DIR/refute/batch-<NN>.jsonl` -- clusters from `clusters.jsonl` (each groups findings with one root cause; read the member findings in `findings/` for their detail) and PASS verdicts written by other agents.

You did not write any of these rows. Your job is to **try to prove each one wrong.**

## For a finding

Look for what would make it false:

- a guard, check or precondition elsewhere (a caller, a wrapper, a framework, the type system) that prevents the scenario;
- language or runtime semantics the author of the finding misread;
- the scenario being unreachable from any entry point;
- the specification (mode A) actually asking for the behaviour.

Decide:

| Outcome | When |
|---|---|
| `upheld` | You could not break it. If you traced the scenario end to end, you may raise confidence to `confirmed` |
| `downgraded` | It is real but less severe or less certain than stated; give the new severity / confidence |
| `rejected` | It is false; cite the `file:line` that disproves it |
| `upgraded` | Only for rows with `refute_kind: "upgrade-candidate"` (a cluster kept below a member's higher, unconfirmed vote): you traced the higher scenario and it holds. Give the new severity, confidence and evidence. If it does not hold, the outcome is `upheld` |

## For a PASS verdict

Look for one counter-example in the region: a place where the item is violated. If you find one, the outcome is `rejected` and you write a new finding (id `REF-<NN>-NNN`) for it.

## Output

`REPORT_DIR/refute/result-<NN>.jsonl`, one row per input row:

```json
{"target":"C-004","outcome":"downgraded","severity":"minor","confidence":"confirmed","evidence":["src/caller.c:40"],"reason":"..."}
```

Write `reason` in OUTPUT_LANGUAGE. Every `rejected`, `downgraded` and `upgraded` needs evidence. New findings from rejected PASS verdicts go to your findings file as usual.
