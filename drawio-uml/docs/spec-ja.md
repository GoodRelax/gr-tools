# drawio-uml 仕様書

| 項目 | 値 |
| --- | --- |
| 文書種別 | ANMS v0.33 準拠 単一仕様書 |
| 対象 | `drawio-uml` ツールスイート(`draw` / `table`) |
| 版 | 0.2.2 |
| 最終更新 | 2026-06-13 |
| 配置 | `gr-tools/drawio-uml/docs/spec-ja.md`(SSOT) |

---

## Chapter 1. Foundation(基本事項)

### 1.1 Background(背景)

AI(LLM)は構造図(クラス図・コンポーネント図・状態機械図等)を「テキストモデルから生成する」用途で多用される。既存のテキスト駆動図ツール(Mermaid / PlantUML)は普及しているが、(a) 自動レイアウトの品質が低くエッジが非端点ノードのボックスを貫通しやすい、(b) 生成後に draw.io のような GUI で手編集できない、という弱点がある。一方 draw.io は GUI 編集に優れるが、図を手作業で組むため大規模図では手間と再現性に欠ける。

### 1.2 Issues(課題)

| ID | 課題 |
| --- | --- |
| IS-1 | Mermaid / PlantUML はレイアウト品質が低く、エッジが非端点ノードのボックスを貫通する。 |
| IS-2 | Mermaid / PlantUML の出力は GUI(draw.io)で継続編集できない。 |
| IS-3 | draw.io 手作業は大規模図で高コストかつ再現不能。 |
| IS-4 | 図を直接編集すると元モデルと乖離し、単一の真実源(SSOT)が失われる。 |
| IS-5 | クラスの責務説明・要素一覧など、図中に置くと可読性を損なう情報の置き場がない。 |

### 1.3 Goals(目標)

本スイートのコアコンセプトは次の3点である。各ゴールは操作的(検証可能)に定義する。

| ID | コアコンセプト(操作的定義) |
| --- | --- |
| GL-1 | **box-avoiding な UML を draw.io 形式で自動生成する。** 「box-avoiding」=どのエッジも自身の端点でないノードのボックス内部を通らないこと(IS-1 の解消)。出力は draw.io ネイティブ図形であり GUI 編集できる(IS-2 の解消)。 |
| GL-2 | **JSON モデルを SSOT とする。** 構造・文書・レイアウト指定をすべて単一の JSON に置き、成果物はそこから生成する(AI が単一入力を生成・編集できる)。 |
| GL-3 | **図に置くと可読性を損なう情報(各要素の責務 `description`・要素一覧)を、同じ JSON から Markdown 表に出力する。** |

注:「綺麗」「困難」等の主観語は背景・目標の導入のみで用い、要求(Chapter 2)では用いない。

### 1.4 Approach(解決方針)

- 単一の JSON モデル(以下「モデル」)を SSOT とし、そこから複数の成果物を**生成**する(成果物は手編集しない)。
- レイアウトは Graphviz `dot` に委譲する。`dot` がノード位置と直交エッジ経路(`splines=ortho`)を計算し、その経路を draw.io の waypoint として取り込む(GL-1)。
- スイートを2つの生成器に分割する:`draw`(モデル → `.drawio` 図)、`table`(モデル → `.md` 表)。両者は同一モデルを入力とする(GL-2, GL-3)。
- 実装は Python 3.10+ と Graphviz、図の画像化のみ draw.io CLI を用いる。

### 1.5 Scope(範囲)

**In-scope:**

- `draw`:`dot` がレイアウト可能なノード=リンク図の生成 — クラス / オブジェクト / コンポーネント / パッケージ / 配置 / 状態機械 / アクティビティ / ユースケース / ER。
- `draw`:クラスタ分け、凡例、帯状(banded)レイアウト、箱回避ルーティング(いずれもオプトイン)。
- `table`:モデルからの node 表・edge 表(Markdown)生成、クラスタ部分木の抽出。

**Out-of-scope:**

- シーケンス図・タイミング図(時間順のライフラインであり、グラフレイアウト問題ではない)。
- `draw` における多重(階層)クラスタの図示(本版では `table` のみ階層対応。ADR-005)。
- 生成物(`.drawio` / `.md` / `.svg` / `.png`)の手編集の支援。

### 1.6 Constraints(制約事項)

| ID | 制約 |
| --- | --- |
| CN-1 | オフラインで動作する SHALL。外部ネットワークサービスに依存しない。 |
| CN-2 | `draw` および `table` は Python 標準ライブラリのみで動作する SHALL(`json` / `re` / `subprocess` / `sys` / `xml`)。 |
| CN-3 | Graphviz `dot` を必須とする SHALL。clustered path の箱回避ルーティングは `neato` または `fdp` を用いる(MAY);いずれも無い場合の挙動は FR-D-07a に定義する。 |
| CN-4 | `.svg` / `.png` 化には draw.io CLI を用いる(図そのものの生成には不要)。 |
| CN-5 | SSOT は `gr-tools/drawio-uml` とする。配布先(グローバルスキル等)はコピーであり編集しない(ADR-007)。 |

### 1.7 Limitations(制限事項)

