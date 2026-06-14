---
name: drawio-uml
description: Generate clean UML and node-link diagrams as native draw.io (.drawio) files with automatic, non-overlapping layout — Graphviz dot computes both node positions AND orthogonal edge routes, so lines never cut through boxes. Use whenever the user wants to draw, generate, or clean up a diagram in draw.io or drawio — class, state-machine, use-case, component, package, activity, deployment, ER, or object diagrams — especially when layout quality matters (overlapping lines, edges crossing boxes, messy auto-layout, or a Mermaid diagram that looks bad). Also use when reverse-engineering structure from source code into a diagram, or when the user says an existing diagram is ugly, low-quality, or hard to read. Produces real UML shapes (class compartments, state rounded-rects, use-case ellipses, actors, decision diamonds, package folders) with proper UML arrows, exported to PNG/SVG via the draw.io CLI. Optionally arranges nodes into a recursive layout tree of labelled, coloured clusters (TB/LR, nestable) with a legend, generates focused sub-views with --view, and routes EVERY edge — including cross-cluster and whole-cluster (group-to-group) ones — around the boxes via a position-pinned Graphviz pass. Two layout engines via options.engine: cluster-dot (default; structure diagrams) and dot (a single dot run for edge-driven flow — state machine / activity — that follows the transitions for a clean top-to-bottom layout). Edges may connect whole clusters (e.g. layer/module dependencies), not just nodes. Does NOT do sequence or timing diagrams. Requires Graphviz (dot, plus neato/fdp for the pinned routing pass), draw.io desktop, and Python 3.10+. The same model also yields a standalone Markdown document (H1 title + node/edge/cluster tables: responsibilities, element lists) via the companion table.py.
---

# drawio-uml: clean UML / node-link diagrams in draw.io

## Why this works (read first)

A diagram has two separable qualities, produced by different things:

- **Content** — which boxes, what's in them, and how they relate, in correct notation. This is *your* job (read the code/spec, model it).
- **Layout** — where boxes go and how lines route so nothing overlaps. This is an *algorithm's* job.

Messy diagrams (hand-made, or Mermaid) happen because layout is a graph-drawing problem — you cannot fix overlapping lines by writing more detailed prose. So this skill hands layout to **Graphviz `dot`**, and crucially asks dot to route the **edges** too (`splines=ortho`), not just place nodes. Importing those routes as draw.io waypoints is what removes line-vs-box overlaps. draw.io then renders native shapes and exports.

Division of labor: **you = content**, **dot = layout (positions + edge routing)**, **draw.io = render, edit, export**.

## What this can draw

Anything that is **boxes and arrows** — i.e. a node-link graph dot can lay out:

| Diagram | Node shapes | Edge arrows |
|---------|-------------|-------------|
| **Class** | `class` (compartments) | `generalization` `realization` `composition` `aggregation` `directed_association` `dependency` |
| **Object** | `object` (underlined name) | `directed_association` `association` |
| **ER** | `entity` (compartments) | `directed_association` (multiplicity in label) |
| **State machine** | `initial` `state` `final` | `transition` (event/guard in label) |
| **Activity** | `initial` `action` `decision` `final` | `transition` (guard in label) |
| **Use case** | `actor` `usecase` | `association` (actor–uc), `dependency` + `«include»`/`«extend»` label |
| **Component** | `component` `box` | `dependency` `directed_association` |
| **Package** | `package` | `dependency` |
| **Deployment** | `box` `component` | `directed_association` `dependency` |

**Not supported: sequence and timing diagrams.** They are ordered by *time* along lifelines, which is not a graph-layout problem — dot does not help, and forcing it produces nonsense. Tell the user this honestly and suggest Mermaid `sequenceDiagram` or PlantUML instead.

## Layout: pick an engine, then flat or cluster tree

**Engine** — `options.engine` (default `cluster-dot`). Two engines; both draw the labelled cluster boxes:

