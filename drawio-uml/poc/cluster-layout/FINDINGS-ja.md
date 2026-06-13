# PoC 所見 — クラスタ階層化(作戦1 / cluster-hierarchy)

対象モデル: ARC-AGI-3 ドメインモデル(`samples/gr-arc-3-domain-model.documented.model.json`)
狙い: input → consider → output / vocabulary の帯はそのまま、**`consider` を world|goal|plan の3サブ群に左→右で分け**、Conception をその上に置く。input の Probe/TurnRecord は縦積み。
環境: Graphviz 13.1.2(dot/neato/fdp)、draw.io desktop(`C:\Program Files\draw.io\draw.io.exe`、headless export 可)、Python 3.13。
本体 `scripts/draw.py` は**不変**。検証は本 PoC ディレクトリ内のみ(回帰 golden 非汚染)。

## 結論

- **入れ子クラスタの描画自体は可能**(dot は nested `subgraph cluster` を綺麗に描く)。
- **「1つの dot run で兄弟サブクラスタを左→右に強制」= A1 は不成立**。順序固定の唯一の手 `rank=same`＋flat 陰線は、入れ子クラスタとぶつかり **dot がクラスタ所属を剥奪→ Segmentation fault**。ADR-005 が「リスク高」と却下した地雷を実証。
- **A2(階層グリッド合成)が頑健**。各サブ群を独立 dot run で組み、**Python が左→右に配置**(既存 banded ロジックを1段深くするだけ。順序は Python が保証)。**狙いの絵を end-to-end で再現済み**(`arc_hier.png`)。

## フェーズと証跡

| Phase | 内容 | 結果 | 成果物 |
| --- | --- | --- | --- |
| 1 | consider 単体を入れ子クラスタで描画(陰線なし) | 箱は綺麗 / 自然配置は world\|plan\|goal に崩れ・MarkovState 沈下 | `p1_consider_nested.png` |
| 2 | `ordering=out` ＋ クロス群 `constraint=false` | 各サブ群内は綺麗化。但し左右順は固定できず(world\|plan\|goal のまま) | `p2_consider_ordered.png` |
| 2b | `rank=same`＋flat 陰線で順序強制 | **警告(cluster 所属剥奪)＋ Segmentation fault** → A1 棄却 | (出力なし) |
| 入力 | input の Probe/TurnRecord を陰線で縦積み | **成立**(確実) | `p2_input_stack.png` |
| 3 | A2 を `draw_poc.py`(draw.py のコピー)に実装し ARC 全体を描画 | **狙いの絵を再現**。幾何チェック合格 | `arc_hier.drawio` / `arc_hier.png` |

幾何チェック(`arc_hier.drawio` より): 3 内箱は全て外箱の内側・相互非重複、input は TurnRecord↑/Probe↓。

## A2 の仕組み(`draw_poc.py` の差分)

- `cluster` は ADR-005 のパス文字列をそのまま使う: `consider/world` 等。top セグメントが帯クラスタ、`options.layout.rows` は top キー参照(現行どおり)。
- `_layout_hier_cluster()`: サブ群を独立 `_layout_one_cluster()`(TB)で組み、**初出順に左→右で Python 合成**。`cluster==ckey` 丁度のノード(Conception)はヘッダとして上に中央寄せ。戻り値は `_layout_one_cluster` と同形 `(pos,{},(w,h))` なので**外側 banded 合成は不変**。
- `_layout_one_cluster()`: 内部エッジが無いクラスタは陰線でメンバを縦連結(input の縦積み)。
- `cluster_box_cells()`: top セグメントで**外箱**、`/` を含む full パスで**内箱**を描画。外箱を先に出して z 順で背面に。入れ子を持つ外箱だけ pad を増やす。
- `_route_pinned()` は不変(flat pinned グラフ。入れ子に非依存で全エッジ箱回避)。

## 本実装(SSOT=`scripts/draw.py`)への論点 / DA 表の種

| ID | 論点 | 案 |
| --- | --- | --- |
| H1 | サブ群の左右順の指定 | (a) 初出順[PoC 採用] / (b) `options.layout` にサブ順キー追加 / (c) パスに序数 |
| H2 | 内箱の色・凡例 | PoC は内箱グレー。凡例が内箱まで列挙する点(`legend_cell` が `specs.values()` 全列挙)を要整理 |
| H3 | 既存 banded 置換 or 共存 | A2 は既存 banded の**拡張**(置換不要)。非階層モデルは現挙動維持=**バイト一致**を回帰で固定 |
| H4 | model.schema.json | `options.clusters` を full パスキー許容に。階層の入れ子段数(2段で十分か) |
| H5 | spec 反映 | ADR-005 / LM-1 改訂(draw もパス階層を描く)、FR 追加、版 0.3.0、敵対的レビュー |
| H6 | Variant B(§11 単一 dot run 置換) | **棄却推奨**(2b の segfault が実証)。コード簡素化目的でも割に合わない |

## 再現コマンド

```bash
# 個別 PoC(draw.io 不要)
dot -Tpng p1_consider_nested.dot   -o p1_consider_nested.png
dot -Tpng p2_consider_ordered.dot  -o p2_consider_ordered.png
dot -Tpng p2_input_stack.dot       -o p2_input_stack.png
# A2 end-to-end
python draw_poc.py arc_hier.model.json arc_hier.drawio
"C:\Program Files\draw.io\draw.io.exe" -x -f png -e -b 12 -o arc_hier.png arc_hier.drawio
```
