# BND -- boundaries and off-by-one (priority lens)

Lens code: `BND`. Characteristic: `reliability` (or `security` when an out-of-bounds access is reachable from external input).

**Reading cannot prove the absence of an off-by-one error.** So this lens judges two things that reading can decide: whether boundaries are **represented** in one consistent, named way, and whether each boundary survives concrete counter-examples.

## Checklist

| Item | Check |
|---|---|
| BND-1 | **One interval convention per region.** Ranges are half-open `[start, end)` or closed `[first, last]` consistently; where both exist, the closed ones say so in the name (`lastIndex`, `endInclusive`) |
| BND-2 | **No unexplained `+1` / `-1` on lengths, counts, ends or indices.** Each such adjustment has a reason that is evident (an idiom of the language, a named conversion) or stated. An adjustment made to "make the numbers come out right" signals mixed conventions |
| BND-3 | **Iteration uses the language's iteration constructs** (for-each, iterators, slices, ranges) where they exist; manually stepped indices are justified |
| BND-4 | **Comparisons against lengths are right**: `<` vs `<=` against a size or count; loop termination on the last element; empty input |
| BND-5 | **0-based / 1-based conversions** (user-facing numbering, file line numbers, protocol fields, calendar months) happen at one clearly named boundary, not scattered |
| BND-6 | **Fence-post cases**: n intervals vs n+1 points; pagination (first page, last partial page, exactly-full page); time ranges (inclusive end dates, midnight, end of month) |
| BND-7 | **Capacity**: buffer sizes include terminators, headers or separators; fixed-width integers cannot overflow or wrap at the stated or plausible maximum; signed/unsigned mixing in comparisons and subtraction |
| BND-8 | **Edge values are handled**: zero, one element, maximum, negative, absent/null, empty string or collection |

## Method

1. Search your region for boundary arithmetic: `+ 1`, `- 1`, `+1`, `-1`, `<=`, `>=` next to names containing `len`, `length`, `size`, `count`, `end`, `last`, `max`, `index`, `idx`, `offset`, `pos`, `page`, `limit`, and the language's length functions. Also search index loops.
2. For each hit, decide which convention the surrounding code uses and whether this hit follows it.
3. For every suspect, **try concrete inputs**: empty, one element, exactly the capacity, capacity + 1, the maximum value of the type. Write down the input that breaks it. A finding without a breaking input is `plausible` at most.
4. For BND-1, list the conventions you found per component in your notes (e.g. "slices: half-open; date ranges: closed, named `...Inclusive`").

Severity guide: an out-of-bounds read or write reachable from input -> `critical` or `major` by profile; a dropped or duplicated element in a reachable case -> `major`; mixed conventions without a current defect -> `minor`.