| ID | 制限 | 妥協の理由 |
| --- | --- | --- |
| LM-1 | `draw` は `cluster` 値を不透明な1ラベルとして扱い、階層クラスタを入れ子の箱として描かない。 | 図の階層レイアウトは大規模改修でありリスクが高く、現需要にない(ADR-005, YAGNI)。 |
| LM-2 | 自己参照(`source == target`)は経路描画されない(FR-D-15)。属性・ラベルで表現する。 | `splines=ortho` が自己ループを扱えない Graphviz の制約。 |
| LM-3 | シーケンス/タイミング図は生成できない。 | グラフレイアウト問題でないため(Out-of-scope)。 |
| LM-4 | `neato`/`fdp` がいずれも無い環境では box-avoiding を保証しない(FR-D-07a の degrade)。 | dot 単独では全エッジの事後箱回避ができないため。 |

### 1.8 Glossary(用語集)

| 用語 | 定義 |
| --- | --- |
| モデル (model) | スイートの唯一の入力。`options` / `nodes` / `edges` を持つ JSON オブジェクト。SSOT。 |
| node | 図の箱(クラス・状態・コンポーネント等)を表すモデル要素。 |
| edge | node 間の関係(継承・関連・依存等)を表すモデル要素。 |
| cluster | node が属するグループ。値は `/` 区切りの**パス文字列**(例 `"a/b/c"`)。 |
| stereotype | node 見出し上の `«...»` 表記。任意文字列。描画上の特別扱いは `interface`/`abstract`(イタリック化)・`object`(下線)のみ。 |
| italic | node の真偽値。`true` で見出し名を斜体にする(`stereotype` の `interface`/`abstract` による斜体化とは独立の明示指定。ただし shape=`object` の下線が優先する)。 |
| compartment | クラス/エンティティ/オブジェクトを名前・属性・操作の3区画で描く箱(swimlane)。 |
| box-avoiding | どのエッジも自身の端点でないノードのボックス内部を通らない状態。GL-1 の検証基準。 |
| flat path | クラスタ系キー(`cluster`(node) / `options.clusters` / `options.layout`)を持たないモデルの描画経路。最小コーナを原点 (40,40) に置く。 |
| clustered path | 上記クラスタ系キーのいずれかを持つモデルの描画経路。最小コーナを原点 (70,70)=`MARGIN` に置く。 |
| banded layout | `options.layout.rows` でクラスタを帯状(行)に配置するレイアウト。 |
| pinned routing | 全ノード位置を固定し `neato -n2`(失敗時 `fdp -n2` → `neato -n`)で全エッジを箱回避ルーティングする最終パス。 |
| suite(スイート) | `drawio-uml` 全体。生成器 `draw` と `table` を含む。 |
| draw | モデル → `.drawio` 図を生成する描画部(本体ファイル `draw.py`)。 |
| table | モデル → `.md` 表を生成する作表部(本体ファイル `table.py`)。 |
| description | node/edge の**責務を簡潔に表す主説明**(1行)。図には出ない。`table` が消費する。 |
| remark | description を**補足する従説明**(属性に現れない由来・ADR・制約)。図には出ない。`table` が消費する。 |
| common prefix(共通接頭) | 対象 node 群の cluster パスに共通する先頭セグメント列。`table` が表示時に除去する。 |

### 1.9 Notation(表記規約)

RFC 2119 / 8174 に準拠する。**SHALL/MUST**=必須、**SHOULD**=推奨、**MAY**=任意。EARS 構文中の `shall` は SHALL と同義。

---

## Chapter 2. Requirements(要求)

各 FR の受入シナリオは Chapter 4.1、FR×Scenario 対応は Chapter 5 のトレース表に示す。

### 2.1 Functional Requirements(機能要求)

#### 2.1.1 描画部 `draw`

ディスパッチ条件で用いる「クラスタ系キー」とは `cluster`(node) / `options.clusters` / `options.layout` の3つを指す(以下統一)。

