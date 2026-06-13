"""Unit + acceptance tests for table.py 0.3.0 (spec Chapter 5, SC-101..109).
Run: python tests/test_table.py -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import table  # noqa: E402


class PureFunctions(unittest.TestCase):
    def test_common_prefix(self):
        self.assertEqual(table.common_prefix(["a/b/c", "a/b/d"]), ["a", "b"])
        self.assertEqual(table.common_prefix(["a/b", "x/y"]), [])
        self.assertEqual(table.common_prefix(["a/b"]), ["a", "b"])
        self.assertEqual(table.common_prefix([]), [])

    def test_escape_cell(self):
        self.assertEqual(table.escape_cell("x|y"), "x\\|y")
        self.assertEqual(table.escape_cell("a<br>b"), "a<br>b")
        self.assertEqual(table.escape_cell(3), "3")

    def test_in_subtree(self):
        self.assertTrue(table.in_subtree("a/b", "a/b"))
        self.assertTrue(table.in_subtree("a/b/c", "a/b"))
        self.assertFalse(table.in_subtree("a/bc", "a/b"))
        self.assertFalse(table.in_subtree("a", "a/b"))

    def test_strip_prefix(self):
        self.assertEqual(table.strip_prefix("a/b/c", ["a", "b"]), "c")
        self.assertEqual(table.strip_prefix("a/b", ["a", "b"]), "")
        self.assertEqual(table.strip_prefix("a/b/c", []), "a / b / c")

    def test_node_paths(self):
        # named-ancestor chain; nameless levels skipped; internal-cluster case
        layout = {"clusters": [
            {"name": "consider", "label": "C", "clusters": [
                {"nodes": ["Conception"]},                       # under named consider only
                {"direction": "row", "clusters": [
                    {"name": "world", "label": "W", "nodes": ["WorldModel"]}]}]}]}
        paths = table.node_paths(layout)
        self.assertEqual(paths["Conception"], "consider")        # deepest named = consider
        self.assertEqual(paths["WorldModel"], "consider/world")

    def test_select_cluster(self):
        nodes = [{"name": "X"}, {"name": "Y"}, {"name": "Z"}, {"name": "W"}]
        paths = {"X": "a/b", "Y": "a/bc", "Z": "a/b/c"}          # W has no path
        self.assertEqual([n["name"] for n in table.select_cluster(nodes, paths, "a/b")], ["X", "Z"])
        self.assertEqual(len(table.select_cluster(nodes, paths, None)), 4)

    def test_select_edges_modes(self):
        edges = [{"source": "X", "target": "P"}, {"source": "Q", "target": "R"}]
        self.assertEqual(table.select_edges(edges, {"X"}, "cluster"),
                         [{"source": "X", "target": "P"}])        # either endpoint
        self.assertEqual(table.select_edges(edges, {"X", "P"}, "view"),
                         [{"source": "X", "target": "P"}])        # both endpoints
        self.assertEqual(table.select_edges(edges, {"X"}, "view"), [])  # P missing -> excluded
        self.assertEqual(len(table.select_edges(edges, set(), "all")), 2)


def _clustered():
    return {"nodes": [{"name": "A", "description": "d1"}, {"name": "B"},
                      {"name": "C"}, {"name": "D"}],
            "edges": [{"source": "A", "target": "C", "arrow": "dependency"},
                      {"source": "C", "target": "Zz"}],
            "layout": {"name": "a", "label": "A", "clusters": [
                {"name": "b", "label": "B", "clusters": [
                    {"nodes": ["A"]},                            # a/b
                    {"name": "x", "label": "X", "nodes": ["D"]}]},  # a/b/x
                {"name": "bc", "label": "BC", "nodes": ["C"]}]},    # a/bc
            "views": {"v": {"label": "V", "nodes": ["A", "C"]}}}


class Acceptance(unittest.TestCase):
    def test_sc101_columns_and_prefix(self):              # FR-T-01/02/04
        m = {"nodes": [{"name": "A", "description": "d1"}, {"name": "B"}], "edges": [],
             "layout": {"name": "x", "label": "X", "clusters": [
                 {"name": "core", "label": "Core", "nodes": ["A"]},
                 {"name": "infra", "label": "Infra", "nodes": ["B"]}]}}
        out = table.render(m, None, None)
        self.assertIn("| cluster | name | description | remark |", out)
        self.assertIn("| core | A | d1 |  |", out)        # prefix "x" removed
        self.assertIn("| infra | B |  |  |", out)

    def test_sc102_cluster_column_dropped(self):          # FR-T-05
        m = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": []}   # no layout -> no paths
        node_sec = table.render(m, None, None).split("#### Edges")[0]
        self.assertIn("| name | description | remark |", node_sec)
        self.assertNotIn("cluster", node_sec)

    def test_sc103_cluster_filter(self):                  # FR-T-03/06/07
        out = table.render(_clustered(), "a/b", None)
        node_sec, edge_sec = out.split("#### Edges")
        self.assertIn("| A |", node_sec)
        self.assertIn("| D |", node_sec)
        self.assertNotIn("| C |", node_sec)               # a/bc not under a/b
        self.assertIn("dependency", edge_sec)             # A in scope -> A->C kept (either-end)
        self.assertNotIn("Zz", edge_sec)                  # C->Zz, neither in scope

    def test_sc104_escape_and_br(self):                   # FR-T-08
        m = {"nodes": [{"name": "A", "description": "x|y<br>z"}], "edges": []}
        self.assertIn("x\\|y<br>z", table.render(m, None, None))

    def test_sc107_unset_arrow_empty(self):               # FR-T-03
        m = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": [{"source": "A", "target": "B"}]}
        edge_sec = table.render(m, None, None).split("#### Edges")[1]
        self.assertIn("|  | A | B |  |  |  |", edge_sec)

    def test_sc108_view_induced(self):                    # FR-T-10
        out = table.render(_clustered(), None, "v")       # view v = nodes A, C
        node_sec, edge_sec = out.split("#### Edges")
        self.assertIn("| A |", node_sec)
        self.assertIn("| C |", node_sec)
        self.assertNotIn("| D |", node_sec)               # not in view
        self.assertIn("dependency", edge_sec)             # A->C induced (both in view)
        self.assertNotIn("Zz", edge_sec)                  # C->Zz, Zz not in view

    def test_undefined_edge_endpoint_ok(self):            # table tolerates undefined endpoints
        m = {"nodes": [{"name": "A"}], "edges": [{"source": "A", "target": "NOPE"}]}
        self.assertIn("NOPE", table.render(m, None, None))  # renders, no crash


class CLI(unittest.TestCase):
    def _run(self, model, extra=()):
        d = tempfile.mkdtemp()
        mp, op = os.path.join(d, "m.json"), os.path.join(d, "o.md")
        with open(mp, "w", encoding="utf-8") as fh:
            json.dump(model, fh)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "table.py"), mp, op, *extra],
                           capture_output=True, text=True)
        return r, op

    def test_sc105_no_match_warns(self):                  # FR-T-06a
        m = {"nodes": [{"name": "A"}], "edges": [],
             "layout": {"name": "a", "label": "A", "nodes": ["A"]}}
        r, _ = self._run(m, ("--cluster", "zzz"))
        self.assertEqual(r.returncode, 0)
        self.assertIn("warning", r.stderr.lower())

    def test_sc106_missing_required_nonzero(self):        # FR-T-09
        r, _ = self._run({"nodes": [{"name": "A"}], "edges": [{"target": "A"}]})
        self.assertNotEqual(r.returncode, 0)

    def test_sc109_view_cluster_exclusive(self):          # FR-T-10a
        r, _ = self._run(_clustered(), ("--cluster", "a/b", "--view", "v"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("exclusive", r.stderr.lower())

    def test_frc03_bad_json_nonzero(self):                # FR-C-03
        d = tempfile.mkdtemp()
        mp, op = os.path.join(d, "m.json"), os.path.join(d, "o.md")
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "table.py"), mp, op],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
