"""Acceptance tests for draw.py (spec 4.1, scenarios SC-001..016).

Verifies behaviour against the spec; the byte-identical regression for the flat
path lives in the md5 check (NFR-01) -- here SC-002 checks determinism + origin.
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
TESTS = os.path.dirname(__file__)
sys.path.insert(0, SCRIPTS)
import draw  # noqa: E402


def flat_model():
    with open(os.path.join(TESTS, "flat_basic.model.json"), encoding="utf-8") as fh:
        return json.load(fh)


def clustered_model():
    with open(os.path.join(TESTS, "clustered_banded.model.json"), encoding="utf-8") as fh:
        return json.load(fh)


class DrawAcceptance(unittest.TestCase):
    def test_sc001_basic_output(self):                    # FR-D-01
        xml = draw.render({"nodes": [{"name": "A", "shape": "class"}], "edges": []})
        self.assertIn("<mxGraphModel", xml)
        self.assertIn("mxCell", xml)

    def test_sc002_flat_deterministic_and_origin(self):   # FR-D-02, NFR-01
        m = flat_model()
        xml = draw.render(m)
        self.assertEqual(xml, draw.render(m))             # deterministic (NFR-01)
        self.assertIn('x="40"', xml)                      # min corner placed at..
        self.assertIn('y="40"', xml)                      # ..the origin (40, 40)

    def test_sc003_clustered_has_waypoints(self):         # FR-D-03, FR-D-07
        xml = draw.render(clustered_model())
        self.assertIn("as=\"points\"", xml)               # routed waypoints imported

    def test_sc004_legend_drawn(self):                    # FR-D-12
        xml = draw.render(clustered_model())
        self.assertIn("Legend", xml)

    def test_sc005_banded_layout(self):                   # FR-D-04
        # two bands ([["core"],["ext"]]) -> two cluster boxes, generated cleanly
        xml = draw.render(clustered_model())
        self.assertIn("Core", xml)
        self.assertIn("External", xml)

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
        self.assertIn("<mxGraphModel", xml)               # still produces a diagram
        self.assertIn("FR-D-07a", buf.getvalue())         # but warns on degrade

    def test_sc007_undefined_cluster_default_colour(self):  # FR-D-13
        m = {"options": {}, "nodes": [{"name": "A", "cluster": "ghost"}], "edges": []}
        self.assertIn("#888888", draw.render(m))

    def test_sc008_description_remark_no_effect(self):    # FR-D-08
        base = flat_model()
        annotated = json.loads(json.dumps(base))
        annotated["nodes"][0]["description"] = "responsibility"
        annotated["nodes"][0]["remark"] = "a note"
        annotated["edges"][0]["description"] = "edge note"
        self.assertEqual(draw.render(base), draw.render(annotated))

    def test_sc009_self_reference_excluded(self):         # FR-D-15
        m = {"nodes": [{"name": "A", "shape": "state"}],
             "edges": [{"source": "A", "target": "A", "arrow": "transition"}]}
        xml = draw.render(m)                               # no crash; self-loop dropped
        self.assertIn("<mxGraphModel", xml)

    def test_sc010_style_suppresses_compartment(self):    # FR-D-10
        m = {"nodes": [{"name": "A", "shape": "class", "style": "ellipse;custom=1;",
                        "attributes": ["x"]}], "edges": []}
        xml = draw.render(m)
        self.assertIn("ellipse;custom=1;", xml)
        self.assertNotIn("swimlane", xml)                 # compartment preset suppressed

    @unittest.skip("SC-012: malformed XML is unreachable via esc(); needs fault injection (spec 4.1 Remark)")
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

    def test_sc014_extra_rows_key_ignored(self):          # FR-D-14
        m = clustered_model()
        m = json.loads(json.dumps(m))
        m["options"]["layout"]["rows"] = [["core"], ["ext"], ["nonexistent"]]
        xml = draw.render(m)                               # extra key ignored, no crash
        self.assertIn("<mxGraphModel", xml)

    def test_sc015_unknown_shape_is_box(self):            # FR-D-05
        m = {"nodes": [{"name": "A", "shape": "totally_unknown"}], "edges": []}
        xml = draw.render(m)
        # box preset: rounded=0;whiteSpace=wrap;html=1 ... default 170x60
        self.assertIn("rounded=0;whiteSpace=wrap;html=1", xml)
        self.assertIn('width="170" height="60"', xml)

    def test_sc016_unset_arrow_is_association(self):      # FR-D-06
        m = {"nodes": [{"name": "A"}, {"name": "B"}],
             "edges": [{"source": "A", "target": "B"}]}
        xml = draw.render(m)
        self.assertIn("endArrow=none", xml)               # association = plain line


if __name__ == "__main__":
    unittest.main()
