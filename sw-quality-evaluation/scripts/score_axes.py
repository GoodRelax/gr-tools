"""Compute the axis scores, the design score and the radar charts of a report.

Usage: python score_axes.py <REPORT_DIR> [<SKILL_DIR>]

Scores are computed, never judged: the agents decide each checklist verdict and
each finding's severity; this script turns them into 1-10 scores with the rules in
axes.json, so the same evidence always gives the same score.

Reads (in REPORT_DIR):
  findings/*.jsonl          verdict rows of every lens agent (final.jsonl is skipped)
  findings/final.jsonl      merged, refuted findings: severity, confidence,
                            characteristics (first = most harmed) and items
  verdict-overrides.jsonl   optional: {"agent","item","verdict"} -- PASS verdicts
                            the refuters overturned
  partition.json            region line counts (for the size correction)
  profile.json              {"weights": {"<characteristic>": "high|medium|low|n/a"}}
  axis-overrides.json       optional: {"cannot_judge": {"<axis id>": "<reason>"}}
  labels.json               optional: translated chart titles, axis labels, legend
Writes:
  scores.json, charts/<chart id>.json and charts/<chart id>.svg
"""
import json
import pathlib
import subprocess
import sys

SEVERITY_ORDER = ["info", "minor", "major", "critical"]


def read_jsonl(path):
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def matches(item, patterns):
    for pattern in patterns:
        if pattern.endswith("*") and str(item).startswith(pattern[:-1]):
            return True
        if item == pattern:
            return True
    return False


def effective_severity(finding, lower_plausible):
    severity = finding.get("severity", "info")
    if lower_plausible and finding.get("confidence") == "plausible" and severity in SEVERITY_ORDER[1:]:
        return SEVERITY_ORDER[SEVERITY_ORDER.index(severity) - 1], True
    return severity, False


def checklist_level(verdicts, config):
    points = config["checklist_points"]
    scored = [v for v in verdicts if v in points]
    if not scored:
        return None, None, {}
    counts = {key: scored.count(key) for key in points}
    rate = 100.0 * sum(points[v] for v in scored) / (2 * len(scored))
    for rule in config["checklist_levels"]:
        if rate >= rule["min_rate"] and (not rule.get("no_fail") or counts["FAIL"] == 0):
            return rule["score"], rate, counts
    return 1, rate, counts


def defect_level(findings, units, config):
    counting = config["counting"]
    critical = major = minor = 0
    unconfirmed_major = False
    for finding in findings:
        severity, lowered = effective_severity(finding, counting["plausible_counts_one_level_lower"])
        if severity == "critical":
            critical += 1
        elif severity == "major":
            major += 1
        elif severity == "minor":
            minor += 1
            if lowered:
                unconfirmed_major = True
    major_per_unit = major / units
    minor_per_unit = minor / units
    if critical >= 2:
        level = 2
    elif critical == 1:
        level = 3
    elif major > 0:
        # "A few" and "many" are per 5,000 lines, so a large code base is not marked
        # down for size alone: fewer than one major per unit leaves the axis at 6.
        if major_per_unit >= counting["several"][0]:
            level = 4
        elif major_per_unit >= 1:
            level = 5
        else:
            level = 6
    else:
        if minor_per_unit == 0:
            level = 10
        elif minor_per_unit <= counting["a_few"][1]:
            level = 9
        elif minor_per_unit <= counting["several"][1]:
            level = 8
        elif minor_per_unit <= counting["minor_many_upper"]:
            level = 7
        else:
            level = 6
        if unconfirmed_major:
            level = min(level, 6)
    detail = {"critical": critical, "major": major, "minor": minor,
              "units": round(units, 2), "unconfirmed_major": unconfirmed_major}
    return level, detail


def finding_matches_axis(finding, axis, findings_by):
    if findings_by == "characteristic":
        characteristics = finding.get("characteristics") or [finding.get("characteristic")]
        return bool(characteristics) and characteristics[0] == axis["id"]
    items = finding.get("items") or ([finding["item"]] if finding.get("item") else [])
    return any(matches(item, axis["items"]) for item in items)


def score_group(verdicts, findings, units, config):
    """Score one axis (or a pool of axes) from its verdicts and findings."""
    check, rate, counts = checklist_level(verdicts, config)
    defects, detail = defect_level(findings, units, config)
    if check is None and not findings:
        return None, {"reason": "no verdicts and no findings"}
    score = defects if check is None else min(check, defects)
    how = {"checklist_counts": counts, "checklist_rate": None if rate is None else round(rate, 1),
           "checklist_level": check, "defects": detail, "defect_level": defects, "score": score}
    return score, how


