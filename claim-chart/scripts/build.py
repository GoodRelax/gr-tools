#!/usr/bin/env python3
"""Build a single-file, interactive claim chart from verbatim patent claims.

Usage:
    python -I scripts/build.py OUT.html SRC_DIR [SRC_DIR ...]

One SRC_DIR per patent. The build runs these steps for each and stops at the
first problem, writing nothing:

  1. read      claims.txt, meta.json, tree.json, the summary files named in
               meta.json, and the optional tr.<lang>.json and ai.json
  2. verify    every claim tree, joined back in order, equals its claim text
               character for character (nothing may be reworded)
  3. annotate  every node gets a label (1A, 1B.2, ...) and its span [s, e)
               in the claim text
  4. explain   a leaf under a NOT gets an "i.e." sentence: the negation with
               only that leaf filled in
  5. check     translations keep the [label] holes of the original; every AI
               evidence quote occurs in its file (its line number is computed
               here, never taken from the AI)
  6. write     everything is embedded as JSON in template.html

The file formats are described in DESIGN.md and in schema/.
"""

import copy
import datetime
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent          # claim-chart/scripts
TEMPLATE = HERE / "template.html"
RESULT_SCHEMA = HERE.parent / "schema" / "claim-chart-result.schema.json"

# A claim header line: JP "【請求項" + digits + "】" (fullwidth or ASCII digits), or US "1."
JP_HEADER = re.compile("^【請求項[０-９0-9]+】$")
US_HEADER = re.compile(r"^\d+\.\s*$")
# A hole that stands for a child in a translation, e.g. "［1C.1］"
HOLE = re.compile("［([^［］]+)］")
CHECK_VALUES = {"true": "T", "false": "F", "tbd": "U"}


class BuildError(Exception):
    """A problem in the input; the message says which file and what."""


# ---------------------------------------------------------------- reading

