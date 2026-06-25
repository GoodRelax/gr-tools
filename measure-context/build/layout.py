# -*- coding: utf-8 -*-
"""Shared 2-D geometry for the four diagrams.

Produces backend-neutral "primitives" (shapes + polyline edges in a px
coordinate space) that the SVG (.html), mxGraph (.drawio) and python-pptx
(.pptx) renderers all consume, so those three formats draw the same figure.

A diagram dict looks like:
    {"size": (W, H),
     "shapes": [Shape, ...],
     "edges":  [Edge, ...]}
Shape  = {"kind": "rect|roundrect|diamond|stadium|note", "x","y","w","h","label"}
Edge   = {"points": [(x,y), ...], "label": str, "arrow": bool, "dashed": bool}
The arrowhead (when arrow=True) sits at the last point.
"""
import content as C


def _rect(kind, x, y, w, h, label):
    return {"kind": kind, "x": x, "y": y, "w": w, "h": h, "label": label}


def _edge(points, label="", arrow=True, dashed=False):
    return {"points": points, "label": label, "arrow": arrow, "dashed": dashed}


def _center(s):
    return (s["x"] + s["w"] / 2.0, s["y"] + s["h"] / 2.0)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# --------------------------------------------------------------------------
# Diagram 1: block diagram
# --------------------------------------------------------------------------
def layout_block():
    bw, bh = 170, 44
    shapes = {}
    # sensors, left column
    for i, nid in enumerate(C.BLOCK_SENSORS):
        y = 30 + i * 64
        shapes[nid] = _rect("rect", 20, y, bw, bh, C.node_label(C.BLOCK_NODES, nid))
    # ECU, centre
    ecu = _rect("rect", 300, 135, 180, 90, C.node_label(C.BLOCK_NODES, "ECU"))
    shapes["ECU"] = ecu
    # actuators, right column
    for i, nid in enumerate(C.BLOCK_ACTUATORS):
        y = 84 + i * 74
        shapes[nid] = _rect("rect", 590, y, bw, bh, C.node_label(C.BLOCK_NODES, nid))

    edges = []
    ey0, ey1 = ecu["y"] + 8, ecu["y"] + ecu["h"] - 8
    for (src, dst, label) in C.BLOCK_EDGES:
        s, d = shapes[src], shapes[dst]
        scx, scy = _center(s)
        dcx, dcy = _center(d)
        if dst == "ECU":  # sensor -> ECU (left edge)
            p1 = (s["x"] + s["w"], scy)
            p2 = (d["x"], _clamp(scy, ey0, ey1))
        else:  # ECU -> actuator (right edge)
            p1 = (s["x"] + s["w"], _clamp(dcy, ey0, ey1))
            p2 = (d["x"], dcy)
        edges.append(_edge([p1, p2], label))
    return {"size": (790, 360), "shapes": list(shapes.values()), "edges": edges}


# --------------------------------------------------------------------------
# Diagram 2: state machine
# --------------------------------------------------------------------------
def layout_state():
    w, h = 140, 56
    pos = {
        "OFF": (30, 30),
        "STANDBY": (30, 150),
        "ACTIVE": (250, 150),
        "OVERRIDE": (470, 150),
        "FAULT": (250, 280),
    }
    shapes = {sid: _rect("roundrect", x, y, w, h, sid) for sid, (x, y) in pos.items()}

    def clip(rect, tx, ty):
        cx, cy = _center(rect)
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        hw, hh = rect["w"] / 2.0, rect["h"] / 2.0
        sx = hw / abs(dx) if dx else 1e9
        sy = hh / abs(dy) if dy else 1e9
        s = min(sx, sy)
        return cx + dx * s, cy + dy * s

    # group bidirectional pairs so they can be offset apart
    groups = {}
    for t in C.STATE_TRANSITIONS:
        groups.setdefault(frozenset((t[0], t[1])), []).append(t)

    edges = []
    for (src, dst, label) in C.STATE_TRANSITIONS:
        s, d = shapes[src], shapes[dst]
        scx, scy = _center(s)
        dcx, dcy = _center(d)
        pair = groups[frozenset((src, dst))]
        off = 0.0
        if len(pair) == 2:
            off = 9.0 if pair.index((src, dst, label)) == 0 else -9.0
        # perpendicular unit vector
        vx, vy = dcx - scx, dcy - scy
        ln = (vx * vx + vy * vy) ** 0.5 or 1.0
        px, py = -vy / ln * off, vx / ln * off
        p1 = clip(s, dcx, dcy)
        p2 = clip(d, scx, scy)
        edges.append(_edge([(p1[0] + px, p1[1] + py), (p2[0] + px, p2[1] + py)], label))
    return {"size": (650, 370), "shapes": list(shapes.values()), "edges": edges}


