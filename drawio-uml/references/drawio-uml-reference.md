# drawio-uml — reference

Depth behind SKILL.md: concepts, install, the full preset catalog, per-diagram-type
worked examples, the coordinate transform, the cluster / legend / banded-layout /
box-avoiding-routing extensions, and troubleshooting.

## Contents
1. The three tools and how they relate
2. Install matrix (cross-platform)
3. Node shape catalog
4. Edge arrow catalog
5. Colour palette
6. Per-diagram-type recipes (worked model.json)
7. The dot → draw.io coordinate transform
8. Troubleshooting
9. Clusters (grouping nodes into labelled boxes)
10. Legend
11. Banded / compass layout (`options.layout.rows`)
12. Box-avoiding edge routing (the pinned final pass)
13. Worked example: clustered + banded class diagram

## 1. The three tools and how they relate

- **Graphviz** — takes a graph (nodes + edges) and lays it out automatically. **`dot`** is its layered (Sugiyama-style) engine: it ranks nodes into levels and minimises crossings; with `splines=ortho` it also produces orthogonal edge routes that avoid node boxes. Input is the **DOT language** (`digraph G { A -> B }`). Class/state/activity/component diagrams all want `dot`. **`neato`/`fdp`** are Graphviz's force-directed engines; with `-n2` they DON'T lay anything out — they take node positions you supply and only route the edges. This skill uses `neato -n2` for the final box-avoiding routing pass (§12).
- **draw.io / diagrams.net** — a free editor (desktop / browser / VS Code). Files are `.drawio` (`mxGraphModel` XML). It has native shapes for every UML element and a desktop **CLI** that exports to PNG/SVG/PDF, embedding the source XML so exports stay editable.
- **The generator** (`scripts/draw.py`) is the glue: JSON model → `.drawio` XML, calling `dot` for positions and edge routes (and `neato -n2` for whole-graph routing on clustered models).

dot and draw.io never talk directly: dot computes geometry, draw.io renders, the generator translates.

## 2. Install matrix (cross-platform)

| Tool | Windows (winget) | macOS (Homebrew) | Debian/Ubuntu |
|------|------------------|------------------|----------------|
| Graphviz (required; bundles dot + neato + fdp) | `winget install Graphviz.Graphviz` | `brew install graphviz` | `sudo apt-get install -y graphviz` |
| draw.io desktop (export) | `winget install JGraph.Draw` | `brew install --cask drawio` | .deb/.AppImage from github.com/jgraph/drawio-desktop/releases |
| Python 3.10+ (required) | `winget install Python.Python.3.12` | `brew install python` | `sudo apt-get install -y python3` |

After installing Graphviz on Windows, open a new shell so `dot` is on PATH (`dot -V` to verify; `neato -V` too). Node.js is not needed.

## 3. Node shape catalog

Set per node via `"shape"`. `{fill}`/`{stroke}` come from the node's `fill`/`stroke`. Any node may instead supply a raw `"style"` to override, and `"w"`/`"h"` to resize.

| shape | draw.io style | default w×h | notes |
|-------|---------------|-------------|-------|
| `class` `entity` `object` | `swimlane;childLayout=stackLayout;…` | 260×auto | compartments from `attributes`/`methods`; `object` underlines the name |
| `component` | `rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;` | 180×70 | add `"stereotype":"component"` for the «component» tag |
| `package` | `shape=folder;tabWidth=64;tabHeight=18;tabPosition=left;` | 200×100 | tabbed folder |
| `box` | `rounded=0;whiteSpace=wrap;html=1;` | 170×60 | plain box — deployment node / generic |
| `usecase` | `ellipse;whiteSpace=wrap;html=1;` | 160×70 | |
| `actor` | `shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;` | 40×70 | stick figure, label below |
| `state` | `rounded=1;arcSize=30;whiteSpace=wrap;html=1;` | 150×56 | |
| `action` | `rounded=1;arcSize=45;whiteSpace=wrap;html=1;` | 150×50 | flatter rounded rect |
| `decision` | `rhombus;whiteSpace=wrap;html=1;` | 100×70 | activity decision/merge |
| `initial` | `ellipse;fillColor=#333333;strokeColor=#333333;` | 30×30 | filled start dot (no label) |
| `final` | `ellipse;…` + inner filled dot | 34×34 | bullseye (generator adds the inner dot) |
| `note` | `shape=note;whiteSpace=wrap;html=1;` | 170×70 | dog-eared annotation |

