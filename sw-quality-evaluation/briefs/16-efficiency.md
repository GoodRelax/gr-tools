# EFF -- efficiency of heavy work (priority lens)

Lens code: `EFF`. Characteristic: `performance-efficiency` (or `reliability` / `safety` when a deadline miss is a failure).

**A heavy task done in a worse complexity class than a readily available one is a defect, not a tuning opportunity.** Doing in O(N^2) what O(N log N) or O(log N) would do works in every small test and collapses at the first real data size. This lens finds the heavy work, states its actual and its achievable complexity, and judges the gap at the sizes the product will meet.

Constant factors and micro-optimisations are **not** this lens's business, except on a proven hot path with a stated time budget.

## Checklist

| Item | Check |
|---|---|
| EFF-1 | **Heavy work is identified**: list every task in your region whose cost grows with data size (N records, items, nodes, events, bytes) or that runs at high frequency (per request, per frame, per tick, per interrupt, per event, per keystroke). For each, state N and the frequency: from the specification (mode A), from limits in the code, or from the profile -- marked `stated` or `assumed` |
| EFF-2 | **Complexity fits**: for each heavy task, state its actual time complexity and the best complexity readily achievable with standard data structures and algorithms. FAIL when the actual is worse by a factor that grows with N (O(N^2) where O(N log N) or O(N) is available; O(N) per query where an index gives O(log N) or O(1)) and N at the expected scale makes the difference matter |
| EFF-3 | **No hidden quadratic patterns**: a linear lookup (`contains`, `indexOf`, `find`, scanning a list) inside a loop over the same scale; insertion or removal at the front of an array inside a loop; building a string or array by repeated concatenation that copies; sorting inside a loop; nested loops to match or join two collections; recomputing an aggregate from scratch on every event instead of updating it incrementally; redrawing or re-deriving everything on each small change; library calls whose cost is linear hidden inside loops |
| EFF-4 | **Round trips are batched**: no query, request, file open or device access inside a loop where one batched call would do; independent I/O is not serialised needlessly; large reads are paged or streamed |
| EFF-5 | **Memory scales**: large inputs are streamed rather than loaded whole when the size is unbounded; large structures are not copied repeatedly; memory use is proportional to what is needed |
| EFF-6 | **Work is not repeated**: the same computation with the same inputs is not done many times within one operation. Prefer computing once per operation and passing the result over adding a cache (a cache is a copy -- see the cache lens) |
| EFF-7 | **Worst case, where time is a requirement**: if the profile has real-time, latency or deadline constraints, judge the worst case, not the average -- unbounded loops, allocation, blocking calls, or structures with a bad worst case on a time-critical path. Otherwise `NA` |
| EFF-8 | **Targets**: mode A -- compare with the specification's performance targets; where there is no target, judge by the expected N and frequency and say so. Mode B -- judge by the sizes the code itself admits (limits, types, test data) and the profile |

## Method

1. Start from `REPORT_DIR/tools/complexity.*` hot spots, then search for nested loops, loops containing lookups, I/O or sorting, and handlers that run per event or per frame.
2. For each heavy task: write its actual complexity, its achievable complexity and the data structure or algorithm that achieves it.
3. **Put numbers on it**: at the expected N, how many operations, or round trips, actual vs achievable (for example "N = 50,000 items -> 1.25e9 comparisons vs 8e5"). State whether N is `stated` or `assumed`.
4. If the loop is in your region but the costly operation it calls is elsewhere, set `cross_region`.

Severity guide: a complexity gap that breaks a stated target, or makes the product unusable at its expected size -> `major` (`critical` if a deadline miss is a safety or availability failure per the profile); a gap that matters only above the expected size -> `minor`, with the size at which it starts to matter; a gap at a size the code itself bounds small (state the bound) -> no finding.
