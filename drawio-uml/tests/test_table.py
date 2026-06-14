"""Unit + acceptance tests for table.py 0.4.0 (spec Chapter 5, SC-101..112).

0.4.0: the model has a REQUIRED top-level `title`; table emits a standalone doc
(`# <title>` then `## Nodes` / `## Edges`); under --view the H1 is the view label.
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
        layout = {"clusters": [
            {"name": "consider", "label": "C", "clusters": [
                {"nodes": ["Conception"]},
                {"direction": "row", "clusters": [
                    {"name": "world", "label": "W", "nodes": ["WorldModel"]}]}]}]}
        paths = table.node_paths(layout)
        self.assertEqual(paths["Conception"], "consider")
        self.assertEqual(paths["WorldModel"], "consider/world")

    def test_select_cluster(self):
        nodes = [{"name": "X"}, {"name": "Y"}, {"name": "Z"}, {"name": "W"}]
        paths = {"X": "a/b", "Y": "a/bc", "Z": "a/b/c"}
        self.assertEqual([n["name"] for n in table.select_cluster(nodes, paths, "a/b")], ["X", "Z"])
        self.assertEqual(len(table.select_cluster(nodes, paths, None)), 4)

    def test_select_edges_modes(self):
        edges = [{"source": "X", "target": "P"}, {"source": "Q", "target": "R"}]
        self.assertEqual(table.select_edges(edges, {"X"}, "cluster"),
                         [{"source": "X", "target": "P"}])
        self.assertEqual(table.select_edges(edges, {"X", "P"}, "view"),
                         [{"source": "X", "target": "P"}])
        self.assertEqual(table.select_edges(edges, {"X"}, "view"), [])
        self.assertEqual(len(table.select_edges(edges, set(), "all")), 2)


def _clustered():
    return {"title": "Clustered model",
            "nodes": [{"name": "A", "description": "d1"}, {"name": "B"},
                      {"name": "C"}, {"name": "D"}],
            "edges": [{"source": "A", "target": "C", "arrow": "dependency"},
                      {"source": "C", "target": "Zz"}],
            "layout": {"name": "a", "label": "A", "clusters": [
                {"name": "b", "label": "B", "clusters": [
                    {"nodes": ["A"]},
                    {"name": "x", "label": "X", "nodes": ["D"]}]},
                {"name": "bc", "label": "BC", "nodes": ["C"]}]},
            "views": {"v": {"label": "View V", "nodes": ["A", "C"]}}}


class Acceptance(unittest.TestCase):
    def test_sc101_columns_and_prefix(self):              # FR-T-01/02/04
        m = {"title": "T", "nodes": [{"name": "A", "description": "d1"}, {"name": "B"}], "edges": [],
             "layout": {"name": "x", "label": "X", "clusters": [
                 {"name": "core", "label": "Core", "nodes": ["A"]},
                 {"name": "infra", "label": "Infra", "nodes": ["B"]}]}}
        out = table.render(m, None, None)
        self.assertIn("| cluster | name | description | remark |", out)
        self.assertIn("| core | A | d1 |  |", out)
        self.assertIn("| infra | B |  |  |", out)

    def test_sc102_cluster_column_dropped(self):          # FR-T-05
        m = {"title": "T", "nodes": [{"name": "A"}, {"name": "B"}], "edges": []}  # no layout -> no paths
        node_sec = table.render(m, None, None).split("## Edges")[0]
        self.assertIn("| name | description | remark |", node_sec)
        self.assertNotIn("| cluster |", node_sec)

    def test_sc103_cluster_filter(self):                  # FR-T-03/06/07
        out = table.render(_clustered(), "a/b", None)
        node_sec, edge_sec = out.split("## Edges")
        self.assertIn("| A |", node_sec)
        self.assertIn("| D |", node_sec)
        self.assertNotIn("| C |", node_sec)
        self.assertIn("dependency", edge_sec)
        self.assertNotIn("Zz", edge_sec)

    def test_sc104_escape_and_br(self):                   # FR-T-08
        m = {"title": "T", "nodes": [{"name": "A", "description": "x|y<br>z"}], "edges": []}
        self.assertIn("x\\|y<br>z", table.render(m, None, None))

    def test_sc107_unset_arrow_empty(self):               # FR-T-03
        m = {"title": "T", "nodes": [{"name": "A"}, {"name": "B"}],
             "edges": [{"source": "A", "target": "B"}]}
        edge_sec = table.render(m, None, None).split("## Edges")[1]
        self.assertIn("|  | A | B |  |  |  |", edge_sec)

    def test_sc108_view_induced(self):                    # FR-T-10
        out = table.render(_clustered(), None, "v")
        node_sec, edge_sec = out.split("## Edges")
        self.assertIn("| A |", node_sec)
        self.assertIn("| C |", node_sec)
        self.assertNotIn("| D |", node_sec)
        self.assertIn("dependency", edge_sec)
        self.assertNotIn("Zz", edge_sec)

    def test_sc110_title_h1_standalone(self):             # FR-T-11
        m = {"title": "My Doc", "nodes": [{"name": "A"}], "edges": []}
        out = table.render(m, None, None)
        self.assertTrue(out.startswith("# My Doc\n"))     # H1 first line
        self.assertIn("## Nodes", out)
        self.assertIn("## Edges", out)
        self.assertNotIn("####", out)                     # no legacy H4

    def test_sc111_view_label_is_h1(self):                # FR-T-11
        out = table.render(_clustered(), None, "v")
        self.assertTrue(out.startswith("# View V\n"))     # H1 = view label, not model title
        self.assertIn("## Nodes", out)

    def test_sc112_missing_title_fails(self):             # FR-T-11a
        self.assertRaises(SystemExit, table.render,
                          {"nodes": [{"name": "A"}], "edges": []}, None, None)
        self.assertRaises(SystemExit, table.render,        # empty title
                          {"title": "", "nodes": [{"name": "A"}], "edges": []}, None, None)
        self.assertRaises(SystemExit, table.render,        # whitespace-only title
                          {"title": "  ", "nodes": [{"name": "A"}], "edges": []}, None, None)

    def test_title_edge_cases(self):                      # FR-T-11 hardening (code review)
        # multi-line title collapses to a single H1 line (no stray body line)
        out = table.render({"title": "a\nb", "nodes": [{"name": "A"}], "edges": []}, None, None)
        self.assertTrue(out.startswith("# a b\n"))
        self.assertNotIn("\nb\n", out)
        # --cluster keeps the MODEL title as H1 (not a cluster name)
        self.assertTrue(table.render(_clustered(), "a/b", None).startswith("# Clustered model\n"))
        # a view WITHOUT an explicit label uses the view key as H1
        m = {"title": "T", "nodes": [{"name": "A"}], "edges": [],
             "views": {"plain": {"nodes": ["A"]}}}
        self.assertTrue(table.render(m, None, "plain").startswith("# plain\n"))

    def test_sc113_clusters_section(self):                # FR-T-12
        m = {"title": "T", "nodes": [{"name": "A"}, {"name": "B"}], "edges": [],
             "layout": {"direction": "column", "clusters": [
                 {"name": "up", "label": "Up", "description": "upper layer", "remark": "see X", "nodes": ["A"]},
                 {"name": "lo", "label": "Lo", "nodes": ["B"]}]}}
        out = table.render(m, None, None)
        self.assertIn("## Clusters", out)
        self.assertIn("| cluster | label | description | remark |", out)
        self.assertIn("| up | Up | upper layer | see X |", out)
        self.assertTrue(out.index("## Edges") < out.index("## Clusters"))   # section order

    def test_sc113_flat_model_no_clusters_section(self):  # FR-T-12 (omit when none)
        m = {"title": "T", "nodes": [{"name": "A"}], "edges": []}
        self.assertNotIn("## Clusters", table.render(m, None, None))

    def test_validate_layout_duplicate_name_fails(self):  # cluster integrity (table side)
        m = {"title": "T", "nodes": [{"name": "A"}, {"name": "B"}], "edges": [],
             "layout": {"clusters": [{"name": "d", "label": "1", "nodes": ["A"]},
                                     {"name": "d", "label": "2", "nodes": ["B"]}]}}
        self.assertRaises(SystemExit, table.render, m, None, None)


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
        m = {"title": "T", "nodes": [{"name": "A"}], "edges": [],
             "layout": {"name": "a", "label": "A", "nodes": ["A"]}}
        r, _ = self._run(m, ("--cluster", "zzz"))
        self.assertEqual(r.returncode, 0)
        self.assertIn("warning", r.stderr.lower())

    def test_sc106_missing_required_nonzero(self):        # FR-T-09
        r, _ = self._run({"title": "T", "nodes": [{"name": "A"}], "edges": [{"target": "A"}]})
        self.assertNotEqual(r.returncode, 0)

    def test_sc109_view_cluster_exclusive(self):          # FR-T-10a
        r, _ = self._run(_clustered(), ("--cluster", "a/b", "--view", "v"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("exclusive", r.stderr.lower())

    def test_sc112_missing_title_cli_nonzero(self):       # FR-T-11a (CLI)
        r, _ = self._run({"nodes": [{"name": "A"}], "edges": []})  # no title
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("title", r.stderr.lower())

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
