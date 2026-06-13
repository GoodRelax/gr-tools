# drawio-uml 機能拡張 検討 引継プロンプト(次セッション用)

> 機能拡張「**クラスタの階層化 + dot 中心レイアウト(陰線方式)**」の **検討フェーズ**(調査・PoC・設計)を行う。
> いきなり実装しない。作業ディレクトリ: `gr-tools/drawio-uml`。SSOT = `docs/spec-ja.md`(現 0.2.2)。
> 命名・設計判断は勝手に決めず DA 表(複数案+評価軸)→ オーナー決定。git commit/push/tag はオーナーが手動。

## 0. まず読む(目的を申告してから)

1. `docs/spec-ja.md`(0.2.2)— 仕様 SSOT。特に **ADR-005**(cluster はパス文字列;階層対応は `table` のみ、`draw` は当面フラット=YAGNI で却下)、**LM-1**(draw は cluster を不透明1ラベル扱い)、FR-D-03/04、§3.4。
2. `scripts/draw.py` — 描画実装。特に `dot_layout_clustered` / `_dot_layout_banded` / `_layout_one_cluster` / `_emit_cluster` / `_route_pinned` / `cluster_box_cells` / `legend_cell`。
3. `references/drawio-uml-reference.md` §9–§13(clusters / legend / banded / box-avoiding routing)。**特に §11 にある「1回の dot 実行では帯配置を強制できない」理由**。

## 1. 現状のレイアウト機構(最重要・誤解しやすい)

| 描画経路 | ノード位置 | エッジ経路(箱回避) | クラスタの並べ方 |
| --- | --- | --- | --- |
| flat(クラスタ無し) | **dot** | **dot**(`splines=ortho`) | — |
| clustered(`rows` 無し) | **dot**(`subgraph cluster_*` で 1 run) | dot + **neato -n2** 再ルート | **dot**(subgraph が自動配置) |
| banded(`options.layout.rows`) | **dot**(クラスタ毎に独立 run) | **neato -n2** 再ルート | ← **ここだけ Python**(`rows` で grid 合成 = `_dot_layout_banded`) |

- 矢印が箱を貫通しないのは **全経路 dot/neato** がやっている(`_route_pinned`)。
- Python がレイアウトするのは **banded のクラスタ配置だけ**。理由(reference §11):dot を 1 回回しても「上段に input|consider|output、下段に vocabulary 全幅」のような帯を強制できない(クラスタが edge mass の方へ寄る/高さが揃わない)。so 各クラスタを独立に dot レイアウト → Python が rows 通りに grid 合成している。

## 2. やりたいこと(オーナーの要望)

1. **クラスタを階層構造で指定可能に** — cluster パス `a/b/c` を `draw` が **入れ子の箱**(dot の入れ子 `subgraph cluster`)で描く。現状は ADR-005 / LM-1 で「draw はフラット1ラベル」と却下済み → **これを覆す**。
2. **「陰線(invisible edge, `style=invis`)」でクラスタを並べ、dot にレイアウトさせる** — 見えない矢印で「この帯/箱の下にあれ」と配置順序・整列を dot に指示し、現状の Python grid 合成(`_dot_layout_banded`)を **dot 1 パスに戻す**。
3. 真の狙い:**JSON で簡単にレイアウト(配置・階層)を指定でき、かつ矢印が箱とかぶらない(dot)** を両立する。

## 3. 検討すべき設計判断(検討事項)

- **入れ子 subgraph cluster の dot 表現と品質** — `subgraph cluster_a { subgraph cluster_b { … } }`。dot は入れ子 cluster を描けるが、レイアウト品質・ラベル位置・余白は要 PoC。
- **invisible edge で帯/順序を制御できるか** — `rows` 相当の帯配置を invisible edge(`style=invis` + `rank=same` / `constraint`)で **1 dot run** に。§11 が「1 run では無理」とした点を、invisible edge で再挑戦できるか PoC。
- **現 banded(`_dot_layout_banded`)を置換するか共存か** — オーナー未決定。PoC 結果で評価(置換できれば grid 合成コードを削減できる)。**置換/共存の評価**自体をタスク化。
- **box-avoiding routing(`_route_pinned`)の階層対応** — 入れ子箱でも全エッジ box-avoiding を維持。
- **クラスタ箱の入れ子描画(`cluster_box_cells`)+ 凡例(`legend_cell`)** — 階層に対応(z 順、入れ子の枠)。
- **モデル表現(JSON / schema)** — 階層は既存のパス文字列 `a/b/c` をそのまま使えるはず。`options.clusters` / `options.layout` の拡張方法、`model.schema.json` の更新。

## 4. リスク・制約(厳守)

- **ADR-005 の却下経緯**:階層図示は「レイアウト再帰化・入れ子ボックス・クラスタ間ルーティングの大改修でリスク高」と当時 YAGNI 却下した。今回その大改修に踏み込むので、**PoC で実現性とレイアウト品質を実証してから本実装**。汚ければ却下 or 別手段。
- **回帰 byte-identical**:既存の flat / clustered / banded 出力(`tests/` の golden、ARC `v007`)を壊さない。**新方式はオプトイン**(既存モデルは現挙動を維持)。
- 標準ライブラリのみ(NFR-02)、Graphviz `dot`/`neato`。このマシン: uv 不可 / git-bash の `grep -P` 不可(抽出は python)/ model.json は UTF-8。

## 5. 次セッションのタスク(この順序で)

- **T-PoC1(陰線)**:`.dot` を手書きし、invisible edge で `rows` 相当の帯配置が **1 dot run** で出せるか実験(`dot -Tplain` で座標確認 + PNG 目視)。
- **T-PoC2(階層)**:入れ子 `subgraph cluster`(`a/b/c`)が dot で綺麗に描けるか実験。
- **T-設計**:PoC を基に DA 表 →(a)陰線方式の採否、(b)現 banded 置換/共存、(c)階層 cluster のモデル表現 を **オーナー決定**。
- **T-spec**:ADR-005 を改訂 or 新 ADR、LM-1 更新、FR 追加、版 0.3.0 へ。敵対的レビュー(R1–R6)。
- **T-実装**:`draw.py` の clustered path を拡張。回帰維持(golden / ARC v007 byte-identical)。テスト追加。

## 6. 参照(実装の該当関数)

`draw.py`: `dot_layout_clustered`(banded 振り分け)、`_dot_layout_banded`(Python grid 合成=置換候補)、`_layout_one_cluster`(クラスタ単独 dot run)、`_emit_cluster`(subgraph 出力)、`_route_pinned`(箱回避ルート)、`cluster_box_cells`(クラスタ枠)、`legend_cell`(凡例)。
`spec`: ADR-005 / LM-1 / FR-D-03/04/07 / §3.4 cluster。 `reference`: §11(帯配置の理由)/ §12(pinned routing)。

## 7. 現状サマリ(この拡張の前提)

draw / table は 0.2.2 で完成・テスト緑・skill 配布済み(memory `drawio-uml-status` 参照)。本拡張は **clustered path の再設計**であり、flat / table には影響させない。