Title rendering: `«stereotype»` on its own line above a bold name; `interface`/`abstract` stereotypes (or `"italic": true`) italicise the name; `object` underlines it.

## 4. Edge arrow catalog

Set per edge via `"arrow"`. All inherit `edgeStyle=orthogonalEdgeStyle;rounded=0;`.

| arrow | style fragment | meaning |
|-------|----------------|---------|
| `generalization` | `endArrow=block;endFill=0;endSize=14;` | generalization (extends) |
| `realization` | `endArrow=block;endFill=0;endSize=14;dashed=1;` | realization (implements) |
| `composition` | `startArrow=diamondThin;startFill=1;startSize=14;endArrow=open;endFill=0;` | composition |
| `aggregation` | `startArrow=diamondThin;startFill=0;startSize=14;endArrow=open;endFill=0;` | aggregation |
| `directed_association` | `endArrow=open;` | directed association (navigability arrow) |
| `dependency` | `endArrow=open;dashed=1;` | dependency; use label `«include»`/`«extend»` for use-case |
| `transition` | `endArrow=block;endFill=1;endSize=10;` | state / activity flow |
| `association` | `endArrow=none;` | plain association (no arrowhead) |

For `generalization`/`realization` the generator feeds dot the edge reversed so the parent ranks above the child; the drawn arrow still points child → parent.

## 5. Colour palette

Colour by role so related nodes read together (fill / stroke):

| role | fill | stroke |
|------|------|--------|
| adapter / boundary | `#DAE8FC` | `#6C8EBF` |
| interface / protocol | `#E1D5E7` | `#9673A6` |
| concrete / active state | `#D5E8D4` | `#82B366` |
| entity / service | `#EEF0FF` | `#5B5FC7` |
| value / passive | `#F5F5F5` | `#999999` |
| external / decision | `#FFF2CC` | `#D6B656` |
| actor / highlight | `#FFE6CC` | `#D79B00` |

## 6. Per-diagram-type recipes (worked model.json)

**Class** — compartments + UML relations:

```json
{"nodes": [
  {"name": "Shape", "shape": "class", "stereotype": "abstract", "fill": "#E1D5E7", "stroke": "#9673A6",
   "attributes": ["# x: int", "# y: int"], "methods": ["+ area(): float"]},
  {"name": "Circle", "shape": "class", "fill": "#D5E8D4", "stroke": "#82B366",
   "attributes": ["+ r: float"], "methods": ["+ area(): float"]}],
 "edges": [{"source": "Circle", "target": "Shape", "arrow": "generalization"}]}
```

**State machine** — `initial` / `state` / `final` + `transition` (label = event/guard):

```json
{"nodes": [
  {"name": "start", "shape": "initial"},
  {"name": "Open", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "Closed", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "end", "shape": "final"}],
 "edges": [
  {"source": "start", "target": "Open", "arrow": "transition"},
  {"source": "Open", "target": "Closed", "arrow": "transition", "label": "close()"},
  {"source": "Closed", "target": "end", "arrow": "transition", "label": "dispose()"}]}
```

**Activity** — `initial` / `action` / `decision` / `final`; guards in labels:

```json
{"nodes": [
  {"name": "go", "shape": "initial"},
  {"name": "Validate", "shape": "action", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "valid?", "shape": "decision", "fill": "#FFF2CC", "stroke": "#D6B656"},
  {"name": "Save", "shape": "action", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "done", "shape": "final"}],
 "edges": [
  {"source": "go", "target": "Validate", "arrow": "transition"},
  {"source": "Validate", "target": "valid?", "arrow": "transition"},
  {"source": "valid?", "target": "Save", "arrow": "transition", "label": "yes"},
  {"source": "valid?", "target": "done", "arrow": "transition", "label": "no"},
  {"source": "Save", "target": "done", "arrow": "transition"}]}
```

**Use case** — `actor` + `usecase`; `association` for participation, `dependency` + `«include»`/`«extend»`. Use `"options": {"rankdir": "LR"}`:

```json
{"options": {"rankdir": "LR"},
 "nodes": [
  {"name": "Customer", "shape": "actor", "fill": "#DAE8FC", "stroke": "#6C8EBF"},
  {"name": "Checkout", "shape": "usecase", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "Pay", "shape": "usecase", "fill": "#D5E8D4", "stroke": "#82B366"}],
 "edges": [
  {"source": "Customer", "target": "Checkout", "arrow": "association"},
  {"source": "Checkout", "target": "Pay", "arrow": "dependency", "label": "«include»"}]}
```

