#!/usr/bin/env python3
"""drawio-uml: clean UML / node-link diagrams (.drawio) from a JSON model (0.3.0).

Native draw.io shapes laid out by Graphviz `dot`, which computes BOTH node
positions AND orthogonal edge routes (splines=ortho). The edge routes are
imported as draw.io waypoints so lines route around boxes instead of through them.

0.3.0 model (see schema/model.schema.json):
  * nodes  : flat node definitions, referenced elsewhere by name.
  * edges  : relations between nodes.
  * layout : a RECURSIVE cluster tree. Each cluster arranges its contents along
             `direction` (row=left->right / column=top->bottom), draws a dashed
             labelled box iff it has a `label`, cascades color/fill to descendant
             nodes (nearest ancestor wins), and holds EXACTLY ONE of `clusters`
             (child clusters) or `nodes` (member node names). Omit `layout` for a
             flat diagram (dot lays out everything; flow = options.direction).
  * views  : named node subsets; --view KEY renders the induced subgraph (the
             master layout pruned to the selected nodes).
  * options: direction (default column=TB), column_width, node_separation,
             rank_separation.

Layout engine (clustered path): each LEAF cluster is laid out in its own dot run
(reliable on a single simple group); Python composes children by `direction`
(so sibling order is guaranteed); a final position-pinned neato/fdp pass routes
EVERY edge around the placed boxes.

Requires Python 3.10+ and Graphviz `dot` on PATH (plus `neato`/`fdp` for the
pinned routing pass used by the clustered path).

Usage:
    python draw.py MODEL.json OUT.drawio [--view KEY]
"""
import json
import re
import subprocess
import sys
import xml.dom.minidom as minidom
from collections import Counter, OrderedDict

# ---------------------------------------------------------------- edge arrows
ARROW = {
    "generalization":       "endArrow=block;endFill=0;endSize=14;",
    "realization":          "endArrow=block;endFill=0;endSize=14;dashed=1;",
    "composition":          "startArrow=diamondThin;startFill=1;startSize=14;endArrow=open;endFill=0;",
    "aggregation":          "startArrow=diamondThin;startFill=0;startSize=14;endArrow=open;endFill=0;",
    "directed_association": "endArrow=open;",
    "dependency":           "endArrow=open;dashed=1;",
    "transition":           "endArrow=block;endFill=1;endSize=10;",
    "association":          "endArrow=none;",
}
EDGE_BASE = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#3A3A3A;"
             "fontSize=11;fontColor=#222222;labelBackgroundColor=#FFFFFF;")

# ------------------------------------------------------- node shape presets
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
COMPARTMENT = {"class", "entity", "object"}
NO_LABEL = {"initial", "final"}

DEFAULT_FILL, DEFAULT_STROKE = "#EEF0FF", "#5B5FC7"
TITLE_H, ROW_H, DIV_H = 40, 22, 10

# -- clustered-layout constants --
MARGIN = 70             # canvas margin (room for top-left cluster labels)
PAD, TOP_PAD = 24, 34   # cluster box padding (sides / top for its label)
ROW_GAP = 80            # gap between children arranged left->right
COL_GAP = 90            # gap between children arranged top->bottom
DEPTH_WARN = 4          # warn when labelled nesting on a root->leaf path exceeds this
DEFAULT_BOX_COLOR = "#888888"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _unwrap(out):
    """Graphviz -Tplain wraps long physical lines with a trailing backslash; rejoin
    continuation lines on the RAW text before splitting, so long node ids / labels
    (= long node names) don't break parsing (FR-D-03b)."""
    return re.sub(r"\\\r?\n", "", out)


def _unq(tok):
    """Strip the surrounding double-quotes Graphviz adds around long ids/labels in
    -Tplain output, so a quoted node id matches its unquoted nid/cid key (FR-D-03b).
    (Generated ids are alnum/underscore, so they never contain spaces or quotes.)"""
    return tok[1:-1] if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"' else tok


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


