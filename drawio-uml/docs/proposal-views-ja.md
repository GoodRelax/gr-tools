# drawio-uml 機能提案書 — Views(関心事ごとの小ビュー分割)

> **【SUPERSEDED — 2026-06-13】** 本提案は **spec 0.3.0(`docs/spec-ja.md`)の ADR-010・FR-D-16/16a・FR-T-10/10a に統合・実装済み**。本書記載の旧形式は 0.3.0 と異なる:views は `options.views` ではなく **top-level `views`**、cluster 参照は `/` 前方一致ではなく **`cluster.name`**、`--view`/`--cluster` は **排他**、本書独自の「ADR-009 = Views」番号は spec では **ADR-010**(ADR-009 は layout ツリー)。**正は spec 0.3.0**。本書は起案の経緯記録として残置する。

| 項目 | 値 |
| --- | --- |
| 文書種別 | 機能提案書(Proposal → 承認後に spec-ja.md へ反映) |
| 対象 | `drawio-uml` スイート(`draw` / `table`) |
| 基底版 | spec-ja.md 0.2.2 |
| 状態 | Proposed(レビュー待ち) |
| 日付 | 2026-06-13 |
| 起案元 | ARC-AGI-3 ドメインモデル協議(18 node / 26 edge の単一図が判読困難) |

---

## 1. 背景・課題

ノードリンク図は1枚に詰め込むと読めない(可読限界 ≒ 7–12 箱)。ARC ドメインモデルは
18 node / 26 edge で、単一図にすると判読困難であることが実地で確認された。

既存の調整手段(`options.layout.rows` / `node_separation` / `rank_separation`)は
**配置の微調整**であって、「関心事ごとに小さく見せる」需要には応えない。さらに
クラスタ内の段(rank)・左右順・座標を per-node に指定する手段は公開しておらず
(レイアウトは `dot` に委譲)、自動レイアウトを手で矯正するのは設計上不毛である。

ベストプラクティスは **「完全さ=モデル(SSOT)/ 読みやすさ=複数の小ビュー」** の分離。
1つの SSOT から関心事別の部分図を生成する手段を提供する。

| ID | 課題(追加) |
| --- | --- |
| IS-6 | 大規模モデルを単一図にすると判読不能。関心事単位の部分ビューを生成する手段がない。 |

---

## 2. 提案概要

モデルに **`options.views`** を追加する。各ビューは SSOT のノード部分集合を
**名前付きで選ぶ純粋フィルタ**であり、ノード/エッジを**追加も改変もしない**。

- `draw` と `table` の双方が `--view KEY` を受理し、当該ビューの**誘導部分グラフ**
  (両端が集合内のエッジのみ)を出力する。
- `--view` 無指定時は全体を出力する(現行どおり・**バイト一致**)。

これにより、ひとつの SSOT から関心事ごとに「小さく読める図 + 対応する責務表」を
同時に得られる。

---

## 3. データ形式

`options` 配下に `views` を追加(オプトイン):

```json
{
  "options": {
    "views": {
      "answer": { "label": "The Conception (answer)",
                  "nodes": ["Conception", "WorldModel", "GoalPredicate", "Step", "GamePlan"] },
      "world":  { "label": "World & prediction",
                  "nodes": ["WorldModel", "InteractionRule", "PiStateAbstraction", "MarkovState", "GoalPredicate"] },
      "vocab":  { "label": "Vocabulary",
                  "clusters": ["vocabulary"] }
    }
  }
}
```

| キー | 位置 | 意味 |
| --- | --- | --- |
| `views` | `options` 配下 | `{ "<viewKey>": <view> }` のマップ(オプトイン) |
| `label` | view | 図タイトル / 表見出し用の表示名(省略時は `<viewKey>`) |
| `nodes` | view | このビューに含める node 名の明示列挙 |
| `clusters` | view | 指定クラスタ配下の全 node を含める短縮指定(`/` セグメント前方一致、FR-T-06 と同規則) |

`nodes` と `clusters` の少なくとも一方を持つ。両方ある場合は和集合。

### model.schema.json 追加(draft-07)

```json
"views": {
  "type": "object",
  "additionalProperties": {
    "type": "object",
    "properties": {
      "label":    { "type": "string" },
      "nodes":    { "type": "array", "items": { "type": "string" } },
      "clusters": { "type": "array", "items": { "type": "string" } }
    },
    "anyOf": [ { "required": ["nodes"] }, { "required": ["clusters"] } ],
    "additionalProperties": false
  }
}
```

