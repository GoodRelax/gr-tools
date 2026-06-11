#!/usr/bin/env python3
"""drawio-uml: clean UML / node-link diagrams (.drawio) from a JSON model.

Native draw.io shapes laid out by Graphviz `dot`, which computes BOTH node
positions AND orthogonal edge routes (splines=ortho). The edge routes are
imported as draw.io waypoints so lines route around boxes instead of through them.

Supported (any node-link diagram dot can lay out):
  class, object, component, package, deployment, state-machine, activity,
  use-case, ER.  NOT supported: sequence / timing diagrams — those are
  time-ordered lifelines, not a graph-layout problem; use a different tool.

Requires Python 3.10+ and Graphviz `dot` on PATH.

Usage:
    python drawio_uml.py MODEL.json OUT.drawio

Model schema (see references/drawio-uml-reference.md for the full menu):
{
  "options": {"rankdir": "TB", "col_w": 260, "nodesep": 0.7, "ranksep": 1.1},
  "nodes": [
    {"name": "Animal", "shape": "class", "stereotype": "abstract",
     "fill": "#DAE8FC", "stroke": "#6C8EBF",
     "attrs": ["+ name: str"], "methods": ["+ speak(): str"]},
    {"name": "Idle", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
    {"name": "start", "shape": "initial"}
  ],
  "edges": [
    {"source": "Dog", "target": "Animal", "arrow": "gen"},
    {"source": "Idle", "target": "Running", "arrow": "transition", "label": "play()"}
  ]
}

Back-compat: "classes" is accepted as an alias for "nodes", and edge "kind" as an
alias for "arrow"; a node with attrs/methods and no shape defaults to a class box.
Any node may set a raw draw.io "style" string to override the shape preset.
"""
import json
import re
import subprocess
import sys
import xml.dom.minidom as minidom

# ---------------------------------------------------------------- edge arrows
ARROW = {
    "gen":        "endArrow=block;endFill=0;endSize=14;",                                   # generalization
    "real":       "endArrow=block;endFill=0;endSize=14;dashed=1;",                          # realization
    "comp":       "startArrow=diamondThin;startFill=1;startSize=14;endArrow=open;endFill=0;",  # composition
    "aggr":       "startArrow=diamondThin;startFill=0;startSize=14;endArrow=open;endFill=0;",  # aggregation
    "assoc":      "endArrow=open;",                                                          # association (directed)
    "dep":        "endArrow=open;dashed=1;",                                                 # dependency / include / extend
    "transition": "endArrow=block;endFill=1;endSize=10;",                                    # state / activity flow
    "line":       "endArrow=none;",                                                          # plain association (actor-usecase)
}
EDGE_BASE = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#3A3A3A;"
             "fontSize=11;fontColor=#222222;labelBackgroundColor=#FFFFFF;")

# ------------------------------------------------------- node shape presets
# shape -> (style_template, default_w, default_h). {fill}/{stroke} are substituted.
SHAPES = {
    "component": ("rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;spacingTop=4;fillColor={fill};strokeColor={stroke};", 180, 70),
    "package":   ("shape=folder;tabWidth=64;tabHeight=18;tabPosition=left;whiteSpace=wrap;html=1;verticalAlign=top;fillColor={fill};strokeColor={stroke};", 200, 100),
    "node":      ("rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};", 170, 60),
    "usecase":   ("ellipse;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};", 160, 70),
    "actor":     ("shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor={fill};strokeColor={stroke};", 40, 70),
    "state":     ("rounded=1;whiteSpace=wrap;html=1;arcSize=30;fillColor={fill};strokeColor={stroke};", 150, 56),
    "action":    ("rounded=1;whiteSpace=wrap;html=1;arcSize=45;fillColor={fill};strokeColor={stroke};", 150, 50),
    "decision":  ("rhombus;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};", 100, 70),
    "initial":   ("ellipse;fillColor=#333333;strokeColor=#333333;", 30, 30),
    "final":     ("ellipse;fillColor=none;strokeColor=#333333;strokeWidth=2;", 34, 34),
    "note":      ("shape=note;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};", 170, 70),
}
COMPARTMENT = {"class", "entity", "object"}     # rendered as swimlanes with member rows
NO_LABEL = {"initial", "final"}

