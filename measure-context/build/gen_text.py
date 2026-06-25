# -*- coding: utf-8 -*-
"""Renderers for the text-based formats: .txt, .md, .drawio, .html.

(.sdoc lives in gen_sdoc.py because its grammar is validated with strictdoc.)
Every renderer walks the SAME document order so the logical content matches:

  title/abstract
  1 概要        -> 図1 構成図
  2 機能要求
  3 状態遷移    -> 図2 状態遷移図
  4 シーケンス  -> 図3 シーケンス図
  5 処理フロー  -> 図4 フローチャート
  6 機能安全
  7 表          -> 表1 / 表2 / 図5 capture1 / 図6 capture2
"""
import os
import content as C
import layout as LY
from common import (count_tokens, dwidth, pad_disp, plain_table,
                    xml_escape, html_escape)

SAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))


def _meta_lines():
    return [
        ("文書番号", C.DOC["doc_id"]),
        ("版数", C.DOC["version"]),
        ("発行日", C.DOC["date"]),
        ("作成", C.DOC["owner"]),
    ]


# ==========================================================================
# .txt  (ASCII-art figures, plain aligned tables, image path references)
# ==========================================================================
def _state_label(src, dst):
    for s, d, l in C.STATE_TRANSITIONS:
        if s == src and d == dst:
            return l
    return ""


def ascii_block():
    sensors = C.BLOCK_SENSORS
    left_w = max(dwidth(C.node_label(C.BLOCK_NODES, s)) for s in sensors)
    sens_edge = {src: lab for (src, dst, lab) in C.BLOCK_EDGES if dst == "ECU"}
    segs = {s: "--" + sens_edge[s] + "-->" for s in sensors}
    mid_w = max(dwidth(v) for v in segs.values())
    ecu = ["+-----------+", "|           |", "| LKAS ECU  |", "|           |", "+-----------+"]
    act = [(dst, lab) for (src, dst, lab) in C.BLOCK_EDGES if src == "ECU"]
    lines = []
    for i, s in enumerate(sensors):
        lab = pad_disp(C.node_label(C.BLOCK_NODES, s), left_w, "right")
        seg = pad_disp(segs[s], mid_w, "left")
        right = ""
        if i in (1, 2, 3):
            dst, albl = act[i - 1]
            right = " --" + albl + "--> " + C.node_label(C.BLOCK_NODES, dst)
        lines.append("%s %s %s%s" % (lab, seg, ecu[i], right))
    return "\n".join(lines)


def ascii_state():
    chain = (
        "        +-----+      +---------+      +--------+      +----------+\n"
        "        | OFF | <--> | STANDBY | <--> | ACTIVE | <--> | OVERRIDE |\n"
        "        +-----+      +---------+      +--------+      +----------+\n"
        "                                          |  \\          |\n"
        "                          (故障検出)       v   v         v\n"
        "                                      +-------+\n"
        "                                      | FAULT |\n"
        "                                      +-------+\n"
    )
    legend = [
        "  遷移条件 (初期状態: OFF):",
        "    OFF --(%s)--> STANDBY" % _state_label("OFF", "STANDBY"),
        "    STANDBY --(%s)--> OFF" % _state_label("STANDBY", "OFF"),
        "    STANDBY --(%s)--> ACTIVE" % _state_label("STANDBY", "ACTIVE"),
        "    ACTIVE --(%s)--> STANDBY" % _state_label("ACTIVE", "STANDBY"),
        "    ACTIVE --(%s)--> OVERRIDE" % _state_label("ACTIVE", "OVERRIDE"),
        "    OVERRIDE --(%s)--> ACTIVE" % _state_label("OVERRIDE", "ACTIVE"),
        "    STANDBY/ACTIVE/OVERRIDE --(%s)--> FAULT" % _state_label("ACTIVE", "FAULT"),
        "    FAULT --(%s)--> OFF" % _state_label("FAULT", "OFF"),
    ]
    return chain + "\n" + "\n".join(legend)


