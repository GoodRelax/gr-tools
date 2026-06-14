"""Acceptance tests for draw.py 0.6.0 (spec 4.1, scenarios SC-001..032).

Models are built inline in the 0.6.0 format (recursive `layout` cluster tree +
`views`; direction TB/LR; options.engine dot|cluster-dot). Requires Graphviz
`dot` (and `neato`/`fdp` for the cluster-dot routing pass).
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
        "layout": {"direction": "TB", "clusters": [
            {"direction": "LR", "clusters": [
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


def cluster_edge_model():
    """Two stacked labelled clusters with a cluster->cluster 'depends on' edge."""
    return {"nodes": [{"name": "N1", "shape": "box"}, {"name": "N2", "shape": "box"}],
            "edges": [{"source": "lower", "target": "upper", "arrow": "dependency", "label": "depends on"}],
            "layout": {"direction": "TB", "clusters": [
                {"name": "upper", "label": "Upper", "color": "#B36200", "nodes": ["N1"]},
                {"name": "lower", "label": "Lower", "color": "#2E8B57", "nodes": ["N2"]}]}}


def dot_model():
    """A composite state machine for the dot engine: a labelled cluster, ordinary
    transitions, a cluster-endpoint transition (i->grp, grp->C) and a node
    self-loop (B->B). engine='dot' + direction TB (FR-D-19)."""
    return {"title": "SM",
            "options": {"engine": "dot", "direction": "TB"},
            "nodes": [{"name": "i", "shape": "initial"},
                      {"name": "A", "shape": "state"},
                      {"name": "B", "shape": "state"},
                      {"name": "C", "shape": "state"}],
            "edges": [{"source": "i", "target": "grp", "arrow": "transition"},
                      {"source": "A", "target": "B", "arrow": "transition"},
                      {"source": "B", "target": "B", "arrow": "transition", "label": "self"},
                      {"source": "grp", "target": "C", "arrow": "transition", "label": "done"}],
            "layout": {"clusters": [
                {"nodes": ["i"]},
                {"name": "grp", "label": "Group", "color": "#2F8FA8", "fill": "#E8F4F7",
                 "nodes": ["A", "B"]},
                {"nodes": ["C"]}]}}


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

    def test_sc005_tb_lr_tree(self):                      # FR-D-03
        # core | infra arranged left-to-right (LR) -> core's box left of infra's box
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
        cluster = {"direction": "TB", "nodes": ["P", "Q"]}
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

    # ---- 0.5.0: cluster-endpoint edges + long-name fix (SC-021..026) ----
    def test_sc021_cluster_endpoint_edge_anchored_routed(self):   # FR-D-17, FR-D-07
        xml = draw.render(cluster_edge_model())
        self.assertIn('source="cluster_lower" target="cluster_upper"', xml)
        self.assertIn('as="points"', xml)                 # box-avoiding waypoints

    def test_sc022_node_to_cluster_edge(self):            # FR-D-17
        m = cluster_edge_model()
        m["edges"] = [{"source": "N2", "target": "upper", "arrow": "dependency"}]
        self.assertIn('source="n_N2" target="cluster_upper"', draw.render(m))

    def test_sc023_ambiguous_endpoint_fails(self):        # FR-D-17
        m = {"nodes": [{"name": "dup"}, {"name": "N"}],
             "edges": [{"source": "dup", "target": "N"}],
             "layout": {"clusters": [{"name": "dup", "label": "D", "nodes": ["dup"]},
                                     {"name": "e", "label": "E", "nodes": ["N"]}]}}
        self.assertRaises(SystemExit, draw.render, m)

    def test_sc024_unlabelled_cluster_endpoint_fails(self):  # FR-D-17
        m = {"nodes": [{"name": "A"}, {"name": "B"}],
             "edges": [{"source": "grp", "target": "A"}],
             "layout": {"clusters": [{"name": "grp", "nodes": ["A", "B"]}]}}  # named, no label
        self.assertRaises(SystemExit, draw.render, m)

    def test_sc025_long_node_name_renders(self):          # FR-D-03b
        long = "X" + "_verylongnodename" * 15
        m = {"nodes": [{"name": long, "shape": "box"}, {"name": "Y", "shape": "box"}],
             "edges": [{"source": long, "target": "Y", "arrow": "dependency"}],
             "layout": {"name": "l", "label": "L", "nodes": [long, "Y"]}}
        self.assertIn("<mxGraphModel", draw.render(m))

    def test_sc026_view_drops_cluster_edge_when_endpoint_pruned(self):  # FR-D-16, FR-D-17
        m = cluster_edge_model()
        m["views"] = {"justupper": {"label": "U", "clusters": ["upper"]}}
        xml = draw.render(m, "justupper")
        self.assertNotIn("cluster_lower", xml)            # lower pruned away
        self.assertNotIn('target="cluster_upper"', xml)   # lower->upper edge dropped

    def test_degenerate_cluster_edge_not_routed(self):    # FR-D-17 (containment)
        m = cluster_edge_model()
        m["edges"] = [{"source": "N1", "target": "upper", "arrow": "dependency"}]  # N1 inside upper
        xml = draw.render(m)
        self.assertIn('source="n_N1" target="cluster_upper"', xml)  # cell emitted
        self.assertNotIn('as="points"', xml)              # but not routed

    def test_anon_box_id_no_collision_with_cid(self):     # box_cell id reservation
        m = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": [],
             "layout": {"direction": "TB", "clusters": [
                 {"label": "Anon band", "nodes": ["A"]},                # anonymous labelled box
                 {"name": "box_0", "label": "Named box_0", "nodes": ["B"]}]}}
        xml = draw.render(m)
        self.assertEqual(xml.count('id="cluster_box_0"'), 1)  # only the named cluster's box

    # ---- 0.6.0: layout engines + direction TB/LR (SC-027..032) ----
    def test_sc027_default_engine_is_cluster_dot(self):   # FR-D-18
        # engine omitted == engine "cluster-dot": same clustered output (boxes + routing)
        base = draw.render(clustered_model())
        m = clustered_model()
        m["options"] = {"engine": "cluster-dot"}
        self.assertEqual(base, draw.render(m))
        self.assertIn("cluster_core", base)               # clustered path drew the boxes

    def test_sc028_dot_engine_native_clusters(self):      # FR-D-18, FR-D-19
        xml = draw.render(dot_model())
        self.assertIn("<mxGraphModel", xml)
        self.assertIn('id="cluster_grp"', xml)            # composite box from dot bb (both engines draw boxes)
        self.assertIn('target="cluster_grp"', xml)        # cluster-endpoint transition -> box mxCell
        self.assertIn('as="points"', xml)                 # edge splines imported as waypoints
        self.assertIn("curved=1;", xml)                   # dot-only edge style (proves render_dot ran, not cluster-dot)

    def test_sc029_invalid_engine_fails(self):            # FR-D-18
        m = {"title": "T", "options": {"engine": "graphviz"},
             "nodes": [{"name": "A"}], "edges": []}
        self.assertRaises(SystemExit, draw.render, m)

    def test_sc030_invalid_direction_fails(self):         # FR-D-20
        opt_bad = {"nodes": [{"name": "A"}, {"name": "B"}], "edges": [],
                   "options": {"direction": "column"}}     # abolished value -> fail-fast
        self.assertRaises(SystemExit, draw.render, opt_bad)
        cl_bad = {"nodes": [{"name": "A"}], "edges": [],
                  "layout": {"direction": "sideways", "label": "X", "nodes": ["A"]}}
        self.assertRaises(SystemExit, draw.render, cl_bad)

    def test_sc031_dot_ignores_per_cluster_direction_warns(self):  # FR-D-20
        base = draw.render(dot_model())                   # no per-cluster direction
        m = dot_model()
        m["layout"]["clusters"][1]["direction"] = "LR"    # per-cluster direction under dot
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            xml = draw.render(m)
        self.assertIn("per-cluster direction", buf.getvalue())  # warned
        self.assertEqual(xml, base)                       # and truly ignored (byte-identical layout)

    def test_sc032_dot_draws_self_loop(self):             # FR-D-15, FR-D-19
        xml = draw.render(dot_model())                    # B->B is drawn WITH a loop spline
        cell = re.search(r'<mxCell id="edge\d+"[^>]*source="n_B" target="n_B".*?</mxCell>', xml)
        self.assertIsNotNone(cell)                        # cluster-dot would route no waypoints here
        self.assertIn('as="points"', cell.group(0))       # the self-loop carries dot's arc spline

    def test_dot_flat_no_layout(self):                    # FR-D-19 (layout-None branch)
        m = {"title": "T", "options": {"engine": "dot"},
             "nodes": [{"name": "A", "shape": "state"}, {"name": "B", "shape": "state"}],
             "edges": [{"source": "A", "target": "B", "arrow": "transition"}]}
        xml = draw.render(m)
        self.assertIn('id="n_A"', xml)
        self.assertIn("curved=1;", xml)                   # dot engine ran
        self.assertNotIn("cluster_", xml)                 # no boxes
        self.assertNotIn("Legend", xml)                   # no legend without labelled clusters

    def test_dot_view_pruned(self):                       # FR-D-16 x FR-D-19
        m = dot_model()
        m["views"] = {"justgrp": {"label": "G", "clusters": ["grp"]}}
        xml = draw.render(m, "justgrp")
        self.assertIn('id="cluster_grp"', xml)            # surviving cluster box under dot
        self.assertNotIn('id="n_C"', xml)                 # C pruned away

    def test_dot_anonymous_labelled_cluster(self):        # FR-D-19 (cluster_anon_<k> reservation)
        m = {"title": "T", "options": {"engine": "dot"},
             "nodes": [{"name": "A", "shape": "state"}, {"name": "B", "shape": "state"}],
             "edges": [{"source": "A", "target": "B", "arrow": "transition"}],
             "layout": {"clusters": [
                 {"label": "Anon", "nodes": ["A"]},                       # anonymous labelled -> anonbox_0
                 {"name": "anon_0", "label": "Named", "nodes": ["B"]}]}}   # claims cluster_anon_0 in dot
        xml = draw.render(m)
        self.assertIn('id="anonbox_0"', xml)              # anonymous box drawn from its own bb
        self.assertIn('id="cluster_anon_0"', xml)         # named cluster's box (cid), no clash

    def test_dot_generalization_reversed(self):           # FR-D-06 x FR-D-19 (spline reversal)
        m = {"title": "T", "options": {"engine": "dot"},
             "nodes": [{"name": "Base", "shape": "class"}, {"name": "Derived", "shape": "class"}],
             "edges": [{"source": "Derived", "target": "Base", "arrow": "generalization"}]}
        xml = draw.render(m)
        self.assertIn('source="n_Derived" target="n_Base"', xml)  # endpoints NOT swapped in the cell
        self.assertIn("endArrow=block;endFill=0;", xml)           # hollow triangle (at parent)

    def test_dot_per_cluster_direction_warns_once(self):  # FR-D-20 (aggregate, warn once)
        m = dot_model()
        m["layout"]["direction"] = "LR"                   # root declares direction
        m["layout"]["clusters"][1]["direction"] = "LR"    # and a child too
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            draw.render(m)
        self.assertEqual(buf.getvalue().count("per-cluster direction"), 1)  # one aggregated warning

    def test_dot_parallel_edges_distinct_routes(self):    # parallel edges keep distinct splines (no route collapse)
        m = {"title": "T", "options": {"engine": "dot"},
             "nodes": [{"name": "A", "shape": "state"}, {"name": "B", "shape": "state"}],
             "edges": [{"source": "A", "target": "B", "arrow": "transition", "label": "e1"},
                       {"source": "A", "target": "B", "arrow": "transition", "label": "e2"}]}
        arrs = re.findall(r'<Array as="points">(.*?)</Array>', draw.render(m))
        self.assertEqual(len(arrs), 2)                    # both routed
        self.assertEqual(len(set(arrs)), 2)               # with DISTINCT waypoints

    def test_dot_empty_cluster_endpoint_fails(self):      # hardening: empty labelled cluster endpoint
        m = {"title": "T", "options": {"engine": "dot"},
             "nodes": [{"name": "A"}],
             "edges": [{"source": "A", "target": "E", "arrow": "transition"}],
             "layout": {"clusters": [{"nodes": ["A"]},
                                     {"name": "E", "label": "E", "nodes": []}]}}
        self.assertRaises(SystemExit, draw.render, m)     # fail-fast, not KeyError


if __name__ == "__main__":
    unittest.main()
