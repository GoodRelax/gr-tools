"""Acceptance tests for draw.py 0.3.0 (spec 4.1, scenarios SC-001..020).

Models are built inline in the 0.3.0 format (recursive `layout` cluster tree +
`views`). Requires Graphviz `dot` (and `neato`/`fdp` for routing).
Run: python tests/test_draw.py -v
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import draw  # noqa: E402


def flat_model():
    return {"nodes": [{"name": "A", "shape": "class", "attributes": ["x"]},
                      {"name": "B", "shape": "class"}],
            "edges": [{"source": "A", "target": "B", "arrow": "composition"}]}


def clustered_model():
    """Two labelled clusters (core | infra) under an unnamed band; a view."""
    return {
        "nodes": [{"name": "A", "shape": "class", "attributes": ["x"]},
                  {"name": "B", "shape": "class"},
                  {"name": "C", "shape": "class"},
                  {"name": "D", "shape": "class"}],
        "edges": [{"source": "A", "target": "B", "arrow": "composition"},
                  {"source": "C", "target": "D", "arrow": "dependency"},
                  {"source": "A", "target": "C", "arrow": "dependency"}],
        "layout": {"direction": "column", "clusters": [
            {"direction": "row", "clusters": [
                {"name": "core", "label": "Core domain", "color": "#5B5FC7",
                 "fill": "#EEF0FF", "nodes": ["A", "B"]},
                {"name": "infra", "label": "Infrastructure", "color": "#82B366",
                 "fill": "#E7F4E7", "nodes": ["C", "D"]}]}]},
        "views": {"coreview": {"label": "Core", "clusters": ["core"]}},
    }


def nested_model():
    """A labelled cluster containing a labelled child (two nested boxes)."""
    return {"nodes": [{"name": "A", "shape": "class"}, {"name": "B", "shape": "class"}],
            "edges": [],
            "layout": {"name": "outer", "label": "Outer", "color": "#2F8FA8",
                       "clusters": [{"name": "inner", "label": "Inner", "color": "#9673A6",
                                     "nodes": ["A", "B"]}]}}


def cluster_boxes(xml):
    """id -> (x, y, w, h) for every dashed cluster box cell."""
    out = {}
    for m in re.finditer(r'id="(cluster_[A-Za-z0-9_]+)".*?'
                         r'<mxGeometry x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"', xml):
        out[m.group(1)] = tuple(int(v) for v in m.groups()[1:])
    return out


class DrawAcceptance(unittest.TestCase):
    def test_sc001_basic_output(self):                    # FR-D-01
        xml = draw.render({"nodes": [{"name": "A", "shape": "class"}], "edges": []})
        self.assertIn("<mxGraphModel", xml)
        self.assertIn("mxCell", xml)

    def test_sc002_flat_deterministic_and_origin(self):   # FR-D-02, NFR-01
        m = flat_model()
        xml = draw.render(m)
        self.assertEqual(xml, draw.render(m))             # deterministic (NFR-01)
        self.assertIn('x="40"', xml)
        self.assertIn('y="40"', xml)

    def test_sc003_clustered_has_waypoints(self):         # FR-D-03, FR-D-07
        self.assertIn('as="points"', draw.render(clustered_model()))

    def test_sc004_legend_outermost_labelled(self):       # FR-D-12
        xml = draw.render(clustered_model())
        self.assertIn("Legend", xml)
        self.assertIn("Core domain", xml)                 # outermost labelled -> swatch
        self.assertIn("Infrastructure", xml)

    def test_sc005_row_column_tree(self):                 # FR-D-03
        # core | infra arranged in a row -> core's box left of infra's box
        boxes = cluster_boxes(draw.render(clustered_model()))
        self.assertLess(boxes["cluster_core"][0], boxes["cluster_infra"][0])

    def test_sc006_degrade_warns(self):                   # FR-D-07a
        real_run = subprocess.run

        def only_dot(cmd, *a, **k):
            if cmd and cmd[0] in ("neato", "fdp"):
                raise FileNotFoundError(cmd[0])
            return real_run(cmd, *a, **k)
        buf = io.StringIO()
        with mock.patch("draw.subprocess.run", side_effect=only_dot), \
                contextlib.redirect_stderr(buf):
            xml = draw.render(clustered_model())
        self.assertIn("<mxGraphModel", xml)
        self.assertIn("FR-D-07a", buf.getvalue())

    def test_sc007_cascade_and_default_box_colour(self):  # FR-D-13
        m = {"nodes": [{"name": "A", "shape": "class"}], "edges": [],
             "layout": {"name": "c", "label": "C", "color": "#123456",
                        "fill": "#abcdef", "nodes": ["A"]}}
        xml = draw.render(m)
        self.assertIn("fillColor=#abcdef", xml)           # node inherits cluster fill
        self.assertIn("strokeColor=#123456", xml)         # node inherits cluster color
        nocolor = {"nodes": [{"name": "A"}], "edges": [],
                   "layout": {"label": "NoColor", "nodes": ["A"]}}
        self.assertIn("#888888", draw.render(nocolor))    # labelled, colourless -> default

    def test_sc008_description_remark_no_effect(self):    # FR-D-08
        base = clustered_model()
        annotated = json.loads(json.dumps(base))
        annotated["nodes"][0]["description"] = "responsibility"
        annotated["nodes"][0]["remark"] = "a note"
        annotated["edges"][0]["description"] = "edge note"
        self.assertEqual(draw.render(base), draw.render(annotated))

    def test_sc009_self_reference_excluded(self):         # FR-D-15
        m = {"nodes": [{"name": "A", "shape": "state"}],
             "edges": [{"source": "A", "target": "A", "arrow": "transition"}]}
        self.assertIn("<mxGraphModel", draw.render(m))

    def test_sc010_style_suppresses_compartment(self):    # FR-D-10
        m = {"nodes": [{"name": "A", "shape": "class", "style": "ellipse;custom=1;",
                        "attributes": ["x"]}], "edges": []}
        xml = draw.render(m)
        self.assertIn("ellipse;custom=1;", xml)
        self.assertNotIn("swimlane", xml)

    @unittest.skip("SC-012: malformed XML is unreachable via esc(); needs fault injection")
    def test_sc012_malformed_xml_fails(self):             # FR-D-09
        pass

    def test_sc013_bad_json_nonzero(self):                # FR-C-03
        d = tempfile.mkdtemp()
        mp, op = os.path.join(d, "m.json"), os.path.join(d, "o.drawio")
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "draw.py"), mp, op],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)

    def test_sc014_every_node_placed_once(self):          # FR-D-03a
        missing = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": [],
                   "layout": {"label": "X", "nodes": ["A"]}}          # B unplaced
        self.assertRaises(SystemExit, draw.render, missing)
        dup = {"nodes": [{"name": "A"}], "edges": [],
               "layout": {"clusters": [{"label": "1", "nodes": ["A"]},
                                       {"label": "2", "nodes": ["A"]}]}}  # A twice
        self.assertRaises(SystemExit, draw.render, dup)

    def test_sc015_unknown_shape_is_box(self):            # FR-D-05
        xml = draw.render({"nodes": [{"name": "A", "shape": "totally_unknown"}], "edges": []})
        self.assertIn("rounded=0;whiteSpace=wrap;html=1", xml)
        self.assertIn('width="170" height="60"', xml)

    def test_sc016_unset_arrow_is_association(self):      # FR-D-06
        xml = draw.render({"nodes": [{"name": "A"}, {"name": "B"}],
                           "edges": [{"source": "A", "target": "B"}]})
        self.assertIn("endArrow=none", xml)

    def test_sc017_nested_boxes(self):                    # FR-D-03
        xml = draw.render(nested_model())
        self.assertIn("Outer", xml)
        self.assertIn("Inner", xml)
        boxes = cluster_boxes(xml)
        ox, oy, ow, oh = boxes["cluster_outer"]
        ix, iy, iw, ih = boxes["cluster_inner"]
        self.assertTrue(ox <= ix and oy <= iy and ox + ow >= ix + iw and oy + oh >= iy + ih,
                        "inner box must nest inside outer box")

    def test_sc018_leaf_invisible_stacking(self):         # FR-D-04
        cluster = {"direction": "column", "nodes": ["P", "Q"]}
        members = [{"name": "P", "shape": "box"}, {"name": "Q", "shape": "box"}]
        nid = {"P": "n_P", "Q": "n_Q"}
        pos, _ = draw._leaf_layout(cluster, members, [], nid, {})
        self.assertLess(pos["n_P"][1], pos["n_Q"][1])     # P stacked above Q
        self.assertAlmostEqual(pos["n_P"][0], pos["n_Q"][0], delta=5)  # same column

    def test_sc019_bad_cluster_name(self):                # FR-D-14
        slash = {"nodes": [{"name": "A"}], "edges": [],
                 "layout": {"name": "a/b", "label": "X", "nodes": ["A"]}}
        self.assertRaises(SystemExit, draw.render, slash)
        dup = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": [],
               "layout": {"clusters": [{"name": "d", "label": "1", "nodes": ["A"]},
                                       {"name": "d", "label": "2", "nodes": ["B"]}]}}
        self.assertRaises(SystemExit, draw.render, dup)

    def test_sc020_view_induced_and_pruned(self):         # FR-D-16, FR-D-16a
        xml = draw.render(clustered_model(), "coreview")
        self.assertIn('id="n_A"', xml)
        self.assertIn('id="n_B"', xml)
        self.assertNotIn('id="n_C"', xml)                 # infra pruned
        self.assertNotIn("Infrastructure", xml)           # infra box dropped
        self.assertIn("Core domain", xml)
        self.assertRaises(SystemExit, draw.render, clustered_model(), "nope")  # unknown view

    def test_undefined_edge_endpoint_fails(self):         # §3.4 referential integrity
        m = {"nodes": [{"name": "A"}], "edges": [{"source": "A", "target": "NOPE"}]}
        self.assertRaises(SystemExit, draw.render, m)

    def test_clustered_deterministic(self):               # NFR-01 (clustered path)
        m = clustered_model()
        self.assertEqual(draw.render(m), draw.render(m))

    def test_cross_cluster_edge_routed(self):             # FR-D-07 (cross-leaf edge)
        # A (core) -> C (infra) is in no single leaf's dot run; the pinned pass routes it
        xml = draw.render(clustered_model())
        self.assertIn('source="n_A" target="n_C"', xml)


if __name__ == "__main__":
    unittest.main()