def ascii_sequence():
    ids = [p[0] for p in C.SEQ_PARTICIPANTS]
    col = {pid: 3 + i * 9 for i, pid in enumerate(ids)}
    width = max(col.values()) + 4
    header = [" "] * width
    for pid in ids:
        s = pid
        start = col[pid] - len(s) // 2
        for k, ch in enumerate(s):
            header[start + k] = ch
    base = [" "] * width
    for pid in ids:
        base[col[pid]] = "|"
    rows = ["".join(header), "".join(base)]
    n = 0
    for (src, dst, label) in C.SEQ_MESSAGES:
        n += 1
        row = list(base)
        if src == dst:
            c = col[src]
            for k, ch in enumerate("[self]"):
                row[c - 2 + k] = ch
        else:
            a, b = col[src], col[dst]
            lo, hi = sorted((a, b))
            for x in range(lo, hi + 1):
                row[x] = "-"
            row[b] = ">" if b > a else "<"
            row[a] = "|"
        rows.append("".join(row).rstrip() + "   (%d) %s" % (n, label))
    legend = "  凡例: " + " / ".join("%s=%s" % (pid, lab) for pid, lab in C.SEQ_PARTICIPANTS)
    return "\n".join(rows) + "\n" + legend


def ascii_flow():
    L = lambda i: C.node_label(C.FLOW_NODES, i)
    arrow = "   |\n   v"
    out = []
    out.append("( %s )" % L("S"))
    out.append(arrow)
    out.append("[ %s ]" % L("P1"))
    out.append(arrow)
    out.append("[ %s ]" % L("P2"))
    out.append(arrow)
    out.append("< %s > --Yes--> [ %s ] --> (出力更新へ)" % (L("D1"), L("F1")))
    out.append("   | No")
    out.append("   v")
    out.append("[ %s ]" % L("P3"))
    out.append(arrow)
    out.append("< %s > --No--> [ %s ] --> (出力更新へ)" % (L("D2"), L("P4")))
    out.append("   | Yes")
    out.append("   v")
    out.append("[ %s ]" % L("P5"))
    out.append(arrow)
    out.append("< %s > --Yes--> [ %s ] --> (出力更新へ)" % (L("D3"), L("P6")))
    out.append("   | No")
    out.append("   v")
    out.append("[ %s ]" % L("P7"))
    out.append(arrow)
    out.append("[ %s ]   <-- フェールセーフ/制御停止/介入抑制 から合流" % L("P8"))
    out.append(arrow)
    out.append("[ %s ]" % L("P9"))
    out.append(arrow)
    out.append("( %s )" % L("E"))
    return "\n".join(out)


