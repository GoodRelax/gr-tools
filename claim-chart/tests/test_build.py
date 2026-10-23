#!/usr/bin/env python3
"""Tests for build.py: the samples build, and each broken input is refused.

Run:  python -I tests/test_build.py
Each negative case copies a sample into a temporary folder, breaks one thing,
and expects build.py to exit with 1 and to name the problem.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent   # claim-chart
BUILD = ROOT / "scripts" / "build.py"
SAMPLES = ROOT / "samples"
FIXTURE = ROOT / "tests" / "fixtures" / "src-XX0000001"  # a made-up claim with a NOT, a reference, an optional clause
SAMPLE = "src-US8046721"
FAILED = []


def run(out, *srcs):
    r = subprocess.run([sys.executable, "-I", str(BUILD), str(out), *map(str, srcs)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def check(name, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + name + ("" if ok else "\n      " + detail.strip().replace("\n", "\n      ")))
    if not ok:
        FAILED.append(name)


def broken(name, edit, expect):
    """Copy the sample (and the target files it cites), apply edit(folder), expect a refusal."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        src = tmp / SAMPLE
        shutil.copytree(SAMPLES / SAMPLE, src)
        shutil.copytree(SAMPLES / "target-sample", tmp / "target-sample")
        edit(src)
        code, out = run(tmp / "out.html", src)
        check(name, code == 1 and expect in out and not (tmp / "out.html").exists(), out)


def edit_json(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        code, out = run(pathlib.Path(tmp) / "us.html", SAMPLES / "src-US5946647", SAMPLES / "src-US8046721")
        check("the samples build", code == 0 and "every tree matches" in out, out)
        code, out = run(pathlib.Path(tmp) / "fx.html", FIXTURE)
        check("the made-up claim builds", code == 0, out)

    broken("a reworded leaf is refused",
           lambda s: edit_json(s / "tree.json", lambda d: d["claims"][1]["A"][2].update(L="the moving comprises any path.")),
           "tree text differs from the claim")
    broken("a dropped character in claims.txt is refused",
           lambda s: (s / "claims.txt").write_text((s / "claims.txt").read_text(encoding="utf-8").replace("touch-sensitive", "touch sensitive", 1), encoding="utf-8"),
           "tree text differs from the claim")
    broken("a reference to a later claim is refused",
           lambda s: edit_json(s / "tree.json", lambda d: d["claims"][1]["A"][0].update(R=3)),
           "not an earlier claim")
    broken("a translation that loses a hole is refused",
           lambda s: edit_json(s / "tr.ja.json", lambda d: d["nodes"].update({"1C": "動かすこと"})),
           "holes")
    broken("a translation with the wrong line count is refused",
           lambda s: edit_json(s / "tr.ja.json", lambda d: d["lines"]["1"].pop()),
           "lines for")
    broken("an AI quote that is not in the target is refused",
           lambda s: edit_json(s / "ai.json", lambda d: d["judgments"]["1B"]["evidence"][0].update(quote="鍵の絵を大きく出す。")),
           "quote not found")
    broken("an AI check on a node without wording is refused",
           lambda s: edit_json(s / "ai.json", lambda d: d["judgments"].update({"1C": {"check": "true"}})),
           "takes no check")
    broken("a NOT over two lists is refused",
           lambda s: edit_json(s / "tree.json", lambda d: d["claims"].__setitem__(1, {"A": [
               {"R": 1, "t": "The method of claim 1"}, ", wherein ",
               {"N": [{"A": [{"L": "the moving comprises movement along any desired path."}]},
                      {"A": [{"L": ""}]}]}]})),
           "a NOT must wrap exactly one plain list of leaves")

    print("\n%d failed" % len(FAILED) if FAILED else "\nall passed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
