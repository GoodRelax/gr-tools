# 改善要望書 — フロー図向け dot ネイティブ・レイアウトエンジン(0.6.0)

| 項目 | 値 |
| --- | --- |
| 文書種別 | 改善要望書(設計合意済み。次フェーズで仕様化) |
| 対象 | `drawio-uml`(`scripts/draw.py` 中心。`schema` / `table.py` / docs も波及) |
| 目標版 | 0.6.0 |
| 起票 | 2026-06-14 |
| 状態 | **設計合意済み**(オーナー決定)。実装は Spec フェーズから |
| 関連 | `docs/spec-ja.md`(現行仕様 0.5.0)/ `poc/state-machine-dot/`(本要望の PoC・実証済み) |

---

## 1. 背景・課題

状態機械(state machine)図を現行エンジンで生成すると **縦長・窮屈で読みにくい**。同じ図を Mermaid で描く方が読みやすかった。一方、本スイートの **「モデル JSON を SSOT にできる」価値は捨てがたい**(Mermaid は SSOT/再生成・GUI 編集で劣る)。

→ **JSON SSOT を保ったまま、状態機械を Mermaid 並みに読みやすく**したい。

実例:`ARC-AGI-3` 側 `docs/activity-log/_assets-history/state-machine/v001/`(複合状態 Solving/Consider/Plan を cluster、遷移を edge=0.5.0 のクラスタ端点エッジで表現したモデル)。

## 2. 根本原因

現行のクラスタ描画(仕様書の **A2 / ADR-009**)は:

> 各葉クラスタを独立 dot run でレイアウト → Python が宣言された `direction`(row/column)で**積む** → 最後に pinned neato で配線。

つまり **遷移エッジをレイアウトに使わない**(宣言構造で積み、配線は後付け)。だが状態機械・アクティビティは **エッジ(流れ)がレイアウトを決めるべき**図。Mermaid が綺麗なのは dagre/dot 系の**階層レイアウトがエッジに従う**から。現行方式とフロー図は相性が悪く、縦長で硬い絵になる。

## 3. PoC 検証結果(`poc/state-machine-dot/`)

`sm_to_dot.py` がモデル JSON を **dot ネイティブ**(複合状態=`subgraph cluster_*`、遷移=edge、クラスタ端点遷移=`lhead`/`ltail`+`compound=true`)へ変換し、1回の dot run で描画。

- **レイアウト品質**:`native_lr.png`(LR)は **Mermaid 同等以上にクリーン**(入れ子枠が整列、predict ループ・back-edge が自然配線)。`native.png`(TB)も A2 より明確に綺麗。**dot がエッジに従って並べる**のが効いている。
- **`.drawio` 再構築が可能**:`dot -Tjson` から **クラスタ `bb` 3/3・ノード `pos` 17・エッジ spline `_draw_` 20/20** を抽出できることを確認。座標は points・y-up・原点左下(`-Tplain` と同系統。既存の座標変換を流用、スケールは inch ではなく points)。
- 詳細は `poc/state-machine-dot/FINDINGS.md`。

**結論:dot ネイティブ・フローエンジンは有効。本実装する。**

## 4. 要望(0.6.0 仕様)

### 4.1 レイアウトエンジンを2系統にする

`options.engine` を追加。図の性格で使い分ける:

| `engine` | 対象 | 方式 |
| --- | --- | --- |
| **`cluster-dot`**(既定) | class / component / package / ER(**構造**図) | 現行 A2。あなたがクラスタツリーを組み、dot は各葉を組む、Python が合成 |
| **`dot`**(新規) | state machine / activity(**流れ**図) | グラフ全体を1回 dot に渡し、**dot が流れ・箱・配線を決める** |

- 既定 = `cluster-dot`(省略時。既存モデルは無改修で従来どおり)。
- `dot` エンジンの中身:
  1. 複合状態(labelled cluster)→ native `subgraph cluster_*`(label 付き)。
  2. 遷移 → edge。**クラスタ端点遷移**(0.5.0 の cluster-endpoint edge。例:`NewGame→solving`)→ 内部アンカーノード + `lhead`/`ltail`、`compound=true`。
  3. **1回の `dot -Tjson`** を実行 → node `pos` + cluster `bb` + edge spline を取得。
  4. points→draw.io px へ変換(既存変換を流用)→ native shape / 破線箱 / waypoint を emit。
  5. **自己ループ(self-transition)を描ける**(現行 A2/pinned は FR-D-15 で skip。状態機械に有用)。
