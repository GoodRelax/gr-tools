"""table.py -- generate Markdown node/edge tables from a drawio-uml model (0.3.0).

Companion to draw.py: both read the same model JSON (the SSOT). draw.py renders
the diagram and ignores `description`/`remark`; table.py emits the documentation
tables (responsibilities and element lists) that would clutter the diagram, and
is the consumer of `description`/`remark`.

A node's cluster PATH is derived from the `layout` tree: the chain of NAMED
ancestor clusters from root to the node's leaf (nameless levels skipped), joined
with '/'. A node whose deepest named ancestor is an internal cluster takes that
cluster's path (e.g. a node directly under named `consider` -> "consider").

Usage:
    python table.py MODEL.json OUT.md [--cluster KEY | --view KEY]

--cluster KEY restricts to KEY and its subtree, matched at '/' segment boundaries
(a/b matches a/b and a/b/*, not a/bc); edges with EITHER endpoint in scope are
kept. --view KEY restricts to a named view (nodes plus the nodes under named
clusters) and keeps only INDUCED edges (both endpoints in scope). --cluster and
--view are mutually exclusive. Standard library only.
"""
import json
import sys


# ----------------------------------------------------------------- pure helpers
def escape_cell(value):
    """Escape a value for a Markdown table cell: `|` becomes `\\|`. `<br>` is
    passed through; real newlines are never emitted (FR-T-08)."""
    return str(value).replace("|", "\\|")


def common_prefix(paths):
    """Longest list of leading `/`-separated segments shared by every path."""
    if not paths:
        return []
    segmented = [p.split("/") for p in paths]
    prefix = []
    for group in zip(*segmented):
        if all(seg == group[0] for seg in group):
            prefix.append(group[0])
        else:
            break
    return prefix


def strip_prefix(path, prefix):
    """`path` with the leading `prefix` segments removed, rejoined with ' / '."""
    return " / ".join(path.split("/")[len(prefix):])


def in_subtree(path, key):
    """True when `path` equals `key` or sits under it at a segment boundary
    (in_subtree('a/b/c', 'a/b') True; in_subtree('a/bc', 'a/b') False; FR-T-06)."""
    return path == key or path.startswith(key + "/")


# ----------------------------------------------------- layout-tree path derivation
def node_paths(layout):
    """name -> cluster path (chain of NAMED ancestor clusters joined by '/').
    Nodes under no named cluster get '' (no cluster). (FR-T-04, FR-D-14)."""
    paths = {}

    def walk(cluster, chain):
        nm = cluster.get("name")
        chain2 = chain + [nm] if nm else chain
        if "nodes" in cluster:
            path = "/".join(chain2)
            for name in cluster["nodes"]:
                paths[name] = path
        else:
            for child in cluster.get("clusters", []):
                walk(child, chain2)

    if layout:
        walk(layout, [])
    return paths


def find_cluster(cluster, name):
    if cluster is None:
        return None
    if cluster.get("name") == name:
        return cluster
    if "nodes" not in cluster:
        for child in cluster.get("clusters", []):
            hit = find_cluster(child, name)
            if hit:
                return hit
    return None


def node_names_under(cluster):
    if cluster is None:
        return set()
    if "nodes" in cluster:
        return set(cluster["nodes"])
    out = set()
    for child in cluster.get("clusters", []):
        out |= node_names_under(child)
    return out


# ----------------------------------------------------------------- selection
def select_cluster(nodes, paths, key):
    """--cluster KEY: nodes whose derived path is in KEY's subtree. Nodes with no
    path (no named cluster) are excluded. key None -> every node."""
    if key is None:
        return list(nodes)
    return [n for n in nodes
            if paths.get(n["name"], "") and in_subtree(paths[n["name"]], key)]


def select_view(model, key):
    """--view KEY: the view's node set (view.nodes plus nodes under view.clusters).
    Fail fast on unknown view / node / cluster (FR-T-10a)."""
    views = model.get("views") or {}
    if key not in views:
        sys.exit("table: unknown --view %r (known: %s)" % (key, ", ".join(sorted(views)) or "none"))
    view = views[key]
    nodes = model.get("nodes") or []
    allnames = {n["name"] for n in nodes}
    layout = model.get("layout")
    selected = set(view.get("nodes", []))
    for cname in view.get("clusters", []):
        cl = find_cluster(layout, cname) if layout else None
        if cl is None:
            sys.exit("table: view %r references unknown cluster %r" % (key, cname))
        selected |= node_names_under(cl)
    unknown = selected - allnames
    if unknown:
        sys.exit("table: view %r references unknown node(s): %s" % (key, ", ".join(sorted(unknown))))
    return [n for n in nodes if n["name"] in selected]


def select_edges(edges, scope_names, mode):
    """mode 'all' -> every edge; 'cluster' -> either endpoint in scope (FR-T-07);
    'view' -> both endpoints in scope (induced subgraph; FR-T-10)."""
    if mode == "all":
        return list(edges)
    if mode == "view":
        return [e for e in edges
                if e.get("source") in scope_names and e.get("target") in scope_names]
    return [e for e in edges
            if e.get("source") in scope_names or e.get("target") in scope_names]


