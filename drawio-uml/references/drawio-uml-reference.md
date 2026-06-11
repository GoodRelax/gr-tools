# drawio-uml — reference

Depth behind SKILL.md: concepts, install, the full preset catalog, per-diagram-type
worked examples, the coordinate transform, and troubleshooting.

## Contents
1. The three tools and how they relate
2. Install matrix (cross-platform)
3. Node shape catalog
4. Edge arrow catalog
5. Colour palette
6. Per-diagram-type recipes (worked model.json)
7. The dot → draw.io coordinate transform
8. Troubleshooting

## 1. The three tools and how they relate

- **Graphviz** — takes a graph (nodes + edges) and lays it out automatically. **`dot`** is its layered (Sugiyama-style) engine: it ranks nodes into levels and minimises crossings; with `splines=ortho` it also produces orthogonal edge routes that avoid node boxes. Input is the **DOT language** (`digraph G { A -> B }`). Class/state/activity/component diagrams all want `dot`.
- **draw.io / diagrams.net** — a free editor (desktop / browser / VS Code). Files are `.drawio` (`mxGraphModel` XML). It has native shapes for every UML element and a desktop **CLI** that exports to PNG/SVG/PDF, embedding the source XML so exports stay editable.
- **The generator** (`scripts/drawio_uml.py`) is the glue: JSON model → `.drawio` XML, calling `dot` for positions and edge routes.

dot and draw.io never talk directly: dot computes geometry, draw.io renders, the generator translates.

## 2. Install matrix (cross-platform)

| Tool | Windows (winget) | macOS (Homebrew) | Debian/Ubuntu |
|------|------------------|------------------|----------------|
| Graphviz (required) | `winget install Graphviz.Graphviz` | `brew install graphviz` | `sudo apt-get install -y graphviz` |
| draw.io desktop (export) | `winget install JGraph.Draw` | `brew install --cask drawio` | .deb/.AppImage from github.com/jgraph/drawio-desktop/releases |
| Python 3.10+ (required) | `winget install Python.Python.3.12` | `brew install python` | `sudo apt-get install -y python3` |

After installing Graphviz on Windows, open a new shell so `dot` is on PATH (`dot -V` to verify). Node.js is not needed.

## 3. Node shape catalog

Set per node via `"shape"`. `{fill}`/`{stroke}` come from the node's `fill`/`stroke`. Any node may instead supply a raw `"style"` to override, and `"w"`/`"h"` to resize.

| shape | draw.io style | default w×h | notes |
|-------|---------------|-------------|-------|
| `class` `entity` `object` | `swimlane;childLayout=stackLayout;…` | 260×auto | compartments from `attrs`/`methods`; `object` underlines the name |
| `component` | `rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;` | 180×70 | add `"stereotype":"component"` for the «component» tag |
| `package` | `shape=folder;tabWidth=64;tabHeight=18;tabPosition=left;` | 200×100 | tabbed folder |
| `node` | `rounded=0;whiteSpace=wrap;html=1;` | 170×60 | plain box — deployment node / generic |
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
| `gen` | `endArrow=block;endFill=0;endSize=14;` | generalization (extends) |
| `real` | `endArrow=block;endFill=0;endSize=14;dashed=1;` | realization (implements) |
| `comp` | `startArrow=diamondThin;startFill=1;startSize=14;endArrow=open;endFill=0;` | composition |
| `aggr` | `startArrow=diamondThin;startFill=0;startSize=14;endArrow=open;endFill=0;` | aggregation |
| `assoc` | `endArrow=open;` | directed association |
| `dep` | `endArrow=open;dashed=1;` | dependency; use label `«include»`/`«extend»` for use-case |
| `transition` | `endArrow=block;endFill=1;endSize=10;` | state / activity flow |
| `line` | `endArrow=none;` | plain association (actor–usecase) |