def read_text(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def read_json(path):
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as e:
        raise BuildError("%s: not valid JSON (%s)" % (path, e))


def split_claims(text, where):
    """Return [(header, body)] in order; the body excludes the header line."""
    claims = []
    for line in text.rstrip().split("\n"):
        if JP_HEADER.match(line) or US_HEADER.match(line):
            claims.append((line, []))
        elif claims:
            claims[-1][1].append(line)
        else:
            raise BuildError("%s: text before the first claim header" % where)
    return [(header, "\n".join(lines)) for header, lines in claims]


def expand(x, where):
    """Turn the short JSON form of a node into the full form used everywhere else.

    "text"                 glue: claim text that is not a condition by itself
    {"L": "text"}          leaf, checked by a person
    {"P": "text"}          optional clause ("... may ..."), always true
    {"R": n, "t": "text"}  reference to claim n; mirrors that claim's verdict
    {"A"|"O"|"N": [...]}   AND / OR / NOT over its parts, with optional
                           "own": true (its own wording is a condition too) and
                           "alt": true (the scope reads two ways; AND/OR switchable)
    """
    if isinstance(x, str):
        return x
    if not isinstance(x, dict):
        raise BuildError("%s: a node must be a string or an object, got %r" % (where, x))
    if "L" in x:
        return {"k": "leaf", "parts": [x["L"]]}
    if "P" in x:
        return {"k": "opt", "parts": [x["P"]]}
    if "R" in x:
        return {"k": "ref", "ref": x["R"], "parts": [x["t"]]}
    for short, kind in (("A", "and"), ("O", "or"), ("N", "not")):
        if short in x:
            node = {"k": kind, "parts": [expand(p, where) for p in x[short]]}
            if kind != "not":
                node["own"] = bool(x.get("own"))
                node["alt"] = bool(x.get("alt"))
            return node
    raise BuildError("%s: unknown node %r" % (where, x))


# ---------------------------------------------------------------- tree helpers

def kids(node):
    return [p for p in node["parts"] if not isinstance(p, str)]


def walk(node):
    yield node
    for k in kids(node):
        yield from walk(k)


def flatten(node):
    return "".join(p if isinstance(p, str) else flatten(p) for p in node["parts"])


def letters(i):
    return chr(ord("A") + i) if i < 26 else "Z" + str(i - 25)


# ---------------------------------------------------------------- verify / annotate

def verify_text(tree, body, where):
    joined = flatten(tree)
    if joined == body:
        return
    i = next((i for i, (a, b) in enumerate(zip(joined, body)) if a != b), min(len(joined), len(body)))
    raise BuildError("%s: tree text differs from the claim at char %d\n  claim: %r\n  tree : %r"
                     % (where, i, body[max(0, i - 20):i + 40], joined[max(0, i - 20):i + 40]))


def verify_shape(tree, n, where):
    for node in walk(tree):
        if node["k"] == "ref" and not 1 <= node["ref"] < n:
            raise BuildError("%s: refers to claim %d, which is not an earlier claim" % (where, node["ref"]))
        if node["k"] == "not":
            # De Morgan is exact only when the negation wraps one plain list of leaves
            ks = kids(node)
            ok = (len(ks) == 1 and ks[0]["k"] in ("and", "or") and not ks[0]["own"] and not ks[0]["alt"]
                  and all(k["k"] == "leaf" for k in kids(ks[0])))
            if not ok:
                raise BuildError("%s: a NOT must wrap exactly one plain list of leaves" % where)


def annotate(node, label, start):
    """Label the node (claim "1", elements "1A", deeper "1A.1") and record its span."""
    node["id"] = node["label"] = label
    node["s"] = pos = start
    child = 0
    for part in node["parts"]:
        if isinstance(part, str):
            pos += len(part)
            continue
        sub = label + letters(child) if label.isdigit() else label + "." + str(child + 1)
        child += 1
        pos = annotate(part, sub, pos)
    node["e"] = pos
    return pos


def explain_negations(tree, lang):
    """Give each leaf under a NOT its "i.e." sentence, e.g. "tool protocol" ->
    "does not depend on a specific tool protocol": the NOT's wording with only
    this leaf of its list filled in. Mechanical only - nothing is reworded."""
    joiner = " " if lang == "en" else ""
    for neg in walk(tree):
        if neg["k"] != "not":
            continue
        lst = kids(neg)[0]
        before_list = "".join(p for p in neg["parts"][:neg["parts"].index(lst)])
        after_list = "".join(p for p in neg["parts"][neg["parts"].index(lst) + 1:])
        idx = [i for i, p in enumerate(lst["parts"]) if not isinstance(p, str)]
        list_prefix = "".join(lst["parts"][:idx[0]])
        list_suffix = "".join(lst["parts"][idx[-1] + 1:])
        for leaf in kids(lst):
            s = before_list + list_prefix + leaf["parts"][0] + list_suffix + after_list
            leaf["ie"] = re.sub(r"\n[  ]*", joiner, s)


# ---------------------------------------------------------------- optional inputs

def load_summary(src, meta):
    """Summary sections (problem / solution / effect): first line is the heading."""
    out = []
    for item in meta.get("summary", []):
        heading, _, rest = read_text(src / item["file"]).rstrip().partition("\n")
        out.append({"role": item["role"], "heading": heading, "text": rest})
    return out


def load_translations(src, claims, summary):
    """tr.<lang>.json: {"nodes": {id: text}, "lines": {n: [...]}, "summary": {role: [heading, para...]}}."""
    nodes = {n["id"]: n for c in claims for n in walk(c["tree"])}
    langs = []
    for path in sorted(src.glob("tr.*.json")):
        lang = path.name.split(".")[1]
        tr = read_json(path)
        for node_id, text in tr.get("nodes", {}).items():
            node = nodes.get(node_id)
            if node is None:
                raise BuildError("%s: no node %s" % (path, node_id))
            want = sorted(k["label"] for k in kids(node))
            if sorted(HOLE.findall(text)) != want:
                raise BuildError("%s: node %s: holes %s, expected %s" % (path, node_id, sorted(HOLE.findall(text)), want))
            node.setdefault("tr", {})[lang] = text
        for n, lines in tr.get("lines", {}).items():
            claim = claims[int(n) - 1]
            count = len(claim["body"].split("\n"))
            if len(lines) != count:
                raise BuildError("%s: claim %s: %d lines for %d" % (path, n, len(lines), count))
            claim.setdefault("trLines", {})[lang] = lines
        for sec in summary:
            paras = tr.get("summary", {}).get(sec["role"])
            if paras is None:
                continue
            count = len(sec["text"].split("\n")) + 1
            if len(paras) != count:
                raise BuildError("%s: summary %s: %d entries for %d (heading + paragraphs)" % (path, sec["role"], len(paras), count))
            sec.setdefault("tr", {})[lang] = paras
        langs.append(lang)
        print("  %s: %s translation checked (%d nodes)" % (src.name, lang, len(tr.get("nodes", {}))))
    return langs


def load_ai(src, claims):
    """ai.json: AI provisional checks, each with evidence quoted from the target files."""
    path = src / "ai.json"
    if not path.exists():
        return None
    ai = read_json(path)
    base = (src / ai.get("base", ".")).resolve()
    nodes = {n["id"]: n for c in claims for n in walk(c["tree"])}
    squash = lambda s: re.sub(r"\s+", "", s)
    files = {}
    judgments = {}
    for node_id, j in ai["judgments"].items():
        node = nodes.get(node_id)
        if node is None:
            raise BuildError("%s: no node %s" % (path, node_id))
        if not (node["k"] == "leaf" or node.get("own")):
            raise BuildError("%s: node %s takes no check" % (path, node_id))
        if j.get("check") not in CHECK_VALUES:
            raise BuildError("%s: node %s: check must be true, false or tbd" % (path, node_id))
        evidence = []
        for ev in j.get("evidence", []):
            if ev["file"] not in files:
                files[ev["file"]] = read_text(base / ev["file"]).split("\n")
            want = squash(ev["quote"])
            line = next((i + 1 for i, l in enumerate(files[ev["file"]]) if want in squash(l)), None)
            if line is None:
                raise BuildError("%s: node %s: quote not found in %s: %r" % (path, node_id, ev["file"], ev["quote"][:60]))
            evidence.append({"file": ev["file"], "line": line, "quote": ev["quote"]})
        judgments[node_id] = {"v": CHECK_VALUES[j["check"]], "reason": j.get("reason", ""), "evidence": evidence}
    print("  %s: %d AI judgments, every quote found in its file" % (src.name, len(judgments)))
    return {"target": ai.get("target", ""), "by": ai.get("by", ""), "date": ai.get("date", ""), "judgments": judgments}


# ---------------------------------------------------------------- one patent

def build_patent(src):
    meta = read_json(src / "meta.json")
    claims_text = split_claims(read_text(src / "claims.txt"), src / "claims.txt")
    trees = read_json(src / "tree.json")["claims"]
    if len(trees) != len(claims_text):
        raise BuildError("%s: %d trees for %d claims" % (src / "tree.json", len(trees), len(claims_text)))
    claims = []
    for n, ((header, body), short) in enumerate(zip(claims_text, trees), start=1):
        where = "%s claim %d" % (src.name, n)
        tree = expand(copy.deepcopy(short), where)
        verify_text(tree, body, where)
        verify_shape(tree, n, where)
        annotate(tree, str(n), 0)
        explain_negations(tree, meta.get("origLang", "ja"))
        claims.append({"n": n, "header": header, "body": body, "tree": tree})
    summary = load_summary(src, meta)
    patent = {k: v for k, v in meta.items() if k != "summary"}
    patent.update({"summaryList": summary, "claims": claims,
                   "trLangs": load_translations(src, claims, summary), "ai": load_ai(src, claims)})
    print("%s: %d claims, every tree matches its claim text" % (patent["id"], len(claims)))
    return patent


# ---------------------------------------------------------------- output

def embed(obj):
    # "<" is escaped so the JSON can never close the <script> block it sits in
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def write_html(out, patents):
    html = read_text(TEMPLATE)
    data = {"uiLang": "ja", "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "patents": patents}
    for mark, value in (("/*CC_DATA*/", embed(data)), ("/*CC_SCHEMA*/", embed(read_json(RESULT_SCHEMA)))):
        if html.count(mark) != 1:
            raise BuildError("template.html: placeholder %s must appear exactly once" % mark)
        html = html.replace(mark, value)
    out.write_text(html, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (out, out.stat().st_size))


def main(argv):
    # messages name Japanese files and nodes; never depend on the console's code page
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    if len(argv) < 3:
        print(__doc__)
        return 2
    try:
        patents = [build_patent(pathlib.Path(p)) for p in argv[2:]]
        write_html(pathlib.Path(argv[1]), patents)
    except (BuildError, OSError, KeyError) as e:
        print("build failed: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