---

## 4. セマンティクス

1. **ノード集合** = `nodes`(明示名)∪ `members(clusters)`(指定クラスタ配下の全 node)。
2. **エッジ** = source と target の**両端が集合内**のもののみ(誘導部分グラフ=induced subgraph)。
   片端が集合外のエッジは描かない(宙ぶらりんの線を出さない)。
3. **クラスタ箱・凡例・`layout.rows`** は集合内に存在するクラスタだけに**自動フィルタ**する
   (空クラスタは band と legend から除外。既存 FR-D-14「rows の不在キーは無視」を流用)。
4. ノードは**複数ビューに属してよい**(例:`Conception` は answer と loop の双方)。
5. ビューは**選ぶだけ**。node/edge を追加・改変しない(SSOT 不変条件)。
6. `--view` 無指定時の出力は本機能導入前と**バイト一致**(NFR-01)。

### 既知の限界(設計上の帰結)

誘導部分グラフは**構造ビュー**に適する(選んだ node 間の構造エッジが揃う)。
一方、`perceive → consider → act` のような**振る舞いの流れ**はモデルに対応する
構造エッジを持たないため、ビューにすると関係ノードが孤立する。
**ループ全体像は本機能の対象外**であり、別途フロー図等で表現する
(「クラス図は構造、振る舞いは別」)。境界ノードを薄く出す `neighbors`(ゴースト)は
将来オプション(§8 ロードマップ)。

---

## 5. CLI

```bash
draw  MODEL.json OUT.drawio  --view answer     # ビュー answer の図のみ
table MODEL.json OUT.md      --view answer     # ビュー answer の責務表のみ
draw  MODEL.json OUT.drawio                    # 無指定 = 全体(現行・バイト一致)
```

- 短縮形 `-v` を `--view` のエイリアスとする(任意)。
- `table` の既存 `--cluster`(FR-T-06/07, サブツリー選択)とは**別概念**:
  `--cluster` は source/target の**一方**が対象なら含める(文脈重視)、
  `--view` は**両端**が集合内のみ(誘導部分グラフ)。両者は**排他**(同時指定はエラー)。
- 未知の `--view KEY`、またはビューが参照する未知 node 名は **fail fast**(非ゼロ終了)。

---

## 6. 命名・決定(確定)

| ID | 決定 | 代案 | 根拠 |
| --- | --- | --- | --- |
| D1 | ブロック名 = `views` | lenses / boards / subsets | `clusters`/`layout` と並列。業界標準語(Structurizr=views, D2=boards) |
| D2 | node 選択キー = `nodes` | include / members / select | 最も明快。top-level `nodes` と文脈で混同しない |
| D3 | `clusters` 短縮を併設 | `nodes` のみ | 全クラスタ系ビューが1行で書け、クラスタへの node 追加に自動追随 |
| D4 | 検証 = fail fast | warn+skip | 改名・打鍵ミスを即検出。FR-T-09 と同方針 |

---

## 7. 仕様反映案(承認後に spec-ja.md へ)

### 機能要求(追加)

- **FR-D-16**(Event): When `--view KEY` が与えられ KEY が `options.views` に存在する、
  `draw` は当該ビューの**誘導部分グラフ**(node = `nodes` ∪ `members(clusters)`;
  edge = 両端が集合内)のみを描画する SHALL。クラスタ箱・band・凡例は集合内に
  存在するクラスタに限定する SHALL。`--view` 無指定時は全体を描画する(現行不変)。
- **FR-D-16a**(Unwanted): If `--view KEY` の KEY が `options.views` に無い、または
  いずれかのビューが存在しない node 名を参照する、then `draw` はエラーを報告して
  非ゼロ終了する SHALL(fail fast)。
- **FR-T-10**(Event): When `--view KEY` が与えられる、`table` は node 表・edge 表を
  当該ビュー(同一ノード集合・両端誘導エッジ)に限定する SHALL。
- **FR-T-10a**(Unwanted): If `--view` と `--cluster` が同時指定される、then `table` は
  エラーを報告して非ゼロ終了する SHALL(排他)。