**Component / package / deployment** — `component`, `package`, `box`; `dependency`/`directed_association`:

```json
{"nodes": [
  {"name": "Frontend", "shape": "package", "fill": "#F5F5F5", "stroke": "#999999"},
  {"name": "ApiGateway", "shape": "component", "stereotype": "component", "fill": "#DAE8FC", "stroke": "#6C8EBF"},
  {"name": "Postgres", "shape": "box", "fill": "#E1D5E7", "stroke": "#9673A6"}],
 "edges": [
  {"source": "Frontend", "target": "ApiGateway", "arrow": "dependency", "label": "calls"},
  {"source": "ApiGateway", "target": "Postgres", "arrow": "directed_association"}]}
```

**ER** — `entity` (compartments hold columns); multiplicity in the edge label:

```json
{"nodes": [
  {"name": "Customer", "shape": "entity", "fill": "#EEF0FF", "stroke": "#5B5FC7",
   "attributes": ["PK id: int", "name: text"]},
  {"name": "Order", "shape": "entity", "fill": "#EEF0FF", "stroke": "#5B5FC7",
   "attributes": ["PK id: int", "FK customer_id: int"]}],
 "edges": [{"source": "Customer", "target": "Order", "arrow": "directed_association", "label": "1 .. *"}]}
```

**Object** — `object` underlines the instance name (`name : Class`):

```json
{"nodes": [
  {"name": "alice : Customer", "shape": "object", "fill": "#EEF0FF", "stroke": "#5B5FC7",
   "attributes": ["id = 7", "name = Alice"]}],
 "edges": []}
```

## 7. The dot → draw.io coordinate transform

`dot -Tplain` emits **inches**, origin **bottom-left**, y **up**. draw.io uses **pixels**, origin **top-left**, y **down**. The generator converts every point identically:

- `px = inch * 72`
- flip y with graph height `H`: `y_px = (H - y_inch) * 72`
- translate so the min corner sits at `(40, 40)` (flat path) or `(MARGIN, MARGIN)` (clustered path; `MARGIN=70`, room for cluster labels)

Applying the same transform to node corners and edge polyline points is what keeps the imported routes aligned with the boxes. The pinned routing pass (§12) does this in reverse and then forward again — see there.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `dot: command not found` | Graphviz not installed / not on PATH | install, open a new shell, `dot -V` |
| cross-cluster edges cut through boxes | `neato`/`fdp` missing → routing pass skipped | install full Graphviz; `neato -V` must work |
| lines cut through boxes (flat model) | edge routes not imported | the generator imports `splines=ortho` routes already; if hand-rolling, do the same |
| diagram blank / won't open | malformed XML (unescaped `& < >`) | escape them; the generator validates with `minidom` and fails fast |
| draw.io CLI hangs on Linux | Electron has no display | `xvfb-run -a "$DRAWIO" … --no-sandbox` |
| a shape renders as a plain box | unknown `shape` name | use a catalog name (section 3) or pass a raw `"style"` |
| labels clipped in a class box | box too narrow | raise `options.col_w` or set per-node `"w"` |
| self-transition missing | `splines=ortho` drops self-loops | model recursion as an attribute, or add the self-edge by hand in draw.io |
| `'cp932' codec can't encode '—'` | Windows console encoding on the dot subprocess | the generator passes `encoding="utf-8"` to dot on the cluster paths; keep it |
| asked for a sequence diagram | not a graph-layout problem | decline; suggest Mermaid `sequenceDiagram` or PlantUML |

---

# Extensions: clusters, legend, banded layout, box-avoiding routing

Everything below is **opt-in and additive**. A model with no `cluster` / `options.clusters` / `options.layout` keys takes the stock flat path (§1–§8) and renders byte-identically to the stock skill. The moment any of those keys appears, the generator switches to the clustered path described here.

## 9. Clusters (grouping nodes into labelled boxes)

Give a node a `"cluster": "<key>"` and describe each cluster under `options.clusters`:

```json
"options": {
  "clusters": {
    "core":  {"label": "Core domain",   "stroke": "#5B5FC7", "fill": "#EEF0FF"},
    "infra": {"label": "Infrastructure", "stroke": "#82B366", "fill": "#E7F4E7"}
  }
}
```