- **`cluster-dot`** (default) — for **structure** diagrams (class, component, package, ER), where you want explicit bands and order. Each leaf cluster is laid out by its own dot run and Python composes them along `direction`; a position-pinned pass then routes every edge around the boxes. Has the flat and clustered paths below.
- **`dot`** — for **flow** diagrams (state machine, activity). The whole model goes through ONE dot run, so the layout **follows the transition edges** (composite states become native boxes; cluster-endpoint transitions clip at the box border) for a clean top-to-bottom flow. It **draws self-loops**, honours only `options.direction` (a per-cluster `direction` is ignored, with a warning), and needs only `dot` (no neato/fdp). Prefer it for anything edge-driven.

Within `cluster-dot`, two layout paths, chosen by whether the model has a `layout`:

- **Flat** (no `layout`) — dot lays out every node; flow follows `options.direction` (`TB` = top-down, the default; `LR` = left-to-right). Best for a single diagram of up to ~12 boxes.
- **Clustered** (a `layout` tree) — `layout` is a RECURSIVE tree of clusters. Each cluster arranges its children/members along its `direction` (`TB`/`LR`) and draws a dashed labelled box **iff it has a `label`** (a label-less cluster is an invisible arrangement-only container). A cluster holds EITHER child `clusters` or member `nodes` (referenced by name). This is how you get `input | consider | output` across the top with a full-width `vocabulary` band below — and nested sub-groups inside a cluster.

On top of the clustered path:

- **Colour cascade** — a cluster's `color`/`fill` cascades to its descendant nodes (nearest ancestor wins; a node's own `fill`/`stroke` overrides), so you don't repeat colours on every node.
- **Legend** — a row of swatches for the **outermost** labelled clusters (deduped by colour) plus the UML arrow-kind glyphs (◆ ◇ → ⇢), under the diagram.
- **Box-avoiding routing for ALL edges** — a final **position-pinned Graphviz pass** (`neato -n2` / `fdp -n2`, `splines=ortho`) routes *every* edge — internal, cross-cluster, **and cluster-endpoint (group-to-group)** — around the placed boxes.
- **Views** (`--view KEY`) — a named subset of nodes rendered as the induced subgraph (the master layout pruned to those nodes). One model (SSOT) → many small, focused diagrams.

Under **`cluster-dot`**, each leaf cluster is laid out in its own dot run (members ordered by their internal edges, or stacked along `direction` via invisible edges when they have none); Python composes the children by `direction`, so sibling order is exactly the listed order. Validation is fail-fast: every node must be placed exactly once, cluster names are unique and `/`-free.

## Prerequisites (check once per machine)

```bash
dot -V            # Graphviz — the layout engine (REQUIRED)
neato -V          # ships with Graphviz — used by the pinned edge-routing pass
python --version  # 3.10+ — runs the bundled generator (REQUIRED)
```

draw.io desktop is required only for PNG/SVG export; the `.drawio` opens/edits in draw.io regardless. CLI binary: `"C:\Program Files\draw.io\draw.io.exe"` (Windows), `/Applications/draw.io.app/Contents/MacOS/draw.io` (macOS), `drawio` (Linux). Install help and the full concept/style reference are in `references/drawio-uml-reference.md` — read it for install issues, the full preset catalog, or to explain the toolchain.

## Workflow

### 1. Build the model

Read the target — source code or a spec — and extract the nodes and relations. **Be faithful: real names/attributes/methods, not invented ones.** Precision is the point. Keep member lists short so boxes stay readable. Write a `model.json`:

```json
{
  "title": "Player state machine",
  "options": {"engine": "dot", "direction": "TB", "column_width": 260, "node_separation": 0.7, "rank_separation": 1.1},
  "nodes": [
    {"name": "Idle", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
    {"name": "Running", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
    {"name": "start", "shape": "initial"},
    {"name": "stop", "shape": "final"}
  ],
  "edges": [
    {"source": "start", "target": "Idle", "arrow": "transition"},
    {"source": "Idle", "target": "Running", "arrow": "transition", "label": "play()"},
    {"source": "Running", "target": "stop", "arrow": "transition", "label": "end()"}
  ]
}
```