DEFAULT_FILL, DEFAULT_STROKE = "#EEF0FF", "#5B5FC7"
TITLE_H, ROW_H, DIV_H = 40, 22, 10


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_compartment(node):
    if "style" in node:
        return False
    sh = node.get("shape")
    if sh in COMPARTMENT:
        return True
    return sh is None and bool(node.get("attrs") or node.get("methods"))


def comp_h(node):
    a, m = node.get("attrs", []), node.get("methods", [])
    h = TITLE_H + ROW_H * len(a) + ROW_H * len(m)
    return h + DIV_H if a and m else h


def node_size(node, opt):
    if is_compartment(node):
        return node.get("w", opt.get("col_w", 260)), comp_h(node)
    _, dw, dh = SHAPES.get(node.get("shape", "node"), SHAPES["node"])
    return node.get("w", dw), node.get("h", dh)


def title_raw(node):
    st, name = node.get("stereotype", ""), node.get("name", "")
    if node.get("shape") == "object":
        nm = "<u>%s</u>" % name
    elif node.get("italic") or st in ("interface", "abstract"):
        nm = "<i>%s</i>" % name
    else:
        nm = "<b>%s</b>" % name
    return ("«%s»<br>" % st if st else "") + nm


# ------------------------------------------------------------------- layout
def dot_layout(nodes, edges, nid, opt):
    """Graphviz dot -> (pos, routes) in draw.io px. px = inch*72, y flipped
    (dot origin bottom-left), then translated so the min corner is (40, 40).
    Nodes and edge points share the exact same transform so they line up."""
    g = ["digraph G {",
         "rankdir=%s; nodesep=%s; ranksep=%s; splines=ortho;"
         % (opt.get("rankdir", "TB"), opt.get("nodesep", 0.7), opt.get("ranksep", 1.1)),
         "node [shape=box, fixedsize=true];"]
    for n in nodes:
        w, h = node_size(n, opt)
        g.append('%s [width=%.3f, height=%.3f];' % (nid[n["name"]], w / 72.0, h / 72.0))
    for e in edges:
        s, t = nid[e["source"]], nid[e["target"]]
        # gen/real are fed reversed so the PARENT ranks above the child; the
        # polyline is direction-agnostic and reversed back when drawn.
        a, b = (t, s) if arrow_of(e) in ("gen", "real") else (s, t)
        g.append("%s -> %s;" % (a, b))
    g.append("}")
    out = subprocess.run(["dot", "-Tplain"], input="\n".join(g),
                         capture_output=True, text=True, check=True).stdout
    H = None
    pos, routes = {}, {}
    for ln in out.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "graph":
            H = float(p[3])
        elif p[0] == "node":
            cx, cy, w, h = (float(v) for v in p[2:6])
            pos[p[1]] = ((cx - w / 2) * 72, (H - cy - h / 2) * 72)
        elif p[0] == "edge":
            t, hd, k = p[1], p[2], int(p[3])
            c = p[4:4 + 2 * k]
            routes[(t, hd)] = [(float(c[2 * i]) * 72, (H - float(c[2 * i + 1])) * 72)
                               for i in range(k)]
    mnx = min(x for x, _ in pos.values())
    mny = min(y for _, y in pos.values())
    pos = {n: (x - mnx + 40, y - mny + 40) for n, (x, y) in pos.items()}
    routes = {e: [(x - mnx + 40, y - mny + 40) for x, y in pts] for e, pts in routes.items()}
    return pos, routes


def arrow_of(e):
    return e.get("arrow") or e.get("kind") or "assoc"