- **FR-C-04**(Constraint): `options.views` は任意のマップ。各エントリは `label?` /
  `nodes?` / `clusters?` を持ち、`nodes` と `clusters` の少なくとも一方を持つ SHALL。
  `clusters` の一致は `/` セグメント境界の前方一致(FR-T-06 と同規則)とする SHALL。

### 設計判断(追加)

- **ADR-009 — Views:SSOT 内の純粋フィルタ。draw/table 双方が消費**
  *Status:* Proposed /
  *Context:* 大規模モデルの単一図は判読不能(IS-6)。レイアウト調整では関心事分割を
  解決できず、per-node のレイアウト制御も非公開。 /
  *Decision:* `options.views` に名前付きノード部分集合を置き、`--view` で `draw`/`table`
  双方が誘導部分グラフを出力する。エッジは両端が集合内のもののみ。 /
  *Alternatives:* (a) ビューごとに別 model ファイル → モデルと乖離し SSOT を失う(IS-4 再発)。
  (b) node に tag を持たせる分散方式 → 少数の厳選ビュー集合の管理に不向き・全 node を汚す。
  (c) `--cluster` 流用のみ → クラスタ内部分集合(例「Conception の内訳」)を表現できず粗い。 /
  *Consequences:* 単一 SSOT から関心事別の図+責務表が得られる。ビューは構造を追加・改変
  しない(純フィルタ)。振る舞い/フロー全体像は対象外(誘導部分グラフは既存の構造
  エッジしか描かない)。

### 受入シナリオ(追加)

```gherkin
  Scenario: SC-017 draw --view は誘導部分グラフを描く (traces: FR-D-16)
    Given options.views.answer を持つモデル
    When  draw.py MODEL.json OUT.drawio --view answer を実行する
    Then  answer のノードと、その両端が集合内のエッジだけが描かれる
    And   集合内に node を持たないクラスタは band と凡例から除外される

  Scenario: SC-018 未知ビュー/未知ノードは異常終了 (traces: FR-D-16a)
    Given 存在しない --view KEY、または未知 node を参照するビュー
    When  draw.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-019 --view 無指定は導入前とバイト一致 (traces: FR-D-16, NFR-01)
    Given options.views を持つモデル
    When  draw.py を --view なしで実行する
    Then  views 追加前の .drawio とバイト一致する

  Scenario: SC-108 table --view はビューに限定する (traces: FR-T-10)
    Given options.views.answer を持つモデル
    When  table.py MODEL.json OUT.md --view answer を実行する
    Then  node 表・edge 表が answer のノード集合と両端誘導エッジに限定される

  Scenario: SC-109 --view と --cluster の同時指定は異常終了 (traces: FR-T-10a)
    Given --view と --cluster の両方
    When  table.py を実行する
    Then  エラーを報告して非ゼロ終了する
```

### テスト

- `tests/` に views フィクスチャを追加。`--view` あり/なしの回帰(なし=既存基準とバイト一致)。
- 誘導エッジ・空クラスタ除外・fail fast(未知キー/未知ノード/排他)を単体+受入で検証。

---

## 8. 後方互換・再現性

- `--view` 無指定の出力は本機能導入前と**バイト一致**(NFR-01・FR-D-02 を維持)。
- `options.views` を持たないモデルは一切影響を受けない(完全オプトイン)。

---

## 9. 配布(ADR-007)

実装は **SSOT = `gr-tools/drawio-uml`** に対して行い、配布コピー(グローバルスキル等)へ
**再配布**する。コピーは編集しない。

---

## 10. ロードマップ(本提案では作らない / YAGNI)

| 項目 | 内容 |
| --- | --- |
| `exclude` | ビューから特定 node を除外 |
| `neighbors`(ghost) | 境界ノードを薄く描いて文脈を補う(振る舞い/フロー寄りビュー向け) |
| view 単位 `layout` 上書き | ビューごとに band 構成を変える |
| `--view all` | 全ビューを一括生成(`OUT.<viewKey>.drawio`) |

---

## 11. レビュー観点(起案者メモ)

- 命名 D1–D4 は確定。`label` 省略時の既定= viewKey でよいか。
- `clusters` 短縮のサブツリー一致を `--cluster` と完全一致させる点の確認。
- `--view`/`--cluster` 排他の是非(片方優先にするか、エラーにするか)。本提案はエラー。
- 凡例(FR-D-12)を view 時に「存在クラスタのみ」に絞る点の明文化。