def render_txt():
    o = []
    o.append("=" * 70)
    o.append(C.DOC["title"])
    o.append("=" * 70)
    for k, v in _meta_lines():
        o.append("%s: %s" % (k, v))
    o.append("")
    o.append("概要: " + C.DOC["abstract"])
    o.append("")

    def section(num):
        n, head, paras = next(s for s in C.SECTIONS if s[0] == num)
        o.append("")
        o.append("%s %s" % (n, head))
        o.append("-" * 60)
        for p in paras:
            o.append(p)

    def figure(caption, art):
        o.append("")
        o.append("[%s]" % caption)
        o.append(art)

    section("1")
    figure(C.FIG_BLOCK, ascii_block())
    section("2")
    section("3")
    figure(C.FIG_STATE, ascii_state())
    section("4")
    figure(C.FIG_SEQ, ascii_sequence())
    section("5")
    figure(C.FIG_FLOW, ascii_flow())
    section("6")
    section("7")
    o.append("")
    o.append("[%s]" % C.PARAM_TABLE_CAPTION)
    o.append(plain_table(C.PARAM_TABLE_HEADER, C.PARAM_TABLE_ROWS))
    o.append("")
    o.append("[%s]" % C.IF_TABLE_CAPTION)
    o.append(plain_table(C.IF_TABLE_HEADER, C.IF_TABLE_ROWS))
    o.append("")
    o.append("[%s]" % C.FIG_CAP1)
    o.append("[画像: %s]" % C.CAPTURE1)
    o.append("")
    o.append("[%s]" % C.FIG_CAP2)
    o.append("[画像: %s]" % C.CAPTURE2)
    o.append("")
    text = "\n".join(o)
    with open(os.path.join(SAMPLES, "spec_lkas.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


# ==========================================================================
# .md  (mermaid figures, Markdown tables, image references)
# ==========================================================================
def mermaid_block():
    o = ["flowchart LR"]
    for nid, label in C.BLOCK_NODES:
        o.append('    %s["%s"]' % (nid, label))
    for (src, dst, lab) in C.BLOCK_EDGES:
        o.append("    %s -->|%s| %s" % (src, lab, dst))
    return "\n".join(o)


def mermaid_state():
    o = ["stateDiagram-v2", "    [*] --> %s" % C.STATE_INITIAL]
    for (src, dst, lab) in C.STATE_TRANSITIONS:
        o.append("    %s --> %s: %s" % (src, dst, lab))
    return "\n".join(o)


def mermaid_sequence():
    o = ["sequenceDiagram"]
    for pid, label in C.SEQ_PARTICIPANTS:
        o.append("    participant %s as %s" % (pid, label))
    for (src, dst, lab) in C.SEQ_MESSAGES:
        o.append("    %s->>%s: %s" % (src, dst, lab))
    return "\n".join(o)


def mermaid_flow():
    shape = {"start": ("([", "])"), "end": ("([", "])"),
             "process": ("[", "]"), "decision": ("{", "}")}
    o = ["flowchart TD"]
    for (nid, kind, label) in C.FLOW_NODES:
        a, b = shape[kind]
        o.append('    %s%s"%s"%s' % (nid, a, label, b))
    for (src, dst, lab) in C.FLOW_EDGES:
        if lab:
            o.append("    %s -->|%s| %s" % (src, lab, dst))
        else:
            o.append("    %s --> %s" % (src, dst))
    return "\n".join(o)


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |"]
    out.append("| " + " | ".join("---" for _ in header) + " |")
    for r in rows:
        cells = [str(c).replace("|", "\\|") for c in r]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def render_md():
    o = []
    o.append("# " + C.DOC["title"])
    o.append("")
    o.append(" / ".join("**%s:** %s" % (k, v) for k, v in _meta_lines()))
    o.append("")
    o.append("> " + C.DOC["abstract"])

    def section(num):
        n, head, paras = next(s for s in C.SECTIONS if s[0] == num)
        o.append("")
        o.append("## %s %s" % (n, head))
        for p in paras:
            o.append("")
            o.append(p)

    def mermaid(caption, code):
        o.append("")
        o.append("**%s**" % caption)
        o.append("")
        o.append("```mermaid")
        o.append(code)
        o.append("```")

    section("1")
    mermaid(C.FIG_BLOCK, mermaid_block())
    section("2")
    section("3")
    mermaid(C.FIG_STATE, mermaid_state())
    section("4")
    mermaid(C.FIG_SEQ, mermaid_sequence())
    section("5")
    mermaid(C.FIG_FLOW, mermaid_flow())
    section("6")
    section("7")
    o.append("")
    o.append("**%s**" % C.PARAM_TABLE_CAPTION)
    o.append("")
    o.append(md_table(C.PARAM_TABLE_HEADER, C.PARAM_TABLE_ROWS))
    o.append("")
    o.append("**%s**" % C.IF_TABLE_CAPTION)
    o.append("")
    o.append(md_table(C.IF_TABLE_HEADER, C.IF_TABLE_ROWS))
    o.append("")
    o.append("**%s**" % C.FIG_CAP1)
    o.append("")
    o.append("![%s](%s)" % (C.FIG_CAP1, C.CAPTURE1))
    o.append("")
    o.append("**%s**" % C.FIG_CAP2)
    o.append("")
    o.append("![%s](%s)" % (C.FIG_CAP2, C.CAPTURE2))
    o.append("")
    text = "\n".join(o)
    with open(os.path.join(SAMPLES, "spec_lkas.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


# ==========================================================================
# .html  (inline SVG figures, <table>, <img> references)
# ==========================================================================
def _svg_text(cx, cy, label, size=13, fill="#1b2330"):
    return ('<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
            'font-size="%d" fill="%s">%s</text>' % (cx, cy, size, fill, html_escape(label)))


def _svg_edge_label(pts, label):
    i = len(pts) // 2
    ax, ay = pts[i - 1]
    bx, by = pts[i]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    w = dwidth(label) * 7 + 6
    return ('<rect x="%.1f" y="%.1f" width="%d" height="16" fill="#ffffff" opacity="0.85"/>'
            % (mx - w / 2, my - 8, w) +
            _svg_text(mx, my, label, size=11, fill="#5a6675"))


def svg_diagram(g):
    W, H = g["size"]
    o = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" '
         'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">' % (W, H, W, H)]
    o.append('<defs><marker id="arr" markerWidth="10" markerHeight="8" refX="8" refY="3" '
             'orient="auto" markerUnits="strokeWidth">'
             '<path d="M0,0 L8,3 L0,6 Z" fill="#33415c"/></marker></defs>')
    o.append('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (W, H))
    for e in g["edges"]:
        pts = " ".join("%.1f,%.1f" % (x, y) for x, y in e["points"])
        dash = ' stroke-dasharray="5,4"' if e["dashed"] else ""
        mk = ' marker-end="url(#arr)"' if e["arrow"] else ""
        o.append('<polyline points="%s" fill="none" stroke="#33415c" stroke-width="1.5"%s%s/>'
                 % (pts, dash, mk))
    for s in g["shapes"]:
        x, y, w, h = s["x"], s["y"], s["w"], s["h"]
        cx, cy = x + w / 2.0, y + h / 2.0
        k = s["kind"]
        if k == "rect":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="#e8f0fe" stroke="#33415c" stroke-width="1.5"/>' % (x, y, w, h))
        elif k == "note":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="2" fill="#fff7e6" stroke="#b8860b" stroke-width="1.2"/>' % (x, y, w, h))
        elif k == "roundrect":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="12" fill="#e6f4ea" stroke="#1e7e34" stroke-width="1.5"/>' % (x, y, w, h))
        elif k == "stadium":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="#fde7e9" stroke="#b02a37" stroke-width="1.5"/>' % (x, y, w, h, h / 2.0))
        elif k == "diamond":
            o.append('<polygon points="%g,%g %g,%g %g,%g %g,%g" fill="#fff3cd" stroke="#b8860b" stroke-width="1.5"/>'
                     % (cx, y, x + w, cy, cx, y + h, x, cy))
        size = 12 if dwidth(s["label"]) > 16 else 13
        o.append(_svg_text(cx, cy, s["label"], size=size))
    for e in g["edges"]:
        if e["label"]:
            o.append(_svg_edge_label(e["points"], e["label"]))
    o.append("</svg>")
    return "\n".join(o)


def html_table(header, rows):
    o = ["<table>", "<thead><tr>"]
    o.append("".join("<th>%s</th>" % html_escape(h) for h in header))
    o.append("</tr></thead>", )
    o.append("<tbody>")
    for r in rows:
        o.append("<tr>" + "".join("<td>%s</td>" % html_escape(c) for c in r) + "</tr>")
    o.append("</tbody></table>")
    return "\n".join(o)


_HTML_CSS = """
body { font-family: "Segoe UI", "Hiragino Sans", "Meiryo", sans-serif; line-height: 1.7;
       max-width: 980px; margin: 24px auto; padding: 0 16px; color: #1b2330; }
h1 { border-bottom: 3px solid #33415c; padding-bottom: 6px; }
h2 { border-left: 6px solid #33415c; padding-left: 10px; margin-top: 32px; }
.meta { color: #5a6675; font-size: 0.9em; }
.abstract { background: #f3f6fb; border: 1px solid #d8e0ec; padding: 10px 14px; border-radius: 6px; }
figure { margin: 18px 0; }
figcaption { font-weight: bold; color: #33415c; margin-bottom: 6px; }
table { border-collapse: collapse; margin: 10px 0; font-size: 0.9em; }
th, td { border: 1px solid #b8c2d4; padding: 4px 8px; text-align: left; }
th { background: #e8f0fe; }
svg { border: 1px solid #e0e6f0; background: #fff; max-width: 100%; height: auto; }
img { border: 1px solid #c8d0de; max-width: 100%; }
"""


def render_html():
    o = ['<!DOCTYPE html>', '<html lang="ja">', "<head>", '<meta charset="utf-8">',
         "<title>%s</title>" % html_escape(C.DOC["title"]),
         "<style>%s</style>" % _HTML_CSS, "</head>", "<body>"]
    o.append("<h1>%s</h1>" % html_escape(C.DOC["title"]))
    o.append('<p class="meta">' + " / ".join("%s: %s" % (html_escape(k), html_escape(v))
                                              for k, v in _meta_lines()) + "</p>")
    o.append('<p class="abstract">%s</p>' % html_escape(C.DOC["abstract"]))

    def section(num):
        n, head, paras = next(s for s in C.SECTIONS if s[0] == num)
        o.append("<h2>%s %s</h2>" % (html_escape(n), html_escape(head)))
        for p in paras:
            o.append("<p>%s</p>" % html_escape(p))

    def figure_svg(caption, key):
        o.append("<figure>")
        o.append("<figcaption>%s</figcaption>" % html_escape(caption))
        o.append(svg_diagram(LY.ALL[key]()))
        o.append("</figure>")

    section("1")
    figure_svg(C.FIG_BLOCK, "block")
    section("2")
    section("3")
    figure_svg(C.FIG_STATE, "state")
    section("4")
    figure_svg(C.FIG_SEQ, "sequence")
    section("5")
    figure_svg(C.FIG_FLOW, "flow")
    section("6")
    section("7")
    o.append("<figure><figcaption>%s</figcaption>" % html_escape(C.PARAM_TABLE_CAPTION))
    o.append(html_table(C.PARAM_TABLE_HEADER, C.PARAM_TABLE_ROWS) + "</figure>")
    o.append("<figure><figcaption>%s</figcaption>" % html_escape(C.IF_TABLE_CAPTION))
    o.append(html_table(C.IF_TABLE_HEADER, C.IF_TABLE_ROWS) + "</figure>")
    o.append('<figure><figcaption>%s</figcaption><img src="%s" alt="%s"></figure>'
             % (html_escape(C.FIG_CAP1), C.CAPTURE1, html_escape(C.FIG_CAP1)))
    o.append('<figure><figcaption>%s</figcaption><img src="%s" alt="%s"></figure>'
             % (html_escape(C.FIG_CAP2), C.CAPTURE2, html_escape(C.FIG_CAP2)))
    o.append("</body></html>")
    text = "\n".join(o)
    with open(os.path.join(SAMPLES, "spec_lkas.html"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


# ==========================================================================
# .drawio  (mxGraph XML: native shapes/connectors + text cells + table grids)
# ==========================================================================
class _Ids:
    def __init__(self):
        self.n = 1

    def next(self):
        self.n += 1
        return "n%d" % self.n


_SHAPE_STYLE = {
    "rect": "rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#33415c;",
    "note": "shape=note;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#b8860b;",
    "roundrect": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#1e7e34;",
    "stadium": "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b02a37;",
    "diamond": "rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#b8860b;",
}


def _mx_vertex(idc, value, x, y, w, h, style):
    return ('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">'
            '<mxGeometry x="%g" y="%g" width="%g" height="%g" as="geometry"/></mxCell>'
            % (idc, xml_escape(value), style, x, y, w, h))


def _mx_edge(idc, value, points, style):
    src = points[0]
    dst = points[-1]
    way = points[1:-1]
    arr = ""
    if way:
        arr = "<Array as=\"points\">" + "".join(
            '<mxPoint x="%g" y="%g"/>' % (px, py) for px, py in way) + "</Array>"
    return ('<mxCell id="%s" value="%s" style="%s" edge="1" parent="1">'
            '<mxGeometry relative="1" as="geometry">'
            '<mxPoint x="%g" y="%g" as="sourcePoint"/>'
            '<mxPoint x="%g" y="%g" as="targetPoint"/>%s</mxGeometry></mxCell>'
            % (idc, xml_escape(value), style, src[0], src[1], dst[0], dst[1], arr))


def _diagram_cells(g, idc):
    cells = []
    for s in g["shapes"]:
        cells.append(_mx_vertex(idc.next(), s["label"], s["x"], s["y"], s["w"], s["h"],
                                _SHAPE_STYLE[s["kind"]]))
    for e in g["edges"]:
        style = "html=1;rounded=0;"
        style += "endArrow=none;" if not e["arrow"] else "endArrow=classic;"
        if e["dashed"]:
            style += "dashed=1;"
        cells.append(_mx_edge(idc.next(), e["label"], e["points"], style))
    return cells


def _text_cell(idc, value, x, y, w, h, bold=False):
    style = "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;"
    if bold:
        style += "fontStyle=1;"
    return _mx_vertex(idc, value, x, y, w, h, style)


def _table_grid(idc, caption, header, rows, col_w, x0=40, y0=40, rh=26):
    cells = [_text_cell(idc.next(), caption, x0, y0 - 26, sum(col_w), 22, bold=True)]
    xs = [x0]
    for w in col_w:
        xs.append(xs[-1] + w)
    grid = [header] + rows
    for ri, row in enumerate(grid):
        y = y0 + ri * rh
        head = (ri == 0)
        for ci, val in enumerate(row):
            style = ("rounded=0;whiteSpace=wrap;html=1;strokeColor=#b8c2d4;"
                     + ("fillColor=#dae8fc;fontStyle=1;" if head else "fillColor=#ffffff;"))
            cells.append(_mx_vertex(idc.next(), str(val), xs[ci], y, col_w[ci], rh, style))
    return cells, y0 + len(grid) * rh


def _page(name, cells):
    return ('<diagram name="%s">'
            '<mxGraphModel dx="900" dy="640" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" page="1" pageWidth="1169" pageHeight="826" math="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram>'
            % (xml_escape(name), "".join(cells)))


def render_drawio():
    idc = _Ids()
    pages = []

    # page 1: body text as stacked text cells
    cells = []
    y = 20
    cells.append(_text_cell(idc.next(), C.DOC["title"], 40, y, 760, 30, bold=True))
    y += 36
    cells.append(_text_cell(idc.next(), " / ".join("%s: %s" % kv for kv in _meta_lines()),
                            40, y, 760, 20))
    y += 26
    cells.append(_text_cell(idc.next(), "概要: " + C.DOC["abstract"], 40, y, 760, 50))
    y += 60
    for n, head, paras in C.SECTIONS:
        cells.append(_text_cell(idc.next(), "%s %s" % (n, head), 40, y, 760, 22, bold=True))
        y += 26
        for p in paras:
            h = max(24, ((dwidth(p) // 90) + 1) * 18 + 8)
            cells.append(_text_cell(idc.next(), p, 40, y, 760, h))
            y += h + 4
    pages.append(_page("本文", cells))

    # pages 2-5: diagrams
    for name, key in [(C.FIG_BLOCK, "block"), (C.FIG_STATE, "state"),
                      (C.FIG_SEQ, "sequence"), (C.FIG_FLOW, "flow")]:
        g = LY.ALL[key]()
        cells = [_text_cell(idc.next(), name, 20, 10, 700, 22, bold=True)]
        cells += _diagram_cells(g, idc)
        pages.append(_page(name, cells))

    # page 6: tables + capture references (path only, no embedding)
    cells = []
    c1, yend = _table_grid(idc, C.PARAM_TABLE_CAPTION, C.PARAM_TABLE_HEADER,
                           C.PARAM_TABLE_ROWS, [40, 170, 70, 70, 70, 300], x0=40, y0=60)
    cells += c1
    c2, yend2 = _table_grid(idc, C.IF_TABLE_CAPTION, C.IF_TABLE_HEADER, C.IF_TABLE_ROWS,
                            [36, 140, 44, 130, 70, 170, 90, 200], x0=40, y0=yend + 70)
    cells += c2
    yref = yend2 + 50
    cells.append(_text_cell(idc.next(), "%s  [画像参照: %s]" % (C.FIG_CAP1, C.CAPTURE1),
                            40, yref, 760, 24, bold=True))
    cells.append(_text_cell(idc.next(), "%s  [画像参照: %s]" % (C.FIG_CAP2, C.CAPTURE2),
                            40, yref + 30, 760, 24, bold=True))
    pages.append(_page("表と画面参照", cells))

    text = '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net">' \
           + "".join(pages) + "</mxfile>"
    with open(os.path.join(SAMPLES, "spec_lkas.drawio"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    os.makedirs(SAMPLES, exist_ok=True)
    for name, fn in [("txt", render_txt), ("md", render_md),
                     ("html", render_html), ("drawio", render_drawio)]:
        t = fn()
        print("%-7s %7d chars  %7d tokens" % (name, len(t), count_tokens(t)))
