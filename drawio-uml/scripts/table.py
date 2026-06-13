"""table.py -- generate Markdown node/edge tables from a drawio-uml model.

Companion to draw.py: both read the same model JSON (the SSOT). draw.py renders
the diagram and ignores `description`/`remark`; table.py emits the documentation
tables (responsibilities and element lists) that would clutter the diagram, and
is the consumer of `description`/`remark`.

Usage:
    python table.py MODEL.json OUT.md [--cluster KEY]

--cluster KEY restricts the tables to KEY and its subtree, matched at `/` segment
boundaries (a/b matches a/b and a/b/*, not a/bc). Standard library only.
"""
import json
import sys


# ----------------------------------------------------------------- pure helpers
def escape_cell(value):
    """Escape a value for a Markdown table cell: `|` becomes `\\|`. `<br>` is
    passed through (callers use it for in-cell line breaks); real newlines are
    never emitted (FR-T-08)."""
    return str(value).replace("|", "\\|")


def common_prefix(paths):
    """Longest list of leading `/`-separated segments shared by every path.

    ["a/b/c", "a/b/d"] -> ["a", "b"]; ["a/b", "x/y"] -> []; [] -> [].
    """
    if not paths:
        return []
    segmented = [p.split("/") for p in paths]
    prefix = []
    for group in zip(*segmented):          # zip stops at the shortest path
        if all(seg == group[0] for seg in group):
            prefix.append(group[0])
        else:
            break
    return prefix


def strip_prefix(path, prefix):
    """`path` with the leading `prefix` segments removed, rejoined with ' / '.
    strip_prefix("a/b/c", ["a", "b"]) -> "c"."""
    return " / ".join(path.split("/")[len(prefix):])


def in_subtree(cluster, key):
    """True when `cluster` equals `key` or sits under it at a segment boundary:
    in_subtree("a/b", "a/b") and in_subtree("a/b/c", "a/b") are True;
    in_subtree("a/bc", "a/b") is False (FR-T-06)."""
    return cluster == key or cluster.startswith(key + "/")


def select_nodes(nodes, key):
    """Nodes in scope. key is None -> every node. Otherwise the nodes whose
    `cluster` is in KEY's subtree; nodes without a `cluster` are excluded."""
    if key is None:
        return list(nodes)
    return [n for n in nodes
            if n.get("cluster") is not None and in_subtree(n["cluster"], key)]


def select_edges(edges, scope_names, filtering):
    """Edges in scope. When filtering (--cluster given), keep an edge if its
    source or target is among `scope_names`; otherwise keep every edge (FR-T-07)."""
    if not filtering:
        return list(edges)
    return [e for e in edges
            if e.get("source") in scope_names or e.get("target") in scope_names]


def node_table(nodes):
    """Render the node table (FR-T-02). The `cluster` column shows each node's
    cluster path with the common prefix removed; the prefix is computed over the
    nodes that have a cluster. If every cluster cell ends up empty, the column is
    dropped (FR-T-05)."""
    prefix = common_prefix([n["cluster"] for n in nodes if n.get("cluster")])
    cluster_cells = [strip_prefix(n["cluster"], prefix) if n.get("cluster") else ""
                     for n in nodes]
    drop_cluster = all(cell == "" for cell in cluster_cells)
    columns = ["name", "description", "remark"]
    if not drop_cluster:
        columns = ["cluster"] + columns
    lines = ["| " + " | ".join(columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for node, cluster_cell in zip(nodes, cluster_cells):
        cells = []
        if not drop_cluster:
            cells.append(escape_cell(cluster_cell))
        cells.append(escape_cell(node.get("name", "")))
        cells.append(escape_cell(node.get("description", "")))
        cells.append(escape_cell(node.get("remark", "")))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def edge_table(edges):
    """Render the edge table (FR-T-03). `arrow` is emitted as written in the
    model (empty when unset); draw.py's unset->association default is NOT applied."""
    columns = ["arrow", "source", "target", "label", "description", "remark"]
    lines = ["| " + " | ".join(columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for edge in edges:
        cells = [escape_cell(edge.get(c, "")) for c in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------- assembly + IO
def validate(nodes, edges):
    """Fail fast on a missing required field: node.name, edge.source,
    edge.target (FR-T-09)."""
    for node in nodes:
        if "name" not in node:
            sys.exit("table: node is missing required 'name': %r" % (node,))
    for edge in edges:
        for field in ("source", "target"):
            if field not in edge:
                sys.exit("table: edge is missing required '%s': %r" % (field, edge))


def render(model, cluster_key):
    """Model -> Markdown (a node-table section then an edge-table section)."""
    nodes = model.get("nodes") or []
    edges = model.get("edges") or []
    validate(nodes, edges)
    scope_nodes = select_nodes(nodes, cluster_key)
    if cluster_key is not None and not scope_nodes:
        print("table: warning: --cluster %r matched no node" % cluster_key,
              file=sys.stderr)                      # FR-T-06a
    scope_names = {n["name"] for n in scope_nodes}
    scope_edges = select_edges(edges, scope_names, cluster_key is not None)
    return "\n".join([
        "## Nodes", "", node_table(scope_nodes), "",
        "## Edges", "", edge_table(scope_edges), "",
    ])


def main():
    args = sys.argv[1:]
    cluster_key = None
    if "--cluster" in args:
        i = args.index("--cluster")
        if i + 1 >= len(args):
            print("usage: python table.py MODEL.json OUT.md [--cluster KEY]",
                  file=sys.stderr)
            sys.exit(2)
        cluster_key = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        print("usage: python table.py MODEL.json OUT.md [--cluster KEY]",
              file=sys.stderr)
        sys.exit(2)
    try:
        with open(args[0], encoding="utf-8") as fh:
            model = json.load(fh)
    except (OSError, ValueError) as exc:            # ValueError covers JSONDecodeError
        sys.exit("table: cannot read model: %s" % exc)        # FR-C-03
    output = render(model, cluster_key)
    with open(args[1], "w", encoding="utf-8") as fh:
        fh.write(output)
    shown_nodes = select_nodes(model.get("nodes") or [], cluster_key)
    shown_edges = select_edges(model.get("edges") or [],
                               {n["name"] for n in shown_nodes}, cluster_key is not None)
    print("wrote %s (%d nodes, %d edges)" % (args[1], len(shown_nodes), len(shown_edges)))


if __name__ == "__main__":
    main()