- **FR-D-01**(Ubiquitous): `draw` は、モデル(JSON)を入力として `.drawio`(draw.io ネイティブ図形)を出力する SHALL。
- **FR-D-02**(Unwanted): If モデルがクラスタ系キーをいずれも持たない、then `draw` は flat path で描画する SHALL。flat path の出力は決定的であり、同一版での再生成と**バイト一致**する(NFR-01;回帰基準は ADR-003 参照)。
- **FR-D-03**(Event): When モデルがクラスタ系キーのいずれかを持つ、`draw` は clustered path(クラスタ箱・箱回避ルーティングを伴う)で描画する SHALL。
- **FR-D-04**(Event): When `options.layout.rows` が指定される、`draw` はクラスタを帯状(行)に配置する SHALL。row 0 を最上段とし、行内は列挙順に左→右、行は上→下に積む。
- **FR-D-05**(Ubiquitous): `draw` は次の形状をサポートする SHALL — class / entity / object / component / package / box / usecase / actor / state / action / decision / initial / final / note。未知の `shape` は `box` として描画する。`class` / `entity` / `object` は compartment(名前・属性・操作の3区画 swimlane)で描き、形状プリセットは適用しない。
- **FR-D-06**(Ubiquitous): `draw` は次のエッジ種別をサポートする SHALL — generalization / realization / composition / aggregation / directed_association / dependency / transition / association。未知・未指定の `arrow` は `association` として描画する。`generalization` / `realization` は親を上位ランクに置くため `dot` へ反転投入し、描画される矢印は子→親を向く。
- **FR-D-07**(State): While `neato` または `fdp` が PATH に存在する、clustered path において `draw` は全エッジ(内部・クラスタ間を問わず)を box-avoiding な経路で描く SHALL。
- **FR-D-07a**(Unwanted): If `neato` と `fdp` がいずれも PATH に無い、then `draw` は draw.io 自動ルーティングに degrade する SHALL。この場合 box-avoiding(GL-1)を保証しない(LM-4)。degrade の判別のため `draw` は stderr に警告を出す SHOULD(本版は未実装;実装フェーズで対応)。
- **FR-D-08**(State): While `description` / `remark` がモデルに存在する、`draw` はそれらを無視し図を不変に保つ SHALL(SSOT 共有のため)。
- **FR-D-09**(Unwanted): If 生成 XML が整形式(well-formed)でない、then `draw` は `minidom.parseString` が送出する例外を握り潰さず、書き出し前に非ゼロ終了する SHALL(fail fast)。
- **FR-D-10**(Optional): Where `node.style` が指定される、`draw` は形状プリセットおよび compartment 区画化(class/entity/object)を抑止し、当該 raw スタイルのみで描く SHALL。
- **FR-D-11**: 欠番(0.2.2 で削除。旧・後方互換エイリアス `classes`/`kind` の受理要求)。番号は再利用しない。
- **FR-D-12**(Event): When `options.clusters` が定義される、`draw` は凡例(クラスタ swatch + エッジ種別グリフ)を図の下に描く SHALL。エッジ種別グリフは composition / aggregation / association / dependency の4種を固定で描く(全 arrow 種別ではない)。`options.clusters` が無い場合は凡例を描かない。
- **FR-D-13**(Unwanted): If `node.cluster` が `options.clusters` に未定義のキーを指す、then `draw` は既定色 `#888888`・ラベル=キー文字列でクラスタ箱を描く SHALL(これは**色**の規定。**位置**は FR-D-14 が規定し両者は直交する。`options.layout` 使用時も、未定義キーを `rows` に列挙すれば既定色で配置される。`options.layout` 非使用時(`clusters` のみ)は、未定義キーも通常のクラスタとして `dot` の subgraph に配置される)。
- **FR-D-14**(Constraint): `options.layout.rows` はモデル中の全クラスタキーを列挙する SHALL(これは**位置**の規定。色は FR-D-13)。`rows` に列挙されないクラスタの node は位置が未定義となるため不可とする。`rows` が `options.clusters`/`node.cluster` に存在しないキーを含む場合、`draw` は当該キーを無視する SHALL。
- **FR-D-15**(Unwanted): If edge の `source == target`(自己参照)、then `draw` は当該エッジを経路描画から除外する SHALL(代替:自己参照は node 属性で表現する;LM-2)。

#### 2.1.2 作表部 `table`

- **FR-T-01**(Ubiquitous): `table` は、モデル(JSON)を入力として Markdown を出力する SHALL。
- **FR-T-02**(Ubiquitous): `table` は node 表を `| cluster | name | description | remark |` の列で生成する SHALL。
- **FR-T-03**(Ubiquitous): `table` は edge 表を `| arrow | source | target | label | description | remark |` の列で生成する SHALL。`arrow` はモデルの記述値をそのまま出力し(`draw` の未指定→`association` 解決は適用しない)、`arrow` 未指定の edge は当該セルを空とする。
- **FR-T-04**(Ubiquitous): `table` は cluster 列に、対象 node 群の cluster パスから共通接頭を除いた残りを `" / "` 区切りで表示する SHALL。対象 node が1件の場合は共通接頭が全長一致し得る(その帰結は FR-T-05)。
- **FR-T-05**(Unwanted): If 共通接頭の除去後に cluster 列が全行空になる、then `table` は cluster 列自体を出力しない SHALL。
- **FR-T-06**(Event): When `--cluster KEY` が指定される、`table` は KEY とその配下のみを対象とする SHALL。一致は `/` セグメント境界で行う(`a/b` は `a/b` と `a/b/*` に一致し、`a/bc` には一致しない)。`cluster` キーを持たない node は対象外とする。
- **FR-T-06a**(Unwanted): If `--cluster KEY` がどの node にも一致しない、then `table` は空の表(見出し行のみ)を出力し、警告を標準エラーに出す SHALL。
- **FR-T-07**(Event): When `--cluster KEY` が指定される、`table` は source または target の少なくとも一方が対象集合に属す edge を含める SHALL(片方向で十分)。指定なしの場合は全 edge を対象とする。
- **FR-T-08**(Ubiquitous): `table` はセル内の `|` を `\|` にエスケープし、`description` / `remark` 内の改行表現 `<br>` はそのまま出力する SHALL(セル内の実改行は使わない)。
- **FR-T-09**(Unwanted): If 必須フィールド(node の `name`、edge の `source` / `target`)が欠落、then `table` はエラーを報告して非ゼロ終了する SHALL。

#### 2.1.3 共通

- **FR-C-01**(Ubiquitous): `draw` と `table` は**同一のモデル JSON** を入力として受理する SHALL(SSOT)。
- **FR-C-02**: 欠番(再現性・冪等性の要求を NFR-01・NFR-04 に一元化したため。番号は再利用しない)。
- **FR-C-03**(Unwanted): If 入力ファイルが JSON として解析不能、then 生成器はエラーを報告して非ゼロ終了する SHALL。