- `label` — the cluster-box title (top-left) and the cluster's legend text (the part before `—` is used in the legend swatch).
- `stroke` — the dashed cluster-box border colour and the legend swatch colour.
- `fill` — a *suggested* node fill. The generator treats **per-node `fill`/`stroke` as authoritative** and the cluster's `fill`/`stroke` as the cluster-box/legend source, so for a uniform look set each node's `fill` to the cluster `fill` and `stroke` to the cluster `stroke`.

A node with no `cluster` stays top-level (un-boxed). Cluster boxes are computed from the bounding box of their members (`-Tplain` does not emit cluster bboxes), padded by `PAD≈24` on the sides and `TOP_PAD≈34` on top for the label, and emitted **before** the node cells so draw.io's z-order (= document order) puts them behind the boxes.

**Without** `options.layout`, all clusters are laid out in a single `dot` run using `subgraph cluster_*` blocks (dot keeps each cluster contiguous and non-overlapping), then the pinned routing pass (§12) routes every edge around the boxes.

## 10. Legend

When `options.clusters` is present, a legend row is drawn below the diagram: one coloured `■` swatch + label per cluster, then the UML arrow-kind glyphs — `◆ composition`, `◇ aggregation`, `→ association`, `⇢ dependency`. The legend HTML is built with entities (`&#9632;`, `&nbsp;`, `<font color=…>`) and then **escaped like every other cell value** (`&`→`&amp;` etc.); draw.io un-escapes the attribute and renders the HTML. (Emitting raw `&`/`<`/`>` in an XML attribute would break well-formedness — always escape.)

## 11. Banded / compass layout (`options.layout.rows`)

```json
"options": {
  "layout": {"rows": [["input", "consider", "output"], ["vocabulary"]]}
}
```

`rows` is a list of bands. **Row 0 is the TOP band**; within a row, clusters are placed **left → right** in listed order; rows stack **top → bottom**. So the example yields `input | consider | output` across the top and a full-width `vocabulary` band beneath.

**Why each cluster gets its OWN dot run.** Plain `dot` is a 1-D layered engine. A single `dot` run **cannot** force input-left / consider-center / output-right AND a full-width band below: the heavily-connected cluster always migrates toward its edge mass, and one run interleaves clusters of unequal height. (Verified empirically across `rankdir` / `rank=same` / `ordering` / `constraint=false`.) So:

- Each cluster is laid out in an **isolated** `dot -Tplain` run that places its members and routes its **internal** edges orthogonally.
- A cluster that is the **sole** member of its row spans the full width → laid out `LR` (wide strip). Clusters that **share** a row → laid out `TB` (tall column, reads top-down).
- The per-cluster results are composed onto the rows grid: each row centred on the widest row, `CLUSTER_GAP≈90` between clusters in a row, `BAND_GAP≈150` between rows.

This two-stage structure (per-cluster layout → grid composition) is then topped by the routing pass (§12), which re-routes **all** edges over the composed positions.

## 12. Box-avoiding edge routing (the pinned final pass)

**The problem it solves.** When clusters are laid out independently (§11), a cross-cluster edge (e.g. `Probe → GameMove`, or a `consider → vocabulary` dependency) is in *no* single dot run, so it has no precomputed route. Left to draw.io's auto-router, such an edge visibly cuts across boxes.

**The fix — a final, position-pinned Graphviz pass over the whole graph.** After placement has produced the final position of every node (in draw.io px), the generator runs ONE more Graphviz pass that:

1. Emits **every** node with its position **pinned** (`pos="x,y!"`, the trailing `!` = "do not move") and its `width`/`height` fixed (`fixedsize=true`) so the router knows the box extents to avoid.
2. Sets `splines=ortho` and emits **all** edges (internal + cross-cluster), undirected and de-duplicated (we only need the geometry; draw.io applies the arrowheads).
3. Uses an engine that **honours pinned positions and only routes edges**: `neato -n2 -Tplain` (falls back to `fdp -n2`, then `neato -n`). `-n2` means "input already has node positions; do not run layout, just route."
4. Parses the routed polylines and **overwrites the route table for every edge** with these whole-graph, box-avoiding routes (replacing the per-cluster internal routes too, so everything is routed consistently).
5. Imports the polylines as draw.io waypoints exactly like the flat path (`<Array as="points">` of inner `<mxPoint>`s; endpoints `pts[1:-1]` stripped; reversed for `generalization`/`realization`).

