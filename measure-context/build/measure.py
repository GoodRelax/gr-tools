# -*- coding: utf-8 -*-
"""Orchestrate generation + write-token measurement, then self-check identity.

Pipeline (single consistent pass):
  1. generate capture1.png / capture2.png (verify 1280x720)
  2. render txt / md / html / drawio / sdoc  (image = path reference only)
  3. build  xlsx / docx / pptx               (2 captures embedded as image bytes)
  4. measure write tokens with tiktoken cl100k_base:
       text-based : tokens of the whole file text
       office     : (a) logical-content tokens + image tokens [(W*H)/750 x2]
                    (b) generator-source tokens (reference only)
  5. ratios vs the .txt total (= 1.00)
  6. write samples/write_tokens.json
  7. content-identity self-check across all eight formats

All token values are tiktoken cl100k_base APPROXIMATIONS (not Anthropic's
production tokenizer); the relative ratios are the point.
"""
import os
import io
import json
import datetime
import xml.etree.ElementTree as ET
import importlib

import content as C
import gen_text as GT
import gen_sdoc as GS
import gen_xlsx as GX
import gen_docx as GD
import gen_pptx as GP
from gen_captures import make_captures
from common import count_tokens

SAMPLES = GT.SAMPLES
BUILD = os.path.dirname(__file__)


def _lib_versions():
    out = {}
    for label, mod in [("tiktoken", "tiktoken"), ("openpyxl", "openpyxl"),
                       ("python-docx", "docx"), ("python-pptx", "pptx"),
                       ("Pillow", "PIL"), ("strictdoc", "strictdoc")]:
        try:
            m = importlib.import_module(mod)
            out[label] = getattr(m, "__version__", "?")
        except Exception:
            out[label] = "missing"
    return out


def _src_tokens(fname):
    with open(os.path.join(BUILD, fname), encoding="utf-8") as f:
        return count_tokens(f.read())


# ----- text extraction for the content self-check -------------------------
def _drawio_text(xml_text):
    root = ET.fromstring(xml_text)
    parts = []
    for el in root.iter():
        if el.get("value"):
            parts.append(el.get("value"))
        if el.text:
            parts.append(el.text)
    return "\n".join(parts)