(再現性・冪等性は重複を避けるため NFR-01・NFR-04 に一元化する。)

### 2.2 Non-Functional Requirements(非機能要求)

- **NFR-01**(再現性): 同一モデル + 同一版の生成器は、バイト一致する成果物を生成する SHALL。これを唯一の再現性基準とし、FR-D-02・Chapter 5 の回帰テストが参照する。
- **NFR-02**(可搬性): `draw` / `table` は Python 標準ライブラリのみに依存する SHALL(CN-2)。
- **NFR-03**(オフライン): 生成処理はネットワーク接続なしで完了する SHALL(CN-1)。
- **NFR-04**(副作用): 生成器は出力ファイル以外を変更しない SHALL(冪等な再実行が可能)。
- **NFR-05**(性能): 単一コア・メモリ4GB 相当の環境で、`.drawio` 生成のみ(画像化を除く)について 100 node / 200 edge 規模のモデルを 10 秒以内に処理する SHOULD。性能は努力目標であり回帰の合否には含めない。

---

## Chapter 3. Architecture(アーキテクチャ)

### 3.1 Architecture Concept(アーキテクチャ方式)

本スイートは Clean Architecture ではなく、**SSOT + パイプライン型ジェネレータ**である。凡例は機能区分で定義する(レイヤー色分けは生成「対象」の UML 図に適用するものであり、本ツール自身の構成図には機能色を用いる)。

| 区分 | 役割 | 色 | Hex |
| --- | --- | --- | --- |
| Model | SSOT(JSON 入力) | 橙 | `#FF8C00` |
| Generator | draw / table(変換ロジック) | ゴールド | `#FFD700` |
| External | Graphviz / draw.io CLI | 青 | `#87CEEB` |

### 3.2 Components(コンポーネント)

| コンポーネント | 区分 | 責務 |
| --- | --- | --- |
| Model | Model | `options` / `nodes` / `edges` を持つ JSON。両生成器の唯一の入力。 |
| draw | Generator | モデル → `.drawio`。`render()` が `uses_clusters()` で flat/clustered を振り分ける。 |
| ├ flat path | Generator | クラスタ系キーなし。`dot_layout` + `render_flat`。 |
| ├ clustered path | Generator | `dot_layout_clustered`(banded 含む) + `_route_pinned` + `render_clustered`。 |
| └ 共有レンダラ | Generator | `_node_cells` / `_edge_cell`(両 path 共通の図形・エッジ生成)。 |
| table | Generator | モデル → `.md`。node 表・edge 表生成、cluster パス処理、`--cluster` フィルタ。 |
| Graphviz | External | `dot`(レイアウト+ortho 経路)、`neato`/`fdp`(pinned routing)。 |
| draw.io CLI | External | `.drawio` → `.svg` / `.png`(任意)。 |

AI/LLM 連携:本スイートはモデル(JSON)を LLM が生成する前提だが、スイート自身は LLM を**呼び出さない**(プロンプトテンプレートを持たない)。生成物の妥当性は「生成 XML の整形式検証(FR-D-09)」「必須フィールド検証(FR-T-09)」「JSON 解析失敗の検出(FR-C-03)」で担保する。

### 3.3 File Structure(ファイル構成)

```
gr-tools/drawio-uml/                 ← SSOT(ここだけ編集する)
├── scripts/
│   ├── draw.py        描画部(モデル → .drawio)
│   └── table.py       作表部(モデル → .md;実装予定)
├── schema/
│   └── model.schema.json   入力スキーマ(JSON Schema draft-07)
├── tests/                  回帰フィクスチャ + 基準 .drawio
├── references/
│   └── drawio-uml-reference.md
├── docs/
│   └── spec-ja.md     本仕様書
├── README.md
└── SKILL.md
```

- **本版時点の現状:** `draw.py` はリネーム済み(ロジック不変)。`table.py` は実装予定(本仕様の対象)。`schema/model.schema.json`(JSON Schema)と `tests/`(回帰フィクスチャ + 基準 `.drawio`)は本版で追加した。
- 配布コピー(グローバルスキル等)・利用先リポジトリは本ディレクトリからの**コピー**であり、編集しない(ADR-007)。

### 3.4 Domain Model(ドメインモデル=モデルスキーマ)

```
model
├── options
│   ├── rankdir : "TB" | "LR"            既定 TB
│   ├── column_width / node_separation / rank_separation   レイアウト寸法
│   ├── clusters : { <key>: {label, stroke, fill} }   クラスタ定義(オプトイン)
│   └── layout   : { rows: [[<key>...]...] }          帯状配置(オプトイン;全クラスタを列挙)
├── nodes[ node ]
└── edges[ edge ]

node
├── name            (必須・一意)
├── shape           class|entity|object|component|package|box|usecase|actor|
│                   state|action|decision|initial|final|note(既定/未知は box)
├── stereotype / italic
├── cluster         "/" 区切りのパス文字列(例 "a/b/c")
├── attributes[] / methods[]   compartment の属性・操作行
├── fill / stroke / style / width / height
├── description     責務(主・1行)        ← table が消費 / draw は無視(FR-D-08)
└── remark          傍注(属性に出ない補足) ← table が消費 / draw は無視(FR-D-08)

edge
├── source / target (必須)
├── arrow           generalization|realization|composition|aggregation|
│                   directed_association|dependency|transition|association(未指定は association)
├── label           図に出る関係名
├── description     ← table が消費 / draw は無視
└── remark          ← table が消費 / draw は無視
```

