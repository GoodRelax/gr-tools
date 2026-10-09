# CCH -- caches and copies that must stay in sync (priority lens)

Lens code: `CCH`. Characteristic: `reliability` (a stale copy gives a **different** answer, not just a slower one); `performance-efficiency` for bounds.

## What counts as a cache

**Any stored value that duplicates or is derived from another source of truth, and therefore must be kept in sync with it -- whatever it is called.** Searching for the word "cache" finds only a fraction. Include:

- memoised results and lazily initialised values,
- derived values stored next to their inputs (a total stored beside the items it sums),
- denormalised or duplicated copies of the same data in two structures, two components or two stores,
- indexes and lookup maps built from a list,
- UI or client-side state that mirrors model or server state,
- snapshots, buffered or shadow copies of external or device state,
- configuration read once and kept,
- framework-provided caches (query caches, response caches, object-relational mapping session caches).

## Checklist

| Item | Check |
|---|---|
| CCH-1 | **Every copy is known**: for each copy in your region, name its source of truth. List them all in your notes (copy -> source -> where updated) |
| CCH-2 | **Every write path to the source reaches the copy.** Enumerate the places that change the source; each must update or invalidate the copy. One missing path is a FAIL with its scenario |
| CCH-3 | **The key is complete**: a memoised or cached value's key includes every input that affects the value (including configuration, locale, user, version) |
| CCH-4 | **Staleness is decided, not accidental**: where a copy may lag, how much lag is allowed is stated (a number or a condition) and invalidation is tied to source changes, not only to a time-out |
| CCH-5 | **No read before fill**: initialisation order guarantees the copy is filled before it is read, or the empty state is handled |
| CCH-6 | **Concurrent invalidation is safe**: no window where a reader sees half-updated copies; many readers missing at once do not stampede the source |
| CCH-7 | **Bounded**: caches that grow with input have a size or time limit and an eviction rule |
| CCH-8 | **Fewer copies where possible**: a copy without a stated reason (performance, isolation) that could be computed on demand is flagged `minor` -- every copy is a future inconsistency |

## Method

1. Find copies: assignments of computed values to fields or globals; maps/dictionaries filled from other collections; values read from an external source and stored; state duplicated between layers. Use `REPORT_DIR/map.md` for state that crosses components.
2. For each copy, find all writers of its source (search for assignments and mutating calls on it). Compare with the places that refresh the copy.
3. Write the scenario for each gap: "change X through path P -> copy C still holds the old value -> reader R returns Y instead of Z".
4. If the source or a writer lies outside your region, set `cross_region` on the finding.

Severity guide: a reachable stale read that produces a wrong result or wrong stored data -> `major` (or `critical` by profile); an incomplete key -> `major`; unbounded growth -> `minor` or `major` by profile; an unnecessary copy -> `minor`.