**Node shapes** (`shape` field):

| shape | renders as | shape | renders as |
|-------|-----------|-------|-----------|
| `class` `entity` `object` | compartment box (name / attributes / methods) | `usecase` | ellipse |
| `component` | rectangle + «component» | `actor` | stick figure |
| `package` | folder | `state` `action` | rounded rectangle |
| `box` | plain rectangle | `decision` | diamond |
| `initial` | filled dot | `final` | bullseye |
| `note` | dog-eared note | | |

Compartment shapes take `attributes` and `methods` (lists of strings like `"+ name: str"`). Visibility: `+` public, `-` private, `#` protected, `~` package. Mark abstract/interface via `"stereotype"` + the name auto-italicises. Any node may override its preset with a raw draw.io `"style"` string, or set `"width"`/`"height"`.

**Edge arrows** (`arrow` field; source → target is the reading direction):

| arrow | UML meaning | arrow | UML meaning |
|-------|-------------|-------|-------------|
| `generalization` | generalization (extends) | `directed_association` | association, open arrow |
| `realization` | realization (implements) | `dependency` | dependency (dashed); use label `«include»`/`«extend»` |
| `composition` | composition (filled diamond) | `transition` | state/activity flow |
| `aggregation` | aggregation (hollow diamond) | `association` | plain line, no arrowhead (actor–usecase) |

Put multiplicity / role / guard text in the optional edge `"label"`. Colour by layer so related nodes read together (palette in the reference).

**Cluster-endpoint edges** — an edge's `"source"`/`"target"` may name a **cluster** (not just a node), provided that cluster is **named AND labelled** (so it has a drawn box). The edge then anchors to the cluster box and is routed around the others. Use this to relate whole groups instead of forcing the relation onto a representative node — e.g. Clean-Architecture layer dependencies (`{"source": "framework", "target": "adapter", "arrow": "dependency", "label": "depends on"}`) or module/boundary edges. Resolution is node-first then cluster; a name that is both a node and a cluster, an unknown name, or an unnamed/label-less cluster endpoint **fails fast**. An edge between a node and its own enclosing cluster (or a cluster and itself / an ancestor / a descendant) is dropped from routing, like a self-loop.