# ------------------------------------------------------------------- render
def render(model):
    nodes = model.get("nodes") or model.get("classes") or []
    edges = model.get("edges", [])
    opt = model.get("options", {})
    nid = {n["name"]: "n_" + re.sub(r"[^0-9A-Za-z_]", "_", n["name"]) for n in nodes}
    pos, routes = dot_layout(nodes, edges, nid, opt)
    rs = ("text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
          "spacingLeft=8;overflow=hidden;rotatable=0;html=1;fontSize=12;fontColor=#1A1A1A;")
    cells = []
    for node in nodes:
        n = node["name"]
        ni = nid[n]
        w, h = node_size(node, opt)
        x, y = pos[ni]
        fill = node.get("fill", DEFAULT_FILL)
        stroke = node.get("stroke", DEFAULT_STROKE)
        if is_compartment(node):
            attrs, meths = node.get("attrs", []), node.get("methods", [])
            cells.append(
                '<mxCell id="%s" value="%s" style="swimlane;html=1;align=center;'
                'verticalAlign=top;childLayout=stackLayout;startSize=%d;horizontal=1;'
                'horizontalStack=0;resizeParent=1;resizeParentMax=0;collapsible=0;'
                'swimlaneFillColor=#FFFFFF;fillColor=%s;strokeColor=%s;fontColor=#111111;'
                'fontSize=13;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="%d" '
                'height="%d" as="geometry"/></mxCell>'
                % (ni, esc(title_raw(node)), TITLE_H, fill, stroke, round(x), round(y), w, h))
            off = TITLE_H
            for i, a in enumerate(attrs):
                cells.append('<mxCell id="%s__a%d" value="%s" style="%s" vertex="1" parent="%s">'
                             '<mxGeometry y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                             % (ni, i, esc(a), rs, ni, off, w, ROW_H))
                off += ROW_H
            if attrs and meths:
                cells.append('<mxCell id="%s__div" value="" style="line;strokeColor=%s;html=1;" '
                             'vertex="1" parent="%s"><mxGeometry y="%d" width="%d" height="%d" '
                             'as="geometry"/></mxCell>' % (ni, stroke, ni, off, w, DIV_H))
                off += DIV_H
            for j, mm in enumerate(meths):
                cells.append('<mxCell id="%s__m%d" value="%s" style="%s" vertex="1" parent="%s">'
                             '<mxGeometry y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                             % (ni, j, esc(mm), rs, ni, off, w, ROW_H))
                off += ROW_H
        else:
            sh = node.get("shape", "node")
            if "style" in node:
                style = node["style"]
            else:
                style = SHAPES.get(sh, SHAPES["node"])[0].format(fill=fill, stroke=stroke)
            val = "" if sh in NO_LABEL else esc(title_raw(node))
            cells.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">'
                         '<mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                         % (ni, val, style, round(x), round(y), w, h))
            if sh == "final":   # inner filled dot makes the bullseye
                iw, ih = round(w * 0.46), round(h * 0.46)
                ix, iy = round(x + (w - iw) / 2), round(y + (h - ih) / 2)
                cells.append('<mxCell id="%s__dot" value="" style="ellipse;fillColor=#333333;'
                             'strokeColor=#333333;" vertex="1" parent="1"><mxGeometry x="%d" '
                             'y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                             % (ni, ix, iy, iw, ih))
    for i, e in enumerate(edges):
        a = arrow_of(e)
        si, ti = nid[e["source"]], nid[e["target"]]
        key, rev = ((ti, si), True) if a in ("gen", "real") else ((si, ti), False)
        pts = routes.get(key, [])
        if rev:
            pts = pts[::-1]
        inner = "".join('<mxPoint x="%d" y="%d"/>' % (round(px), round(py)) for px, py in pts[1:-1])
        geo = ('<mxGeometry relative="1" as="geometry"><Array as="points">%s</Array>'
               '</mxGeometry>' % inner) if inner else '<mxGeometry relative="1" as="geometry"/>'
        cells.append('<mxCell id="edge%d" value="%s" style="%s" edge="1" parent="1" '
                     'source="%s" target="%s">%s</mxCell>'
                     % (i, esc(e.get("label", "")), EDGE_BASE + ARROW.get(a, ARROW["assoc"]),
                        si, ti, geo))
    xml = ('<mxGraphModel adaptiveColors="auto"><root><mxCell id="0"/>'
           '<mxCell id="1" parent="0"/>%s</root></mxGraphModel>' % "".join(cells))
    minidom.parseString(xml)   # fail fast on malformed XML
    return xml


def main():
    if len(sys.argv) != 3:
        print("usage: python drawio_uml.py MODEL.json OUT.drawio", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as fh:
        model = json.load(fh)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write(render(model))
    nodes = model.get("nodes") or model.get("classes") or []
    print("wrote %s (%d nodes, %d edges)" % (sys.argv[2], len(nodes), len(model.get("edges", []))))


if __name__ == "__main__":
    main()
