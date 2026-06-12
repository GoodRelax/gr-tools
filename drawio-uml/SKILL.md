---
name: drawio-uml
description: Generate clean UML and node-link diagrams as native draw.io (.drawio) files with automatic, non-overlapping layout — Graphviz dot computes both node positions AND orthogonal edge routes, so lines never cut through boxes. Use whenever the user wants to draw, generate, or clean up a diagram in draw.io or drawio — class, state-machine, use-case, component, package, activity, deployment, ER, or object diagrams — especially when layout quality matters (overlapping lines, edges crossing boxes, messy auto-layout, or a Mermaid diagram that looks bad). Also use when reverse-engineering structure from source code into a diagram, or when the user says an existing diagram is ugly, low-quality, or hard to read. Produces real UML shapes (class compartments, state rounded-rects, use-case ellipses, actors, decision diamonds, package folders) with proper UML arrows, exported to PNG/SVG via the draw.io CLI. Optionally groups nodes into labelled, coloured clusters with a legend, arranges clusters into named horizontal bands (compass layout), and routes EVERY edge — including cross-cluster ones — around the boxes via a position-pinned Graphviz pass. Does NOT do sequence or timing diagrams. Requires Graphviz (dot, plus neato/fdp for the pinned routing pass), draw.io desktop, and Python 3.10+.
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
| **Class** | `class` (compartments) | `gen` `real` `comp` `aggr` `assoc` `dep` |
| **Object** | `object` (underlined name) | `assoc` `line` |
| **ER** | `entity` (compartments) | `assoc` (multiplicity in label) |
| **State machine** | `initial` `state` `final` | `transition` (event/guard in label) |
| **Activity** | `initial` `action` `decision` `final` | `transition` (guard in label) |
| **Use case** | `actor` `usecase` | `line` (actor–uc), `dep` + `«include»`/`«extend»` label |
| **Component** | `component` `node` | `dep` `assoc` |
| **Package** | `package` | `dep` |
| **Deployment** | `node` `component` | `assoc` `dep` |

**Not supported: sequence and timing diagrams.** They are ordered by *time* along lifelines, which is not a graph-layout problem — dot does not help, and forcing it produces nonsense. Tell the user this honestly and suggest Mermaid `sequenceDiagram` or PlantUML instead.

## What this adds over the stock skill

This generator is a **strict superset** of the stock `drawio-uml` skill. A model that uses none of the keys below renders **byte-identically** to stock. On top of that it adds, all **opt-in** and **additive**:

- **Cluster grouping** — give nodes a `"cluster"` key and they get wrapped in a labelled, coloured dashed box.
- **Legend** — when clusters are defined, a legend row of cluster swatches + UML arrow-kind glyphs is drawn under the diagram.
- **Banded / compass layout** — `options.layout.rows` arranges whole clusters into horizontal bands (e.g. `input | consider | output` across the top, a full-width `vocabulary` band below).
- **Box-avoiding edge routing for ALL edges** — after placement, a final **position-pinned Graphviz pass** (`neato -n2` / `fdp -n2`, `splines=ortho`) routes *every* edge — internal **and** cross-cluster — around the placed boxes. No edge cuts through a class box, even when clusters are laid out independently.

If a model sets `cluster` / `options.clusters` / `options.layout`, the generator takes the clustered path; otherwise it takes the stock flat path. The two never interfere.

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
  "options": {"rankdir": "TB", "col_w": 260, "nodesep": 0.7, "ranksep": 1.1},
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
| `class` `entity` `object` | compartment box (name / attrs / methods) | `usecase` | ellipse |
| `component` | rectangle + «component» | `actor` | stick figure |
| `package` | folder | `state` `action` | rounded rectangle |
| `node` | plain rectangle | `decision` | diamond |
| `initial` | filled dot | `final` | bullseye |
| `note` | dog-eared note | | |

Compartment shapes take `attrs` and `methods` (lists of strings like `"+ name: str"`). Visibility: `+` public, `-` private, `#` protected, `~` package. Mark abstract/interface via `"stereotype"` + the name auto-italicises. Any node may override its preset with a raw draw.io `"style"` string, or set `"w"`/`"h"`.

**Edge arrows** (`arrow` field; source → target is the reading direction):

| arrow | UML meaning | arrow | UML meaning |
|-------|-------------|-------|-------------|
| `gen` | generalization (extends) | `assoc` | association (open arrow) |
| `real` | realization (implements) | `dep` | dependency (dashed); use label `«include»`/`«extend»` |
| `comp` | composition (filled diamond) | `transition` | state/activity flow |
| `aggr` | aggregation (hollow diamond) | `line` | plain line, no arrowhead (actor–usecase) |

Put multiplicity / role / guard text in the optional edge `"label"`. Colour by layer so related nodes read together (palette in the reference).

