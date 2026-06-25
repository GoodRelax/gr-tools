# -*- coding: utf-8 -*-
"""Diagram -> relationship-table data.

openpyxl (.xlsx) and python-docx (.docx) have no public autoshape/connector API,
so in those formats each diagram is represented by its native table primitive
(styled cells / Word tables) carrying the same nodes + edges + labels.
.pptx draws the same diagrams with real autoshapes instead.
Returns (title, header, rows) tuples. The note line is appended where useful.
"""
import content as C


def block_table():
    bl = lambda nid: C.node_label(C.BLOCK_NODES, nid)
    rows = [[bl(s), lab, bl(d)] for (s, d, lab) in C.BLOCK_EDGES]
    return (C.FIG_BLOCK, ["源", "信号", "宛先"], rows)


def state_table():
    rows = [[s, lab, d] for (s, d, lab) in C.STATE_TRANSITIONS]
    return (C.FIG_STATE + " (初期状態: %s)" % C.STATE_INITIAL,
            ["遷移元", "遷移条件", "遷移先"], rows)


def sequence_table():
    lab = {pid: l for pid, l in C.SEQ_PARTICIPANTS}
    rows = [[str(i + 1), lab[s], lab[d], m] for i, (s, d, m) in enumerate(C.SEQ_MESSAGES)]
    return (C.FIG_SEQ, ["No", "送信元", "宛先", "メッセージ"], rows)


def flow_node_table():
    kindjp = {"start": "開始", "end": "終了", "process": "処理", "decision": "判断"}
    rows = [[nid, kindjp[k], lbl] for (nid, k, lbl) in C.FLOW_NODES]
    return (C.FIG_FLOW + " (ノード)", ["ID", "種別", "内容"], rows)


def flow_edge_table():
    rows = [[s, (lab or "-"), d] for (s, d, lab) in C.FLOW_EDGES]
    return (C.FIG_FLOW + " (遷移)", ["From", "条件", "To"], rows)


def diagram_tables():
    """All diagram tables in document order (each: (title, header, rows))."""
    return {
        "block": [block_table()],
        "state": [state_table()],
        "sequence": [sequence_table()],
        "flow": [flow_node_table(), flow_edge_table()],
    }