`cluster` の解釈は dual-track:**`draw` は値全体を1つのクラスタ名(不透明文字列)として扱い**(LM-1)、**`table` は `/` で階層として解釈する**(FR-T-04, FR-T-06)。

補足(描画の優先・抑止規則):node の `fill`/`stroke` は cluster の `fill`/`stroke`(塗り・境界の提案)に**優先**する。`node.style` を持つ node は形状プリセットと compartment(`attributes`/`methods`)を**抑止**し raw style のみで描く(FR-D-10)。

### 3.5 Behavior(振る舞い)

**draw の処理フロー:**

1. モデル読込(`json.load`, UTF-8;失敗時 FR-C-03)。
2. `uses_clusters(model)` 判定(クラスタ系キーの有無)。
3. 偽 → flat path:`dot_layout`(`dot -Tplain`)→ 最小コーナを原点 **(40,40)** に平行移動 → `render_flat`。
4. 真 → clustered path:`dot_layout_clustered`(`layout.rows` あれば banded)→ 最小コーナを原点 **(70,70)=MARGIN** に配置 → `_route_pinned` → `render_clustered`(z 順:クラスタ箱 → node → edge → 凡例)。原点が flat と異なるのは、クラスタラベル用の余白を確保するためである。
5. `_route_pinned` は `neato -n2` → `fdp -n2` → `neato -n` の順に試行。いずれも不在/失敗なら空の経路表を返し draw.io 自動ルーティングに degrade する(FR-D-07a)。
6. `minidom.parseString` で整形式検証(FR-D-09)→ ファイル書き出し。

**table の処理フロー:**

1. モデル読込。必須フィールド検証(FR-T-09)。
2. `--cluster` で対象 node 集合を確定(`/` セグメント境界の前方一致;指定なしは全件;FR-T-06)。
3. 対象 node の cluster パスから共通接頭を計算・除去。残りが全空なら cluster 列を落とす(FR-T-05)。
4. node 表を生成(FR-T-02)。
5. edge を対象集合でフィルタ(source/target の一方が対象なら採用;FR-T-07)。
6. edge 表を生成(FR-T-03)。
7. セル `|` を `\|` にエスケープ、`<br>` は素通し → `.md` 書き出し(FR-T-08)。

### 3.6 Decisions(設計判断 / ADR)

各 ADR の決定者は人間(プロジェクトオーナー)である。形式:Status / Context / Decision / Alternatives / Consequences。

**ADR-001 — JSON モデルを SSOT とし、生成物は手編集しない**
*Status:* Accepted / *Context:* 図を直接編集すると元モデルと乖離する(IS-4)。/ *Decision:* モデル(JSON)を唯一の真実源とし、`.drawio` / `.md` は生成物として扱う。/ *Alternatives:* 図(.drawio)を正とし JSON を従とする案 → AI が編集しにくく IS-4 を解決しないため却下。/ *Consequences:* 成果物の手編集は禁止。変更はモデルに加え再生成する。

**ADR-002 — レイアウトを Graphviz `dot` に委譲する**
*Status:* Accepted / *Context:* Mermaid/PlantUML はレイアウトが弱くエッジが箱を貫通する(IS-1)。/ *Decision:* `dot` に位置と `splines=ortho` 経路を計算させ、経路を draw.io の waypoint として取り込む。/ *Alternatives:* (a) PlantUML 内蔵レイアウト → GUI 編集不可・IS-1 を解決しない。(b) `neato`/`sfdp` を主レイアウトに → ノードリンク図の階層表現で `dot` に劣る(`neato` は本スイートでは事後ルーティング専用)。/ *Consequences:* box-avoiding を達成(GL-1)。Graphviz への依存が生じる(CN-3)。

**ADR-003 — flat / clustered の2経路に分け、flat は出力安定性を保つ**
*Status:* Accepted / *Context:* 既存利用および従来のフラット版スキルとの互換が必要。/ *Decision:* クラスタ系キーがないモデルは従来コード経路をそのまま通す。flat path の出力は版間で安定させ、回帰基準(前版の出力 `.drawio`)と md5 比較する。/ *Alternatives:* 単一経路に統合 → 既存出力が変わり回帰が壊れるため却下。/ *Consequences:* 後方互換が保たれる(FR-D-02, NFR-01)。2経路の保守コストが生じる。

**ADR-004 — スイート名 `drawio-uml`、サブ機能 `draw` / `table`**
*Status:* Accepted / *Context:* `drawio_uml` と `uml_table` の非対称が問題視された。/ *Decision:* スイート名は draw.io 出力が肝である点を表す `drawio-uml` とし、機能は動詞 `draw`(描く)/ `table`(表にする)で対称にする。描画本体は `draw.py` にリネーム(ロジック不変)。/ *Alternatives:* `uml_drawio`(語順で肝の draw.io が修飾に落ちる)・`umlkit`/`umlcast`(draw.io 固有性が消える)を却下。/ *Consequences:* 対称な命名体系。将来 `build` 等のサブ機能を追加できる。