**The unit round-trip (the subtle part).** `neato -n`/`-n2` reads `pos` in **points** (origin bottom-left, y up); `-Tplain` re-emits in inches. Rather than guess the engine's graph height or input scale, the generator **pins the nodes and then reads their echoed centres back**: because it also knows each node's centre in draw.io px, it recovers the exact affine map (`x' = x_pt + ox`, `y' = -y_pt + oy`) from those known correspondences and applies it to every routed waypoint. This is immune to scale/height guesswork — the routed lines line up with the boxes exactly. (Sanity-check by rendering the PNG anyway.)

**Constraints.** `splines=ortho` still breaks on self-loops, so the pass **skips** any edge whose source == target — model recursion as an attribute, never a self-edge. The pass operates on the **flat** pinned graph (no subgraphs — positions are already fixed), so the engine never tries to box-pad clusters.

**Result on the reference model** (17–18 nodes, 26 edges, 4 clusters incl. ~8 cross-cluster edges): all 26 edges receive waypoints and a geometric check confirms **no edge segment passes through a non-endpoint box interior**.

## 13. Worked example: clustered + banded class diagram

A compact version of the shape this skill was built for — three clusters across the top, a full-width band below, cross-cluster edges, a legend, box-avoiding routes:

```json
{
  "options": {
    "rankdir": "TB", "node_separation": 0.85, "rank_separation": 1.3, "column_width": 300,
    "layout": {"rows": [["input", "consider", "output"], ["vocabulary"]]},
    "clusters": {
      "input":      {"label": "Input port — perception",     "stroke": "#2F8FA8", "fill": "#E3F2F5"},
      "consider":   {"label": "Consider — the Conception",   "stroke": "#9673A6", "fill": "#EDE7F6"},
      "output":     {"label": "Output port — action",        "stroke": "#D79B00", "fill": "#FFF0DD"},
      "vocabulary": {"label": "Vocabulary — Lexicon",        "stroke": "#82B366", "fill": "#E7F4E7"}
    }
  },
  "nodes": [
    {"name": "Conception", "shape": "class", "cluster": "consider", "fill": "#EDE7F6", "stroke": "#9673A6",
     "attributes": ["goal : GoalPredicate", "plan : GamePlan"]},
    {"name": "GoalPredicate", "shape": "class", "cluster": "consider", "fill": "#EDE7F6", "stroke": "#9673A6",
     "attributes": ["kind : Atom|AND|OR|SEQUENCE"], "methods": ["test(state) : bool"]},
    {"name": "Probe", "shape": "class", "cluster": "input", "fill": "#E3F2F5", "stroke": "#2F8FA8",
     "attributes": ["moves : GameMove[*]"]},
    {"name": "GameMove", "shape": "class", "cluster": "output", "fill": "#FFF0DD", "stroke": "#D79B00",
     "attributes": ["kind", "params (coords?)"]},
    {"name": "GameObject", "shape": "class", "cluster": "vocabulary", "fill": "#E7F4E7", "stroke": "#82B366",
     "attributes": ["id", "profile : Profile"]},
    {"name": "Relation", "shape": "class", "cluster": "vocabulary", "fill": "#E7F4E7", "stroke": "#82B366",
     "attributes": ["arity : n", "detector"]}
  ],
  "edges": [
    {"source": "Conception", "target": "GoalPredicate", "arrow": "composition", "label": "goal"},
    {"source": "Probe", "target": "GameMove", "arrow": "aggregation", "label": "trial moves  1..*"},
    {"source": "GoalPredicate", "target": "GameObject", "arrow": "dependency", "label": "conditions over objects"},
    {"source": "GoalPredicate", "target": "Relation", "arrow": "dependency", "label": "tests relations"},
    {"source": "Relation", "target": "GameObject", "arrow": "directed_association", "label": "over (n) objects"}
  ]
}
```

Generate and export:

```bash
python scripts/draw.py model.json out.drawio
"$DRAWIO" -x -f png -e -b 12 -o out.png out.drawio   # then READ out.png to verify
```

Expect: three labelled dashed cluster boxes across the top (`input`, `consider`, `output`), a full-width `vocabulary` band below, a legend row at the bottom, and every edge — including the `Probe → GameMove` and `GoalPredicate → vocabulary` cross-cluster edges — routed around the boxes rather than through them.
