# drawio-uml

Clean UML / node-link diagrams in **draw.io**, laid out automatically by **Graphviz** — no
overlapping lines, no edges cutting through boxes. Works as a **Claude Code skill**
(auto-triggers on diagram requests) or as a **standalone generator** you run by hand.

You write one `model.json` (the single source of truth); the generator draws the diagram and,
from the same file, Markdown node/edge tables. Grouping and arrangement are an optional recursive
`layout` tree, and `views` carve focused sub-diagrams out of a large model.

## What it is

You write a small `model.json` (boxes + arrows). The generator emits a native `.drawio` file,
asking Graphviz to compute **both** node positions **and** orthogonal edge routes, which it
imports as draw.io waypoints — so lines route *around* boxes, not through them. draw.io renders
the real UML shapes and exports to PNG/SVG.

It draws: class, object, ER, state-machine, activity, use-case, component, package, deployment.
**Not** sequence / timing diagrams (those are time-ordered, not a graph-layout problem — use
Mermaid or PlantUML).

Features (grouping is optional — omit `layout` for a plain flat diagram):

| Feature | What you get |
|---------|--------------|
| **Cluster tree** | `layout` is a recursive tree of clusters; each arranges its children/members along `direction` (`row`/`column`) and draws a labelled, coloured dashed box when it has a `label`. Nestable — e.g. `world \| goal \| plan` inside `consider`, `input \| consider \| output` across the top, a full-width `vocabulary` band below. |
| **Colour cascade** | A cluster's `color`/`fill` cascades to its descendant nodes (nearest ancestor wins; a node's own wins) — no repeating colours per node. |
| **Legend** | A row of swatches for the outermost labelled clusters (deduped by colour) + UML arrow glyphs (◆ ◇ → ⇢), under the diagram. |
| **Views** | `views` defines named node subsets; `--view KEY` renders the induced subgraph (the master layout pruned to those nodes) — one SSOT, many small diagrams. |
| **Edges that never cross boxes** | A final **position-pinned Graphviz pass** (`neato -n2`, `splines=ortho`) routes *every* edge — including cross-cluster ones — around the placed boxes. Verified: 0 edge-through-box crossings on the 26-edge reference model. |

A model with no `layout` takes the flat path (dot lays out everything; flow = `options.direction`).
The schema and full mechanism are documented in `SKILL.md` and
`references/drawio-uml-reference.md` (§9–§13).

## What's in this folder

| File | Purpose |
|------|---------|
| `SKILL.md` | The Claude Code skill manifest (frontmatter + workflow + new schema keys). |
| `scripts/draw.py` | Generator: JSON model → `.drawio` (native shapes + dot layout + pinned routing). |
| `scripts/table.py` | Generator: JSON model → `.md` node/edge tables (consumes `description`/`remark`). |
| `drawio-uml.bat` | Windows launcher: drag-and-drop model JSON → `.drawio` + `.md` + `.svg` + `.png`. |
| `schema/model.schema.json` | JSON Schema (draft-07) for the model — editor autocomplete / validation. |
| `references/drawio-uml-reference.md` | Concepts, install matrix, full shape/arrow catalog, per-type examples, cluster-tree/cascade/legend/views/edge-routing sections, troubleshooting. |
| `README.md` | This file. |

## Prerequisites