**Documentation fields** (`description`, `remark`) — any node, edge, **or cluster** may carry a `"description"` (a node/edge's one-line responsibility, or a cluster's purpose) and a `"remark"` (a side note: origin, ADR, constraint). `draw` **ignores** them, so the diagram is unchanged; **`table` emits them** (node/edge in their tables, cluster ones in a `## Clusters` section). Use these instead of cluttering the boxes. A **required** top-level **`title`** names the document: `table` emits it as the H1 so the `.md` is a standalone document (under `--view` the view's `label` is the H1 instead); `draw` ignores `title`. The full model schema is formalised in `schema/model.schema.json` (JSON Schema draft-07, strict — it catches typos in keys, and requires `title`).

### 1b. (Optional) cluster tree, cascade, legend, and views

Add a `layout` (a recursive cluster tree) to group and arrange nodes; omit it for a flat diagram. A cluster sets `direction` (`TB`/`LR`), draws a box when it has a `label`, may set `color`/`fill` (which **cascade** to its descendant nodes), may set a `name` (for `--view`/`--cluster` references and the table cluster path), and holds EITHER child `clusters` or member `nodes` (referenced by name). Add `views` for focused sub-diagrams.

```json
{
  "title": "Agent loop",
  "options": {"direction": "TB", "column_width": 300},
  "nodes": [
    {"name": "Probe", "shape": "class", "attributes": ["moves : GameMove[*]"]},
    {"name": "TurnRecord", "shape": "class", "attributes": ["frames : Frame[*]"]},
    {"name": "Conception", "shape": "class", "attributes": ["goal", "plan"]},
    {"name": "WorldModel", "shape": "class", "attributes": ["rules"]},
    {"name": "GoalPredicate", "shape": "class", "methods": ["test() : bool"]},
    {"name": "GameMove", "shape": "class", "attributes": ["kind"]}
  ],
  "edges": [
    {"source": "Conception", "target": "WorldModel", "arrow": "composition", "label": "world"},
    {"source": "Conception", "target": "GoalPredicate", "arrow": "composition", "label": "goal"},
    {"source": "Probe", "target": "GameMove", "arrow": "aggregation", "label": "trial moves"}
  ],
  "layout": {
    "direction": "TB",
    "clusters": [
      {"direction": "LR", "clusters": [
        {"name": "input", "label": "Input port", "color": "#2F8FA8", "fill": "#E3F2F5",
         "nodes": ["TurnRecord", "Probe"]},
        {"name": "consider", "label": "Consider", "color": "#9673A6", "fill": "#EDE7F6",
         "clusters": [
           {"nodes": ["Conception"]},
           {"direction": "LR", "clusters": [
             {"name": "world", "label": "world", "nodes": ["WorldModel"]},
             {"name": "goal",  "label": "goal",  "nodes": ["GoalPredicate"]}
           ]}
         ]},
        {"name": "output", "label": "Output port", "color": "#D79B00", "fill": "#FFF0DD",
         "nodes": ["GameMove"]}
      ]}
    ]
  },
  "views": {
    "answer": {"label": "The Conception", "nodes": ["Conception", "WorldModel", "GoalPredicate"]},
    "io":     {"label": "I/O ports", "clusters": ["input", "output"]}
  }
}
```

This yields `input | consider | output` across the top, with `consider` holding `Conception` above a `world | goal` LR sub-band; `input`'s two edge-less members stack vertically (invisible-edge alignment). `draw.py model.json answer.drawio --view answer` then draws just the Conception internals.

Layout / view keys:

| key | scope | meaning |
|-----|-------|---------|
| `engine` | options | `cluster-dot` (default; structure: class/component/package/ER) **or** `dot` (edge-driven flow: state machine / activity). Both draw the cluster boxes. |
| `direction` | cluster / options | `TB` = top→bottom (default), `LR` = children left→right. Resolves cluster → `options.direction` → `TB`. Under `engine:"dot"` only `options.direction` applies (per-cluster `direction` ignored, with a warning). |
| `label` | cluster | present ⇒ a dashed labelled box is drawn; absent ⇒ invisible arrangement-only container. |
| `name` | cluster | id for `--view`/`--cluster` and the table cluster path. Unique across clusters, no `/`. |
| `color` / `fill` | cluster | box border colour / a node-fill suggestion; both **cascade** to descendant nodes (nearest ancestor wins; a node's own `fill`/`stroke` wins over both). |
| `clusters` ⊻ `nodes` | cluster | child clusters (internal node) **or** member node names (leaf) — exactly one. Order = arrangement order. |
| `description` / `remark` | cluster | the group's purpose / a side note; `draw` ignores them, `table` lists them in `## Clusters`. A named+labelled cluster may also be an edge endpoint (see **Cluster-endpoint edges**). |
| `views.<key>` | top level | `{label?, nodes?, clusters?}` — a named node subset (`nodes` ∪ nodes under named `clusters`); `--view <key>` draws/tabulates its induced subgraph. |

The **legend** lists the outermost labelled clusters (deduped by colour) whenever a labelled cluster exists. **Box-avoiding routing** runs automatically on any clustered model — expect **no edge to cross any box**, including cross-cluster edges. Up to ~3 labelled nesting levels read well; deeper warns. See the reference §9–§12 for the full mechanism.

### 2. Generate the diagram (and tables)

```bash
python <SKILL_DIR>/scripts/draw.py  model.json out.drawio [--view KEY]                 # the .drawio diagram
python <SKILL_DIR>/scripts/table.py model.json out.md   [--cluster KEY | --view KEY]   # node/edge tables (.md)
```

`<SKILL_DIR>` is this skill's directory. `draw.py` emits native shapes, pulls positions + orthogonal routes from `dot` (and, for clustered models, the pinned `neato -n2` routing pass), self-validates the XML, and prints a confirmation. `table.py` writes a **standalone** Markdown document — an H1 title (the model `title`, or the view's `label` under `--view`) then `## Nodes` / `## Edges` (and `## Clusters` when the model has named/labelled clusters) — and consumes `description`/`remark` (including cluster ones). `--view KEY` (both tools) renders only that view's induced subgraph; `--cluster KEY` (table only) narrows the tables to a cluster subtree (matched on the cluster `name` path); `--view` and `--cluster` are mutually exclusive. A malformed model — a missing/blank `title`, an edge endpoint that resolves to neither a node nor a named+labelled cluster (or is ambiguously both), a duplicate or `/`-bearing cluster name, or a node not placed exactly once — fails fast.

**One-shot human workflow (Windows):** drag one or more `model.json` files onto `drawio-uml.bat` (in the skill root) — it runs both generators and exports `.svg`/`.png`, writing all outputs next to each input.

### 3. Export to PNG/SVG (recommended)

```bash
DRAWIO="/c/Program Files/draw.io/draw.io.exe"   # macOS: /Applications/draw.io.app/Contents/MacOS/draw.io ; Linux: drawio
"$DRAWIO" -x -f png -e -b 12 -o out.drawio.png out.drawio
"$DRAWIO" -x -f svg -e -b 12 -o out.drawio.svg out.drawio
```

`-x` export, `-f` format, `-e` embed editable XML, `-b` border, `-o` output. Headless Linux: `xvfb-run -a ... --no-sandbox`.

### 4. Verify

Read the exported PNG and check: shapes render as intended, arrowheads are the correct kind, and **no box is crossed by an edge** (for clustered models, check the cross-cluster edges especially). Reading the image back is the cheapest way to catch a problem before showing the user.

## Tuning layout (if anything overlaps)

- **Engine for flows**: a state-machine / activity diagram that looks cramped or scattered under the default `cluster-dot` usually reads far better with `options.engine:"dot"` (dot lays it out following the transitions — a clean top-to-bottom flow).
- **More room**: raise `options.rank_separation` / `options.node_separation`.
- **Orientation**: `options.direction` = `"TB"` (top-down, default) or `"LR"` (left-to-right) — `LR` suits use-case and wide hierarchies. A per-cluster `direction` overrides it locally (cluster-dot only; `engine:"dot"` honours only `options.direction`).
- **Cluster gaps**: children arranged `LR` are `ROW_GAP` apart, `TB` are `COL_GAP` apart (constants near the top of the script).
- **Fewer crossings by design**: keep the primary structure (inheritance, control flow) as the backbone; dash or drop secondary `dependency`/`directed_association` edges. Or split concerns into `views`.
- **Interactive last resort**: open in draw.io, `Arrange → Layout → Vertical Tree` / `Hierarchical`, or drag.

## Pitfalls

- The generator escapes `&`, `<`, `>` for you (including the legend HTML); if you hand-edit `.drawio` XML, do the same.
- Self-loops (an edge from a node to itself — a state's self-transition): the **`dot` engine draws them**, so for state machines with self-transitions use `options.engine:"dot"`. The `cluster-dot` path uses `splines=ortho`, which cannot route a self-loop and skips them — there, model recursion as an **attribute/label** or add the loop by hand in draw.io.
- Keep `model.json` as the single source of truth and regenerate, rather than editing the `.drawio` by hand — that keeps the diagram reproducible.
- The pinned routing pass needs `neato` (or `fdp`) from Graphviz on PATH. If neither is found, clustered models still render but cross-cluster edges fall back to draw.io's auto-router (which may cross boxes) — install Graphviz fully.
- Sequence/timing diagrams: decline and suggest Mermaid/PlantUML (see "What this can draw").

## Reference

`references/drawio-uml-reference.md` — concepts (what Graphviz/dot/draw.io are), the cross-platform install matrix, the full shape + arrow preset catalog with raw style strings, per-diagram-type worked `model.json` examples, the dot→draw.io coordinate-transform math, the **cluster tree / cascade / legend / views / box-avoiding-routing** sections with a worked clustered example, and a troubleshooting table.