def main():
    report_dir = pathlib.Path(sys.argv[1])
    skill_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(__file__).resolve().parent.parent
    config = read_json(skill_dir / "axes.json", None)
    labels = read_json(report_dir / "labels.json", {})
    profile = read_json(report_dir / "profile.json", {"weights": {}})
    overrides = read_json(report_dir / "axis-overrides.json", {}).get("cannot_judge", {})

    verdict_rows = []
    for path in sorted((report_dir / "findings").glob("*.jsonl")):
        if path.name != "final.jsonl":
            verdict_rows += [r for r in read_jsonl(path) if r.get("kind") == "verdict"]
    overturned = {(r.get("agent"), r.get("item")): r["verdict"]
                  for r in read_jsonl(report_dir / "verdict-overrides.jsonl")}
    for row in verdict_rows:
        key = (row.get("agent"), row.get("item"))
        if key in overturned:
            row["verdict"] = overturned[key]
    findings = [r for r in read_jsonl(report_dir / "findings" / "final.jsonl")
                if r.get("severity") in ("critical", "major", "minor")]

    partition = read_json(report_dir / "partition.json", {"regions": []})
    lines = sum(region.get("lines", 0) for region in partition.get("regions", []))
    units = max(1.0, lines / config["counting"]["lines_per_unit"])

    charts_dir = report_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    result = {"lines_in_scope": lines, "size_units": round(units, 2), "charts": []}
    errors = []
    for chart in config["charts"]:
        chart_out = {"id": chart["id"], "axes": []}
        radar_axes = []
        pooled_verdicts, pooled_findings = [], {}
        for axis in chart["axes"]:
            label = labels.get("axes", {}).get(axis["id"], axis["label"])
            verdicts = [r["verdict"] for r in verdict_rows if matches(r.get("item"), axis["items"])]
            axis_findings = [f for f in findings if finding_matches_axis(f, axis, chart["findings_by"])]
            if chart["id"] == "product" and profile.get("weights", {}).get(axis["id"]) == "n/a":
                chart_out["axes"].append({"id": axis["id"], "label": label, "status": "not-applicable"})
                radar_axes.append({"label": label, "status": "not-applicable"})
                continue
            if axis["id"] in overrides:
                if axis.get("mandatory"):
                    errors.append(f"axis '{axis['id']}' is mandatory and may not be 'cannot judge': read more, then score it")
                chart_out["axes"].append({"id": axis["id"], "label": label, "status": "cannot-judge",
                                          "reason": overrides[axis["id"]]})
                radar_axes.append({"label": label, "status": "cannot-judge"})
                continue
            score, how = score_group(verdicts, axis_findings, units, config)
            if score is None and axis.get("mandatory"):
                errors.append(f"axis '{axis['id']}' is mandatory but has no verdicts or findings")
            status = "scored" if score is not None else "cannot-judge"
            chart_out["axes"].append({"id": axis["id"], "label": label, "status": status, "score": score,
                                      "how": how, "findings": [f.get("id") for f in axis_findings]})
            radar_axes.append({"label": label, "score": score} if score is not None
                              else {"label": label, "status": "cannot-judge"})
            pooled_verdicts += verdicts
            for f in axis_findings:
                pooled_findings[f.get("id")] = f
        if chart["id"] == "design":
            score, how = score_group(pooled_verdicts, list(pooled_findings.values()), units, config)
            result["design_score"] = {"score": score, "how": how}
        result["charts"].append(chart_out)

        chart_labels = labels.get("charts", {}).get(chart["id"], {})
        radar = {"title": "", "max": 10, "axes": radar_axes,
                 "legend": {"cannot_judge": labels.get("cannot_judge", "Cannot judge"),
                            "not_applicable": labels.get("not_applicable", "Not applicable")}}
        chart_out["title"] = chart_labels.get("title", chart["title"])
        chart_out["subtitle"] = chart_labels.get("subtitle", chart["subtitle"])
        data_path = charts_dir / f"{chart['id']}.json"
        data_path.write_text(json.dumps(radar, ensure_ascii=False, indent=1), encoding="utf-8")
        subprocess.run([sys.executable, str(skill_dir / "scripts" / "radar_chart.py"),
                        str(data_path), str(charts_dir / f"{chart['id']}.svg")], check=True)

    result["errors"] = errors
    (report_dir / "scores.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for chart in result["charts"]:
        print(chart["id"], [(a["id"], a.get("score", a["status"])) for a in chart["axes"]])
    print("design score:", result.get("design_score", {}).get("score"))
    for error in errors:
        print("ERROR:", error)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