### 1b. (Optional) clusters, a legend, and banded layout

To group nodes, add a `"cluster"` key per node and describe each cluster under `options.clusters`. To arrange whole clusters into bands, add `options.layout.rows`. **All three keys are opt-in — omit them for the stock flat diagram.**

```json
{
  "options": {
    "rankdir": "TB", "col_w": 300,
    "clusters": {
      "input":      {"label": "Input port — perception", "color": "#2F8FA8", "tint": "#E3F2F5"},
      "consider":   {"label": "Consider — the Conception", "color": "#9673A6", "tint": "#EDE7F6"},
      "output":     {"label": "Output port — action", "color": "#D79B00", "tint": "#FFF0DD"},
      "vocabulary": {"label": "Vocabulary — Lexicon", "color": "#82B366", "tint": "#E7F4E7"}
    },
    "layout": {"rows": [["input", "consider", "output"], ["vocabulary"]]}
  },
  "nodes": [
    {"name": "Probe", "shape": "class", "cluster": "input",
     "fill": "#E3F2F5", "stroke": "#2F8FA8", "attrs": ["moves : GameMove[*]"]},
    {"name": "GameMove", "shape": "class", "cluster": "output",
     "fill": "#FFF0DD", "stroke": "#D79B00", "attrs": ["kind", "params"]}
  ],
  "edges": [
    {"source": "Probe", "target": "GameMove", "arrow": "aggr", "label": "trial moves"}
  ]
}
```

New schema keys:

| key | scope | meaning |
|-----|-------|---------|
| `"cluster": "<key>"` | per node | put this node in that cluster. No `cluster` ⇒ node stays top-level (un-boxed). |
| `options.clusters` | `{ "<key>": {"label", "color", "tint"} }` | `label` = cluster-box title + legend text; `color` = dashed border + legend swatch; `tint` = a suggested fill. **Per-node `fill`/`stroke` win** — set them to the cluster's tint/color for a uniform look. |
| `options.layout.rows` | `[[clusterKey, …], …]` | **banded/compass layout.** Row 0 is the TOP band; within a row clusters sit left→right in listed order; rows stack top→bottom. A cluster alone in its row spans full width (laid out as a wide LR strip); clusters sharing a row are tall TB columns. |

The **legend** is drawn whenever `options.clusters` is present. **Box-avoiding routing** runs automatically on any clustered model — you don't enable it, and you should expect **no edge to cross any box**, including cross-cluster edges. See the reference §9–§12 for the full mechanism.

### 2. Generate the .drawio

```bash
python <SKILL_DIR>/scripts/drawio_uml.py model.json out.drawio
```

`<SKILL_DIR>` is this skill's directory. The script emits native shapes, pulls positions + orthogonal routes from `dot` (and, for clustered models, the pinned `neato -n2` routing pass), self-validates the XML, and prints a confirmation. A malformed model fails fast.

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

- **More room**: raise `options.ranksep` / `options.nodesep`.
- **Orientation**: `options.rankdir` = `"TB"` (top-down, default) or `"LR"` — `"LR"` suits use-case and wide hierarchies.
- **Banded gaps**: clusters in a row are `CLUSTER_GAP` apart; bands are `BAND_GAP` apart (constants near the top of the script).
- **Fewer crossings by design**: keep the primary structure (inheritance, control flow) as the backbone; dash or drop secondary `dep`/`assoc` edges.
- **Interactive last resort**: open in draw.io, `Arrange → Layout → Vertical Tree` / `Hierarchical`, or drag.

## Pitfalls

- The generator escapes `&`, `<`, `>` for you (including the legend HTML); if you hand-edit `.drawio` XML, do the same.
- `splines=ortho` dislikes self-loops (an edge from a node to itself — common in state machines for a self-transition, or a recursive composite). Model recursion as an **attribute/label**, not a self-edge; the routing pass skips self-loops for the same reason. If you truly need one, add it by hand in draw.io.
- Keep `model.json` as the single source of truth and regenerate, rather than editing the `.drawio` by hand — that keeps the diagram reproducible.
- The pinned routing pass needs `neato` (or `fdp`) from Graphviz on PATH. If neither is found, clustered models still render but cross-cluster edges fall back to draw.io's auto-router (which may cross boxes) — install Graphviz fully.
- Sequence/timing diagrams: decline and suggest Mermaid/PlantUML (see "What this can draw").

## Reference

`references/drawio-uml-reference.md` — concepts (what Graphviz/dot/draw.io are), the cross-platform install matrix, the full shape + arrow preset catalog with raw style strings, per-diagram-type worked `model.json` examples, the dot→draw.io coordinate-transform math, the **clusters / legend / banded-layout / box-avoiding-routing** sections with a worked clustered+banded example, and a troubleshooting table.