# ----------------------------------------------------------------- rendering
def node_table(nodes, paths):
    """Render the node table (FR-T-02). The `cluster` column shows each node's
    derived path with the common prefix removed; dropped entirely if all empty
    (FR-T-05)."""
    cluster_of = [paths.get(n["name"], "") for n in nodes]
    prefix = common_prefix([p for p in cluster_of if p])
    cluster_cells = [strip_prefix(p, prefix) if p else "" for p in cluster_of]
    drop_cluster = all(cell == "" for cell in cluster_cells)
    columns = ["name", "description", "remark"]
    if not drop_cluster:
        columns = ["cluster"] + columns
    lines = ["| " + " | ".join(columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for node, cell in zip(nodes, cluster_cells):
        cells = []
        if not drop_cluster:
            cells.append(escape_cell(cell))
        cells.append(escape_cell(node.get("name", "")))
        cells.append(escape_cell(node.get("description", "")))
        cells.append(escape_cell(node.get("remark", "")))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def edge_table(edges):
    """Render the edge table (FR-T-03). `arrow` is emitted as written (empty when
    unset); draw.py's unset->association default is NOT applied."""
    columns = ["arrow", "source", "target", "label", "description", "remark"]
    lines = ["| " + " | ".join(columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for edge in edges:
        cells = [escape_cell(edge.get(c, "")) for c in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------- assembly + IO
def validate(nodes, edges):
    """Fail fast on a missing required field (FR-T-09)."""
    for node in nodes:
        if "name" not in node:
            sys.exit("table: node is missing required 'name': %r" % (node,))
    for edge in edges:
        for field in ("source", "target"):
            if field not in edge:
                sys.exit("table: edge is missing required '%s': %r" % (field, edge))


def render(model, cluster_key, view_key):
    """Model -> a standalone Markdown document: an H1 title, then `## Nodes` and
    `## Edges` (FR-T-11). The H1 is the view's label under --view, else the model's
    required `title`."""
    nodes = model.get("nodes") or []
    edges = model.get("edges") or []
    validate(nodes, edges)
    title = model.get("title")
    if not title or not str(title).strip():               # FR-T-11a
        sys.exit("table: model is missing required non-empty 'title'")
    paths = node_paths(model.get("layout"))
    if view_key is not None:
        scope_nodes = select_view(model, view_key)
        mode = "view"
        view = (model.get("views") or {})[view_key]       # exists (select_view checked)
        h1 = view.get("label") or view_key                # FR-T-11: --view -> view label
    elif cluster_key is not None:
        scope_nodes = select_cluster(nodes, paths, cluster_key)
        if not scope_nodes:
            print("table: warning: --cluster %r matched no node" % cluster_key,
                  file=sys.stderr)                        # FR-T-06a
        mode = "cluster"
        h1 = title
    else:
        scope_nodes = list(nodes)
        mode = "all"
        h1 = title
    scope_names = {n["name"] for n in scope_nodes}
    scope_edges = select_edges(edges, scope_names, mode)
    h1_line = " ".join(str(h1).splitlines())              # raw, but force a single line
    return "\n".join([
        "# " + h1_line, "",
        "## Nodes", "", node_table(scope_nodes, paths), "",
        "## Edges", "", edge_table(scope_edges), "",
    ])


def main():
    args = sys.argv[1:]
    cluster_key = view_key = None
    for flag in ("--cluster", "--view"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print("usage: python table.py MODEL.json OUT.md [--cluster KEY | --view KEY]",
                      file=sys.stderr)
                sys.exit(2)
            value = args[i + 1]
            del args[i:i + 2]
            if flag == "--cluster":
                cluster_key = value
            else:
                view_key = value
    if cluster_key is not None and view_key is not None:    # FR-T-10a
        sys.exit("table: --cluster and --view are mutually exclusive")
    if len(args) != 2:
        print("usage: python table.py MODEL.json OUT.md [--cluster KEY | --view KEY]",
              file=sys.stderr)
        sys.exit(2)
    try:
        with open(args[0], encoding="utf-8") as fh:
            model = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.exit("table: cannot read model: %s" % exc)      # FR-C-03
    output = render(model, cluster_key, view_key)
    with open(args[1], "w", encoding="utf-8") as fh:
        fh.write(output)
    # report counts actually written
    nodes, edges = model.get("nodes") or [], model.get("edges") or []
    paths = node_paths(model.get("layout"))
    if view_key is not None:
        sn = select_view(model, view_key)
        se = select_edges(edges, {n["name"] for n in sn}, "view")
    elif cluster_key is not None:
        sn = select_cluster(nodes, paths, cluster_key)
        se = select_edges(edges, {n["name"] for n in sn}, "cluster")
    else:
        sn, se = nodes, edges
    print("wrote %s (%d nodes, %d edges)" % (args[1], len(sn), len(se)))


if __name__ == "__main__":
    main()