**ADR-005 — `cluster` はパス文字列。階層対応は `table` のみ、`draw` は当面フラット**
*Status:* Accepted / *Context:* 作表はパス処理で階層対応が容易だが、図の階層レイアウトは大規模改修でリスクが高く、現需要にない。/ *Decision:* `cluster` をパス文字列で統一し、`table` のみ階層解釈する。`draw` は値全体を1ラベルとして扱う。/ *Alternatives:* `draw` も入れ子 `subgraph cluster` で階層図示する案 → レイアウト再帰化・入れ子ボックス・クラスタ間ルーティングの大改修でリスク高、ARC 等の現利用はフラットで足りるため却下(YAGNI)。/ *Consequences:* `table` は階層対応(FR-T-04)。`draw` の階層図示は将来課題(LM-1)。

**ADR-006 — `description` / `remark` をモデルに追加し、`draw` は無視・`table` が消費**
*Status:* Accepted / *Context:* 図で表現困難な責務説明・一覧の置き場がない(IS-5)。/ *Decision:* 文書系フィールド `description`(責務)/ `remark`(傍注)をモデルに置き、`draw` は無視、`table` が表に出す。/ *Alternatives:* 解説を別 `.md` に手書きする案 → モデルと二重管理になり IS-4 を再発させるため却下。/ *Consequences:* 構造も文書も単一 SSOT に集約(GL-3)。`draw` 出力は不変(FR-D-08)。

**ADR-007 — SSOT は `gr-tools/drawio-uml`、他は配布コピー(編集禁止)**
*Status:* Accepted / *Context:* 同一ツールがスキル・利用先に分散コピーされていた。/ *Decision:* `gr-tools/drawio-uml` を唯一の編集点とし、他はコピーとする。/ *Alternatives:* 各所で個別編集 → 版が分岐し SSOT を失うため却下。/ *Consequences:* 単一真実源。配布(同期)手順が必要。

**ADR-008 — ルーティング不能時は draw.io 自動ルーティングへ degrade する**
*Status:* Accepted / *Context:* clustered path の box-avoiding は `neato`/`fdp` に依存するが、これらが無い環境がありうる(CN-3)。/ *Decision:* `neato`/`fdp` がいずれも使えない場合、異常終了せず draw.io 自動ルーティングに degrade する(box-avoiding は保証しない)。/ *Alternatives:* 異常終了する案 → 図自体は生成可能なのにツールが止まり可用性を損なうため却下。/ *Consequences:* 可用性を優先(FR-D-07a)。degrade 時は GL-1 を満たさない(LM-4)。degrade 判別用の stderr 警告は SHOULD だが本版未実装(FR-D-07a)。

---

## Chapter 4. Specification(仕様)

### 4.1 Scenarios(シナリオ / Gherkin)

```gherkin
Feature: draw — モデルから .drawio を生成

  Scenario: SC-001 基本入出力 (traces: FR-D-01)
    Given 妥当なモデル JSON
    When  draw.py MODEL.json OUT.drawio を実行する
    Then  OUT.drawio が draw.io ネイティブ図形として生成される

  Scenario: SC-002 クラスタなしモデルは flat path で出力安定 (traces: FR-D-02, NFR-01)
    Given クラスタ系キーを持たないモデル
    When  draw.py で .drawio を生成する
    Then  同一版での再生成と md5 がバイト一致する
    And   最小コーナが原点 (40,40) に配置される

  Scenario: SC-003 クラスタありモデルは箱回避経路を持つ (traces: FR-D-03, FR-D-07)
    Given options.clusters と node.cluster を持つモデル
    And   neato または fdp が PATH に存在する
    When  draw.py で .drawio を生成する
    Then  いずれのエッジも非端点ノードのボックスを貫通しない

  Scenario: SC-004 凡例の描画 (traces: FR-D-12)
    Given options.clusters が定義されたモデル
    When  draw.py で .drawio を生成する
    Then  図の下にクラスタ swatch とエッジ種別グリフの凡例が描かれる

  Scenario: SC-005 帯状レイアウト (traces: FR-D-04)
    Given options.layout.rows = [["a","b"],["c"]] と対応クラスタを持つモデル
    When  draw.py で .drawio を生成する
    Then  row 0 の a,b が上段に左→右、c が下段に配置される

  Scenario: SC-006 ルーティングエンジン不在時の degrade (traces: FR-D-07a)
    Given options.clusters を持つモデル
    And   neato も fdp も PATH に存在しない
    When  draw.py で .drawio を生成する
    Then  draw.io 自動ルーティングに degrade して .drawio を生成する
    But   box-avoiding は保証されない

  Scenario: SC-007 未定義クラスタキー (traces: FR-D-13)
    Given options.clusters に定義のないキーを node.cluster が指すモデル
    When  draw.py で .drawio を生成する
    Then  当該クラスタ箱は色 #888888・ラベル=キー文字列で描かれる

  Scenario: SC-008 description/remark は図に影響しない (traces: FR-D-08)
    Given 既存モデルに description と remark を追加したモデル
    And   同一環境・同一描画経路(flat / clustered)で生成する
    When  draw.py で .drawio を生成する
    Then  追加前の .drawio とバイト一致する

  Scenario: SC-009 自己参照エッジの除外 (traces: FR-D-15)
    Given source と target が同一の edge を含むモデル
    When  draw.py で .drawio を生成する
    Then  当該エッジは経路描画されない

  Scenario: SC-010 style 上書きは compartment を抑止 (traces: FR-D-10)
    Given shape=class かつ style を持つ node
    When  draw.py で .drawio を生成する
    Then  当該 node は区画化されず raw style で描かれる


  Scenario: SC-012 不正 XML は異常終了 (traces: FR-D-09)
    Given 整形式でない XML を生成させる入力
    When  draw.py を実行する
    Then  書き出し前に非ゼロ終了する

  Scenario: SC-013 不正 JSON は異常終了 (traces: FR-C-03)
    Given JSON として解析不能なファイル
    When  draw.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-014 rows の余分キーは無視 (traces: FR-D-14)
    Given options.layout.rows が options.clusters に無いキーを含むモデル
    When  draw.py で .drawio を生成する
    Then  当該キーは無視され、図に影響しない

  Scenario: SC-015 未知 shape は box (traces: FR-D-05)
    Given shape にカタログ外の値を持つ node
    When  draw.py で .drawio を生成する
    Then  当該 node は box(汎用の箱)として描画される

  Scenario: SC-016 未指定 arrow は association (traces: FR-D-06)
    Given arrow を持たない edge
    When  draw.py で .drawio を生成する
    Then  当該 edge は association(矢印なしの線)として描画される
```

