#!/usr/bin/env python3
"""drawio-uml: clean UML / node-link diagrams (.drawio) from a JSON model.

Native draw.io shapes laid out by Graphviz `dot`, which computes BOTH node
positions AND orthogonal edge routes (splines=ortho). The edge routes are
imported as draw.io waypoints so lines route around boxes instead of through them.

Supported (any node-link diagram dot can lay out):
  class, object, component, package, deployment, state-machine, activity,
  use-case, ER.  NOT supported: sequence / timing diagrams — those are
  time-ordered lifelines, not a graph-layout problem; use a different tool.

This is the IMPROVED generator: it is a strict superset of the stock global
drawio-uml skill. A model that sets NONE of the cluster/banded keys renders
BYTE-IDENTICALLY to the stock skill (the flat code path below is kept verbatim).
On top of that it adds, opt-in:
  * cluster grouping        -- per-node "cluster" key -> a labelled, coloured box
  * a legend                -- cluster swatches + UML arrow-kind glyphs
  * banded / compass layout -- options.layout.rows = [[clusterKey, ...], ...]
  * box-avoiding routing    -- a FINAL position-pinned Graphviz pass (neato -n2 /
    fdp -n2) routes EVERY edge -- including cross-cluster edges -- around the
    placed boxes, so no edge cuts through a class box.

Requires Python 3.10+ and Graphviz `dot` on PATH (plus `neato`/`fdp` for the
pinned routing pass used by the cluster paths).

Usage:
    python draw.py MODEL.json OUT.drawio

Model schema (see references/drawio-uml-reference.md for the full menu):
{
  "options": {"rankdir": "TB", "column_width": 260, "node_separation": 0.7, "rank_separation": 1.1},
  "nodes": [
    {"name": "Animal", "shape": "class", "stereotype": "abstract",
     "fill": "#DAE8FC", "stroke": "#6C8EBF",
     "attributes": ["+ name: str"], "methods": ["+ speak(): str"]},
    {"name": "Idle", "shape": "state", "fill": "#D5E8D4", "stroke": "#82B366"},
    {"name": "start", "shape": "initial"}
  ],
  "edges": [
    {"source": "Dog", "target": "Animal", "arrow": "generalization"},
    {"source": "Idle", "target": "Running", "arrow": "transition", "label": "play()"}
  ]
}

Opt-in clustering / banding (additive - omit for the stock behaviour):
  options.clusters = { "<key>": {"label": str, "stroke": "#RRGGBB", "fill": "#RRGGBB"} }
  options.layout   = { "rows": [["input","consider","output"], ["vocabulary"]] }
  each node may carry  "cluster": "<key>"

A node with attributes/methods and no shape defaults to a class box.
Any node may set a raw draw.io "style" string to override the shape preset.
"""
import json
import re
import subprocess
import sys
import xml.dom.minidom as minidom
from collections import OrderedDict

# ---------------------------------------------------------------- edge arrows
ARROW = {
    "generalization":       "endArrow=block;endFill=0;endSize=14;",                                   # generalization
    "realization":          "endArrow=block;endFill=0;endSize=14;dashed=1;",                          # realization
    "composition":          "startArrow=diamondThin;startFill=1;startSize=14;endArrow=open;endFill=0;",  # composition
    "aggregation":          "startArrow=diamondThin;startFill=0;startSize=14;endArrow=open;endFill=0;",  # aggregation
    "directed_association": "endArrow=open;",                                                          # association with navigability arrow
    "dependency":           "endArrow=open;dashed=1;",                                                 # dependency / include / extend
    "transition":           "endArrow=block;endFill=1;endSize=10;",                                    # state / activity flow
    "association":          "endArrow=none;",                                                          # plain association (no arrowhead)
}
EDGE_BASE = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#3A3A3A;"
             "fontSize=11;fontColor=#222222;labelBackgroundColor=#FFFFFF;")