def _node_cells(node, nid, pos, opt, rs, eff):
    """Render ONE node into a list of mxCells. `eff` maps node name -> the
    resolved (fill, stroke) after cluster cascade (node's own values win)."""
    n = node["name"]
    ni = nid[n]
    w, h = node_size(node, opt)
    x, y = pos[ni]
    fill, stroke = eff[n]
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
        if sh == "final":
            iw, ih = round(w * 0.46), round(h * 0.46)
            ix, iy = round(x + (w - iw) / 2), round(y + (h - ih) / 2)
            out.append('<mxCell id="%s__dot" value="" style="ellipse;fillColor=#333333;'
                       'strokeColor=#333333;" vertex="1" parent="1"><mxGeometry x="%d" '
                       'y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                       % (ni, ix, iy, iw, ih))
    return out


def _edge_cell(i, e, ref, routes):
    a = arrow_of(e)
    si, ti = ref[e["source"]], ref[e["target"]]
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


def make_nid(nodes):
    return {n["name"]: "n_" + re.sub(r"[^0-9A-Za-z_]", "_", n["name"]) for n in nodes}


def rs_style():
    return ("text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
            "spacingLeft=8;overflow=hidden;rotatable=0;html=1;fontSize=12;fontColor=#1A1A1A;")


def direction_to_rankdir(direction):
    return "TB" if direction == "column" else "LR"


def resolve_styles(nodes, layout):
    """name -> resolved (fill, stroke). A node's own fill/stroke win; else the
    NEAREST enclosing cluster's fill / color (cascaded independently); else the
    package default. Nodes not under any cluster fall back to own / default."""
    own = {n["name"]: (n.get("fill"), n.get("stroke")) for n in nodes}
    eff = {}

    def walk(cluster, inh_fill, inh_stroke):
        cf = cluster.get("fill", inh_fill)
        cs = cluster.get("color", inh_stroke)
        if is_leaf(cluster):
            for name in cluster["nodes"]:
                of, os_ = own.get(name, (None, None))
                eff[name] = (of or cf or DEFAULT_FILL, os_ or cs or DEFAULT_STROKE)
        else:
            for ch in cluster["clusters"]:
                walk(ch, cf, cs)

    if layout:
        walk(layout, None, None)
    for name, (of, os_) in own.items():
        eff.setdefault(name, (of or DEFAULT_FILL, os_ or DEFAULT_STROKE))
    return eff


# ======================================================================
#  FLAT PATH  (no `layout`: dot lays out every node; flow = options.direction)
# ======================================================================
def dot_layout(nodes, edges, nid, opt):
    """Graphviz dot -> (pos, routes) in draw.io px. y flipped, min corner at (40,40)."""
    rankdir = direction_to_rankdir(opt.get("direction", "column"))
    g = ["digraph G {",
         "rankdir=%s; nodesep=%s; ranksep=%s; splines=ortho;"
         % (rankdir, opt.get("node_separation", 0.7), opt.get("rank_separation", 1.1)),
         "node [shape=box, fixedsize=true];"]
    for n in nodes:
        w, h = node_size(n, opt)
        g.append('%s [width=%.3f, height=%.3f];' % (nid[n["name"]], w / 72.0, h / 72.0))
    for e in edges:
        s, t = nid[e["source"]], nid[e["target"]]
        a, b = (t, s) if arrow_of(e) in ("generalization", "realization") else (s, t)
        g.append("%s -> %s;" % (a, b))
    g.append("}")
    out = subprocess.run(["dot", "-Tplain"], input="\n".join(g),
                         capture_output=True, text=True, check=True, encoding="utf-8").stdout
    out = _unwrap(out)
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
            pos[_unq(p[1])] = ((cx - w / 2) * 72, (H - cy - h / 2) * 72)
        elif p[0] == "edge":
            t, hd, k = _unq(p[1]), _unq(p[2]), int(p[3])
            c = p[4:4 + 2 * k]
            routes[(t, hd)] = [(float(c[2 * i]) * 72, (H - float(c[2 * i + 1])) * 72)
                               for i in range(k)]
    if not pos:
        return {}, {}
    mnx = min(x for x, _ in pos.values())
    mny = min(y for _, y in pos.values())
    pos = {n: (x - mnx + 40, y - mny + 40) for n, (x, y) in pos.items()}
    routes = {e: [(x - mnx + 40, y - mny + 40) for x, y in pts] for e, pts in routes.items()}
    return pos, routes


def render_flat(model, nodes, edges):
    opt = model.get("options", {})
    nid = make_nid(nodes)
    pos, routes = dot_layout(nodes, edges, nid, opt)
    eff = resolve_styles(nodes, None)
    rs = rs_style()
    cells = []
    for node in nodes:
        cells += _node_cells(node, nid, pos, opt, rs, eff)
    for i, e in enumerate(edges):
        cells.append(_edge_cell(i, e, nid, routes))
    xml = ('<mxGraphModel adaptiveColors="auto"><root><mxCell id="0"/>'
           '<mxCell id="1" parent="0"/>%s</root></mxGraphModel>' % "".join(cells))
    minidom.parseString(xml)
    return xml


# ======================================================================
#  CLUSTERED PATH  (recursive `layout` tree: compose + nested boxes + routing)
# ======================================================================
def cid(key):
    return "cluster_" + re.sub(r"[^0-9A-Za-z_]", "_", key)


def is_leaf(cluster):
    return "nodes" in cluster


def resolve_direction(cluster, opt):
    return cluster.get("direction") or opt.get("direction") or "column"


def _parse_plain(out, off_x, off_y, re_origin):
    out = _unwrap(out)
    H = None
    raw_pos, raw_size = {}, {}
    for ln in out.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "graph":
            H = float(p[3])
        elif p[0] == "node":
            cx, cy, w, h = (float(v) for v in p[2:6])
            i = _unq(p[1])
            raw_pos[i] = ((cx - w / 2) * 72, (H - cy - h / 2) * 72)
            raw_size[i] = (w * 72, h * 72)
    if re_origin and raw_pos:
        mnx = min(x for x, _ in raw_pos.values())
        mny = min(y for _, y in raw_pos.values())
    else:
        mnx = mny = 0.0
    pos = {n: (x - mnx + off_x, y - mny + off_y) for n, (x, y) in raw_pos.items()}
    return pos, raw_size


def _run_dot(g_lines):
    out = subprocess.run(["dot", "-Tplain"], input="\n".join(g_lines),
                         capture_output=True, text=True, check=True, encoding="utf-8").stdout
    pos, raw_size = _parse_plain(out, 0.0, 0.0, re_origin=True)
    bw = max((pos[n][0] + raw_size[n][0] for n in pos), default=0.0)
    bh = max((pos[n][1] + raw_size[n][1] for n in pos), default=0.0)
    return pos, (bw, bh)


def _leaf_layout(cluster, members, edges, nid, opt):
    """Lay out one leaf cluster's members in their own dot run; positions are
    origin-normalised (min corner at (0,0)). With internal structural edges dot's
    rank layout governs; without any, members are chained with INVISIBLE edges so
    they line up along `direction` in listed order."""
    direction = resolve_direction(cluster, opt)
    nodesep, ranksep = opt.get("node_separation", 0.8), opt.get("rank_separation", 1.25)
    g = ["digraph G {",
         "rankdir=%s; nodesep=%s; ranksep=%s; splines=ortho;"
         % (direction_to_rankdir(direction), nodesep, ranksep),
         "node [shape=box, fixedsize=true];"]
    for n in members:
        w, h = node_size(n, opt)
        g.append('%s [width=%.3f, height=%.3f];' % (nid[n["name"]], w / 72.0, h / 72.0))
    names = {n["name"] for n in members}
    has_internal = False
    for e in edges:
        if e["source"] in names and e["target"] in names:
            s, t = nid[e["source"]], nid[e["target"]]
            a, b = (t, s) if arrow_of(e) in ("generalization", "realization") else (s, t)
            g.append("%s -> %s;" % (a, b))
            has_internal = True
    if not has_internal and len(members) > 1:
        for p, q in zip(members, members[1:]):
            g.append("%s -> %s [style=invis];" % (nid[p["name"]], nid[q["name"]]))
    g.append("}")
    return _run_dot(g)


def compose(cluster, edges, nid, opt, nodemap):
    """Recursively lay out a cluster. Returns (pos, (w, h), boxes) in a local
    frame whose top-left (including this cluster's own box, if labelled) is (0,0).
    `boxes` = [(cluster, x0, y0, x1, y1), ...] OUTERMOST-FIRST (document/z order)."""
    if is_leaf(cluster):
        members = [nodemap[name] for name in cluster["nodes"]]
        pos, (mw, mh) = _leaf_layout(cluster, members, edges, nid, opt)
        if "label" in cluster:
            pos = {k: (x + PAD, y + TOP_PAD) for k, (x, y) in pos.items()}
            ew, eh = mw + 2 * PAD, mh + TOP_PAD + PAD
            return pos, (ew, eh), [(cluster, 0.0, 0.0, ew, eh)]
        return pos, (mw, mh), []

    direction = resolve_direction(cluster, opt)
    children = [compose(ch, edges, nid, opt, nodemap) for ch in cluster["clusters"]]
    gap = ROW_GAP if direction == "row" else COL_GAP
    pos, boxes = {}, []
    if direction == "row":
        cross = max((h for (_, (w, h), _) in children), default=0.0)
        cur = 0.0
        for cpos, (cw, ch), cboxes in children:
            dx, dy = cur, (cross - ch) / 2.0
            for k, (x, y) in cpos.items():
                pos[k] = (x + dx, y + dy)
            boxes += [(c, x0 + dx, y0 + dy, x1 + dx, y1 + dy) for (c, x0, y0, x1, y1) in cboxes]
            cur += cw + gap
        content_w, content_h = (cur - gap if children else 0.0), cross
    else:
        cross = max((w for (_, (w, h), _) in children), default=0.0)
        cur = 0.0
        for cpos, (cw, ch), cboxes in children:
            dx, dy = (cross - cw) / 2.0, cur
            for k, (x, y) in cpos.items():
                pos[k] = (x + dx, y + dy)
            boxes += [(c, x0 + dx, y0 + dy, x1 + dx, y1 + dy) for (c, x0, y0, x1, y1) in cboxes]
            cur += ch + gap
        content_w, content_h = cross, (cur - gap if children else 0.0)

    if "label" in cluster:
        pos = {k: (x + PAD, y + TOP_PAD) for k, (x, y) in pos.items()}
        boxes = [(c, x0 + PAD, y0 + TOP_PAD, x1 + PAD, y1 + TOP_PAD)
                 for (c, x0, y0, x1, y1) in boxes]
        ew, eh = content_w + 2 * PAD, content_h + TOP_PAD + PAD
        return pos, (ew, eh), [(cluster, 0.0, 0.0, ew, eh)] + boxes
    return pos, (content_w, content_h), boxes


def _parse_plain_raw(out):
    out = _unwrap(out)
    centres, polylines = {}, {}
    for ln in out.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "node":
            centres[_unq(p[1])] = (float(p[2]) * 72.0, float(p[3]) * 72.0)
        elif p[0] == "edge":
            t, hd, k = _unq(p[1]), _unq(p[2]), int(p[3])
            c = p[4:4 + 2 * k]
            polylines[(t, hd)] = [(float(c[2 * i]) * 72.0, float(c[2 * i + 1]) * 72.0)
                                  for i in range(k)]
    return centres, polylines


def _route_pinned(nodes, edges, ref, opt, pos, cl_pins=None, skip=None):
    """FINAL box-avoiding routing over the WHOLE graph: pin every node AND every
    cluster-endpoint box at its placed centre, then let neato/fdp (-n2) route the
    edges with splines=ortho. `ref` maps an endpoint name -> its mxCell id (node
    `nid` or cluster `cid`); `cl_pins` maps a cluster `cid` -> (x, y, w, h) box
    geometry; `skip` is a set of frozenset({id, id}) pairs left unrouted (FR-D-17)."""
    cl_pins = cl_pins or {}
    skip = skip or set()
    if not pos and not cl_pins:
        return {}
    size, cpos = {}, {}
    for n in nodes:                                          # nodes: id == ref[name] == nid
        i = ref[n["name"]]
        size[i] = node_size(n, opt)
        cpos[i] = pos[i]
    for bid, (x, y, w, h) in cl_pins.items():                # cluster boxes (boxes order = deterministic)
        size[bid] = (w, h)
        cpos[bid] = (x, y)
    lines = ["graph G {", "  splines=ortho;", "  node [shape=box, fixedsize=true];"]
    for i, (px, py) in cpos.items():
        w, h = size[i]
        lines.append('  %s [width=%.4f, height=%.4f, pos="%.3f,%.3f!"];'
                     % (i, w / 72.0, h / 72.0, px + w / 2.0, -(py + h / 2.0)))
    seen = set()
    for e in edges:
        s, t = ref[e["source"]], ref[e["target"]]
        if s == t or frozenset((s, t)) in skip or (s, t) in seen or (t, s) in seen:
            continue
        seen.add((s, t))
        lines.append("  %s -- %s;" % (s, t))
    lines.append("}")
    src = "\n".join(lines)
    out = None
    for engine in (["neato", "-n2", "-Tplain"], ["fdp", "-n2", "-Tplain"], ["neato", "-n", "-Tplain"]):
        try:
            r = subprocess.run(engine, input=src, capture_output=True, text=True, encoding="utf-8")
        except FileNotFoundError:
            continue
        if r.returncode == 0 and r.stdout.strip():
            out = r.stdout
            break
    if out is None:
        print("draw: warning: neato/fdp unavailable; box-avoiding routing skipped, "
              "falling back to draw.io auto-routing (FR-D-07a)", file=sys.stderr)
        return {}
    centres, polylines = _parse_plain_raw(out)
    oxs, oys = [], []
    for i, (px, py) in cpos.items():
        if i not in centres:
            continue
        w, h = size[i]
        cx_pt, cy_pt = centres[i]
        oxs.append((px + w / 2.0) - cx_pt)
        oys.append((py + h / 2.0) + cy_pt)
    if not oxs:
        return {}
    ox, oy = sum(oxs) / len(oxs), sum(oys) / len(oys)

    def to_px(pt):
        return (pt[0] + ox, -pt[1] + oy)

    table = {}
    for (a, b), pts in polylines.items():
        conv = [to_px(p) for p in pts]
        table[(a, b)] = conv
        table[(b, a)] = conv[::-1]
    routes = {}
    for e in edges:
        s, t = ref[e["source"]], ref[e["target"]]
        if s == t or frozenset((s, t)) in skip:
            continue
        key = (t, s) if arrow_of(e) in ("generalization", "realization") else (s, t)
        if key in table:
            routes[key] = table[key]
    return routes


def box_cell(cluster, idx, x, y, w, h):
    name = cluster.get("name")
    bid = cid(name) if name else "anonbox_%d" % idx        # reserved prefix cid() cannot emit (no collision)
    col = cluster.get("color") or DEFAULT_BOX_COLOR
    return ('<mxCell id="%s" value="%s" style="rounded=1;arcSize=3;fillColor=none;'
            'strokeColor=%s;dashed=1;dashPattern=8 4;strokeWidth=2;verticalAlign=top;'
            'align=left;spacingLeft=10;spacingTop=6;fontStyle=1;fontColor=%s;fontSize=13;'
            'html=1;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="%d" height="%d" '
            'as="geometry"/></mxCell>'
            % (bid, esc(cluster.get("label", "")), col, col,
               round(x), round(y), round(w), round(h)))


def outermost_labelled(cluster, found=None):
    """(label, color) for every labelled cluster that has no labelled ancestor."""
    if found is None:
        found = []
    if cluster is None:
        return found
    if "label" in cluster:
        found.append((cluster["label"], cluster.get("color") or DEFAULT_BOX_COLOR))
        return found                       # stop: descendants are not outermost
    if not is_leaf(cluster):
        for ch in cluster["clusters"]:
            outermost_labelled(ch, found)
    return found


def legend_cell(outermost, x, y, w):
    parts, seen = ["<b>Legend</b> &nbsp; "], set()
    for label, color in outermost:
        if color in seen:
            continue
        seen.add(color)
        parts.append("<font color='%s'>&#9632;</font> %s &nbsp; " % (color, label.split(" — ")[0]))
    parts.append("&nbsp;|&nbsp; &#9670; composition &nbsp; &#9671; aggregation "
                 "&nbsp; &#8594; association &nbsp; &#8674; dependency")
    val = esc("".join(parts))
    return ('<mxCell id="legend" value="%s" style="rounded=1;arcSize=4;whiteSpace=wrap;'
            'html=1;fillColor=#FBFBFB;strokeColor=#BBBBBB;align=left;verticalAlign=middle;'
            'spacingLeft=10;spacingRight=10;fontSize=12;fontColor=#333333;" vertex="1" '
            'parent="1"><mxGeometry x="%d" y="%d" width="%d" height="56" as="geometry"/></mxCell>'
            % (val, round(x), round(y), round(w)))


def validate_tree(nodes, layout):
    """FR-D-03a / FR-D-14: every node placed exactly once; cluster names unique
    and '/'-free; warn when labelled nesting exceeds DEPTH_WARN."""
    placed, names, max_depth = [], [], [0]

    def walk(c, depth):
        nm = c.get("name")
        if "nodes" in c and "clusters" in c:
            sys.exit("draw: cluster has both 'nodes' and 'clusters': %r"
                     % (nm or c.get("label") or "<anonymous>"))
        if nm is not None:
            if "/" in nm:
                sys.exit("draw: cluster name must not contain '/': %r" % nm)
            names.append(nm)
        d = depth + (1 if "label" in c else 0)
        max_depth[0] = max(max_depth[0], d)
        if is_leaf(c):
            placed.extend(c["nodes"])
        else:
            for ch in c["clusters"]:
                walk(ch, d)

    walk(layout, 0)
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        sys.exit("draw: duplicate cluster name(s): %s" % ", ".join(dups))
    allnames = [n["name"] for n in nodes]
    known = set(allnames)
    cnt = Counter(placed)
    missing = [n for n in allnames if n not in cnt]
    dupn = sorted({n for n, c in cnt.items() if c > 1})
    unknown = sorted({n for n in placed if n not in known})
    if missing or dupn or unknown:
        sys.exit("draw: layout must place every node exactly once "
                 "(missing=%s, duplicated=%s, unknown=%s)" % (missing, dupn, unknown))
    if max_depth[0] > DEPTH_WARN:
        print("draw: warning: labelled cluster nesting is %d deep (>%d); deep nesting "
              "is hard to read (LM-1)" % (max_depth[0], DEPTH_WARN), file=sys.stderr)


def render_clustered(model, nodes, edges, layout):
    opt = model.get("options", {})
    nid = make_nid(nodes)
    nodemap = {n["name"]: n for n in nodes}
    validate_tree(nodes, layout)
    pos, _, boxes = compose(layout, edges, nid, opt, nodemap)
    pos = {k: (x + MARGIN, y + MARGIN) for k, (x, y) in pos.items()}
    boxes = [(c, x0 + MARGIN, y0 + MARGIN, x1 + MARGIN, y1 + MARGIN)
             for (c, x0, y0, x1, y1) in boxes]
    # endpoint resolution: ref maps node name -> nid, named+labelled cluster -> cid (FR-D-17)
    node_names = set(nid)
    clusters = collect_clusters(layout)
    ref = dict(nid)
    for cname, cl in clusters.items():
        if "label" in cl:
            ref[cname] = cid(cname)
    # cluster-endpoint boxes to pin during routing, cid -> (x, y, w, h), in boxes order
    cluster_eps = {x for e in edges for x in (e["source"], e["target"])
                   if x in clusters and "label" in clusters[x]}
    cl_pins = OrderedDict()
    for (c, x0, y0, x1, y1) in boxes:
        nm = c.get("name")
        if nm in cluster_eps:
            cl_pins[cid(nm)] = (x0, y0, x1 - x0, y1 - y0)
    # degenerate (containment) endpoint pairs left unrouted, like self-loops (FR-D-17)
    skip = set()
    for e in edges:
        a = _endpoint_membership(e["source"], node_names, clusters)
        b = _endpoint_membership(e["target"], node_names, clusters)
        if a and b and (a <= b or b <= a):
            skip.add(frozenset((ref[e["source"]], ref[e["target"]])))

    routes = _route_pinned(nodes, edges, ref, opt, pos, cl_pins, skip)
    if cl_pins:                                              # clip routes to endpoint box boundaries (FR-D-07)
        def _inside(pt, rect):
            x, y, w, h = rect
            return x <= pt[0] <= x + w and y <= pt[1] <= y + h
        for key, pts in list(routes.items()):
            rects = [cl_pins[k] for k in key if k in cl_pins]
            if rects and len(pts) > 2:
                routes[key] = ([pts[0]]
                               + [p for p in pts[1:-1] if not any(_inside(p, r) for r in rects)]
                               + [pts[-1]])
    eff = resolve_styles(nodes, layout)
    rs = rs_style()

    cells = []
    for idx, (c, x0, y0, x1, y1) in enumerate(boxes):       # boxes are outer-first -> behind
        cells.append(box_cell(c, idx, x0, y0, x1 - x0, y1 - y0))
    for node in nodes:
        cells += _node_cells(node, nid, pos, opt, rs, eff)
    for i, e in enumerate(edges):
        cells.append(_edge_cell(i, e, ref, routes))

    outer = outermost_labelled(layout)
    if outer:
        maxx = max([x1 for (_, _, _, x1, _) in boxes]
                   + [pos[nid[n["name"]]][0] + node_size(n, opt)[0] for n in nodes], default=MARGIN)
        maxy = max([y1 for (_, _, _, _, y1) in boxes]
                   + [pos[nid[n["name"]]][1] + node_size(n, opt)[1] for n in nodes], default=MARGIN)
        cells.append(legend_cell(outer, MARGIN, maxy + 36, max(900, maxx - MARGIN)))

    xml = ('<mxGraphModel adaptiveColors="auto"><root><mxCell id="0"/>'
           '<mxCell id="1" parent="0"/>%s</root></mxGraphModel>' % "".join(cells))
    minidom.parseString(xml)
    return xml


# ----------------------------------------------------------------- views
def node_names_under(cluster):
    if cluster is None:
        return set()
    if is_leaf(cluster):
        return set(cluster["nodes"])
    out = set()
    for ch in cluster["clusters"]:
        out |= node_names_under(ch)
    return out


def collect_clusters(layout):
    """name -> cluster object, for every NAMED cluster in the tree (FR-D-17)."""
    out = {}

    def walk(c):
        nm = c.get("name")
        if nm is not None:
            out[nm] = c
        if not is_leaf(c):
            for ch in c["clusters"]:
                walk(ch)

    if layout:
        walk(layout)
    return out


def find_cluster(cluster, name):
    if cluster is None:
        return None
    if cluster.get("name") == name:
        return cluster
    if not is_leaf(cluster):
        for ch in cluster["clusters"]:
            hit = find_cluster(ch, name)
            if hit:
                return hit
    return None


def prune(cluster, selected):
    """Prune the layout tree to `selected` node names: drop empty leaves and
    childless internal clusters. Returns a pruned copy or None if empty."""
    if is_leaf(cluster):
        kept = [n for n in cluster["nodes"] if n in selected]
        if not kept:
            return None
        c = dict(cluster)
        c["nodes"] = kept
        return c
    kids = [k for k in (prune(ch, selected) for ch in cluster["clusters"]) if k]
    if not kids:
        return None
    c = dict(cluster)
    c["clusters"] = kids
    return c


def apply_view(model, key):
    views = model.get("views") or {}
    if key not in views:                                    # FR-D-16a
        sys.exit("draw: unknown --view %r (known: %s)" % (key, ", ".join(sorted(views)) or "none"))
    view = views[key]
    nodes = model.get("nodes") or []
    allnames = {n["name"] for n in nodes}
    layout = model.get("layout")
    selected = set(view.get("nodes", []))
    for cname in view.get("clusters", []):
        cl = find_cluster(layout, cname) if layout else None
        if cl is None:
            sys.exit("draw: view %r references unknown cluster %r" % (key, cname))
        selected |= node_names_under(cl)
    unknown = selected - allnames
    if unknown:
        sys.exit("draw: view %r references unknown node(s): %s" % (key, ", ".join(sorted(unknown))))
    if not selected:
        sys.exit("draw: view %r selects no node" % key)
    fnodes = [n for n in nodes if n["name"] in selected]
    flayout = prune(layout, selected) if layout else None

    def _survives(x):                                       # FR-D-16: a node selected, or a cluster still drawn
        if x in selected:
            return True
        return flayout is not None and find_cluster(flayout, x) is not None

    fedges = [e for e in (model.get("edges") or [])
              if _survives(e.get("source")) and _survives(e.get("target"))]
    return fnodes, fedges, flayout


# ----------------------------------------------------------------- dispatch
def _endpoint_membership(name, node_names, clusters):
    """Nodes 'covered' by an endpoint: a node -> {itself}; a cluster -> its
    descendant node set. Drives the containment-degeneracy test (FR-D-17)."""
    if name in node_names:
        return frozenset((name,))
    cl = clusters.get(name)
    return frozenset(node_names_under(cl)) if cl is not None else frozenset()


def _validate_endpoints(edges, node_names, clusters):
    """FR-D-17: every edge endpoint resolves to exactly one node OR one
    named+labelled cluster. Ambiguous / unknown / unnamed-or-label-less -> fail-fast."""
    amb, unk, badcl = set(), set(), set()
    for e in edges:
        for x in (e.get("source"), e.get("target")):
            cl = clusters.get(x)
            in_node = x in node_names
            if in_node and cl is not None:
                amb.add(str(x))
            elif in_node:
                continue
            elif cl is not None:
                if "label" not in cl:
                    badcl.add(str(x))
            else:
                unk.add("(missing)" if x is None else str(x))
    msgs = []
    if amb:
        msgs.append("ambiguous (node and cluster share the name): %s" % ", ".join(sorted(amb)))
    if unk:
        msgs.append("unknown (no such node or cluster): %s" % ", ".join(sorted(unk)))
    if badcl:
        msgs.append("cluster endpoint has no label (no box to anchor): %s" % ", ".join(sorted(badcl)))
    if msgs:
        sys.exit("draw: invalid edge endpoint(s): " + "; ".join(msgs))


def render_model(model, view_key=None):
    """Resolve (optionally a --view) and render. Returns (xml, nodes, edges) where
    nodes/edges are the ones actually drawn. Fails fast (§3.4 referential integrity)
    when an edge references an undefined node."""
    nodes = model.get("nodes") or []
    edges = model.get("edges") or []
    layout = model.get("layout")
    node_names = {n["name"] for n in nodes}
    clusters = collect_clusters(layout)
    _validate_endpoints(edges, node_names, clusters)        # FR-D-17: node -> cluster resolution
    if view_key is not None:
        nodes, edges, layout = apply_view(model, view_key)
    xml = render_clustered(model, nodes, edges, layout) if layout else render_flat(model, nodes, edges)
    return xml, nodes, edges


def render(model, view_key=None):
    """Model -> .drawio XML string. (render_model also returns the drawn counts.)"""
    return render_model(model, view_key)[0]


def main():
    args = sys.argv[1:]
    view_key = None
    if "--view" in args:
        i = args.index("--view")
        if i + 1 >= len(args):
            print("usage: python draw.py MODEL.json OUT.drawio [--view KEY]", file=sys.stderr)
            sys.exit(2)
        view_key = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        print("usage: python draw.py MODEL.json OUT.drawio [--view KEY]", file=sys.stderr)
        sys.exit(2)
    try:
        with open(args[0], encoding="utf-8") as fh:
            model = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.exit("draw: cannot read model: %s" % exc)
    xml, rn, re_ = render_model(model, view_key)
    with open(args[1], "w", encoding="utf-8") as fh:
        fh.write(xml)
    suffix = " (--view %s)" % view_key if view_key else ""
    print("wrote %s (%d nodes, %d edges)%s" % (args[1], len(rn), len(re_), suffix))


if __name__ == "__main__":
    main()