```gherkin
Feature: table — モデルから .md を生成

  Scenario: SC-101 node 表の既定列 (traces: FR-T-01, FR-T-02, FR-T-04)
    Given cluster を持つモデル
    When  table.py で .md を生成する
    Then  node 表が | cluster | name | description | remark | を持つ
    And   cluster 列は共通接頭を除いたパスを " / " で表示する

  Scenario: SC-102 共通接頭除去で全空なら列消滅 (traces: FR-T-05)
    Given 全 node が単一クラスタ直下にあるモデル
    When  table.py で .md を生成する
    Then  cluster 列は出力されず | name | description | remark | になる

  Scenario: SC-103 edge 表とクラスタフィルタ (traces: FR-T-03, FR-T-06, FR-T-07)
    Given 階層 cluster を持つモデル
    When  table.py を --cluster a/b 付きで実行する
    Then  対象は a/b と a/b/* の node に限られ a/bc は含まれない
    And   source か target の一方が対象である edge を含む

  Scenario: SC-104 セルのエスケープと改行 (traces: FR-T-08)
    Given description に "|" と "<br>" を含むモデル
    When  table.py で .md を生成する
    Then  セル内の "|" は "\|" に変換される
    And   "<br>" はそのまま出力される

  Scenario: SC-105 一致0件は空表と警告 (traces: FR-T-06a)
    Given どの node にも一致しない --cluster 指定
    When  table.py を実行する
    Then  見出し行のみの表を出力し、警告を標準エラーに出す

  Scenario: SC-106 必須欠落は異常終了 (traces: FR-T-09)
    Given source を欠く edge を含むモデル
    When  table.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-107 未指定 arrow は空セル (traces: FR-T-03)
    Given arrow を持たない edge を含むモデル
    When  table.py で .md を生成する
    Then  edge 表の当該 arrow セルは空になる(`association` に解決しない)
```

**Result:** SKIP  **Remark:** `table` は新規実装対象。`draw` シナリオは実装(`draw.py`)に対し次フェーズで検証する。SC-011 は欠番(0.2.2 でエイリアス受入シナリオを削除)。SC-012 は整形式でない XML の生成経路が `esc()` により通常到達不能のため、検証は fault injection を前提とする。

### 4.2 CLI Definition(コマンド定義)

| 生成器 | コマンド | 主オプション |
| --- | --- | --- |
| draw | `python draw.py MODEL.json OUT.drawio` | (なし) |
| table | `python table.py MODEL.json OUT.md [--cluster KEY]` | `--cluster`:対象部分木(`/` セグメント前方一致) |

`.svg` / `.png` 化(draw のみ・任意):`drawio -x -f png -e -b 12 -o OUT.drawio.png OUT.drawio`。

### 4.3 Output Format(`table` の Markdown 出力形式)

- 出力は1つの `.md` に「node 表」「edge 表」の2セクションを順に含む。
- セル区切り `|` のエスケープは `\|`。改行は `<br>`(セル内実改行は使わない)。
- cluster 列はパス階層の共通接頭を除いた表示。除去後に全行空なら列を省く(FR-T-05)。

---

## Chapter 5. Test Strategy(テスト戦略)

| テストレベル | 対象 | 方針 | 合格基準 |
| --- | --- | --- | --- |
| 単体 | `table` の純関数(共通接頭計算 / セルエスケープ / cluster フィルタ) | 入出力ペアで検証 | 合格率 100% |
| 回帰 | `draw` flat path | 既知モデルの出力を基準 `.drawio` と md5 比較(NFR-01) | バイト一致 |
| 結合 | model → draw → `.svg`、model → table → `.md` | 代表モデルで端から端まで | 例外なく完了 |
| 受入 | Ch4.1 シナリオ | Gherkin に対応 | 全シナリオ PASS |