# ------------------------------------------------------- node shape presets
# shape -> (style_template, default_w, default_h). {fill}/{stroke} are substituted.
SHAPES = {
    "component": ("rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;spacingTop=4;fillColor={fill};strokeColor={stroke};", 180, 70),
    "package":   ("shape=folder;tabWidth=64;tabHeight=18;tabPosition=left;whiteSpace=wrap;html=1;verticalAlign=top;fillColor={fill};strokeColor={stroke};", 200, 100),
    "box":       ("rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};", 170, 60),
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

# -- clustered-layout constants (only used on the opt-in cluster/banded path) --
MARGIN = 70            # canvas margin (room for top-left cluster labels)
PAD, TOP_PAD = 24, 34  # cluster box padding (sides / top for its label)
BAND_GAP = 150         # vertical gap between stacked layout bands (options.layout)
CLUSTER_GAP = 90       # horizontal gap between clusters within one band


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_compartment(node):
    if "style" in node:
        return False
    sh = node.get("shape")
    if sh in COMPARTMENT:
        return True
    return sh is None and bool(node.get("attributes") or node.get("methods"))


def comp_h(node):
    a, m = node.get("attributes", []), node.get("methods", [])
    h = TITLE_H + ROW_H * len(a) + ROW_H * len(m)
    return h + DIV_H if a and m else h


def node_size(node, opt):
    if is_compartment(node):
        return node.get("width", opt.get("column_width", 260)), comp_h(node)
    _, dw, dh = SHAPES.get(node.get("shape", "box"), SHAPES["box"])
    return node.get("width", dw), node.get("height", dh)


def title_raw(node):
    st, name = node.get("stereotype", ""), node.get("name", "")
    if node.get("shape") == "object":
        nm = "<u>%s</u>" % name
    elif node.get("italic") or st in ("interface", "abstract"):
        nm = "<i>%s</i>" % name
    else:
        nm = "<b>%s</b>" % name
    return ("«%s»<br>" % st if st else "") + nm


def arrow_of(e):
    return e.get("arrow") or "association"


def _node_cells(node, nid, pos, opt, rs):
    """Render ONE node into a list of mxCells (shared by both paths).

    Class/entity/object -> a swimlane compartment box (name / attrs / methods);
    any other shape -> its preset (or a raw "style"); `final` gets its inner dot.
    Returns a list of XML cell strings."""
    n = node["name"]
    ni = nid[n]
    w, h = node_size(node, opt)
    x, y = pos[ni]
    fill = node.get("fill", DEFAULT_FILL)
    stroke = node.get("stroke", DEFAULT_STROKE)
    out = []
    if is_compartment(node):
        attrs, meths = node.get("attributes", []), node.get("methods", [])
        out.append(
            '<mxCell id="%s" value="%s" style="swimlane;html=1;align=center;'
            'verticalAlign=top;childLayout=stackLayout;startSize=%d;horizontal=1;'
            'horizontalStack=0;resizeParent=1;resizeParentMax=0;collapsible=0;'
            'swimlaneFillColor=#FFFFFF;fillColor=%s;strokeColor=%s;fontColor=#111111;'
            'fontSize=13;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="%d" '
            'height="%d" as="geometry"/></mxCell>'
            % (ni, esc(title_raw(node)), TITLE_H, fill, stroke, round(x), round(y), w, h))
        off = TITLE_H
        for i, a in enumerate(attrs):
            out.append('<mxCell id="%s__a%d" value="%s" style="%s" vertex="1" parent="%s">'
                       '<mxGeometry y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                       % (ni, i, esc(a), rs, ni, off, w, ROW_H))
            off += ROW_H
        if attrs and meths:
            out.append('<mxCell id="%s__div" value="" style="line;strokeColor=%s;html=1;" '
                       'vertex="1" parent="%s"><mxGeometry y="%d" width="%d" height="%d" '
                       'as="geometry"/></mxCell>' % (ni, stroke, ni, off, w, DIV_H))
            off += DIV_H
        for j, mm in enumerate(meths):
            out.append('<mxCell id="%s__m%d" value="%s" style="%s" vertex="1" parent="%s">'
                       '<mxGeometry y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                       % (ni, j, esc(mm), rs, ni, off, w, ROW_H))
            off += ROW_H
    else:
        sh = node.get("shape", "box")
        if "style" in node:
            style = node["style"]
        else:
            style = SHAPES.get(sh, SHAPES["box"])[0].format(fill=fill, stroke=stroke)
        val = "" if sh in NO_LABEL else esc(title_raw(node))
        out.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">'
                   '<mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                   % (ni, val, style, round(x), round(y), w, h))
        if sh == "final":   # inner filled dot makes the bullseye
            iw, ih = round(w * 0.46), round(h * 0.46)
            ix, iy = round(x + (w - iw) / 2), round(y + (h - ih) / 2)
            out.append('<mxCell id="%s__dot" value="" style="ellipse;fillColor=#333333;'
                       'strokeColor=#333333;" vertex="1" parent="1"><mxGeometry x="%d" '
                       'y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                       % (ni, ix, iy, iw, ih))
    return out


def _edge_cell(i, e, nid, routes):
    """Render ONE edge into an mxCell with imported waypoints (shared)."""
    a = arrow_of(e)
    si, ti = nid[e["source"]], nid[e["target"]]
    key, rev = ((ti, si), True) if a in ("generalization", "realization") else ((si, ti), False)
    pts = routes.get(key, [])
    if rev:
        pts = pts[::-1]
    inner = "".join('<mxPoint x="%d" y="%d"/>' % (round(px), round(py)) for px, py in pts[1:-1])
    geo = ('<mxGeometry relative="1" as="geometry"><Array as="points">%s</Array>'
           '</mxGeometry>' % inner) if inner else '<mxGeometry relative="1" as="geometry"/>'
    return ('<mxCell id="edge%d" value="%s" style="%s" edge="1" parent="1" '
            'source="%s" target="%s">%s</mxCell>'
            % (i, esc(e.get("label", "")), EDGE_BASE + ARROW.get(a, ARROW["association"]),
               si, ti, geo))


# ======================================================================
#  FLAT PATH  (stock global skill, kept VERBATIM for byte-identity)
#  Used whenever the model carries no cluster / clusters / layout keys.
# ======================================================================
def dot_layout(nodes, edges, nid, opt):
    """Graphviz dot -> (pos, routes) in draw.io px. px = inch*72, y flipped
    (dot origin bottom-left), then translated so the min corner is (40, 40).
    Nodes and edge points share the exact same transform so they line up."""
    g = ["digraph G {",
         "rankdir=%s; nodesep=%s; ranksep=%s; splines=ortho;"
         % (opt.get("rankdir", "TB"), opt.get("node_separation", 0.7), opt.get("rank_separation", 1.1)),
         "node [shape=box, fixedsize=true];"]
    for n in nodes:
        w, h = node_size(n, opt)
        g.append('%s [width=%.3f, height=%.3f];' % (nid[n["name"]], w / 72.0, h / 72.0))
    for e in edges:
        s, t = nid[e["source"]], nid[e["target"]]
        # gen/real are fed reversed so the PARENT ranks above the child; the
        # polyline is direction-agnostic and reversed back when drawn.
        a, b = (t, s) if arrow_of(e) in ("generalization", "realization") else (s, t)
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


def render_flat(model):
    """The stock global-skill renderer. Produces output byte-identical to the
    original drawio-uml skill for any model with no cluster/banded keys."""
    nodes = model.get("nodes") or []
    edges = model.get("edges", [])
    opt = model.get("options", {})
    nid = {n["name"]: "n_" + re.sub(r"[^0-9A-Za-z_]", "_", n["name"]) for n in nodes}
    pos, routes = dot_layout(nodes, edges, nid, opt)
    rs = ("text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
          "spacingLeft=8;overflow=hidden;rotatable=0;html=1;fontSize=12;fontColor=#1A1A1A;")
    cells = []
    for node in nodes:
        cells += _node_cells(node, nid, pos, opt, rs)
    for i, e in enumerate(edges):
        cells.append(_edge_cell(i, e, nid, routes))
    xml = ('<mxGraphModel adaptiveColors="auto"><root><mxCell id="0"/>'
           '<mxCell id="1" parent="0"/>%s</root></mxGraphModel>' % "".join(cells))
    minidom.parseString(xml)   # fail fast on malformed XML
    return xml


# ======================================================================
#  CLUSTERED PATH  (opt-in: clusters / legend / banded layout / routing)
# ======================================================================
def cid(key):
    return "cluster_" + re.sub(r"[^0-9A-Za-z_]", "_", key)


def _parse_plain(out, off_x, off_y, skip_pairs, re_origin):
    """Parse `dot -Tplain` / `neato -n2 -Tplain` output -> (pos, size, routes).

    Coordinates are converted to draw.io px (px = pt, y flipped by graph height
    H). When re_origin is True the result is shifted so its min node corner sits
    at (off_x, off_y) (used by per-cluster runs that get composed onto a grid).
    When re_origin is False the transformed coords keep dot's own origin and just
    add (off_x, off_y) (used by the pinned routing pass, whose pins are already
    absolute). Edges whose (tail, head) is in skip_pairs are dropped.
    """
    H = None
    raw_pos, raw_size, raw_routes = {}, {}, {}
    for ln in out.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "graph":
            H = float(p[3])
        elif p[0] == "node":
            cx, cy, w, h = (float(v) for v in p[2:6])
            raw_pos[p[1]] = ((cx - w / 2) * 72, (H - cy - h / 2) * 72)
            raw_size[p[1]] = (w * 72, h * 72)
        elif p[0] == "edge":
            t, hd, k = p[1], p[2], int(p[3])
            if (t, hd) in skip_pairs:
                continue
            c = p[4:4 + 2 * k]
            raw_routes[(t, hd)] = [(float(c[2 * i]) * 72, (H - float(c[2 * i + 1])) * 72)
                                   for i in range(k)]
    if re_origin:
        mnx = min(x for x, _ in raw_pos.values())
        mny = min(y for _, y in raw_pos.values())
    else:
        mnx = mny = 0.0
    pos = {n: (x - mnx + off_x, y - mny + off_y) for n, (x, y) in raw_pos.items()}
    routes = {e: [(x - mnx + off_x, y - mny + off_y) for x, y in pts]
              for e, pts in raw_routes.items()}
    return pos, raw_size, routes


def _run_dot(g_lines, off_x=0.0, off_y=0.0, skip_pairs=frozenset()):
    """Run `dot -Tplain` on the given source lines; return (pos, routes, (w,h)).

    pos/routes are in draw.io px (y flipped) with the sub-graph's min corner moved
    to (off_x, off_y) so a caller can place it anywhere. (w,h) is the drawn extent.
    """
    out = subprocess.run(["dot", "-Tplain"], input="\n".join(g_lines),
                         capture_output=True, text=True, check=True,
                         encoding="utf-8").stdout
    pos, raw_size, routes = _parse_plain(out, off_x, off_y, frozenset(skip_pairs),
                                         re_origin=True)
    bw = max(pos[n][0] - off_x + raw_size[n][0] for n in pos)
    bh = max(pos[n][1] - off_y + raw_size[n][1] for n in pos)
    return pos, routes, (bw, bh)


def _emit_cluster(g, ckey, members, nid, opt, specs):
    """Append one `subgraph cluster_*` block (members + their sizes)."""
    g.append('subgraph %s {' % cid(ckey))
    g.append('label="%s"; labeljust=l; fontsize=14; margin=18; '
             'style=rounded; color="%s";'
             % (specs.get(ckey, {}).get("label", ckey),
                specs.get(ckey, {}).get("stroke", "#888888")))
    for n in members:
        w, h = node_size(n, opt)
        g.append('%s [width=%.3f, height=%.3f];' % (nid[n["name"]], w / 72.0, h / 72.0))
    g.append('}')


def _layout_one_cluster(ckey, members, edges, nid, opt, specs, rankdir):
    """Lay out a SINGLE cluster in its own dot run; return (pos, routes, (w,h)).

    `rankdir` controls the cluster's internal shape: TB for a tall column that
    reads top-down (UML class hierarchy), LR for a wide horizontal strip (used for
    a full-width band cluster). Only edges internal to this cluster are included so
    dot routes them; cross-cluster edges are routed later by the pinned pass.
    """
    nodesep, ranksep = opt.get("node_separation", 0.8), opt.get("rank_separation", 1.25)
    g = ["digraph G {",
         "rankdir=%s; nodesep=%s; ranksep=%s; splines=ortho; compound=true;"
         % (rankdir, nodesep, ranksep),
         "node [shape=box, fixedsize=true];"]
    _emit_cluster(g, ckey, members, nid, opt, specs)
    names = {n["name"] for n in members}
    for e in edges:
        if e["source"] in names and e["target"] in names:
            s, t = nid[e["source"]], nid[e["target"]]
            a, b = (t, s) if arrow_of(e) in ("generalization", "realization") else (s, t)
            g.append("%s -> %s;" % (a, b))
    g.append("}")
    return _run_dot(g)


def _dot_layout_banded(nodes, edges, nid, opt, rows):
    """Compass/grid layout honoring options.layout.rows (opt-in).

    Plain dot is a 1-D layered engine: a single run cannot force
    input-left / consider-center / output-right AND a full-width vocabulary band
    below -- the heavily-connected `consider` cluster always migrates toward its
    edge mass, and a single run interleaves clusters of unequal height (verified
    empirically across rankdir / rank=same / ordering / constraint=false tricks).
    So each CLUSTER is laid out in its own dot run and the results are composed
    onto a grid described by options.layout.rows:

      * Per cluster: an isolated dot run lays out its members and ROUTES its
        internal edges orthogonally (so lines never cut its own boxes).
      * Grid placement: row 0 is the TOP band; within a row clusters are placed
        left -> right in listed order, CLUSTER_GAP apart, aligned at the band top.
        Rows stack top -> bottom, BAND_GAP apart, each row centred on the widest
        row.  => input | consider | output over a full-width vocabulary band.

    Returns (pos, routes). The per-cluster internal routes are produced here but
    then REPLACED wholesale by the final pinned routing pass (_route_pinned),
    which routes ALL edges (internal + cross-cluster) around the placed boxes.
    """
    by_cluster = OrderedDict()
    for n in nodes:
        by_cluster.setdefault(n.get("cluster"), []).append(n)
    specs = opt.get("clusters", {})

    # 1. lay out every cluster independently. A cluster that is the SOLE member of
    #    its row spans the full width, so lay it LR (wide strip); clusters that sit
    #    beside others in a row are laid TB (tall column reading top-down).
    solo = {row[0] for row in rows if len(row) == 1}
    laid = {}   # ckey -> (pos, routes, (w,h))
    for ckey, members in by_cluster.items():
        if ckey is not None and members:
            rankdir = "LR" if ckey in solo else "TB"
            laid[ckey] = _layout_one_cluster(ckey, members, edges, nid, opt, specs,
                                             rankdir)

    # 2. measure each row's extent (clusters side by side, CLUSTER_GAP apart)
    row_w, row_h = [], []
    for row in rows:
        cks = [c for c in row if c in laid]
        w = sum(laid[c][2][0] for c in cks) + CLUSTER_GAP * max(0, len(cks) - 1)
        h = max((laid[c][2][1] for c in cks), default=0.0)
        row_w.append(w)
        row_h.append(h)
    total_w = max(row_w, default=0.0)

    # 3. place clusters: rows stacked top->bottom, each row centred & laid L->R
    pos, y_cursor = {}, 0.0
    for ri, row in enumerate(rows):
        cks = [c for c in row if c in laid]
        x_cursor = MARGIN + (total_w - row_w[ri]) / 2.0
        for ckey in cks:
            cpos, croutes, (cw, ch) = laid[ckey]
            dx, dy = x_cursor, MARGIN + y_cursor     # align clusters at band top
            for n, (x, y) in cpos.items():
                pos[n] = (x + dx, y + dy)
            x_cursor += cw + CLUSTER_GAP
        y_cursor += row_h[ri] + BAND_GAP

    # 4. route EVERY edge around the placed boxes (cross-cluster ones included)
    routes = _route_pinned(nodes, edges, nid, opt, pos)
    return pos, routes


def dot_layout_clustered(nodes, edges, nid, opt):
    """dot -Tplain -> (pos, routes) in draw.io px, grouping members by cluster.

    With options.layout.rows present -> banded compass layout. Otherwise a single
    dot run with `subgraph cluster_*` blocks (dot keeps each cluster contiguous),
    then a pinned routing pass so cross-cluster edges also avoid boxes."""
    if opt.get("layout", {}).get("rows"):
        return _dot_layout_banded(nodes, edges, nid, opt, opt["layout"]["rows"])
    by_cluster = OrderedDict()
    for n in nodes:
        by_cluster.setdefault(n.get("cluster"), []).append(n)
    specs = opt.get("clusters", {})
    g = ["digraph G {",
         "rankdir=%s; nodesep=%s; ranksep=%s; splines=ortho; compound=true;"
         % (opt.get("rankdir", "TB"), opt.get("node_separation", 0.8), opt.get("rank_separation", 1.25)),
         "node [shape=box, fixedsize=true];"]

    def emit_node(n):
        w, h = node_size(n, opt)
        g.append('%s [width=%.3f, height=%.3f];' % (nid[n["name"]], w / 72.0, h / 72.0))

    for ckey, members in by_cluster.items():
        if ckey is None:
            for n in members:
                emit_node(n)
        else:
            g.append('subgraph %s {' % cid(ckey))
            g.append('label="%s"; labeljust=l; fontsize=14; margin=18; '
                     'style=rounded; color="%s";'
                     % (specs.get(ckey, {}).get("label", ckey),
                        specs.get(ckey, {}).get("stroke", "#888888")))
            for n in members:
                emit_node(n)
            g.append('}')
    for e in edges:
        s, t = nid[e["source"]], nid[e["target"]]
        a, b = (t, s) if arrow_of(e) in ("generalization", "realization") else (s, t)
        g.append("%s -> %s;" % (a, b))
    g.append("}")
    pos, _, _ = _run_dot(g, off_x=MARGIN, off_y=MARGIN)
    routes = _route_pinned(nodes, edges, nid, opt, pos)
    return pos, routes


def _parse_plain_raw(out):
    """Parse `-Tplain` into RAW Graphviz points (x right, y up, origin bottom-left)
    WITHOUT any draw.io flip/translate. Returns (centres, polylines) where centres
    maps node-id -> (cx_pt, cy_pt) and polylines maps (tail,head) -> [(x_pt,y_pt)].

    The pinned routing pass uses this so it can solve the unit round-trip
    EMPIRICALLY: the echoed pinned node centres are known in our own draw.io px
    too, so one affine (scale + offset, y-flip) maps every routed point back into
    draw.io space exactly -- no reliance on guessed graph height or input scale."""
    centres, polylines = {}, {}
    for ln in out.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "node":
            cx, cy = float(p[2]) * 72.0, float(p[3]) * 72.0
            centres[p[1]] = (cx, cy)
        elif p[0] == "edge":
            t, hd, k = p[1], p[2], int(p[3])
            c = p[4:4 + 2 * k]
            polylines[(t, hd)] = [(float(c[2 * i]) * 72.0, float(c[2 * i + 1]) * 72.0)
                                  for i in range(k)]
    return centres, polylines


def _route_pinned(nodes, edges, nid, opt, pos):
    """FINAL box-avoiding routing pass over the WHOLE graph (capability 4).

    Every node position is already fixed in draw.io px (`pos`). We hand Graphviz
    those exact positions PINNED (`pos="x,y!"`, fixedsize) and ask it to route the
    edges only (`-n2`), with `splines=ortho`, so it routes EVERY edge -- internal
    AND cross-cluster -- around the placed boxes. The routed polylines are mapped
    back into draw.io px and returned as the route table for all edges.

    Unit round-trip (the trap the handoff warns about): Graphviz `neato -n`/`-n2`
    reads `pos` in POINTS (origin bottom-left, y up); `-Tplain` re-emits in inches.
    Rather than juggle the engine's graph height / input scale by hand, we PIN the
    nodes and then read back their ECHOED centres: since we also know each node's
    centre in draw.io px (from `pos`), we recover the exact affine transform
    (x' = x_pt + ox ;  y' = -y_pt + oy) from those known correspondences and apply
    it to every routed waypoint. This is immune to scale/height guesswork.

    Engine: `neato -n2 -Tplain` (honours pins, routes edges). Falls back to
    `fdp -n2` then a pinned `neato -n` run. Returns the directed route table the
    renderer expects, or {} (draw.io auto-route) if no engine succeeded.
    """
    if not pos:
        return {}
    size = {nid[n["name"]]: node_size(n, opt) for n in nodes}
    # pin y in Graphviz space (y up). px == pt, so just negate draw.io y (y down);
    # the absolute offset is irrelevant -- we recover it from the echo afterward.
    pin = {}   # node-id -> (cx_pt, cy_pt) we asked for, in Graphviz coords
    for n in nodes:
        i = nid[n["name"]]
        w, h = size[i]
        cx = pos[i][0] + w / 2.0
        cy = -(pos[i][1] + h / 2.0)
        pin[i] = (cx, cy)

    lines = ["graph G {",
             "  splines=ortho;",
             "  node [shape=box, fixedsize=true];"]
    for n in nodes:
        i = nid[n["name"]]
        w, h = size[i]
        cx, cy = pin[i]
        lines.append('  %s [width=%.4f, height=%.4f, pos="%.3f,%.3f!"];'
                     % (i, w / 72.0, h / 72.0, cx, cy))
    # undirected edges (we only need routes; arrowheads are applied by draw.io).
    # dedupe so a pair is routed once; the lookup table is keyed both directions.
    seen = set()
    for e in edges:
        if e["source"] == e["target"]:
            continue                        # splines=ortho hates self-loops
        s, t = nid[e["source"]], nid[e["target"]]
        if (s, t) in seen or (t, s) in seen:
            continue
        seen.add((s, t))
        lines.append("  %s -- %s;" % (s, t))
    lines.append("}")
    src = "\n".join(lines)

    out = None
    for engine in (["neato", "-n2", "-Tplain"],
                   ["fdp", "-n2", "-Tplain"],
                   ["neato", "-n", "-Tplain"]):
        try:
            r = subprocess.run(engine, input=src, capture_output=True, text=True,
                               encoding="utf-8")
        except FileNotFoundError:
            continue
        if r.returncode == 0 and r.stdout.strip():
            out = r.stdout
            break
    if out is None:
        return {}

    centres, polylines = _parse_plain_raw(out)
    # recover the affine (x' = x_pt + ox ; y' = -y_pt + oy) from echoed centres.
    # average over all nodes for numerical robustness (they should all agree).
    oxs, oys = [], []
    for i, (px, py) in pos.items():
        if i not in centres:
            continue
        w, h = size[i]
        want_cx = px + w / 2.0
        want_cy = py + h / 2.0          # draw.io centre (y down)
        cx_pt, cy_pt = centres[i]
        oxs.append(want_cx - cx_pt)     # x' = x_pt + ox
        oys.append(want_cy + cy_pt)     # y' = -y_pt + oy  (note +cy_pt: flip)
    if not oxs:
        return {}
    ox = sum(oxs) / len(oxs)
    oy = sum(oys) / len(oys)

    def to_px(pt):
        return (pt[0] + ox, -pt[1] + oy)

    table = {}
    for (a, b), pts in polylines.items():
        conv = [to_px(p) for p in pts]
        table[(a, b)] = conv
        table[(b, a)] = conv[::-1]

    routes = {}
    for e in edges:
        if e["source"] == e["target"]:
            continue
        si, ti = nid[e["source"]], nid[e["target"]]
        key = (ti, si) if arrow_of(e) in ("generalization", "realization") else (si, ti)
        if key in table:
            routes[key] = table[key]
    return routes


def cluster_box_cells(nodes, nid, pos, opt):
    """Dashed, labelled box around each cluster's member bounding box.

    -Tplain does not emit cluster bboxes, so compute each from member positions
    (+ side PAD, top TOP_PAD for the label). Emitted BEFORE node cells so draw.io
    z-order (= document order) puts them behind the boxes."""
    specs = opt.get("clusters", {})
    by_cluster = OrderedDict()
    for n in nodes:
        if n.get("cluster") is not None:
            by_cluster.setdefault(n["cluster"], []).append(n)
    cells, maxx, maxy = [], 0, 0
    for ckey, members in by_cluster.items():
        xs0, ys0, xs1, ys1 = [], [], [], []
        for n in members:
            w, h = node_size(n, opt)
            x, y = pos[nid[n["name"]]]
            xs0.append(x); ys0.append(y); xs1.append(x + w); ys1.append(y + h)
        bx, by = min(xs0) - PAD, min(ys0) - TOP_PAD
        bw, bh = (max(xs1) - min(xs0)) + 2 * PAD, (max(ys1) - min(ys0)) + TOP_PAD + PAD
        col = specs.get(ckey, {}).get("stroke", "#888888")
        lbl = specs.get(ckey, {}).get("label", ckey)
        cells.append(
            '<mxCell id="%s" value="%s" style="rounded=1;arcSize=3;fillColor=none;'
            'strokeColor=%s;dashed=1;dashPattern=8 4;strokeWidth=2;verticalAlign=top;'
            'align=left;spacingLeft=10;spacingTop=6;fontStyle=1;fontColor=%s;fontSize=13;'
            'html=1;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="%d" height="%d" '
            'as="geometry"/></mxCell>'
            % (cid(ckey), esc(lbl), col, col, round(bx), round(by), round(bw), round(bh)))
        maxx, maxy = max(maxx, bx + bw), max(maxy, by + bh)
    return cells, maxx, maxy


def legend_cell(opt, x, y, w):
    specs = opt.get("clusters", {})
    parts = ["<b>Legend</b> &nbsp; "]
    for spec in specs.values():
        parts.append("<font color='%s'>&#9632;</font> %s &nbsp; "
                     % (spec.get("stroke", "#888"), spec.get("label", "").split(" — ")[0]))
    parts.append("&nbsp;|&nbsp; &#9670; composition &nbsp; &#9671; aggregation "
                 "&nbsp; &#8594; association &nbsp; &#8674; dependency")
    val = esc("".join(parts))  # escaped like every value; draw.io un-escapes & renders the HTML
    return ('<mxCell id="legend" value="%s" style="rounded=1;arcSize=4;whiteSpace=wrap;'
            'html=1;fillColor=#FBFBFB;strokeColor=#BBBBBB;align=left;verticalAlign=middle;'
            'spacingLeft=10;spacingRight=10;fontSize=12;fontColor=#333333;" vertex="1" '
            'parent="1"><mxGeometry x="%d" y="%d" width="%d" height="56" as="geometry"/></mxCell>'
            % (val, round(x), round(y), round(w)))


def render_clustered(model):
    """Renderer for the opt-in cluster / legend / banded / routed path.

    Cell order (draw.io z-order = document order): cluster boxes -> node cells ->
    edges -> legend. Full shape menu supported; clustered nodes are usually class
    compartments, but any other shape still renders via the shared _node_cells."""
    nodes = model.get("nodes") or []
    edges = model.get("edges", [])
    opt = model.get("options", {})
    nid = {n["name"]: "n_" + re.sub(r"[^0-9A-Za-z_]", "_", n["name"]) for n in nodes}
    pos, routes = dot_layout_clustered(nodes, edges, nid, opt)

    rs = ("text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
          "spacingLeft=8;overflow=hidden;rotatable=0;html=1;fontSize=12;fontColor=#1A1A1A;")
    cells = []
    # 1. cluster boxes first (behind everything)
    cbox, cmaxx, cmaxy = cluster_box_cells(nodes, nid, pos, opt)
    cells += cbox
    # 2. node cells (class compartments + any other shapes)
    for node in nodes:
        cells += _node_cells(node, nid, pos, opt, rs)
    # 3. edges (routes come from the pinned whole-graph pass -> box-avoiding)
    for i, e in enumerate(edges):
        cells.append(_edge_cell(i, e, nid, routes))
    # 4. legend, below the diagram (rendered whenever clusters exist)
    if opt.get("clusters"):
        cells.append(legend_cell(opt, MARGIN, cmaxy + 36, max(900, cmaxx - MARGIN)))

    xml = ('<mxGraphModel adaptiveColors="auto"><root><mxCell id="0"/>'
           '<mxCell id="1" parent="0"/>%s</root></mxGraphModel>' % "".join(cells))
    minidom.parseString(xml)
    return xml


# ----------------------------------------------------------------- dispatch
def uses_clusters(model):
    opt = model.get("options", {})
    if opt.get("clusters") or opt.get("layout"):
        return True
    nodes = model.get("nodes") or []
    return any(n.get("cluster") is not None for n in nodes)


def render(model):
    """Dispatch: cluster-less models take the verbatim stock path (byte-identical
    to the global skill); models with clusters/banded layout take the new path."""
    if uses_clusters(model):
        return render_clustered(model)
    return render_flat(model)


def main():
    if len(sys.argv) != 3:
        print("usage: python draw.py MODEL.json OUT.drawio", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as fh:
        model = json.load(fh)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write(render(model))
    nodes = model.get("nodes") or []
    nc = len(model.get("options", {}).get("clusters", {}))
    extra = " (%d clusters)" % nc if nc else ""
    print("wrote %s (%d nodes, %d edges)%s"
          % (sys.argv[2], len(nodes), len(model.get("edges", [])), extra))


if __name__ == "__main__":
    main()
