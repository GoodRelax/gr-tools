# drawio-uml (improved)

Clean UML / node-link diagrams in **draw.io**, laid out automatically by **Graphviz** — no
overlapping lines, no edges cutting through boxes. Works as a **Claude Code skill**
(auto-triggers on diagram requests) or as a **standalone generator** you run by hand.

This is the **improved** drawio-uml: a strict superset of the stock skill. A model that uses
none of the new keys renders **byte-identically** to stock; the new features are all opt-in.

## What it is, and what it improves over the stock skill

You write a small `model.json` (boxes + arrows). The generator emits a native `.drawio` file,
asking Graphviz to compute **both** node positions **and** orthogonal edge routes, which it
imports as draw.io waypoints — so lines route *around* boxes, not through them. draw.io renders
the real UML shapes and exports to PNG/SVG.

It draws: class, object, ER, state-machine, activity, use-case, component, package, deployment.
**Not** sequence / timing diagrams (those are time-ordered, not a graph-layout problem — use
Mermaid or PlantUML).

Improvements over the stock skill (all **opt-in**, all **additive**):

| Feature | What you get |
|---------|--------------|
| **Cluster grouping** | Give nodes a `"cluster"` key → each group gets a labelled, coloured dashed box. |
| **Legend** | When clusters exist, a legend row of cluster swatches + UML arrow glyphs (◆ ◇ → ⇢) is drawn under the diagram. |
| **Banded / compass layout** | `options.layout.rows` arranges whole clusters into horizontal bands — e.g. `input \| consider \| output` across the top, a full-width `vocabulary` band below. Each cluster is laid out in its own Graphviz run, then composed onto the grid. |
| **Edges that never cross boxes** | A final **position-pinned Graphviz pass** (`neato -n2`, `splines=ortho`) routes *every* edge — including cross-cluster ones — around the placed boxes. Verified: 0 edge-through-box crossings on the 26-edge / 4-cluster reference model. |

A model with no `cluster` / `options.clusters` / `options.layout` keys takes the stock flat path
and is byte-for-byte identical to the original skill's output. The schema and full mechanism are
documented in `SKILL.md` and `references/drawio-uml-reference.md` (§9–§13).

## What's in this folder

| File | Purpose |
|------|---------|
| `SKILL.md` | The Claude Code skill manifest (frontmatter + workflow + new schema keys). |
| `scripts/drawio_uml.py` | Generator: JSON model → `.drawio` (native shapes + dot layout + pinned routing). |
| `references/drawio-uml-reference.md` | Concepts, install matrix, full shape/arrow catalog, per-type examples, clusters/legend/banded/edge-routing sections, troubleshooting. |
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
this folder there. This **overrides / upgrades the stock `drawio-uml` skill** — Claude loads the
skill from `~/.claude/skills/`, so whatever is there wins.

### Option A — copy (Windows, PowerShell)

```powershell
$src = "$env:USERPROFILE\OneDrive\Documents\GitHub\gr-tools\drawio-uml"
$dst = "$env:USERPROFILE\.claude\skills\drawio-uml"
Remove-Item -Recurse -Force $dst -ErrorAction SilentlyContinue   # drop the stock skill
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
*"make a clustered domain model with an input/consider/output banded layout"*, or
*"clean up this messy Mermaid diagram"*.

## Quick usage (by hand, no Claude)

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
python scripts/drawio_uml.py model.json out.drawio
```

3. Export to PNG (or SVG) with the draw.io CLI:

```bash
DRAWIO="/c/Program Files/draw.io/draw.io.exe"   # macOS: /Applications/draw.io.app/Contents/MacOS/draw.io ; Linux: drawio
"$DRAWIO" -x -f png -e -b 12 -o out.png out.drawio
"$DRAWIO" -x -f svg -e -b 12 -o out.svg out.drawio
```

For a clustered + banded example (the kind this build was made for), see
`references/drawio-uml-reference.md` §13.

## Box-avoiding edge routing — status

**Fully working.** On the 4-cluster / 26-edge reference model (which has ~8 cross-cluster edges
plus a `→ GameMove` fan-in), the pinned `neato -n2` routing pass produces a route for every edge,
and a geometric check (every edge segment vs every non-endpoint box) reports **zero crossings**.
The routing pass requires `neato` (or `fdp`) from Graphviz on PATH; without it, clustered models
fall back to draw.io's auto-router for cross-cluster edges (see Prerequisites).

## Tested on

Graphviz 13.1.2 (dot + neato + fdp) · draw.io desktop · Python 3.13 · Windows 11.
