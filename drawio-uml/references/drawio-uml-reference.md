# drawio-uml — reference

Depth behind SKILL.md: concepts, install, the full preset catalog, per-diagram-type
worked examples, the coordinate transform, the cluster tree / cascade / legend / views /
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
9. Clusters (the recursive `layout` tree)
10. Legend (outermost labelled clusters)
11. Composition, colour cascade, and views
12. Box-avoiding edge routing (the pinned final pass)
13. Worked example: clustered class diagram

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

Set per node via `"shape"`. `{fill}`/`{stroke}` come from the node's `fill`/`stroke`. Any node may instead supply a raw `"style"` to override, and `"width"`/`"height"` to resize.

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
| `final` | `ellipse;fillColor=none;strokeColor=#333333;strokeWidth=2;` + inner filled dot (centred, ~46%) | 34×34 | bullseye (generator adds the inner dot) |
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

**Cluster-endpoint edges.** An edge's `source`/`target` may name a **cluster** (not only a node), provided that cluster is **named AND labelled** (so a box is drawn to anchor to). The edge then connects to the cluster's box and is routed around the others by the pinned pass (§12) — use it for group-to-group relations such as Clean-Architecture layer dependencies. Resolution is **node-first, then cluster**; a name that is both, an unknown name, or an unnamed/label-less cluster endpoint fails fast. A degenerate edge whose endpoints geometrically contain one another (a node and its enclosing cluster; a cluster and itself / an ancestor / a descendant) is excluded from routing, like a self-loop.

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

**Use case** — `actor` + `usecase`; `association` for participation, `dependency` + `«include»`/`«extend»`. Use `"options": {"direction": "row"}`:

```json
{"options": {"direction": "row"},
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

**Layered component — cluster-endpoint edges** — relate whole layers, not representative nodes; the `depends on` arrows connect the layer *boxes* and route in the gaps (each endpoint is a named+labelled cluster, §4):

```json
{"title": "Layers",
 "nodes": [
  {"name": "UI", "shape": "box"}, {"name": "UseCases", "shape": "box"},
  {"name": "Repo", "shape": "box"}, {"name": "DB", "shape": "box"}],
 "edges": [
  {"source": "ui", "target": "domain", "arrow": "dependency", "label": "depends on"},
  {"source": "infra", "target": "domain", "arrow": "dependency", "label": "depends on"}],
 "layout": {"direction": "column", "clusters": [
  {"name": "ui", "label": "UI", "color": "#6C8EBF", "nodes": ["UI"]},
  {"name": "domain", "label": "Domain", "color": "#82B366", "nodes": ["UseCases"]},
  {"name": "infra", "label": "Infrastructure", "color": "#9673A6", "nodes": ["Repo", "DB"]}]}}
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
| labels clipped in a class box | box too narrow | raise `options.column_width` or set per-node `"width"` |
| self-transition missing | `splines=ortho` drops self-loops | model recursion as an attribute, or add the self-edge by hand in draw.io |
| `'cp932' codec can't encode '—'` | Windows console encoding on the dot subprocess | the generator passes `encoding="utf-8"` to dot on the cluster paths; keep it |
| an edge to a cluster is rejected (fails fast) | the endpoint cluster isn't both named **and** labelled | give it a `name` *and* a `label` — a cluster endpoint needs a drawn box to anchor to (§4) |
| edge endpoint "ambiguous" error | a node and a cluster share that name | rename one; endpoints resolve node-first then cluster, and a node/cluster name collision fails fast |
| asked for a sequence diagram | not a graph-layout problem | decline; suggest Mermaid `sequenceDiagram` or PlantUML |

---

# Extensions: cluster tree, cascade, legend, views, box-avoiding routing

Everything below applies when the model has a `layout` (a recursive cluster tree). A model with **no** `layout` takes the flat path (§1–§8): dot lays out every node and the flow follows `options.direction`. The `layout` tree replaces the 0.2.x `node.cluster` / `options.clusters` / `options.layout.rows` keys, which are removed in 0.3.0.

## 9. Clusters (the recursive `layout` tree)

`layout` is a tree of **clusters**. Each cluster:

- arranges its contents along `direction` — `row` (left→right) or `column` (top→bottom); resolves cluster → `options.direction` → `column`;
- draws a dashed labelled box **iff it has a `label`** (no label ⇒ an invisible arrangement-only container, used for unlabelled bands/rows);
- may set `name` (a unique, `/`-free id for `--view`/`--cluster` references and the table cluster path) and `color`/`fill` (which cascade — §11);
- may carry `description` / `remark` (table-only docs — `draw` ignores them; `table` lists them in a `## Clusters` section), and may itself be an edge endpoint when named+labelled (§4);
- holds EXACTLY ONE of `clusters` (child clusters ⇒ internal node) or `nodes` (member node names ⇒ leaf). List order = arrangement order.

```json
"layout": {
  "direction": "row",
  "clusters": [
    {"name": "core",  "label": "Core domain",   "color": "#5B5FC7", "fill": "#EEF0FF", "nodes": ["A", "B"]},
    {"name": "infra", "label": "Infrastructure", "color": "#82B366", "fill": "#E7F4E7", "nodes": ["C", "D"]}
  ]
}
```

