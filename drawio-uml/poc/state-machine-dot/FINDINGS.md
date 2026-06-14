# PoC: dot-native layout for flow diagrams (state machine / activity)

**Date:** 2026-06-14 · **Verdict:** validated — pursue as a second layout engine.

## Problem

The 0.5.0 clustered path (**A2**: each leaf laid out by its own `dot` run, then Python
stacks children by `direction`, then a pinned `neato` pass routes edges) makes
**state machines tall, narrow and hard to read**. Root cause: A2 arranges by the
declared `direction`, **not by the transition edges** — but in a state/activity
diagram the *edges are the structure*. (Mermaid looks better because dagre/dot lays
it out *following the edges*.)

## Idea

For edge-driven diagrams, add a **dot-native "flow" engine**: emit the WHOLE model in
ONE `dot` run — composite states (labelled clusters) become `subgraph cluster_*`,
transitions become edges (cluster-endpoint transitions use `lhead`/`ltail` with
`compound=true`). Let dot's layered ranker do the global layout, then import its
geometry into `.drawio`. Keep A2 for *structured* diagrams (class/component/ER),
where you want to control bands/order.

This is NOT the ADR-009 case (that rejected `rank=same` sibling-ordering, which
segfaults dot 13.x). Here we let dot rank freely; native `subgraph cluster_*` with
no rank hacks is standard, stable Graphviz.

## What this PoC did

`sm_to_dot.py MODEL.json OUT.dot` — translates a drawio-uml state-machine model to
native dot (nested `subgraph cluster_*` + transitions + lhead/ltail). Rendered TB and
LR; probed `-Tjson` for extractability.

Inputs/outputs in this folder: `model.json` (the ARC state machine), `native.dot`,
`native.png` (TB), `native_lr.dot`, `native_lr.png` (LR).

## Results

- **Layout quality:** LR is the win — clean horizontal flow, crisp nested composite
  boxes, tidy `predict` loop and `re-model`/`next level` back-edges. TB is cleaner
  than A2 but still tall (linear pipeline). **rankdir matters**: LR suits a linear SM.
- **Extraction feasible:** `dot -Tjson` yields everything needed to rebuild `.drawio`:
  - clusters: **3/3 have `bb`** (bounding box) → draw the composite boxes;
  - nodes: **17/17 have `pos`** (+ width/height) → place the states;
  - edges: **20/20 have spline `_draw_` (bezier ops)** → import as waypoints.
  - Coords are points, y-up / origin bottom-left (same family as `-Tplain`; reuse the
    existing transform, scale by points not inches, flip y by graph `bb` height).

## Recommendation (for a real feature, e.g. 0.6.0)

1. `options.engine: "compose" | "dot"` (default keep `compose`=A2). Optionally
   auto-pick `dot` when edges are predominantly `transition` (state/activity).
2. dot engine: build the DOT (composites→`subgraph cluster_*`, transitions→edges,
   cluster endpoints→`lhead`/`ltail`), run one `dot -Tjson`, parse node `pos` +
   cluster `bb` + edge splines, transform to draw.io px, emit native shapes/boxes.
3. Honour `options.direction` (TB/LR); document LR for linear state machines.
4. dot-native draws self-loops (A2's pinned pass skips them, FR-D-15) — a bonus for
   state machines.

Trade-off: the dot engine gives up explicit row/column *arrangement* control (the
ranker decides) — which is exactly what you want for flow diagrams, and why A2 stays
for structured ones.
