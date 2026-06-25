# -*- coding: utf-8 -*-
"""StrictDoc (.sdoc) renderer.

Figures are embedded as mermaid inside RST code-blocks (text), tables as RST
list-tables, captures as RST image directives -- per the task's format rule.
Functional requirements (section 2 items) are emitted as [REQUIREMENT] nodes
carrying the *exact* paragraph string in STATEMENT, so content stays identical
to the other formats while using StrictDoc's native requirement tagging.

Validated with `strictdoc export` (strictdoc 0.23.1).
"""
import os
import re
import content as C
from common import rst_code_block, rst_list_table
from gen_text import (mermaid_block, mermaid_state, mermaid_sequence, mermaid_flow,
                      SAMPLES, _meta_lines)


def _text_node(statement):
    return "[TEXT]\nSTATEMENT: >>>\n%s\n<<<\n" % statement


def _req_node(uid, title, statement):
    return ("[REQUIREMENT]\nUID: %s\nTITLE: %s\nSTATEMENT: >>>\n%s\n<<<\n"
            % (uid, title, statement))


def _section(title, body_nodes):
    # No trailing newline: the assembly inserts exactly one blank line between
    # nodes. StrictDoc's parser rejects two consecutive blank lines between
    # top-level sections.
    return "[[SECTION]]\nTITLE: %s\n\n%s\n[[/SECTION]]" % (title, "\n".join(body_nodes))


def _fig_node(caption, mermaid_code):
    return _text_node("**%s**\n\n%s" % (caption, rst_code_block(mermaid_code, "text")))


def _paras_of(num):
    return next(s for s in C.SECTIONS if s[0] == num)


def render_sdoc():
    out = ["[DOCUMENT]", "TITLE: %s" % C.DOC["title"], ""]

    # preamble: metadata + abstract wrapped in a leading section
    # (StrictDoc does not accept a document-level TEXT node ahead of sections).
    meta = " / ".join("%s: %s" % kv for kv in _meta_lines())
    out.append(_section("文書情報", [_text_node("%s\n\n概要: %s" % (meta, C.DOC["abstract"]))]))
    out.append("")

    # Section 1 + figure 1
    n, head, paras = _paras_of("1")
    s1 = [_text_node("\n\n".join(paras)), _fig_node(C.FIG_BLOCK, mermaid_block())]
    out.append(_section("%s %s" % (n, head), s1))
    out.append("")

    # Section 2: intro TEXT, (1)-(5) REQUIREMENT, outro TEXT
    n, head, paras = _paras_of("2")
    s2 = [_text_node(paras[0])]
    for p in paras[1:]:
        m = re.match(r"\(\d\)\s*(.+?)\s*\[(REQ-LKAS-\d+)\]", p)
        if m:
            s2.append(_req_node(m.group(2), m.group(1), p))
        else:
            s2.append(_text_node(p))
    out.append(_section("%s %s" % (n, head), s2))
    out.append("")

    # Section 3 + figure 2
    n, head, paras = _paras_of("3")
    s3 = [_text_node("\n\n".join(paras)), _fig_node(C.FIG_STATE, mermaid_state())]
    out.append(_section("%s %s" % (n, head), s3))
    out.append("")

    # Section 4 + figure 3
    n, head, paras = _paras_of("4")
    s4 = [_text_node("\n\n".join(paras)), _fig_node(C.FIG_SEQ, mermaid_sequence())]
    out.append(_section("%s %s" % (n, head), s4))
    out.append("")

    # Section 5 + figure 4
    n, head, paras = _paras_of("5")
    s5 = [_text_node("\n\n".join(paras)), _fig_node(C.FIG_FLOW, mermaid_flow())]
    out.append(_section("%s %s" % (n, head), s5))
    out.append("")

    # Section 6
    n, head, paras = _paras_of("6")
    out.append(_section("%s %s" % (n, head), [_text_node("\n\n".join(paras))]))
    out.append("")

    # Section 7 + tables + captures
    n, head, paras = _paras_of("7")
    s7 = [_text_node("\n\n".join(paras))]
    s7.append(_text_node(rst_list_table(C.PARAM_TABLE_CAPTION, C.PARAM_TABLE_HEADER,
                                        C.PARAM_TABLE_ROWS)))
    s7.append(_text_node(rst_list_table(C.IF_TABLE_CAPTION, C.IF_TABLE_HEADER,
                                        C.IF_TABLE_ROWS)))
    s7.append(_text_node("**%s**\n\n.. image:: %s" % (C.FIG_CAP1, C.CAPTURE1)))
    s7.append(_text_node("**%s**\n\n.. image:: %s" % (C.FIG_CAP2, C.CAPTURE2)))
    out.append(_section("%s %s" % (n, head), s7))

    text = "\n".join(out) + "\n"  # StrictDoc requires a trailing newline at EOF
    with open(os.path.join(SAMPLES, "spec_lkas.sdoc"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    from common import count_tokens
    t = render_sdoc()
    print("sdoc %7d chars %7d tokens" % (len(t), count_tokens(t)))
