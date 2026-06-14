#!/usr/bin/env python3
"""PoC: render a drawio-uml state-machine model through NATIVE Graphviz clusters
(ONE dot run; the flow is laid out by dot's layered ranker, composite states are
`subgraph cluster_*`) instead of the production A2 path (independent leaf runs +
Python stacking + pinned routing).

Goal: does dot-native composite-state layout read better / more compact than the
tall single-column A2 result? Also probe whether we can extract node positions +
cluster boxes + edge routes for a .drawio rebuild (run with -Tjson separately).

Usage: python sm_to_dot.py MODEL.json OUT.dot
"""
import json
import re
import sys


def nid(n):
    return "n_" + re.sub(r"[^0-9A-Za-z_]", "_", n)


def cidn(n):
    return "cluster_" + re.sub(r"[^0-9A-Za-z_]", "_", n)


def dq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_leaf(c):
    return "nodes" in c


def main():
    model = json.load(open(sys.argv[1], encoding="utf-8"))
    nodemap = {n["name"]: n for n in model["nodes"]}

    entry, exit_, member, cstyle = {}, {}, {}, {}

    def walk(c, anc):
        me = c["name"] if ("label" in c and c.get("name")) else anc
        names = []
        if is_leaf(c):
            for nm in c["nodes"]:
                member[nm] = me
                names.append(nm)
        else:
            for ch in c["clusters"]:
                names += walk(ch, me)
        if "label" in c and c.get("name"):
            inits = [x for x in names if nodemap[x].get("shape") == "initial"]
            states = [x for x in names if nodemap[x].get("shape") not in ("initial", "final")]
            entry[c["name"]] = (inits or states or names)[0]
            exit_[c["name"]] = (states or names)[-1]
            cstyle[c["name"]] = (c.get("color", "#999999"), c.get("fill", "#FFFFFF"), c["label"])
        return names

    walk(model["layout"], None)

    def node_decl(node):
        sh = node.get("shape")
        i = nid(node["name"])
        if sh == "initial":
            return '%s [shape=circle,width=0.2,height=0.2,fixedsize=true,style=filled,fillcolor="#333333",label=""];' % i
        if sh == "final":
            return '%s [shape=doublecircle,width=0.22,height=0.22,fixedsize=true,style=filled,fillcolor="#333333",label=""];' % i
        fill = cstyle.get(member.get(node["name"]), (None, "#F0F0FF", None))[1]
        return '%s [shape=box,style="rounded,filled",fillcolor=%s,color="#6C6C8A",penwidth=1.2,label=%s];' % (
            i, dq(fill), dq(node["name"]))

    def emit(c, depth):
        pad = "  " * (depth + 1)
        out = []
        labelled = "label" in c and c.get("name")
        if labelled:
            col, fill, lab = cstyle[c["name"]]
            out.append('%ssubgraph %s {' % (pad, cidn(c["name"])))
            out.append('%s  label=%s; labeljust=l; fontsize=11; style="rounded,filled"; color=%s; fillcolor=%s; penwidth=1.4;'
                       % (pad, dq(lab), dq(col), dq(_tint(fill))))
        if is_leaf(c):
            for nm in c["nodes"]:
                out.append(pad + "  " + node_decl(nodemap[nm]))
        else:
            for ch in c["clusters"]:
                out += emit(ch, depth + 1)
        if labelled:
            out.append(pad + "}")
        return out

    def _tint(hexc):  # lighten the cluster fill a touch so nested boxes stay distinct
        return hexc

    def anchor(name, head):
        """Resolve an edge endpoint to (node_id, lhead/ltail attr)."""
        if name in nodemap:
            return nid(name), None
        a = (entry if head else exit_)[name]
        return nid(a), ("lhead" if head else "ltail") + "=" + cidn(name)

    lines = ["digraph SM {",
             "  compound=true; rankdir=TB; nodesep=0.35; ranksep=0.5; splines=true;",
             '  graph [fontname="Helvetica"]; node [fontname="Helvetica",fontsize=11];'
             ' edge [fontname="Helvetica",fontsize=9,color="#444444"];']
    lines += emit(model["layout"], 0)
    for e in model.get("edges", []):
        s, sx = anchor(e["source"], head=False)
        t, tx = anchor(e["target"], head=True)
        attrs = []
        if e.get("label"):
            attrs.append("label=" + dq(e["label"]))
        if sx:
            attrs.append(sx)
        if tx:
            attrs.append(tx)
        if s == t:                       # dot drops trivial self-loops poorly; keep but minlen
            attrs.append("minlen=2")
        lines.append("  %s -> %s [%s];" % (s, t, ",".join(attrs)))
    lines.append("}")

    open(sys.argv[2], "w", encoding="utf-8").write("\n".join(lines))
    print("wrote %s" % sys.argv[2])


if __name__ == "__main__":
    main()
