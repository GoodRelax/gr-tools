---
name: drawio-uml
description: Generate clean UML and node-link diagrams as native draw.io (.drawio) files with automatic, non-overlapping layout — Graphviz dot computes both node positions AND orthogonal edge routes, so lines never cut through boxes. Use whenever the user wants to draw, generate, or clean up a diagram in draw.io or drawio — class, state-machine, use-case, component, package, activity, deployment, ER, or object diagrams — especially when layout quality matters (overlapping lines, edges crossing boxes, messy auto-layout, or a Mermaid diagram that looks bad). Also use when reverse-engineering structure from source code into a diagram, or when the user says an existing diagram is ugly, low-quality, or hard to read. Produces real UML shapes (class compartments, state rounded-rects, use-case ellipses, actors, decision diamonds, package folders) with proper UML arrows, exported to PNG/SVG via the draw.io CLI. Does NOT do sequence or timing diagrams. Requires Graphviz (dot), draw.io desktop, and Python 3.10+.
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

## Prerequisites (check once per machine)

```bash
dot -V            # Graphviz — the layout engine (REQUIRED)
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

### 2. Generate the .drawio

```bash
python <SKILL_DIR>/scripts/drawio_uml.py model.json out.drawio
```

`<SKILL_DIR>` is this skill's directory. The script emits native shapes, pulls positions + orthogonal routes from `dot`, self-validates the XML, and prints a confirmation. A malformed model fails fast.

### 3. Export to PNG/SVG (recommended)

```bash
DRAWIO="/c/Program Files/draw.io/draw.io.exe"   # macOS: /Applications/draw.io.app/Contents/MacOS/draw.io ; Linux: drawio
"$DRAWIO" -x -f png -e -b 12 -o out.drawio.png out.drawio
"$DRAWIO" -x -f svg -e -b 12 -o out.drawio.svg out.drawio
```

`-x` export, `-f` format, `-e` embed editable XML, `-b` border, `-o` output. Headless Linux: `xvfb-run -a ... --no-sandbox`.

### 4. Verify

Read the exported PNG and check: shapes render as intended, arrowheads are the correct kind, and **no box is crossed by an edge**. Reading the image back is the cheapest way to catch a problem before showing the user.

## Tuning layout (if anything overlaps)

- **More room**: raise `options.ranksep` / `options.nodesep`.
- **Orientation**: `options.rankdir` = `"TB"` (top-down, default) or `"LR"` — `"LR"` suits use-case and wide hierarchies.
- **Fewer crossings by design**: keep the primary structure (inheritance, control flow) as the backbone; dash or drop secondary `dep`/`assoc` edges.
- **Interactive last resort**: open in draw.io, `Arrange → Layout → Vertical Tree` / `Hierarchical`, or drag.

## Pitfalls

- The generator escapes `&`, `<`, `>` for you; if you hand-edit `.drawio` XML, do the same.
- `splines=ortho` dislikes self-loops (an edge from a node to itself — common in state machines for a self-transition). If you need one, add it by hand in draw.io, or give that node a short detour via an intermediate point.
- Keep `model.json` as the single source of truth and regenerate, rather than editing the `.drawio` by hand — that keeps the diagram reproducible.
- Sequence/timing diagrams: decline and suggest Mermaid/PlantUML (see "What this can draw").

## Reference

`references/drawio-uml-reference.md` — concepts (what Graphviz/dot/draw.io are), the cross-platform install matrix, the full shape + arrow preset catalog with raw style strings, per-diagram-type worked `model.json` examples, the dot→draw.io coordinate-transform math, and a troubleshooting table.