- 将来拡張:`engine: "auto"`(`transition` 主体なら dot を自動選択)は **0.6.0 では対象外**(明示 opt-in を優先)。

### 4.2 命名(決定済み)

- 値は **`dot` / `cluster-dot`**。両方とも **dot を名前に出す**(=「こっそり dot」を避ける、オーナー要件)。
- 由来:`dot`=dot が全体を素直にレイアウト。`cluster-dot`=あなたが**クラスタツリーを組み**、dot は葉を組む。
- doc に一文必須:**両エンジンとも cluster 箱は描く**(「`dot`=クラスタ無し」と誤読させない)。

### 4.3 方向(direction)を `TB`/`LR` に統一(対称性)

「向き」は1概念。**全レベルで `direction: "TB" | "LR"` に統一**する(per-cluster と outermost の両方、両エンジンで対称)。

- `row`/`column` は **廃止** → 機械置換:**`column`→`TB`、`row`→`LR`**。banded 配置は `TB[ LR[a,b], c ]` で従来どおり表現可。
  - 緩和案(任意):移行期間は `row`/`column` を **deprecated 別名**として受理(`column`≡`TB`, `row`≡`LR`)。
- 既定 = **`TB`(縦)**。**オーナーは縦表示を強く好む**(縦スクロール前提。横スクロールは避ける)。
- エンジン別の効き方:
  - `cluster-dot`:per-cluster `direction`(子の並べ方)+ `options.direction`(省略時既定)。= 現行の挙動、語彙だけ TB/LR 化。
  - `dot`:**outermost(`options.direction`)のみ有効** → dot の `rankdir`。**per-cluster `direction` は無視 + stderr 警告**(dot に per-subgraph rankdir は無い。順序を `rank=same` で強制すると ADR-009 の segfault に逆戻り)。
- 任意:`dot` 側のみ `BT`/`RL` も許可してよい。
- キーは **`direction` 一本**(別途 `rankdir` キーは作らない)。値を TB/LR に統一することで対称性を担保。

## 5. 移行

- 既存モデルの `direction: row|column` → `TB|LR` へ一括置換(`ARC-AGI-3` の components v002 / `samples/*` / `tests/*`)。緩和案を採れば段階移行可。
- デモ:`state-machine` モデルに `"engine": "dot"`(+ 既定 `direction: TB`)を付けて再生成し、改善を可視化(縦のまま、A2 より読みやすいこと)。

## 6. 受入基準(実装が満たすこと)

1. `options.engine` で `dot` / `cluster-dot` を選べる。省略時 = `cluster-dot`(後方互換)。不正値は fail-fast。
2. `dot` エンジンで状態機械が **既定で縦(TB)**・エッジ駆動で描かれる。複合状態は dot `bb` から箱、ノードは `pos`、遷移は spline で配線(**クラスタ端点遷移**・**自己ループ**含む)。box 貫通なし。
3. `direction` は全レベル `TB`/`LR`(既定 `TB`)。`dot` は per-cluster `direction` を無視し **警告**。エンジンに合わない direction 値は fail-fast(または deprecated 別名で受理、採用した方針に従う)。
4. `cluster-dot` の描画は**従来どおり**(回帰なし)。row/column→TB/LR 移行後、既存テストが緑。
5. `dot` 出力は決定的(NFR-01)。`-Tplain`/`-Tjson` の長 id 折返し・引用符は既存 `_unwrap`/`_unq` 同様に処理。
6. docs(SKILL / reference / README)に `engine`・`direction` 統一・dot エンジンの使い分けを反映。
7. state-machine デモが再生成され、視覚的に改善している。

## 7. 非対象

- class / component / ER 等の**構造図は `cluster-dot` のまま**(意図的)。
- `engine: "auto"` 自動判定は将来。
- 0.6.0 は `dot` エンジン追加 + `direction` 統一が主眼。

## 8. 参照

- PoC・実証:`poc/state-machine-dot/`(`sm_to_dot.py`, `native*.png`, `FINDINGS.md`)。
- 現行仕様:`docs/spec-ja.md` — A2/ADR-009(クラスタ合成)、FR-D-17(cluster-endpoint edge / `cid`)、FR-D-03b/ADR-013(`-Tplain` の折返し+引用符)、FR-D-07(pinned routing)、`direction_to_rankdir`(`draw.py`)。
- 実装フロー(オーナー指定):**Spec 更新 → 敵対的レビュー → ソース更新 → 敵対的レビュー → テスト反復で緑 → 納品**。コミットはオーナーが手動(要所で依頼。AI は commit/push/tag しない)。