For `gen`/`real` the generator feeds dot the edge reversed so the parent ranks above the child; the drawn arrow still points child → parent.

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
   "attrs": ["# x: int", "# y: int"], "methods": ["+ area(): float"]},
  {"name": "Circle", "shape": "class", "fill": "#D5E8D4", "stroke": "#82B366",
   "attrs": ["+ r: float"], "methods": ["+ area(): float"]}],
 "edges": [{"source": "Circle", "target": "Shape", "arrow": "gen"}]}
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

**Use case** — `actor` + `usecase`; `line` for participation, `dep` + `«include»`/`«extend»`. Use `"options": {"rankdir": "LR"}`:

```json
{"options": {"rankdir": "LR"},
 "nodes": [
  {"name": "Customer", "shape": "actor", "fill": "#DAE8FC", "stroke": "#6C8EBF"},
  {"name": "Checkout", "shape": "usecase", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "Pay", "shape": "usecase", "fill": "#D5E8D4", "stroke": "#82B366"}],
 "edges": [
  {"source": "Customer", "target": "Checkout", "arrow": "line"},
  {"source": "Checkout", "target": "Pay", "arrow": "dep", "label": "«include»"}]}
```

**Component / package / deployment** — `component`, `package`, `node`; `dep`/`assoc`:

```json
{"nodes": [
  {"name": "Frontend", "shape": "package", "fill": "#F5F5F5", "stroke": "#999999"},
  {"name": "ApiGateway", "shape": "component", "stereotype": "component", "fill": "#DAE8FC", "stroke": "#6C8EBF"},
  {"name": "Postgres", "shape": "node", "fill": "#E1D5E7", "stroke": "#9673A6"}],
 "edges": [
  {"source": "Frontend", "target": "ApiGateway", "arrow": "dep", "label": "calls"},
  {"source": "ApiGateway", "target": "Postgres", "arrow": "assoc"}]}
```

**ER** — `entity` (compartments hold columns); multiplicity in the edge label:

```json
{"nodes": [
  {"name": "Customer", "shape": "entity", "fill": "#EEF0FF", "stroke": "#5B5FC7",
   "attrs": ["PK id: int", "name: text"]},
  {"name": "Order", "shape": "entity", "fill": "#EEF0FF", "stroke": "#5B5FC7",
   "attrs": ["PK id: int", "FK customer_id: int"]}],
 "edges": [{"source": "Customer", "target": "Order", "arrow": "assoc", "label": "1 .. *"}]}
```

**Object** — `object` underlines the instance name (`name : Class`):

```json
{"nodes": [
  {"name": "alice : Customer", "shape": "object", "fill": "#EEF0FF", "stroke": "#5B5FC7",
   "attrs": ["id = 7", "name = Alice"]}],
 "edges": []}
```

## 7. The dot → draw.io coordinate transform

`dot -Tplain` emits **inches**, origin **bottom-left**, y **up**. draw.io uses **pixels**, origin **top-left**, y **down**. The generator converts every point identically:

- `px = inch * 72`
- flip y with graph height `H`: `y_px = (H - y_inch) * 72`
- translate so the min corner sits at `(40, 40)`

Applying the same transform to node corners and edge polyline points is what keeps the imported routes aligned with the boxes.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `dot: command not found` | Graphviz not installed / not on PATH | install, open a new shell, `dot -V` |
| lines cut through boxes | edge routes not imported | the generator imports `splines=ortho` routes already; if hand-rolling, do the same |
| diagram blank / won't open | malformed XML (unescaped `& < >`) | escape them; the generator validates with `minidom` and fails fast |
| draw.io CLI hangs on Linux | Electron has no display | `xvfb-run -a "$DRAWIO" … --no-sandbox` |
| a shape renders as a plain box | unknown `shape` name | use a catalog name (section 3) or pass a raw `"style"` |
| labels clipped in a class box | box too narrow | raise `options.col_w` or set per-node `"w"` |
| self-transition missing | `splines=ortho` drops self-loops | add the self-edge by hand in draw.io |
| asked for a sequence diagram | not a graph-layout problem | decline; suggest Mermaid `sequenceDiagram` or PlantUML |