**FR × Scenario トレース表(受入カバレッジ):**

| FR | 検証シナリオ | FR | 検証シナリオ |
| --- | --- | --- | --- |
| FR-D-01 | SC-001 | FR-D-14 | SC-005 / SC-014 |
| FR-D-02 | SC-002 | FR-D-15 | SC-009 |
| FR-D-03 | SC-003 | FR-T-01 | SC-101 |
| FR-D-04 | SC-005 | FR-T-02 | SC-101 |
| FR-D-05 | SC-001 / SC-015 | FR-T-03 | SC-103 / SC-107 |
| FR-D-06 | SC-003 / SC-016 | FR-T-04 | SC-101 |
| FR-D-07 | SC-003 | FR-T-05 | SC-102 |
| FR-D-07a | SC-006 | FR-T-06 / 07 | SC-103 |
| FR-D-08 | SC-008 | FR-T-06a | SC-105 |
| FR-D-09 | SC-012 | FR-T-08 | SC-104 |
| FR-D-10 | SC-010 | FR-T-09 | SC-106 |
| FR-D-12 | SC-004 | FR-C-01 | SC-001 / SC-101(同一入力) |
| FR-D-13 | SC-007 | FR-C-03 | SC-013 |

個別テストケースの詳細は実装フェーズで AI が生成する。

---

## Chapter 6. Design Principles Compliance(SW設計原則 準拠確認)

| カテゴリ | 原則 | 確認観点と本スイートでの準拠 |
| --- | --- | --- |
| 命名 | Naming | `draw` / `table` は動詞で対称。`description` / `remark` は C4/UML 慣習に沿う(用語集 1.8 と一致)。 |
| 簡潔性 | KISS | `table` の cluster はパス文字列1本で階層を表現(列展開しない)。 |
| 簡潔性 | YAGNI | `draw` の階層クラスタは需要が出るまで作らない(ADR-005, LM-1)。 |
| 簡潔性 | DRY | 構造・責務を JSON に一元化(IS-4/IS-5 解消)。再現性記述を NFR-01 に一元化。`_node_cells`/`_edge_cell` を両 path で共有。 |
| 責務分離 | SRP / SoC | `draw`=図、`table`=表で分割。レイアウト(dot)とレンダリング(XML)を分離。 |
| SOLID | OCP | 形状・エッジ種別は辞書(`SHAPES` / `ARROW`)で拡張、分岐を増やさない。 |
| 純粋性 | Pure/Impure | レイアウト計算と I/O(`subprocess` / ファイル書込)を関数境界で分離。 |
| エラー | Error Propagation | XML 整形式検証(FR-D-09)・必須検証(FR-T-09)・JSON 解析失敗(FR-C-03)で握り潰さず非ゼロ終了。ルーティング不能は degrade(ADR-008)。 |
| 可搬性 | (標準のみ) | 標準ライブラリのみ依存(NFR-02)。 |

---

## Appendix(付録)

### A.1 References(参考文献)

1. Graphviz — `dot` レイアウトと `-Tplain` 出力、`neato -n2`/`fdp -n2` の pinned routing。
2. draw.io / diagrams.net — mxGraph 図形と CLI エクスポート。
3. Mermaid / PlantUML — 比較対象(テキスト駆動図ツール)。
4. ANMS v0.33 — 本仕様書のテンプレート(`gr-sw-maker/process-rules/spec-template-ja.md`)。
5. レビュー観点規約 R1–R6(`gr-sw-maker/process-rules/review-standards-ja.md`)。

### A.2 Changelog(変更履歴)

| 版 | 日付 | 変更 |
| --- | --- | --- |
| 0.1.0 | 2026-06-13 | 初版。描画部(既存)の仕様化 + 作表部(新規)の仕様定義。 |
| 0.2.0 | 2026-06-13 | 敵対的レビュー(R1–R6)15件を反映。FR-D-07a/12/13/14/15・FR-T-06a 追加、ADR-008 追加、GL/IS の操作的定義化、原点座標・degrade・トレース表を明記、再現性記述を NFR-01 に一元化。 |
| 0.2.1 | 2026-06-13 | 再レビューの新規 Low 3件を反映。FR-D-07a に degrade 警告 SHOULD(未実装)、FR-D-09 を例外非捕捉の表現に、SC-014(rows 余分キー無視)追加、SC-012 到達性を Remark 明記。 |
| 0.2.2 | 2026-06-13 | 後方互換エイリアス(classes/kind)を全廃(FR-D-11・SC-011 削除;FR-D-11 は欠番)。命名整理:w/h→width/height・attrs→attributes・col_w/nodesep/ranksep→column_width/node_separation/rank_separation・cluster の color/tint→stroke/fill。arrow を UML 正式名(generalization/realization/composition/aggregation/directed_association/dependency/transition/association;未指定は association)、shape の node→box。description=責務(主)/remark=補足(従)を用語集で明確化。レビュー指摘を反映:配置を `docs/` に修正、FR-D-11 欠番マーカー追記、`italic` を用語集に定義、FR-T-03 に未指定 `arrow` の出力規定、FR-D-13/14 の色×位置の直交を明記、SC-015/016(未知 shape→box・未指定 arrow→association)追加。 |