| Tool | Why | Windows | macOS | Linux |
|------|-----|---------|-------|-------|
| **Graphviz** (`dot` **and** `neato`/`fdp`) | layout + the pinned box-avoiding routing pass | `winget install Graphviz.Graphviz` | `brew install graphviz` | `sudo apt-get install -y graphviz` |
| **draw.io desktop** | PNG/SVG/PDF export (`.drawio` opens without it) | `winget install JGraph.Draw` | `brew install --cask drawio` | .deb/.AppImage from the [releases page](https://github.com/jgraph/drawio-desktop/releases) |
| **Python 3.10+** | runs the generator | `winget install Python.Python.3.12` | `brew install python` | `sudo apt-get install -y python3` |

Verify (open a fresh shell after installing Graphviz so it's on PATH):

```bash
dot -V            # Graphviz layout engine
neato -V          # ships with Graphviz; used by the box-avoiding routing pass
python --version  # 3.10 or newer
```

`neato`/`fdp` come bundled with Graphviz — no separate install. If they're missing, clustered
models still render but cross-cluster edges fall back to draw.io's auto-router (which can cross
boxes); install full Graphviz to get the guarantee. Node.js is not needed.

## Installation as a Claude Code skill

To make the skill **active**, it must live at `~/.claude/skills/drawio-uml/`. Copy (or symlink)
this folder there. Claude loads the skill from `~/.claude/skills/`, so the copy there is the
one that runs.

### Option A — copy (Windows, PowerShell)

```powershell
$src = "$env:USERPROFILE\OneDrive\Documents\GitHub\gr-tools\drawio-uml"
$dst = "$env:USERPROFILE\.claude\skills\drawio-uml"
Remove-Item -Recurse -Force $dst -ErrorAction SilentlyContinue   # drop any existing copy
robocopy $src $dst /MIR /XD .git | Out-Null                      # mirror the folder
```

(`robocopy … /MIR` mirrors the tree; `/XD .git` skips any VCS dir. Plain alternative:
`Copy-Item -Recurse -Force $src $dst`.)

### Option B — symlink / junction (Windows) — stays in sync with this repo

A link means edits here are picked up immediately, with no re-copy.

```powershell
$src = "$env:USERPROFILE\OneDrive\Documents\GitHub\gr-tools\drawio-uml"
$dst = "$env:USERPROFILE\.claude\skills\drawio-uml"
Remove-Item -Recurse -Force $dst -ErrorAction SilentlyContinue
# directory symlink (needs Developer Mode or an elevated shell):
New-Item -ItemType SymbolicLink -Path $dst -Target $src
# …or a junction, which needs no special privileges:
#   cmd /c mklink /J "$dst" "$src"
```

### macOS / Linux

```bash
SRC="$HOME/path/to/gr-tools/drawio-uml"
DST="$HOME/.claude/skills/drawio-uml"
rm -rf "$DST"
ln -s "$SRC" "$DST"        # symlink (or: cp -R "$SRC" "$DST" to copy)
```

After installing, ask Claude e.g. *"draw a class diagram of `src/` in draw.io"*,
*"make a clustered domain model with input/consider/output across the top"*, or
*"clean up this messy Mermaid diagram"*.

## Quick usage

**Easiest (Windows) — drag and drop.** Drop one or more `model.json` files onto
`drawio-uml.bat`. For each it writes, next to the input with the same base name,
a `.drawio` diagram, a `.md` table, and `.svg` + `.png` exports. From a shell you
can also run `drawio-uml.bat MODEL.json [MORE.json ...] [--cluster KEY | -c KEY]`
— `--cluster`/`-c` narrows the **table** to a cluster subtree (the diagram always
shows the whole model).

**By hand (any OS, no Claude):**

1. Write a `model.json`:

```json
{"nodes": [
  {"name": "start", "shape": "initial"},
  {"name": "Idle", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "Running", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
  {"name": "stop", "shape": "final"}],
 "edges": [
  {"source": "start", "target": "Idle", "arrow": "transition"},
  {"source": "Idle", "target": "Running", "arrow": "transition", "label": "play()"},
  {"source": "Running", "target": "stop", "arrow": "transition", "label": "end()"}]}
```

2. Generate the `.drawio`:

```bash
python scripts/draw.py model.json out.drawio
```

3. Export to PNG (or SVG) with the draw.io CLI:

```bash
DRAWIO="/c/Program Files/draw.io/draw.io.exe"   # macOS: /Applications/draw.io.app/Contents/MacOS/draw.io ; Linux: drawio
"$DRAWIO" -x -f png -e -b 12 -o out.png out.drawio
"$DRAWIO" -x -f svg -e -b 12 -o out.svg out.drawio
```

For a clustered example with nested clusters and views, see
`references/drawio-uml-reference.md` §13.

## Box-avoiding edge routing — status

**Fully working.** On the 4-cluster / 26-edge reference model (which has ~8 cross-cluster edges
plus a `→ GameMove` fan-in), the pinned `neato -n2` routing pass produces a route for every edge,
and a geometric check (every edge segment vs every non-endpoint box) reports **zero crossings**.
The routing pass requires `neato` (or `fdp`) from Graphviz on PATH; without it, clustered models
fall back to draw.io's auto-router for cross-cluster edges (see Prerequisites).

## Tested on

Graphviz 13.1.2 (dot + neato + fdp) · draw.io desktop · Python 3.13 · Windows 11.
