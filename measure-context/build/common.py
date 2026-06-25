# -*- coding: utf-8 -*-
"""Cross-cutting helpers shared by every renderer.

- tiktoken (cl100k_base) token counter (approximate; differs from the Anthropic
  production tokenizer -- absolute values are approximate, relative ratios are
  the point).
- CJK-aware display width and ASCII box/table primitives (for the .txt renderer).
- RST helpers (for the .sdoc renderer).
- XML/HTML escaping (for .drawio / .html).
"""
import unicodedata
import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Approximate token count with tiktoken cl100k_base.

    disallowed_special=() treats every byte sequence as ordinary text so that
    arbitrary markup (e.g. '<|' fragments) never raises.
    """
    return len(_ENC.encode(text, disallowed_special=()))


# --------------------------------------------------------------------------
# Display width (full-width CJK counts as 2 columns) and padding.
# --------------------------------------------------------------------------
def dwidth(s: str) -> int:
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def pad_disp(s: str, width: int, align: str = "left", fill: str = " ") -> str:
    deficit = width - dwidth(s)
    if deficit <= 0:
        return s
    if align == "left":
        return s + fill * deficit
    if align == "right":
        return fill * deficit + s
    left = deficit // 2
    right = deficit - left
    return fill * left + s + fill * right


# --------------------------------------------------------------------------
# Plain-text aligned table (.txt).
# --------------------------------------------------------------------------
def plain_table(header, rows) -> str:
    cols = len(header)
    widths = [dwidth(str(header[c])) for c in range(cols)]
    for row in rows:
        for c in range(cols):
            widths[c] = max(widths[c], dwidth(str(row[c])))
    out = []
    head = " | ".join(pad_disp(str(header[c]), widths[c], "center") for c in range(cols))
    out.append("| " + head + " |")
    sep = "-+-".join("-" * widths[c] for c in range(cols))
    out.append("+-" + sep + "-+")
    for row in rows:
        line = " | ".join(pad_disp(str(row[c]), widths[c], "left") for c in range(cols))
        out.append("| " + line + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# ASCII box primitives (.txt diagrams).
# --------------------------------------------------------------------------
def ascii_box(label: str, width: int = None):
    """Return a 3-line boxed label as a list of strings (display-width aware)."""
    if width is None:
        width = dwidth(label) + 2
    inner = pad_disp(label, width, "center")
    bar = "+" + "-" * width + "+"
    return [bar, "|" + inner + "|", bar]


def stack_boxes(labels, width):
    """Vertically stacked boxes joined by a short '|' connector line."""
    lines = []
    for i, lab in enumerate(labels):
        lines.extend(ascii_box(lab, width))
    return lines


# --------------------------------------------------------------------------
# RST helpers (.sdoc STATEMENT fields).
# --------------------------------------------------------------------------
def rst_indent(text: str, n: int = 3) -> str:
    pad = " " * n
    return "\n".join((pad + ln if ln else "") for ln in text.split("\n"))


def rst_code_block(code: str, lang: str = "text") -> str:
    return ".. code-block:: %s\n\n%s\n" % (lang, rst_indent(code, 3))


def rst_list_table(caption, header, rows) -> str:
    lines = [".. list-table:: %s" % caption, "   :header-rows: 1", ""]

    def emit_row(cells):
        first = True
        for cell in cells:
            prefix = "   * - " if first else "     - "
            lines.append(prefix + str(cell))
            first = False

    emit_row(header)
    for row in rows:
        emit_row(row)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Escaping.
# --------------------------------------------------------------------------
def xml_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
