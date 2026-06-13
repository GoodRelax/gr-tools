"""Unit + acceptance tests for table.py (spec Chapter 5, scenarios SC-101..107).
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
        self.assertEqual(table.common_prefix(["a/b/c", "a/b"]), ["a", "b"])

    def test_escape_cell(self):
        self.assertEqual(table.escape_cell("x|y"), "x\\|y")
        self.assertEqual(table.escape_cell("a<br>b"), "a<br>b")
        self.assertEqual(table.escape_cell(3), "3")

    def test_in_subtree(self):
        self.assertTrue(table.in_subtree("a/b", "a/b"))
        self.assertTrue(table.in_subtree("a/b/c", "a/b"))
        self.assertTrue(table.in_subtree("a/b", "a"))
        self.assertFalse(table.in_subtree("a/bc", "a/b"))
        self.assertFalse(table.in_subtree("a", "a/b"))

    def test_strip_prefix(self):
        self.assertEqual(table.strip_prefix("a/b/c", ["a", "b"]), "c")
        self.assertEqual(table.strip_prefix("a/b", ["a", "b"]), "")
        self.assertEqual(table.strip_prefix("a/b/c", []), "a / b / c")  # prefix empty -> full path, " / " joined

    def test_select_nodes(self):
        nodes = [{"name": "X", "cluster": "a/b"}, {"name": "Y", "cluster": "a/bc"},
                 {"name": "Z", "cluster": "a/b/c"}, {"name": "W"}]
        self.assertEqual([n["name"] for n in table.select_nodes(nodes, "a/b")], ["X", "Z"])
        self.assertEqual(len(table.select_nodes(nodes, None)), 4)

    def test_select_edges(self):
        edges = [{"source": "X", "target": "P"}, {"source": "Q", "target": "R"}]
        self.assertEqual(table.select_edges(edges, {"X"}, True), [{"source": "X", "target": "P"}])
        self.assertEqual(len(table.select_edges(edges, {"X"}, False)), 2)


class Acceptance(unittest.TestCase):
    def test_sc101_columns_and_prefix(self):              # FR-T-01/02/04
        m = {"nodes": [{"name": "A", "cluster": "x/core", "description": "d1"},
                       {"name": "B", "cluster": "x/infra"}], "edges": []}
        out = table.render(m, None)
        self.assertIn("| cluster | name | description | remark |", out)
        self.assertIn("| core | A | d1 |  |", out)        # prefix "x" removed
        self.assertIn("| infra | B |  |  |", out)

    def test_sc102_cluster_column_dropped(self):          # FR-T-05
        m = {"nodes": [{"name": "A", "cluster": "only"}, {"name": "B", "cluster": "only"}], "edges": []}
        node_sec = table.render(m, None).split("#### Edges")[0]
        self.assertIn("| name | description | remark |", node_sec)
        self.assertNotIn("cluster", node_sec)

    def test_sc103_edge_and_cluster_filter(self):         # FR-T-03/06/07
        m = {"nodes": [{"name": "A", "cluster": "a/b"}, {"name": "C", "cluster": "a/bc"},
                       {"name": "D", "cluster": "a/b/x"}],
             "edges": [{"source": "A", "target": "C", "arrow": "dependency"},
                       {"source": "C", "target": "Zz"}]}
        out = table.render(m, "a/b")
        node_sec, edge_sec = out.split("#### Edges")
        self.assertIn("| A |", node_sec)
        self.assertIn("| D |", node_sec)
        self.assertNotIn("| C |", node_sec)               # a/bc not in a/b subtree
        self.assertIn("dependency", edge_sec)             # A in scope -> kept
        self.assertNotIn("Zz", edge_sec)                  # C->Zz, neither in scope

    def test_sc104_escape_and_br(self):                   # FR-T-08
        m = {"nodes": [{"name": "A", "description": "x|y<br>z"}], "edges": []}
        self.assertIn("x\\|y<br>z", table.render(m, None))

    def test_sc107_unset_arrow_empty(self):               # FR-T-03
        m = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": [{"source": "A", "target": "B"}]}
        edge_sec = table.render(m, None).split("#### Edges")[1]
        self.assertIn("|  | A | B |  |  |  |", edge_sec)   # empty arrow cell


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
        r, _ = self._run({"nodes": [{"name": "A", "cluster": "a"}], "edges": []}, ("--cluster", "zzz"))
        self.assertEqual(r.returncode, 0)
        self.assertIn("warning", r.stderr.lower())

    def test_sc106_missing_required_nonzero(self):        # FR-T-09
        r, _ = self._run({"nodes": [{"name": "A"}], "edges": [{"target": "A"}]})  # source missing
        self.assertNotEqual(r.returncode, 0)

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