**Leaf layout.** Each leaf is laid out in its **own** `dot -Tplain` run (`rankdir` from its `direction`) using only the structural edges among its members. A leaf whose members have **no** internal edges is stacked along `direction` with **invisible edges** (`style=invis`) in listed order — that is how an `input` cluster's `TurnRecord`/`Probe` stack vertically.

**Boxes.** A labelled cluster's box is the bounding box of its members, padded `PAD≈24` on the sides and `TOP_PAD≈34` on top for the label. Boxes are emitted **outermost-first** (document order = z-order) so an outer box sits *behind* its inner boxes. Up to ~3 labelled nesting levels read well; deeper triggers a stderr warning.

## 10. Legend

When the `layout` contains a labelled cluster, a legend row is drawn below the diagram: one coloured `■` swatch + label per **outermost labelled cluster** (a labelled cluster with no labelled ancestor), **deduplicated by colour** (a labelled cluster with no `color` falls back to `#888888`), then the UML arrow-kind glyphs — `◆ composition`, `◇ aggregation`, `→ association`, `⇢ dependency`. Inner sub-clusters add no swatch. Under a `--view`, the outermost set is recomputed on the pruned tree. The legend HTML is built with entities (`&#9632;`, `&nbsp;`, `<font color=…>`) and then **escaped like every other cell value**; draw.io un-escapes the attribute and renders the HTML.

## 11. Composition, colour cascade, and views

**Composition (the A2 engine).** Python composes the tree: each leaf is laid out independently (§9), then each internal cluster places its children along its `direction` — `row` left→right, `column` top→bottom, centred on the cross axis, `ROW_GAP`/`COL_GAP` apart. Sibling order is therefore the **listed order**, guaranteed by Python.

*Why Python composes instead of one big `dot` run.* Plain `dot` is a 1-D layered engine: a single run cannot be forced to put sibling sub-clusters in a chosen left→right order — the heavily-connected one migrates toward its edge mass. The one mechanism that pins sibling order, `rank=same` + flat invisible edges, **conflicts with cluster containment and segfaults `dot` 13.x** (verified). So `dot` only ever lays out a single leaf (its strength), and Python owns the ordering (ADR-009; PoC in `poc/cluster-layout/`).

**Colour cascade.** A cluster's `color` (→ descendant node `stroke`) and `fill` (→ descendant node `fill`) cascade to all descendant nodes. Resolution is **nearest-ancestor**, and `color`/`fill` resolve **independently** (a node can inherit fill from one ancestor and stroke from another). A node's own `fill`/`stroke` overrides the cascade. This removes the per-node colour repetition of the 0.2.x format.

**Views.** `views` maps named node subsets: `{ "<key>": {label?, nodes?, clusters?} }`. The node set = `nodes` (explicit names) ∪ the nodes under every named cluster in `clusters`. `draw.py --view KEY` and `table.py --view KEY` render the **induced subgraph** (only edges with both ends in the set); `draw` prunes the `layout` to the surviving nodes (empty boxes dropped, partial boxes shrink, legend recomputed). A cluster-endpoint edge (§4) survives a view iff **both** endpoint clusters still exist in the pruned tree (each keeps ≥1 selected node). `--view` and table's `--cluster` are mutually exclusive; unknown view / node / cluster names fail fast.

## 12. Box-avoiding edge routing (the pinned final pass)

**The problem it solves.** Because each leaf is laid out independently (§9), a cross-cluster edge (e.g. `Probe → GameMove`) is in *no* single dot run, so it has no precomputed route. Left to draw.io's auto-router, such an edge visibly cuts across boxes.

**The fix — a final, position-pinned Graphviz pass over the whole graph.** After placement has produced the final position of every node (in draw.io px), the generator runs ONE more Graphviz pass that:

1. Emits **every** node with its position **pinned** (`pos="x,y!"`, the trailing `!` = "do not move") and its `width`/`height` fixed (`fixedsize=true`) so the router knows the box extents to avoid.
2. Sets `splines=ortho` and emits **all** edges (internal + cross-cluster), undirected and de-duplicated (we only need the geometry; draw.io applies the arrowheads).
3. Uses an engine that **honours pinned positions and only routes edges**: `neato -n2 -Tplain` (falls back to `fdp -n2`, then `neato -n`). `-n2` means "input already has node positions; do not run layout, just route."
4. Parses the routed polylines and **builds the route table for every edge** from these whole-graph, box-avoiding routes.
5. Imports the polylines as draw.io waypoints exactly like the flat path (`<Array as="points">` of inner `<mxPoint>`s; endpoints `pts[1:-1]` stripped; reversed for `generalization`/`realization`).

**Cluster-endpoint edges (0.5.0).** A cluster used as an edge endpoint joins this same pinned pass as one extra fixed node — its id is the cluster box's `cid(name)`, its position/size the box's already-composed geometry (added in deterministic box order). neato routes the edge to the box like any other; the generator then **clips** the route at the box boundary (interior waypoints falling inside an endpoint box are dropped) and binds the drawn edge to the cluster box `mxCell`, so draw.io re-clips at the perimeter. Because a cluster box overlaps its own children, a pathological overlap can still defeat `ortho`; that degrades per §8 rather than guaranteeing a route.

