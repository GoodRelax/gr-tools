# cross-region-followup -- follow defects across region borders

Lens code: as the lens you follow (EXTRA names it: `NAM`, `BND`, `CCH`, `ORD`, `ROB`, `STR` or `EFF`), with region `X`.

Region agents could not read outside their region. They marked suspects with `cross_region`. You follow them.

## Steps

1. Collect every finding of your lens with a non-null `cross_region` from `REPORT_DIR/findings/<LENS>-*.jsonl`.
2. Group suspects that point at the same other side.
3. For each group, read both sides and decide:
   - **confirmed** -- the defect exists across the border: write a new finding (id `<LENS>-X-NNN`) that cites both sides and the original finding ids in `evidence`;
   - **cleared** -- the other side handles it: write a verdict row with item `XREG`, verdict `PASS`, the original finding id in `remark`, and the handling location in `evidence`.
4. Also check what only a whole-code view can see for your lens:
   - `CCH`: copies in one component whose source is written in another;
   - `ORD`: events produced in one component and consumed in another, under the perturbation table;
   - `BND`: index or length conventions that differ on the two sides of an interface;
   - `ROB`: errors raised in one component and dropped in another;
   - `EFF`: a loop in one component calling an operation in another whose cost grows with N.

Do not re-evaluate findings that do not cross regions.
