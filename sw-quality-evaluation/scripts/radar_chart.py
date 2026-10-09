"""Draw a radar chart as a standalone SVG file, with no third-party packages.

Usage: python radar_chart.py <input.json> <output.svg>

Input JSON:
{
  "title": "Product quality (ISO/IEC 25010:2023)",
  "max": 10,
  "legend": {"cannot_judge": "Cannot judge", "not_applicable": "Not applicable"},
  "axes": [
    {"label": "Functional suitability", "score": 5},
    {"label": "Safety", "status": "not-applicable"},
    {"label": "Naming", "status": "cannot-judge"}
  ]
}

An axis with a score is plotted. An axis whose status is "cannot-judge" is drawn
dashed and left out of the polygon -- it is not a zero. An axis whose status is
"not-applicable" is drawn dotted in grey and left out of the polygon. Labels may be
in any language; they are XML-escaped and written as UTF-8.
"""
import json
import math
import sys
from xml.sax.saxutils import escape

# Sized so that three charts side by side stay legible when each is scaled to
# about a third of a page: large type, a compact radius, room for long labels.
WIDTH = 720
HEIGHT = 560
CENTER_X = WIDTH / 2
CENTER_Y = 290
RADIUS = 160
LABEL_GAP = 22
RING_STEP = 2
FONT_TITLE = 26
FONT_LABEL = 21
FONT_RING = 14

COLOR_GRID = "#c9cdd3"
COLOR_AXIS = "#9aa1aa"
COLOR_TEXT = "#1f2328"
COLOR_MUTED = "#8b929a"
COLOR_FILL = "#2f6fdb"


def point_at(index, count, value, max_value):
    """Return the (x, y) of a value on axis index; axis 0 points straight up."""
    angle = -math.pi / 2 + 2 * math.pi * index / count
    distance = RADIUS * value / max_value
    return CENTER_X + distance * math.cos(angle), CENTER_Y + distance * math.sin(angle)


def label_anchor(x):
    """Choose text-anchor so labels sit outside the chart on every side."""
    if abs(x - CENTER_X) < 8:
        return "middle"
    return "start" if x > CENTER_X else "end"


def build_svg(chart):
    max_value = chart.get("max", 10)
    axes = chart["axes"]
    count = len(axes)
    legend = chart.get("legend", {})
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="sans-serif">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
    ]
    if chart.get("title"):
        parts.append(f'<text x="{CENTER_X}" y="36" text-anchor="middle" font-size="{FONT_TITLE}" '
                     f'font-weight="bold" fill="{COLOR_TEXT}">{escape(chart["title"])}</text>')

    for ring in range(RING_STEP, max_value + 1, RING_STEP):
        ring_points = " ".join(
            f"{x:.1f},{y:.1f}" for x, y in (point_at(i, count, ring, max_value) for i in range(count)))
        parts.append(f'<polygon points="{ring_points}" fill="none" stroke="{COLOR_GRID}" stroke-width="1"/>')
        ring_x, ring_y = point_at(0, count, ring, max_value)
        parts.append(f'<text x="{ring_x + 4:.1f}" y="{ring_y + 4:.1f}" font-size="{FONT_RING}" '
                     f'fill="{COLOR_MUTED}">{ring}</text>')

    plotted = []
    for index, axis in enumerate(axes):
        status = axis.get("status")
        end_x, end_y = point_at(index, count, max_value, max_value)
        dash = {"cannot-judge": ' stroke-dasharray="6 4"', "not-applicable": ' stroke-dasharray="2 4"'}.get(status, "")
        parts.append(f'<line x1="{CENTER_X}" y1="{CENTER_Y}" x2="{end_x:.1f}" y2="{end_y:.1f}" '
                     f'stroke="{COLOR_AXIS}" stroke-width="1"{dash}/>')

        label_x, label_y = point_at(index, count, max_value + max_value * LABEL_GAP / RADIUS, max_value)
        anchor = label_anchor(label_x)
        if status == "not-applicable":
            value_text, color = legend.get("not_applicable", "Not applicable"), COLOR_MUTED
        elif status == "cannot-judge" or axis.get("score") is None:
            value_text, color = legend.get("cannot_judge", "Cannot judge"), COLOR_MUTED
        else:
            value_text, color = str(axis["score"]), COLOR_TEXT
            plotted.append(point_at(index, count, axis["score"], max_value))
        parts.append(f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" font-size="{FONT_LABEL}" '
                     f'fill="{color}">{escape(axis["label"])}</text>')
        parts.append(f'<text x="{label_x:.1f}" y="{label_y + FONT_LABEL + 2:.1f}" text-anchor="{anchor}" font-size="{FONT_LABEL}" '
                     f'font-weight="bold" fill="{color}">{escape(value_text)}</text>')

    if len(plotted) >= 3:
        polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in plotted)
        parts.append(f'<polygon points="{polygon}" fill="{COLOR_FILL}" fill-opacity="0.22" '
                     f'stroke="{COLOR_FILL}" stroke-width="2"/>')
    for x, y in plotted:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{COLOR_FILL}"/>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    chart = json.loads(open(sys.argv[1], encoding="utf-8").read())
    with open(sys.argv[2], "w", encoding="utf-8") as out:
        out.write(build_svg(chart))


if __name__ == "__main__":
    main()
