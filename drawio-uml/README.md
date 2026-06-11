# drawio-uml

Clean UML / node-link diagrams in **draw.io**, laid out automatically by **Graphviz `dot`** — no overlapping lines, no edges cutting through boxes. Works as a **Claude Code skill** (auto-triggers on diagram requests) or as a **standalone generator** you run by hand.

## What's in this folder

| File | Purpose |
|------|---------|
| `SKILL.md` | The Claude Code skill (frontmatter + workflow). |
| `scripts/drawio_uml.py` | Generator: a JSON model → `.drawio` (native shapes + dot orthogonal layout). |
| `references/drawio-uml-reference.md` | Concepts, install matrix, full shape/arrow catalog, per-type examples, troubleshooting. |
| `drawio-class-diagram-toolchain.md` | Long-form report: why it works, step by step. |

## What it draws

class, object, ER, state-machine, activity, use-case, component, package, deployment.
**Not** sequence / timing diagrams (those are time-ordered, not a graph-layout problem — use Mermaid or PlantUML).

## Install as a Claude Code skill

Copy the skill files into a skills directory so Claude auto-discovers them:

- all projects: `~/.claude/skills/drawio-uml/`
- one project: `<project>/.claude/skills/drawio-uml/`

Then just ask, e.g. *"draw a class diagram of `src/` in draw.io"* or *"make a state machine for the order lifecycle"*.

One-file install: package this folder into `drawio-uml.skill` (a zip) with the skill-creator's `package_skill.py`, then unzip it into `~/.claude/skills/`.

## Prerequisites

| Tool | Windows | macOS | Linux |
|------|---------|-------|-------|
| Graphviz `dot` (layout) | `winget install Graphviz.Graphviz` | `brew install graphviz` | `sudo apt-get install -y graphviz` |
| draw.io desktop (export) | `winget install JGraph.Draw` | `brew install --cask drawio` | releases page |
| Python 3.10+ (generator) | `winget install Python.Python.3.12` | `brew install python` | `sudo apt-get install -y python3` |

Verify with `dot -V` and `python --version`. Node.js is not needed.

## Run it by hand (no Claude)

1. Write a `model.json` (schema in `SKILL.md` / the reference).
2. `python scripts/drawio_uml.py model.json out.drawio`
3. Export: `"<drawio-cli>" -x -f png -e -b 12 -o out.png out.drawio`

Minimal example (state machine):

```json
{"nodes": [
  {"name": "start", "shape": "initial"},
  {"name": "Idle", "shape": "state"},
  {"name": "stop", "shape": "final"}],
 "edges": [
  {"source": "start", "target": "Idle", "arrow": "transition"},
  {"source": "Idle", "target": "stop", "arrow": "transition", "label": "end()"}]}
```

## Why it works

Layout quality (no overlapping lines) is an **algorithm** job, not a prompt-detail job. The division of labor:

- **Claude** produces the content (which boxes, what's in them, how they relate).
- **`dot`** computes the layout — node positions *and* orthogonal edge routes (`splines=ortho`), imported as draw.io waypoints so lines route around boxes.
- **draw.io** renders native shapes and exports.

Full rationale and the dot → draw.io coordinate transform are in the report.

## Tested on

Graphviz 13.1.2 · draw.io desktop 30.0.4 · Python 3.13 · Windows 11.