**The unit round-trip (the subtle part).** `neato -n`/`-n2` reads `pos` in **points** (origin bottom-left, y up); `-Tplain` re-emits in inches. Rather than guess the engine's graph height or input scale, the generator **pins the nodes and then reads their echoed centres back**: because it also knows each node's centre in draw.io px, it recovers the exact affine map (`x' = x_pt + ox`, `y' = -y_pt + oy`) from those known correspondences and applies it to every routed waypoint. This is immune to scale/height guesswork — the routed lines line up with the boxes exactly. (Sanity-check by rendering the PNG anyway.)

**Constraints.** `splines=ortho` still breaks on self-loops, so the pass **skips** any edge whose source == target — model recursion as an attribute, never a self-edge. The pass operates on the **flat** pinned graph (no subgraphs — positions are already fixed), so it is independent of nesting depth.

**Long ids (0.5.0).** A long node name yields a long dot id, which `-Tplain` wraps (a trailing `\` continuation) and double-quotes. Every `-Tplain` parser therefore rejoins continuation lines on the raw text *before* splitting, and strips the surrounding quotes from id tokens before matching them to `nid`/`cid` — so long names/labels never break parsing.

**Result on the reference model** (18 nodes, 26 edges incl. ~8 cross-cluster edges): all 26 edges receive waypoints and a geometric check confirms **no edge segment passes through a non-endpoint box interior**.

## 13. Worked example: clustered class diagram

`input | consider | output` across the top with `consider` split into `world | goal`, a full-width `vocabulary` band below, cross-cluster edges, a legend, box-avoiding routes, and two views. Colours cascade from the clusters, so the nodes carry none:

```json
{
  "title": "GR-ARC-3 Domain Model (excerpt)",
  "options": {"direction": "column", "node_separation": 0.85, "rank_separation": 1.3, "column_width": 300},
  "nodes": [
    {"name": "Probe", "shape": "class", "attributes": ["moves : GameMove[*]"]},
    {"name": "TurnRecord", "shape": "class", "attributes": ["frames : Frame[*]"]},
    {"name": "Conception", "shape": "class", "attributes": ["goal : GoalPredicate", "plan : GamePlan"]},
    {"name": "WorldModel", "shape": "class", "attributes": ["rules : InteractionRule[*]"]},
    {"name": "GoalPredicate", "shape": "class", "attributes": ["kind"], "methods": ["test(state) : bool"]},
    {"name": "GameMove", "shape": "class", "attributes": ["kind", "params (coords?)"]},
    {"name": "Relation", "shape": "class", "attributes": ["arity : n", "detector"]}
  ],
  "edges": [
    {"source": "Conception", "target": "WorldModel", "arrow": "composition", "label": "world"},
    {"source": "Conception", "target": "GoalPredicate", "arrow": "composition", "label": "goal"},
    {"source": "Probe", "target": "GameMove", "arrow": "aggregation", "label": "trial moves  1..*"},
    {"source": "GoalPredicate", "target": "Relation", "arrow": "dependency", "label": "tests relations"}
  ],
  "layout": {
    "direction": "column",
    "clusters": [
      {"direction": "row", "clusters": [
        {"name": "input", "label": "Input port — perception", "color": "#2F8FA8", "fill": "#E3F2F5",
         "nodes": ["TurnRecord", "Probe"]},
        {"name": "consider", "label": "Consider — the Conception", "color": "#9673A6", "fill": "#EDE7F6",
         "clusters": [
           {"nodes": ["Conception"]},
           {"direction": "row", "clusters": [
             {"name": "world", "label": "world", "nodes": ["WorldModel"]},
             {"name": "goal",  "label": "goal",  "nodes": ["GoalPredicate"]}
           ]}
         ]},
        {"name": "output", "label": "Output port — action", "color": "#D79B00", "fill": "#FFF0DD",
         "nodes": ["GameMove"]}
      ]},
      {"name": "vocabulary", "label": "Vocabulary — Lexicon", "color": "#82B366", "fill": "#E7F4E7",
       "direction": "row", "nodes": ["Relation"]}
    ]
  },
  "views": {
    "answer": {"label": "The Conception", "nodes": ["Conception", "WorldModel", "GoalPredicate"]},
    "vocab":  {"label": "Vocabulary", "clusters": ["vocabulary"]}
  }
}
```

Generate and export:

```bash
python scripts/draw.py model.json out.drawio                    # the whole model
python scripts/draw.py model.json answer.drawio --view answer   # just the Conception internals
"$DRAWIO" -x -f png -e -b 12 -o out.png out.drawio   # then READ out.png to verify
```

Expect: `input | consider | output` across the top (input's two members stacked vertically), `consider` boxing `Conception` above a `world | goal` sub-row, a full-width `vocabulary` band below, a legend of the four outermost clusters, and every edge — including the `Probe → GameMove` cross-cluster edge — routed around the boxes rather than through them.