def _html_unescape(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _required_strings():
    req = [C.DOC["title"], C.DOC["abstract"]]
    req += C.all_body_paragraphs()
    for row in [C.PARAM_TABLE_HEADER] + C.PARAM_TABLE_ROWS:
        req += [str(x) for x in row]
    for row in [C.IF_TABLE_HEADER] + C.IF_TABLE_ROWS:
        req += [str(x) for x in row]
    req += [lab for _, lab in C.BLOCK_NODES]
    req += [lab for *_, lab in C.BLOCK_EDGES]
    req += list(C.STATES)
    req += [lab for *_, lab in C.STATE_TRANSITIONS]
    req += [lab for _, lab in C.SEQ_PARTICIPANTS]
    req += [lab for *_, lab in C.SEQ_MESSAGES]
    req += [lab for _, _, lab in C.FLOW_NODES]
    req += [lab for *_, lab in C.FLOW_EDGES if lab]
    req += [C.FIG_BLOCK, C.FIG_STATE, C.FIG_SEQ, C.FIG_FLOW,
            C.FIG_CAP1, C.FIG_CAP2, C.PARAM_TABLE_CAPTION, C.IF_TABLE_CAPTION]
    # de-duplicate, preserve order
    seen, out = set(), []
    for s in req:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main():
    os.makedirs(SAMPLES, exist_ok=True)

    # 1. captures
    sizes = make_captures(SAMPLES)
    for name, (w, h) in sizes.items():
        assert (w, h) == (1280, 720), "%s is %dx%d, expected 1280x720" % (name, w, h)
    img_tokens_each = {n: (w * h) / 750.0 for n, (w, h) in sizes.items()}
    office_image_tokens = round(sum(img_tokens_each.values()), 1)  # both captures embedded

    # 2. text-based formats (returned string == file content)
    text_payload = {
        "txt": GT.render_txt(),
        "md": GT.render_md(),
        "html": GT.render_html(),
        "drawio": GT.render_drawio(),
        "sdoc": GS.render_sdoc(),
    }

    # 3. office formats (logical content + generator source)
    office = {}
    for ext, mod, src in [("xlsx", GX, "gen_xlsx.py"),
                          ("docx", GD, "gen_docx.py"),
                          ("pptx", GP, "gen_pptx.py")]:
        path, logical = mod.build()
        office[ext] = {"logical": logical, "code": src}

    # 4-5. assemble measurements
    fmt = {}
    for ext, text in text_payload.items():
        tt = count_tokens(text)
        fmt[ext] = {"text_tokens": tt, "image_tokens": 0, "total": tt}
    for ext, d in office.items():
        tt = count_tokens(d["logical"])
        total = round(tt + office_image_tokens, 1)
        fmt[ext] = {"text_tokens": tt, "image_tokens": office_image_tokens,
                    "total": total, "code_tokens": _src_tokens(d["code"])}

    base = fmt["txt"]["total"]
    order = ["txt", "md", "sdoc", "drawio", "html", "xlsx", "docx", "pptx"]
    for ext in order:
        fmt[ext]["ratio"] = round(fmt[ext]["total"] / base, 3)

    # 6. write_tokens.json
    doc = {
        "meta": {
            "session": "write (書き込みコンテキスト計測). 読み込み計測は別セッションの責務。",
            "tokenizer": "tiktoken",
            "encoding": "cl100k_base",
            "approximation_note": ("全トークン値は tiktoken cl100k_base による近似値。"
                                   "Anthropic本番トークナイザとは数え方が異なるため絶対値は近似。"
                                   "主目的は .txt を基準(1.00)とした相対倍率の比較。"),
            "image_token_formula": "(width*height)/750",
            "captures": {n: list(s) for n, s in sizes.items()},
            "office_image_tokens_explained": (
                "xlsx/docx/pptx は capture1/2 を画像実体として埋め込むため "
                "(1280*720)/750 * 2 = %.1f を加算。txt/md/sdoc/drawio/html はパス参照のみで0。"
                % office_image_tokens),
            "office_metrics_explained": (
                "office の text_tokens は (a)論理内容ベース(セル/段落/図形のテキスト値の合計)。"
                "code_tokens は (b)生成コード参考値(各形式固有の生成モジュール gen_xlsx/gen_docx/gen_pptx の"
                "ソーストークン。共有モジュール content/common/layout/figdata は含めない)。"
                "total と ratio は (a)+image_tokens に基づく主指標。"),
            "baseline": "txt total = 1.00",
            "library_versions": _lib_versions(),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "format_order": order,
        },
        "formats": {ext: fmt[ext] for ext in order},
    }
    with open(os.path.join(SAMPLES, "write_tokens.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    # 7. content-identity self-check
    extracted = {
        "txt": text_payload["txt"],
        "md": text_payload["md"],
        "sdoc": text_payload["sdoc"],
        "drawio": _drawio_text(text_payload["drawio"]),
        "html": _html_unescape(text_payload["html"]),
        "xlsx": office["xlsx"]["logical"],
        "docx": office["docx"]["logical"],
        "pptx": office["pptx"]["logical"],
    }
    required = _required_strings()
    misses = {}
    for ext in order:
        body = extracted[ext]
        miss = [r for r in required if r not in body]
        if miss:
            misses[ext] = miss

    # ---- report ----
    print("== write-token measurement (tiktoken cl100k_base, approximate) ==")
    print("%-7s %12s %12s %10s %8s %12s" %
          ("ext", "text_tokens", "image_tokens", "total", "ratio", "code_tokens"))
    for ext in order:
        d = fmt[ext]
        print("%-7s %12d %12s %10s %8.3f %12s" %
              (ext, d["text_tokens"], d["image_tokens"], d["total"], d["ratio"],
               d.get("code_tokens", "-")))

    print("\n== content-identity self-check ==")
    print("required content strings checked per format:", len(required))
    if not misses:
        print("ALL FORMATS CONTAIN IDENTICAL REQUIRED CONTENT (0 misses).")
    else:
        for ext, miss in misses.items():
            print("  %s: %d missing -> %s" % (ext, len(miss), miss[:5]))

    return doc, misses


if __name__ == "__main__":
    main()