# --------------------------------------------------------------------------
# Diagram 3: sequence
# --------------------------------------------------------------------------
def layout_sequence():
    centers = {"CAM": 70, "ECU": 240, "EPS": 410, "HMI": 560, "DRV": 710}
    top_y, pw, ph = 18, 120, 40
    life_top, life_bot = top_y + ph, 460
    shapes = []
    for pid, label in C.SEQ_PARTICIPANTS:
        cx = centers[pid]
        shapes.append(_rect("rect", cx - pw / 2, top_y, pw, ph, label))
    edges = []
    # lifelines (dashed, no arrow)
    for pid in centers:
        cx = centers[pid]
        edges.append(_edge([(cx, life_top), (cx, life_bot)], "", arrow=False, dashed=True))

    y = 92
    step = 42
    for (src, dst, label) in C.SEQ_MESSAGES:
        if src == dst:  # self action -> note box to the right of the lifeline
            cx = centers[src]
            shapes.append(_rect("note", cx + 6, y - 12, 160, 24, label))
        else:
            sx, dx = centers[src], centers[dst]
            edges.append(_edge([(sx, y), (dx, y)], label))
        y += step
    return {"size": (800, 500), "shapes": shapes, "edges": edges}


# --------------------------------------------------------------------------
# Diagram 4: control-cycle flowchart (hand-tuned coordinates + routes)
# --------------------------------------------------------------------------
def layout_flow():
    L = C.node_label  # (FLOW_NODES, id) -> label
    N = C.FLOW_NODES
    PW, PH = 250, 46          # process box
    DW, DH = 180, 86          # decision diamond
    SW, SH = 180, 44          # start/end stadium
    cx_main, cx_right = 200, 500

    def proc(cx, cy, label):
        return _rect("rect", cx - PW / 2, cy - PH / 2, PW, PH, label)

    def dec(cy, label):
        return _rect("diamond", cx_main - DW / 2, cy - DH / 2, DW, DH, label)

    def stad(cy, label):
        return _rect("stadium", cx_main - SW / 2, cy - SH / 2, SW, SH, label)

    cy = {  # centre-y per node id
        "S": 40, "P1": 110, "P2": 180, "D1": 265, "F1": 265, "P3": 360,
        "D2": 445, "P4": 445, "P5": 540, "D3": 625, "P6": 625, "P7": 720,
        "P8": 790, "P9": 860, "E": 925,
    }
    shapes = {
        "S": stad(cy["S"], L(N, "S")),
        "P1": proc(cx_main, cy["P1"], L(N, "P1")),
        "P2": proc(cx_main, cy["P2"], L(N, "P2")),
        "D1": dec(cy["D1"], L(N, "D1")),
        "F1": proc(cx_right, cy["F1"], L(N, "F1")),
        "P3": proc(cx_main, cy["P3"], L(N, "P3")),
        "D2": dec(cy["D2"], L(N, "D2")),
        "P4": proc(cx_right, cy["P4"], L(N, "P4")),
        "P5": proc(cx_main, cy["P5"], L(N, "P5")),
        "D3": dec(cy["D3"], L(N, "D3")),
        "P6": proc(cx_right, cy["P6"], L(N, "P6")),
        "P7": proc(cx_main, cy["P7"], L(N, "P7")),
        "P8": proc(cx_main, cy["P8"], L(N, "P8")),
        "P9": proc(cx_main, cy["P9"], L(N, "P9")),
        "E": stad(cy["E"], L(N, "E")),
    }

    def bottom(nid):
        s = shapes[nid]
        return (s["x"] + s["w"] / 2, s["y"] + s["h"])

    def top(nid):
        s = shapes[nid]
        return (s["x"] + s["w"] / 2, s["y"])

    def right(nid):
        s = shapes[nid]
        return (s["x"] + s["w"], s["y"] + s["h"] / 2)

    def left(nid):
        s = shapes[nid]
        return (s["x"], s["y"] + s["h"] / 2)

    p8r = right("P8")
    edges = [
        _edge([bottom("S"), top("P1")]),
        _edge([bottom("P1"), top("P2")]),
        _edge([bottom("P2"), top("D1")]),
        _edge([right("D1"), left("F1")], "Yes"),
        _edge([bottom("D1"), top("P3")], "No"),
        _edge([bottom("P3"), top("D2")]),
        _edge([right("D2"), left("P4")], "No"),
        _edge([bottom("D2"), top("P5")], "Yes"),
        _edge([bottom("P5"), top("D3")]),
        _edge([right("D3"), left("P6")], "Yes"),
        _edge([bottom("D3"), top("P7")], "No"),
        _edge([bottom("P7"), top("P8")]),
        _edge([bottom("P8"), top("P9")]),
        _edge([bottom("P9"), top("E")]),
        # right-side merges into P8 via three separate descent lanes
        _edge([right("F1"), (690, cy["F1"]), (690, 778), (p8r[0], 778)]),
        _edge([right("P4"), (665, cy["P4"]), (665, 790), (p8r[0], 790)]),
        _edge([right("P6"), (640, cy["P6"]), (640, 802), (p8r[0], 802)]),
    ]
    return {"size": (760, 970), "shapes": list(shapes.values()), "edges": edges}


ALL = {
    "block": layout_block,
    "state": layout_state,
    "sequence": layout_sequence,
    "flow": layout_flow,
}

if __name__ == "__main__":
    for name, fn in ALL.items():
        g = fn()
        print(name, "size", g["size"], "shapes", len(g["shapes"]), "edges", len(g["edges"]))
