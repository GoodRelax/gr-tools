# drawio-uml 仕様書

| 項目 | 値 |
| --- | --- |
| 文書種別 | ANMS v0.33 準拠 単一仕様書 |
| 対象 | `drawio-uml` ツールスイート(`draw` / `table`) |
| 版 | 0.5.0 |
| 最終更新 | 2026-06-14 |
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
| IS-6 | クラスタ(レイヤ/モジュール境界)自体を端点とする関係(例:Clean Architecture のレイヤ依存)を表現できず、代表ノードに付けると意味が歪む。群レベルの説明(定義・目的)の置き場もない。 |

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
- `draw`:**階層(入れ子)クラスタ**、凡例、`layout` ツリー(行/列)による配置、箱回避ルーティング、関心事**ビュー**(`--view`)。
- `table`:モデルからの node 表・edge 表(Markdown)生成、クラスタ部分木の抽出(`--cluster`)、関心事ビュー(`--view`)。

**Out-of-scope:**

- シーケンス図・タイミング図(時間順のライフラインであり、グラフレイアウト問題ではない)。
- 生成物(`.drawio` / `.md` / `.svg` / `.png`)の手編集の支援。

### 1.6 Constraints(制約事項)

| ID | 制約 |
| --- | --- |
| CN-1 | オフラインで動作する SHALL。外部ネットワークサービスに依存しない。 |
| CN-2 | `draw` および `table` は Python 標準ライブラリのみで動作する SHALL(`json` / `re` / `subprocess` / `sys` / `xml`)。 |
| CN-3 | Graphviz `dot` を必須とする SHALL。clustered path の箱回避ルーティングは `neato`/`fdp` の**存在**に依存する(環境次第=MAY);存在する場合は当該エンジンでルーティングする(FR-D-07, SHALL)。いずれも無い場合の挙動は FR-D-07a に定義する。 |
| CN-4 | `.svg` / `.png` 化には draw.io CLI を用いる(図そのものの生成には不要)。 |
| CN-5 | SSOT は `gr-tools/drawio-uml` とする。配布先(グローバルスキル等)はコピーであり編集しない(ADR-007)。 |

### 1.7 Limitations(制限事項)

| ID | 制限 | 妥協の理由 |
| --- | --- | --- |
| LM-1 | `draw` の入れ子クラスタは可読性のため **labelled で ≤3 段**を推奨し、4 段超で警告する(深い入れ子は箱の余白が嵩み読みにくい)。 | 入れ子描画は 0.3.0 で実装(ADR-009)。深さは可読性が律速のためソフト上限とする。 |
| LM-2 | 自己参照(`source == target`)は経路描画されない(FR-D-15)。属性・ラベルで表現する。 | `splines=ortho` が自己ループを扱えない Graphviz の制約。 |
| LM-3 | シーケンス/タイミング図は生成できない。 | グラフレイアウト問題でないため(Out-of-scope)。 |
| LM-4 | `neato`/`fdp` がいずれも無い環境では box-avoiding を保証しない(FR-D-07a の degrade)。 | dot 単独では全エッジの事後箱回避ができないため。 |
| LM-5 | クラスタ端点エッジは `name` かつ `label` を持つ(箱が描かれる)クラスタに限る。一方の箱が他方を包含する端点対(node↔祖先クラスタ、cluster↔自身/祖先/子孫)は経路描画しない。曖昧名/未知名/無名・無 label 端点は fail-fast(すべて FR-D-17)。 | アンカー箱 mxCell が要る・包含は self-loop と同根。 |

### 1.8 Glossary(用語集)

| 用語 | 定義 |
| --- | --- |
| SSOT (Single Source of Truth) | 単一の真実源。本スイートでは2義で用いる:(1) 編集してよい唯一の場所 = `gr-tools/drawio-uml`(配布先はコピーで編集しない;ADR-007)。(2) 全成果物の生成元となる単一のモデル JSON(構造・文書・レイアウトを集約;GL-2)。 |
| モデル (model) | スイートの唯一の入力。`nodes` / `edges` / `layout` / `views` / `options` を持つ JSON オブジェクト。SSOT。 |
| node | 図の箱(クラス・状態・コンポーネント等)を表すモデル要素。`nodes`(トップ)で**定義**し、`layout` の葉や `views` では**名前で参照**する。 |
| edge | 関係(継承・関連・依存等)を表すモデル要素。端点(`source`/`target`)は node 名、または **labelled+named cluster 名**(クラスタ端点エッジ)。 |
| cluster | `layout` ツリーの要素。`direction` で子の並べ方を決め、`label` があれば破線箱を描く。子クラスタ(`clusters`)かメンバ node 名(`nodes`)のどちらか一方を持つ。node の所属はツリーの葉が定める(0.2.x の `/` 区切りパス文字列・`node.cluster` は廃止;ADR-009)。 |
| direction | cluster の子/メンバの並べ方。`row`=左→右、`column`=上→下。解決順 = cluster → `options.direction` → `column`。葉では dot の rankdir(column=TB / row=LR)を兼ねる。 |
| layout | モデルのルート cluster(再帰ツリー)。配置・箱・所属を一元化する。省略時は flat path。 |
| view | `views` 配下の名前付き node 部分集合(`nodes` ∪ `clusters` 配下)。`--view` で誘導部分グラフ(両端が集合内の edge のみ)を描く。master の `layout` を剪定して再合成する。 |
| cascade(継承) | cluster の `color`→子孫 node の `stroke`、`fill`→子孫 node の `fill` を**最近接祖先**から継承させる規則。node 側の `fill`/`stroke` が優先。 |
| labelled / outermost cluster | `label` を持つ cluster は箱を描く。`label` を持つ祖先がいない labelled cluster = **outermost**(凡例の対象)。 |
| stereotype | node 見出し上の `«...»` 表記。任意文字列。描画上の特別扱いは `interface`/`abstract`(イタリック化)・`object`(下線)のみ。 |
| italic | node の真偽値。`true` で見出し名を斜体にする(`stereotype` の `interface`/`abstract` による斜体化とは独立の明示指定。ただし shape=`object` の下線が優先する)。 |
| compartment | クラス/エンティティ/オブジェクトを名前・属性・操作の3区画で描く箱(swimlane)。 |
| box-avoiding | どのエッジも自身の端点でないノードのボックス内部を通らない状態。GL-1 の検証基準。 |
| flat path | `layout` を持たないモデルの描画経路。dot が全 node を配置(flow 方向 = `options.direction`、既定 column=TB)。最小コーナを原点 (40,40) に置く。 |
| clustered path | `layout` を持つモデルの描画経路。各葉クラスタを独立 dot run で組み、Python が `direction` 順に再帰合成。最小コーナを原点 (70,70)=`MARGIN` に置く。 |
| banded layout | 帯状配置(上段に複数クラスタ・下段に全幅)は `layout` ツリーの特例(`direction:column` の中に `direction:row` の帯)。0.2.x の `options.layout.rows` は廃止(ADR-009)。 |
| pinned routing | 全ノード位置を固定し `neato -n2`(失敗時 `fdp -n2` → `neato -n`)で全エッジを箱回避ルーティングする最終パス。 |
| cluster-endpoint edge(クラスタ端点エッジ) | `source`/`target` がクラスタ名(labelled+named)を指すエッジ。当該クラスタの箱(`cid(name)` の mxCell)に接続し、箱回避ルーティングの対象とする(FR-D-07/17)。 |
| suite(スイート) | `drawio-uml` 全体。生成器 `draw` と `table` を含む。 |
| draw | モデル → `.drawio` 図を生成する描画部(本体ファイル `draw.py`)。 |
| table | モデル → `.md` 表を生成する作表部(本体ファイル `table.py`)。 |
| description | node/edge/**cluster** の**主説明**(node/edge=責務、cluster=その群の定義・目的;1行)。図には出ない。`table` が消費する(cluster は `## Clusters` 節)。 |
| remark | description を**補足する従説明**(属性に現れない由来・ADR・制約)。node/edge/**cluster** に付与可。図には出ない。`table` が消費する。 |
| common prefix(共通接頭) | 対象 node 群の cluster パスに共通する先頭セグメント列。`table` が表示時に除去する。 |

### 1.9 Notation(表記規約)

RFC 2119 / 8174 に準拠する。**SHALL/MUST**=必須、**SHOULD**=推奨、**MAY**=任意。EARS 構文中の `shall` は SHALL と同義。

---

## Chapter 2. Requirements(要求)

各 FR の受入シナリオは Chapter 4.1、FR×Scenario 対応は Chapter 5 のトレース表に示す。

### 2.1 Functional Requirements(機能要求)

#### 2.1.1 描画部 `draw`

ディスパッチは `layout` の有無で決まる:`layout` を持たないモデルは flat path、持つモデルは clustered path(階層クラスタ箱・箱回避ルーティング)。

- **FR-D-01**(Ubiquitous): `draw` は、モデル(JSON)を入力として `.drawio`(draw.io ネイティブ図形)を出力する SHALL。
- **FR-D-02**(Event): When モデルが `layout` を持たない、`draw` は flat path で描画する SHALL。出力は決定的であり、同一版での再生成と**バイト一致**する(NFR-01)。flow 方向は `options.direction`(既定 `column`=TB)。
- **FR-D-03**(Event): When モデルが `layout`(ルート cluster ツリー)を持つ、`draw` は clustered path で描画する SHALL。各**葉クラスタ**を独立 dot run でレイアウトし、Python が各 cluster の `direction`(`row`=左→右 / `column`=上→下)に従って子を**再帰合成**する。`label` を持つ cluster には破線箱を描く(z 順:外側の箱ほど背面)。
- **FR-D-03a**(Constraint): `layout` がある時、全 node は**ちょうど1回**いずれかの葉 `nodes` に出現する SHALL。未配置・重複は `draw` が報告して非ゼロ終了する(fail-fast)。
- **FR-D-03b**(Ubiquitous): `draw` は Graphviz の `-Tplain` 出力を解析する際、**行分割(splitlines)より前に**生文字列上で継続(行末 `\` + 改行、CRLF を含む)を結合する SHALL。これにより長い node 名・長いラベル(= 長い dot id)で `-Tplain` が物理行を折り返しても解析が破綻しない。`_parse_plain`・`_parse_plain_raw` の両解析(flat / clustered / pinned routing)に適用する。
- **FR-D-04**(Event): When 葉クラスタのメンバ間に内部エッジが無い、`draw` は当該メンバを `direction` 方向に陰線(`style=invis`)で整列する SHALL(列挙順=並び順;葉の `direction` は cluster→`options.direction`→`column` で解決)。内部エッジがある葉は dot の rank 配置が支配し、列挙順はヒントに留まる(LM-1 と同根の Graphviz 制約)。
- **FR-D-05**(Ubiquitous): `draw` は次の形状をサポートする SHALL — class / entity / object / component / package / box / usecase / actor / state / action / decision / initial / final / note。未知の `shape` は `box` として描画する。`class` / `entity` / `object` は compartment(名前・属性・操作の3区画 swimlane)で描き、形状プリセットは適用しない。
- **FR-D-06**(Ubiquitous): `draw` は次のエッジ種別をサポートする SHALL — generalization / realization / composition / aggregation / directed_association / dependency / transition / association。未知・未指定の `arrow` は `association` として描画する。`generalization` / `realization` は親を上位ランクに置くため `dot` へ反転投入し、描画される矢印は子→親を向く。
- **FR-D-07**(State): While `neato` または `fdp` が PATH に存在する、clustered path において `draw` は全エッジ(葉内部・クラスタをまたぐ node 間・**クラスタ端点エッジ(FR-D-17)**を問わず)を box-avoiding な経路で描く SHALL(エンジン連鎖は用語集「pinned routing」参照)。クラスタ端点エッジについては、当該クラスタの**合成済み箱の位置・寸法**を持つ固定サイズ・ピン留めノード(id=`cid(name)`)を pinned routing に与えて配線する(堅牢版;ADR-012)。経路端点はクラスタ箱の境界で**クリップ**し、端点クラスタの箱内部に入る waypoint は破棄する(描画は箱 mxCell へ接続するため draw.io も境界で再クリップする)。クラスタ箱は子 node を内包するため、病的な重なりで ortho 配線が成立しない場合は FR-D-07a の degrade に従う(GL-1 は通常配置で満たす)。
- **FR-D-07a**(Unwanted): If `neato` と `fdp` がいずれも PATH に無い、then `draw` は draw.io 自動ルーティングに degrade する SHALL。この場合 box-avoiding(GL-1)を保証しない(LM-4)。degrade の判別のため `draw` は stderr に警告を出す SHOULD(本版は未実装;実装フェーズで対応)。
- **FR-D-08**(State): While `description` / `remark`(node / edge / **cluster**)/ top-level `title` がモデルに存在する、`draw` はそれらを無視し図を不変に保つ SHALL(SSOT 共有のため;`title` は table のみが消費)。
- **FR-D-09**(Unwanted): If 生成 XML が整形式(well-formed)でない、then `draw` は `minidom.parseString` が送出する例外を握り潰さず、書き出し前に非ゼロ終了する SHALL(fail fast)。
- **FR-D-10**(Optional): Where `node.style` が指定される、`draw` は形状プリセットおよび compartment 区画化(class/entity/object)を抑止し、当該 raw スタイルのみで描く SHALL。
- **FR-D-11**: 欠番(0.2.2 で削除。旧・後方互換エイリアス `classes`/`kind` の受理要求)。番号は再利用しない。
- **FR-D-12**(Event): When `layout` に labelled cluster が存在する、`draw` は凡例(クラスタ swatch + エッジ種別グリフ)を図の下に描く SHALL。swatch は **outermost labelled cluster**(`label` を持ち、`label` を持つ祖先がいない cluster)を対象とし、`color` で重複排除する(`color` 無しは `#888888`)。エッジ種別グリフは composition / aggregation / association / dependency の4種を固定で描く。labelled cluster が無い場合は凡例を描かない。
- **FR-D-13**(State): While node が `fill`/`stroke` を持たない、`draw` は**最近接**の祖先 cluster の `fill`/`color` を継承する SHALL(cascade)。`fill` と `color`(→ node の `stroke`)は独立に最近接で解決し、node 側の指定が優先する。labelled cluster が `color` を持たない場合の箱枠線・凡例 swatch は `#888888` とする。
- **FR-D-14**(Constraint): `draw` は `cluster.name` の一意性を検証する SHALL(重複は fail-fast)。`name` は `/` を含まない SHALL(含む場合 fail-fast)。root→葉の経路で **labelled 段数が 4 を超える**場合、`draw` は stderr に警告を出す SHOULD(可読性のソフト上限;無名の器は数えない。LM-1)。
- **FR-D-15**(Unwanted): If edge の `source == target`(自己参照)、then `draw` は当該エッジを経路描画から除外する SHALL(代替:自己参照は node 属性で表現する;LM-2)。
- **FR-D-16**(Event): When `--view KEY` が与えられ KEY が `views` に存在する、`draw` は当該ビューの**誘導部分グラフ**(node = `view.nodes` ∪ `view.clusters` 配下;edge = 両端が集合内)のみを描く SHALL。`layout` を選択 node に**剪定**して再合成し、空の箱・帯は除外、一部生存の箱は survivors に縮小する。凡例の outermost 判定は**剪定後ツリー**で再計算する。クラスタ端点エッジ(FR-D-17)は、両端のクラスタが剪定後も生存(配下に生存 node あり)し、かつ剪定後ツリーで縮退(FR-D-17)に当たらない場合のみ残す(誘導は node メンバ集合の一致ではなく**端点クラスタの生存**で判定する)。`--view` 無指定時は全体を描く。
- **FR-D-16a**(Unwanted): If `--view KEY` の KEY が `views` に無い、または `view` が存在しない node/cluster 名を参照する、then `draw` はエラーを報告して非ゼロ終了する SHALL(fail-fast)。
- **FR-D-17**(Optional): Where edge の `source`/`target` がクラスタ名を指す(クラスタ端点エッジ)、`draw` は当該エッジを node ではなく**クラスタの箱 mxCell**(`cid(name)`)に接続する SHALL。
    - **端点解決**:全エッジ端点を **node 名 → cluster 名** の順で1回だけ解決する単一検証パスとする(既存の node 名のみの事前チェックはこれに**置換**される;§3.5 draw フロー手順1)。次は報告して非ゼロ終了する(fail-fast):(a) node にも cluster にも一致する曖昧名、(b) どちらにも一致しない未知名、(c) `name` なし or `label` なし(箱が描かれない)クラスタを端点とする場合。
    - **縮退の除外**:いずれか一方の箱が他方を**幾何的に包含**する端点対(node がその祖先クラスタ配下にある=どちら向きでも;cluster が自身/祖先/子孫=どちら向きでも)は経路描画から除外する(FR-D-15 と同根。包含判定は配下 node 集合で行う)。`name` 文字列一致の自己ループ除外(FR-D-15)に加えて適用する。
    - **配線**:クラスタ端点エッジは per-leaf(`_leaf_layout`)/ flat(`dot_layout`)の dot run には**投入しない**(pinned routing でのみ扱う)。pinned ノード id・経路表キー・mxCell の `source`/`target` 参照は、node 端点の `nid` に対応して**いずれも `cid(name)`** とする。箱回避は FR-D-07 に従う。

#### 2.1.2 作表部 `table`

- **FR-T-01**(Ubiquitous): `table` は、モデル(JSON)を入力として Markdown を出力する SHALL。
- **FR-T-02**(Ubiquitous): `table` は node 表を `| cluster | name | description | remark |` の列で生成する SHALL。
- **FR-T-03**(Ubiquitous): `table` は edge 表を `| arrow | source | target | label | description | remark |` の列で生成する SHALL。`arrow` はモデルの記述値をそのまま出力し(`draw` の未指定→`association` 解決は適用しない)、`arrow` 未指定の edge は当該セルを空とする。
- **FR-T-04**(Ubiquitous): `table` は cluster 列に、対象 node 群の cluster パス(= `layout` の**名前付き祖先クラスタ連鎖**を `/` で連結;無名段はスキップ。FR-D-14 の符号化と同一)から共通接頭を除いた残りを `" / "` 区切りで表示する SHALL。対象 node が1件の場合は共通接頭が全長一致し得る(その帰結は FR-T-05)。
- **FR-T-05**(Unwanted): If 共通接頭の除去後に cluster 列が全行空になる、then `table` は cluster 列自体を出力しない SHALL。
- **FR-T-06**(Event): When `--cluster KEY` が指定される、`table` は KEY とその配下のみを対象とする SHALL。KEY は `cluster.name` のパス(例 `consider`・`consider/world`)。一致は名前付き祖先パスの `/` セグメント境界で行う(`a/b` は `a/b` と `a/b/*` に一致し、`a/bc` には一致しない)。どの named クラスタにも属さない node は対象外とする。
- **FR-T-06a**(Unwanted): If `--cluster KEY` がどの node にも一致しない、then `table` は空の表(見出し行のみ)を出力し、警告を標準エラーに出す SHALL。
- **FR-T-07**(Event): When `--cluster KEY` が指定される、`table` は source または target の少なくとも一方が対象集合に属す edge を含める SHALL(片方向で十分)。指定なしの場合は全 edge を対象とする。
- **FR-T-08**(Ubiquitous): `table` はセル内の `|` を `\|` にエスケープし、`description` / `remark` 内の改行表現 `<br>` はそのまま出力する SHALL(セル内の実改行は使わない)。
- **FR-T-09**(Unwanted): If 必須フィールド(node の `name`、edge の `source` / `target`)が欠落、then `table` はエラーを報告して非ゼロ終了する SHALL。
- **FR-T-10**(Event): When `--view KEY` が指定される、`table` は node 表・edge 表を当該ビュー(node = `view.nodes` ∪ `view.clusters` 配下;edge = 両端が集合内の誘導)に限定する SHALL。
- **FR-T-10a**(Unwanted): If `--view` と `--cluster` が同時指定される、then `table` はエラーを報告して非ゼロ終了する SHALL(排他)。未知の `--view KEY`、または存在しない node/cluster 名を参照するビューも fail-fast とする。
- **FR-T-11**(Ubiquitous): `table` は出力の先頭に **H1 文書タイトル**を置き、節見出しを `## Nodes` / `## Edges`(および任意で `## Clusters`、FR-T-12)(H2)とする SHALL。H1 は、`--view KEY` 指定時は当該ビューの `label`(label 省略時はビューキー)、それ以外(全体 / `--cluster`)はモデルの top-level `title` とする。`title` はモデルの**必須**プロパティであり、`draw` は無視する(FR-D-08)。H1 は `# ` + 文字列を**そのまま**(raw・エスケープせず・単一行)出力する(表セルのエスケープ FR-T-08 は H1 に適用しない)。(0.3.x までの H4 埋め込み断片モードは廃止。)
- **FR-T-11a**(Unwanted): If モデルが top-level `title` を持たない、または空文字列/空白のみ、then `table` はエラーを報告して非ゼロ終了する SHALL(必須欠落;FR-T-09 と同様。`--view` の有無に依らない)。なお title 欠落モデルは schema-invalid かつ table で fail-fast だが、`draw` は title を要求せず描画できる(意図的非対称:draw は title を消費しない)。
- **FR-T-12**(Event): When モデルが `name` または `label` を持つ cluster を含む、`table` は `## Clusters` 節を `| cluster | label | description | remark |` の列で生成する SHALL。
    - **行対象**:`name` **または** `label` を持つ cluster(両方は不要)。`name` も `label` も持たない純配置 cluster は対象外。対象が1件も無い(例:flat モデル)場合は節を出力しない。
    - **行順**:`layout` ツリーの pre-order(宣言順)で決定的とする(NFR-01)。
    - **`cluster` 列**:root から当該クラスタへの**名前付き祖先連鎖**を `/` 連結(無名段はスキップ)。当該が `name` を持てば末尾に含み、持たなければ最も近い名前付き祖先まで(空になり得る)。**共通接頭は除去しない**(FR-T-05 は適用しない)。`name` を持たない(labelled のみ)行は `label` 列で識別する。
    - **`label`/`description`/`remark` 列**:モデル値(未設定は空欄)。
    - **スコープ**:`--cluster KEY` は KEY 配下の cluster に限定。`--view KEY` は**選択 node を1つ以上配下に持つ** cluster に限定する(table の view スコープは node メンバ集合で判定し、draw の箱剪定とは独立)。
    - **節順**:`## Nodes` → `## Edges` → `## Clusters`。

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
| Model | Model | `nodes` / `edges` / `layout` / `views` / `options` を持つ JSON。両生成器の唯一の入力。 |
| draw | Generator | モデル → `.drawio`。`render()` が `layout` の有無で flat/clustered を振り分ける。`--view` 指定時はビューに剪定。 |
| ├ flat path | Generator | `layout` なし。`dot_layout` + `render_flat`。 |
| ├ clustered path | Generator | `layout` ツリーを再帰合成(葉=独立 dot run、Python が `direction` 順に配置) + `_route_pinned` + `render_clustered`(入れ子箱)。 |
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
│   └── table.py       作表部(モデル → .md;0.3.0 で再実装)
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

- **本版(0.5.0)の作業:** 0.4.0 まで実装・テスト緑。0.5.0 はクラスタ端点エッジ + cluster `description`/`remark`(`## Clusters`)+ `-Tplain` 継続行修正の**追加フェーズ**(本仕様が対象)。`schema/model.schema.json` は 0.5.0 へ更新済み。`scripts/`(draw/table)と `tests/`・基準 `.md` は本フェーズで更新する。設計 PoC・ブリーフは `poc/cluster-layout/`。
- 配布コピー(グローバルスキル等)・利用先リポジトリは本ディレクトリからの**コピー**であり、編集しない(ADR-007)。

### 3.4 Domain Model(ドメインモデル=モデルスキーマ)

機械可読形は `schema/model.schema.json`(JSON Schema draft-07)。構造検証のみを行い、参照整合性(name 一意・全 node を 1 回配置・参照解決)は draw/table が実行時に fail-fast で担保する。

```
model
├── title  : string                       ← **必須**。table が H1 文書タイトルに(FR-T-11)/ draw は無視
├── nodes[ node ]                         ← node 定義(オブジェクト)
├── edges[ edge ]
├── layout : cluster                      ← ルート cluster(再帰ツリー;省略時 flat)
├── views  : { <viewKey>: view }          ← 関心事ビュー(オプトイン)
└── options
    ├── direction : "row" | "column"      既定 column(flat / cluster の既定方向)
    └── column_width / node_separation / rank_separation   レイアウト寸法

cluster(layout ツリーの要素・再帰)
├── direction : "row" | "column"          子/メンバの並べ方(既定 options.direction)
├── label                                 あれば破線箱を描く(無ければ透明な配置器)
├── name                                  view/--cluster の参照 id(一意・"/" 不可)
├── color                                 箱枠線 + 子孫 node の stroke へ cascade
├── fill                                  子孫 node の fill へ cascade(箱は塗らない)
├── description                           群の主説明(定義・目的)  ← table が消費(## Clusters)/ draw は無視
├── remark                               群の傍注                ← table が消費(## Clusters)/ draw は無視
└── (clusters[ cluster ]  ⊻  nodes[ "<node名>" ])   子クラスタ ⊻ メンバ node 名(順=並び順)

node
├── name            (必須・一意)
├── shape           class|entity|object|component|package|box|usecase|actor|
│                   state|action|decision|initial|final|note(既定/未知は box)
├── stereotype / italic
├── attributes[] / methods[]   compartment の属性・操作行
├── fill / stroke              省略時は祖先 cluster から cascade(最近接優先)
├── style / width / height
├── description     責務(主・1行)        ← table が消費 / draw は無視(FR-D-08)
└── remark          傍注(属性に出ない補足) ← table が消費 / draw は無視(FR-D-08)

edge
├── source / target (必須)  node 名 または labelled+named cluster 名(クラスタ端点エッジ;解決は node 優先→cluster、曖昧/未知/無名・無 label は fail-fast。FR-D-17)
├── arrow           generalization|realization|composition|aggregation|
│                   directed_association|dependency|transition|association(未指定は association)
├── label           図に出る関係名
├── description     ← table が消費 / draw は無視
└── remark          ← table が消費 / draw は無視

view
├── label                 表示名(省略時はビューキー)
├── nodes[ "<node名>" ]    明示ノード名
└── clusters[ "<cluster名>" ] クラスタ名(配下を丸ごと)  ← nodes/clusters は最低一方・両方で和集合
```

所属とパス:node の所属は `layout` の葉が定める。node のクラスタパス(table 用)= root→葉の**名前付き祖先 cluster 連鎖**を `/` で連結(無名段はスキップ)。最深の名前付き祖先が**内部クラスタ**の場合はそのパス(例:`consider` 直下の無名葉にある `Conception` は `consider`、`consider`→`world` 配下は `consider/world`)。`draw` は `cluster` を入れ子の箱として描く(0.3.0;ADR-009。0.2.x の「不透明1ラベル」(LM-1 旧)・`node.cluster`・`options.clusters`・`options.layout.rows` は廃止)。

補足(描画の優先・抑止規則):node の `fill`/`stroke` は cluster からの cascade(`fill` / `color`)に**優先**する。`node.style` を持つ node は形状プリセットと compartment(`attributes`/`methods`)を**抑止**し raw style のみで描く(FR-D-10)。

補足(エッジ端点):`edge.source`/`target` は node 名のほか labelled+named cluster 名を取れる(クラスタ端点エッジ)。解決は **node 優先 → cluster**、曖昧名/未知名/無名・無 label クラスタは実行時 fail-fast(FR-D-17)。クラスタ端点は当該クラスタの箱 mxCell(`cid(name)`)に接続し、pinned routing で箱回避する(FR-D-07)。

### 3.5 Behavior(振る舞い)

**draw の処理フロー:**

1. モデル読込(`json.load`, UTF-8;失敗時 FR-C-03)。全エッジ端点を node → cluster の順に解決・検証(FR-D-17;旧 node 限定の事前チェックを置換)。`--view` 指定時はビューに剪定(FR-D-16/16a)。
2. `layout` の有無を判定。
3. 無 → flat path:`dot_layout`(`dot -Tplain`、flow=`options.direction`)→ 最小コーナを原点 **(40,40)** に平行移動 → `render_flat`。
4. 有 → clustered path:`layout` ツリーを**再帰合成**(各葉クラスタを独立 dot run → 親の `direction` 順に Python が配置;内部エッジ無しの葉は陰線整列)→ name 一意・全 node 1 回・深さ警告を検証(FR-D-03a/14)→ 最小コーナを原点 **(70,70)=MARGIN** に配置 → `_route_pinned`(全 node を pin)→ `render_clustered`(z 順:**外側の箱 → 内側の箱** → node → edge → 凡例)。node の fill/stroke は祖先 cluster から cascade(FR-D-13)。
5. `_route_pinned` は全 node をピン留めし、**クラスタ端点エッジがある場合は当該クラスタの合成済み箱(位置・寸法)を id=`cid(name)` の固定サイズ・ピン留めノードとして `boxes` の決定的順序で追加**(経路表キーも `cid(name)`)したうえで、`neato -n2` → `fdp -n2` → `neato -n` の順に試行。経路端点はクラスタ箱境界でクリップし箱内部の waypoint は破棄。`-Tplain` は**行分割前に**生文字列で継続(行末 `\`+改行)を結合してから解析する(FR-D-03b)。いずれも不在/失敗なら空の経路表を返し draw.io 自動ルーティングに degrade する(FR-D-07a)。
6. `minidom.parseString` で整形式検証(FR-D-09)→ ファイル書き出し。

**table の処理フロー:**

1. モデル読込。必須フィールド検証(node.name / edge.source/target / **model.title**;FR-T-09/11a)。`--view`/`--cluster` の排他検証(FR-T-10a)。
2. 対象 node 集合を確定:`--view` ならビュー(`nodes` ∪ `clusters` 配下)、`--cluster` なら名前付き祖先パスの `/` 境界一致(FR-T-06)、無指定は全件。
3. 各 node のクラスタパス(名前付き祖先連鎖)を `layout` から導出し、共通接頭を計算・除去。残りが全空なら cluster 列を落とす(FR-T-05)。
4. node 表を生成(FR-T-02)。
5. edge を対象集合でフィルタ(`--cluster` は source/target の一方が対象なら採用;`--view` は両端が対象=誘導;FR-T-07/10)。
6. edge 表を生成(FR-T-03)。
7. `name`/`label` を持つ cluster があれば `## Clusters` 表を生成(対象は `--cluster`/`--view` で限定;FR-T-12)。
8. 見出しを組む:先頭に H1(`--view` 時は当該ビューの `label`、それ以外はモデル `title`)、節は `## Nodes` / `## Edges`(/ 任意で `## Clusters`)(FR-T-11)。セル `|` を `\|` にエスケープ、`<br>` は素通し → `.md` 書き出し(FR-T-08)。

**実装メモ(0.5.0;ソースフェーズ向け):**

- **端点解決**:`render_model` の node 限定事前チェックを node → cluster 解決器へ置換(FR-D-17)。クラスタ端点エッジは `_leaf_layout` / `dot_layout` へ投入しない。
- **縮退判定**:node↔cluster・cluster↔cluster の包含は `node_names_under` の集合包含で判定(`name` 一致の self-loop に加える)。
- **pinned 追加**:クラスタ箱は `compose` が返す `boxes`(外側優先・list 順)から決定的に追加し、`size`/`pos` 辞書にも登録して affine 変換に参加させる。経路端点は箱境界でクリップ。
- **id 予約**:無名箱 id `cluster_box_%d` は `cid(name)`(接頭 `cluster_`)と衝突しうる(例:`box_0` という名の cluster → `cluster_box_0`)。無名箱 id は `cid` が生成し得ない予約接頭にする。
- **table 側**:`## Clusters` 用に cluster 列挙の木走査を新設(`node_paths` は leaf node のみ)。`--view` スコープは「配下に選択 node を持つ cluster」で判定(table に箱剪定は無い)。

### 3.6 Decisions(設計判断 / ADR)

各 ADR の決定者は人間(プロジェクトオーナー)である。形式:Status / Context / Decision / Alternatives / Consequences。

**ADR-001 — JSON モデルを SSOT とし、生成物は手編集しない**
*Status:* Accepted / *Context:* 図を直接編集すると元モデルと乖離する(IS-4)。/ *Decision:* モデル(JSON)を唯一の真実源とし、`.drawio` / `.md` は生成物として扱う。/ *Alternatives:* 図(.drawio)を正とし JSON を従とする案 → AI が編集しにくく IS-4 を解決しないため却下。/ *Consequences:* 成果物の手編集は禁止。変更はモデルに加え再生成する。

**ADR-002 — レイアウトを Graphviz `dot` に委譲する**
*Status:* Accepted / *Context:* Mermaid/PlantUML はレイアウトが弱くエッジが箱を貫通する(IS-1)。/ *Decision:* `dot` に位置と `splines=ortho` 経路を計算させ、経路を draw.io の waypoint として取り込む。/ *Alternatives:* (a) PlantUML 内蔵レイアウト → GUI 編集不可・IS-1 を解決しない。(b) `neato`/`sfdp` を主レイアウトに → ノードリンク図の階層表現で `dot` に劣る(`neato` は本スイートでは事後ルーティング専用)。/ *Consequences:* box-avoiding を達成(GL-1)。Graphviz への依存が生じる(CN-3)。

**ADR-003 — flat / clustered の2経路に分け、flat は出力安定性を保つ**
*Status:* Accepted(0.3.0 改訂) / *Context:* `layout` を要しない単純な図は dot 単独レイアウトで十分であり、その出力を同一版で安定させ回帰基準としたい。/ *Decision:* `layout` を持たないモデルは flat 経路を通す。flat path の出力は同一版で安定させ、回帰基準 `.drawio` と md5 比較する。/ *Alternatives:* 単一経路に統合 → flat の単純出力に箱回避ルーティング等の差異が混入し回帰が不安定になるため却下。/ *Consequences:* 同一版でのバイト一致が保たれる(FR-D-02, NFR-01)。2経路の保守コストが生じる。(0.3.0:後方互換は不要化したため回帰基準を 0.3.0 出力でリセット。2経路分割と同一版バイト一致は維持。)

**ADR-004 — スイート名 `drawio-uml`、サブ機能 `draw` / `table`**
*Status:* Accepted / *Context:* `drawio_uml` と `uml_table` の非対称が問題視された。/ *Decision:* スイート名は draw.io 出力が肝である点を表す `drawio-uml` とし、機能は動詞 `draw`(描く)/ `table`(表にする)で対称にする。描画本体は `draw.py` にリネーム(ロジック不変)。/ *Alternatives:* `uml_drawio`(語順で肝の draw.io が修飾に落ちる)・`umlkit`/`umlcast`(draw.io 固有性が消える)を却下。/ *Consequences:* 対称な命名体系。将来 `build` 等のサブ機能を追加できる。

**ADR-005 — `cluster` はパス文字列。階層対応は `table` のみ、`draw` は当面フラット**
*Status:* **Superseded by ADR-009(0.3.0)** / *Context:*(0.2.x)図の階層レイアウトは大規模改修でリスクが高く、現需要にないと判断した。/ *Decision:*(旧)`cluster` をパス文字列とし `table` のみ階層解釈、`draw` は1ラベル扱い。/ *撤回理由:* PoC(`poc/cluster-layout/`)で入れ子クラスタの dot 描画と A2(独立 dot run + Python 再帰合成)の実現性・品質を実証し、ARC ドメインモデルで階層図示の需要が顕在化したため YAGNI 前提が崩れた。詳細は ADR-009。

**ADR-006 — `description` / `remark` をモデルに追加し、`draw` は無視・`table` が消費**
*Status:* Accepted / *Context:* 図で表現困難な責務説明・一覧の置き場がない(IS-5)。/ *Decision:* 文書系フィールド `description`(責務)/ `remark`(傍注)をモデルに置き、`draw` は無視、`table` が表に出す。/ *Alternatives:* 解説を別 `.md` に手書きする案 → モデルと二重管理になり IS-4 を再発させるため却下。/ *Consequences:* 構造も文書も単一 SSOT に集約(GL-3)。`draw` 出力は不変(FR-D-08)。

**ADR-007 — SSOT は `gr-tools/drawio-uml`、他は配布コピー(編集禁止)**
*Status:* Accepted / *Context:* 同一ツールがスキル・利用先に分散コピーされていた。/ *Decision:* `gr-tools/drawio-uml` を唯一の編集点とし、他はコピーとする。/ *Alternatives:* 各所で個別編集 → 版が分岐し SSOT を失うため却下。/ *Consequences:* 単一真実源。配布(同期)手順が必要。

**ADR-008 — ルーティング不能時は draw.io 自動ルーティングへ degrade する**
*Status:* Accepted / *Context:* clustered path の box-avoiding は `neato`/`fdp` に依存するが、これらが無い環境がありうる(CN-3)。/ *Decision:* `neato`/`fdp` がいずれも使えない場合、異常終了せず draw.io 自動ルーティングに degrade する(box-avoiding は保証しない)。/ *Alternatives:* 異常終了する案 → 図自体は生成可能なのにツールが止まり可用性を損なうため却下。/ *Consequences:* 可用性を優先(FR-D-07a)。degrade 時は GL-1 を満たさない(LM-4)。degrade 判別用の stderr 警告は SHOULD だが本版未実装(FR-D-07a)。

**ADR-009 — `layout` を再帰 cluster ツリーとし、`draw` が入れ子クラスタを描く(ADR-005 を撤回)**
*Status:* Accepted(0.3.0) / *Context:* 大規模モデルの単一図は判読困難。0.2.x は配置を `options.layout.rows`(Python grid 合成)で帯のみ対応し、`draw` の階層は YAGNI 却下していた(ADR-005)。/ *Decision:* 配置・箱・所属・スタイルを単一の再帰ツリー `layout` に集約する。各 cluster は `direction`(row/column)で子を並べ、`label` があれば箱を描き、`clusters`(子)か `nodes`(メンバ名)を持つ。`color`/`fill` は子孫 node へ最近接 cascade。レイアウトは **A2**:各**葉**を独立 dot run で組み(dot の得意分野)、Python が `direction` 順に再帰合成(順序を Python が保証)、最後に pinned neato で全エッジ箱回避。/ *Alternatives:* (a) 単一 dot run + 入れ子 subgraph + `rank=same` で兄弟順序を強制(A1)→ クラスタ所属と衝突し dot が **segfault**、棄却。(b) 0.2.x の `rows` grid を維持 → 階層・順序の明示指定ができず却下。/ *Consequences:* `draw` が階層図示可能(LM-1 を可読性上限に書換)。`node.cluster`・`options.clusters`・`options.layout.rows` は廃止(後方互換は不要=オーナー決定)。`table` のクラスタパスはツリーの名前付き祖先連鎖から導出(FR-T-04)。

**ADR-010 — `views`:SSOT 内の純フィルタ。`draw`/`table` 双方が誘導部分グラフを出力**
*Status:* Accepted(0.3.0) / *Context:* 1枚に詰めると判読不能(可読限界 ≒ 7–12 箱)。完全さ=モデル / 読みやすさ=複数の小ビュー、の分離が要る。/ *Decision:* `views` に名前付き node 部分集合(`nodes` ∪ `clusters` 配下)を置き、`--view KEY` で `draw`/`table` 双方が誘導部分グラフ(両端が集合内の edge のみ)を出力する。`draw` は master `layout` を選択 node に剪定して再合成する(空箱・空帯は除外、凡例 outermost は剪定後に再計算)。/ *Alternatives:* (a) ビューごとに別モデル → SSOT を失う。(b) node に tag を分散 → 全 node を汚す。(c) `--cluster` 流用のみ → クラスタ内部分集合を表現できない。/ *Consequences:* 単一 SSOT から関心事別の図+表。ビューは構造を改変しない純フィルタ。振る舞いフロー全体像は対象外(誘導は既存構造エッジのみ)。`--view` と `--cluster` は排他(FR-T-10a)。

**ADR-011 — `description`/`remark` を cluster にも拡張し、`table` が `## Clusters` 表に出す**
*Status:* Accepted(0.5.0) / *Context:* レイヤ/モジュール等の群にも「定義・由来」を残したいが置き場がない(IS-6 後段)。/ *Decision:* ADR-006 の文書系フィールド(`description`=主・`remark`=従)を cluster にも認め、`table` が `## Clusters`(`| cluster | label | description | remark |`)に出す。`draw` は無視(FR-D-08)。/ *Alternatives:* 群の説明を node 側に書く → 群レベルの意味が node に滲み出て不正確、却下。別 .md → 二重管理(IS-4)、却下。/ *Consequences:* 群レベルの文書も単一 SSOT に集約(GL-3)。`draw` 出力は不変。

**ADR-012 — edge 端点に cluster を許し(クラスタ端点エッジ)、堅牢な箱回避で配線する**
*Status:* Accepted(0.5.0) / *Context:* レイヤ依存のような**群対群**の関係を表せず、代表 node に付けると「コンポーネント単位の関係は別図」という設計意図と矛盾する(IS-6)。/ *Decision:* `edge.source`/`target` に labelled+named cluster 名を許し、当該クラスタの箱 mxCell(`cid(name)`)へ接続する。解決は node 優先 → cluster、曖昧/未知/無名・無 label は fail-fast(FR-D-17)。箱回避は **pinned routing にクラスタの箱(合成済み位置・寸法、id=`cid(name)`)を固定ノードとして加える堅牢版**とし、通常配置で非貫通を達成する(端点は箱境界でクリップ;クラスタ箱が子 node と重なる病的配置は FR-D-07a の degrade。FR-D-07、GL-1)。/ *Alternatives:* (a) 代表 node 間エッジ → 群の関係を node に歪曲、却下。(b) クラスタ線のみ draw.io 自動ルータ任せ(最小版)→ 隣接箱では足りるが任意配置で貫通しうるため GL-1 を破り却下。/ *Consequences:* レイヤ依存等を正しく図示。pinned routing がクラスタ箱を扱うよう拡張。ノード↔クラスタも副産物として描ける。

**ADR-013 — `-Tplain` の継続行を結合してから解析する**
*Status:* Accepted(0.5.0) / *Context:* `dot`/`neato` の `-Tplain` は長い行を行末 `\` で折り返す。長い node 名(= 長い dot id)やラベルでパーサが破綻していた(欠陥)。/ *Decision:* `-Tplain` を読む全パーサで継続行を結合してから解析する(FR-D-03b)。/ *Alternatives:* node 名長を制限 → 注釈用途等を阻害、却下。/ *Consequences:* 長い名前・ラベルでも安定。出力は不変(NFR-01)。

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
    Given layout を持たないモデル
    When  draw.py で .drawio を生成する
    Then  同一版での再生成と md5 がバイト一致する
    And   最小コーナが原点 (40,40) に配置される

  Scenario: SC-003 クラスタありモデルは箱回避経路を持つ (traces: FR-D-03, FR-D-07)
    Given layout(クラスタツリー)を持つモデル
    And   neato または fdp が PATH に存在する
    When  draw.py で .drawio を生成する
    Then  いずれのエッジも非端点ノードのボックスを貫通しない

  Scenario: SC-004 凡例の描画 (traces: FR-D-12)
    Given layout に labelled cluster を持つモデル
    When  draw.py で .drawio を生成する
    Then  図の下に outermost labelled cluster の swatch(色で重複排除)とエッジ種別グリフの凡例が描かれる

  Scenario: SC-005 行/列ツリー配置 (traces: FR-D-03)
    Given layout = column[ row[a, b], c ](a,b,c は葉クラスタ)
    When  draw.py で .drawio を生成する
    Then  a,b が上段に左→右、c が下段全幅に配置される

  Scenario: SC-006 ルーティングエンジン不在時の degrade (traces: FR-D-07a)
    Given layout(クラスタツリー)を持つモデル
    And   neato も fdp も PATH に存在しない
    When  draw.py で .drawio を生成する
    Then  draw.io 自動ルーティングに degrade して .drawio を生成する
    But   box-avoiding は保証されない

  Scenario: SC-007 色のカスケード (traces: FR-D-13)
    Given fill/stroke を持たない node を含む labelled cluster(color/fill 指定)
    When  draw.py で .drawio を生成する
    Then  当該 node は最近接祖先 cluster の fill/color を継承する
    And   color を持たない labelled cluster の箱枠線は #888888 になる

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

  Scenario: SC-014 layout が全 node を1回配置しないと異常終了 (traces: FR-D-03a)
    Given layout が或る node を未配置、または重複配置するモデル
    When  draw.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-015 未知 shape は box (traces: FR-D-05)
    Given shape にカタログ外の値を持つ node
    When  draw.py で .drawio を生成する
    Then  当該 node は box(汎用の箱)として描画される

  Scenario: SC-016 未指定 arrow は association (traces: FR-D-06)
    Given arrow を持たない edge
    When  draw.py で .drawio を生成する
    Then  当該 edge は association(矢印なしの線)として描画される

  Scenario: SC-017 入れ子クラスタは入れ子の箱で描かれる (traces: FR-D-03)
    Given label を持つ cluster の中に label を持つ子 cluster を入れた layout
    When  draw.py で .drawio を生成する
    Then  外側の箱の内側に子クラスタの箱が重ならず描かれる
    And   子クラスタは親の direction 順に配置される

  Scenario: SC-018 内部エッジ無しの葉は direction 方向に並ぶ (traces: FR-D-04)
    Given 内部エッジを持たない複数メンバの葉クラスタ(direction=column)
    When  draw.py で .drawio を生成する
    Then  メンバは列挙順に縦に並ぶ(陰線整列)

  Scenario: SC-019 cluster.name の重複・スラッシュは異常終了 (traces: FR-D-14)
    Given 同名 cluster を2つ持つ、または name に "/" を含む layout
    When  draw.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-020 draw --view は誘導部分グラフを描く (traces: FR-D-16, FR-D-16a)
    Given views.answer を持つモデル
    When  draw.py MODEL.json OUT.drawio --view answer を実行する
    Then  answer のノードと両端が集合内の edge だけが描かれ、空クラスタ箱は出ない
    And   凡例の outermost 判定は剪定後ツリーで再計算される(view world では world が outermost)
    And   未知の --view KEY は非ゼロ終了する

  Scenario: SC-021 クラスタ端点エッジは箱に接続し箱回避する (traces: FR-D-17, FR-D-07)
    Given source/target がクラスタ名(labelled+named)の edge を持つ layout
    And   neato または fdp が PATH に存在する
    When  draw.py で .drawio を生成する
    Then  当該 edge は当該クラスタの箱 mxCell に接続される
    And   いずれのエッジも非端点ノードのボックスを貫通しない

  Scenario: SC-022 node↔cluster エッジ (traces: FR-D-17)
    Given source が node 名、target がクラスタ名の edge
    When  draw.py で .drawio を生成する
    Then  当該 edge は node とクラスタの箱に接続される

  Scenario: SC-023 曖昧な端点名は異常終了 (traces: FR-D-17)
    Given 同一名の node と cluster があり、その名を edge 端点に使うモデル
    When  draw.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-024 無名/無 label クラスタ端点は異常終了 (traces: FR-D-17)
    Given edge 端点が name なし、または label なし(箱が描かれない)クラスタを指すモデル
    When  draw.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-025 長い node 名/ラベルでも解析が破綻しない (traces: FR-D-03b, NFR-01)
    Given dot の -Tplain 行折返しを誘発する長い node 名を持つモデル
    When  draw.py で .drawio を生成する
    Then  例外なく .drawio が生成される

  Scenario: SC-026 view 剪定でクラスタ端点エッジの生存判定 (traces: FR-D-16, FR-D-17)
    Given クラスタ端点エッジを持ち、片方のクラスタが剪定で消えるビュー
    When  draw.py --view で生成する
    Then  当該 edge は両端クラスタが生存する時のみ残る
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

  Scenario: SC-108 table --view はビューに限定する (traces: FR-T-10)
    Given views.answer を持つモデル
    When  table.py MODEL.json OUT.md --view answer を実行する
    Then  node 表・edge 表が answer のノード集合と両端誘導 edge に限定される

  Scenario: SC-109 --view と --cluster の同時指定は異常終了 (traces: FR-T-10a)
    Given --view と --cluster の両方を指定
    When  table.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-110 全体の table は title を H1 にする (traces: FR-T-11)
    Given top-level title を持つモデル
    When  table.py で .md を生成する(--view なし)
    Then  出力の先頭が `# <title>`、節が `## Nodes` / `## Edges` になる

  Scenario: SC-111 --view の table は view の label を H1 にする (traces: FR-T-11)
    Given views.answer(label あり)と title を持つモデル
    When  table.py MODEL.json OUT.md --view answer を実行する
    Then  出力の先頭が `# <answer の label>`、節が `## Nodes` / `## Edges` になる

  Scenario: SC-112 title 欠落は異常終了 (traces: FR-T-11a)
    Given top-level title を持たないモデル
    When  table.py を実行する
    Then  エラーを報告して非ゼロ終了する

  Scenario: SC-113 Clusters 節に定義/備考が出る (traces: FR-T-12)
    Given name/label と description/remark を持つ cluster を含むモデル
    When  table.py で .md を生成する
    Then  `## Clusters` 節が | cluster | label | description | remark | を持つ
    And   当該クラスタの description/remark が出力される
    And   flat モデルでは `## Clusters` 節を出力しない
```

**Result:** 0.4.0 まで PASS(`tests/test_draw.py` SC-001〜020・SC-012 skip / `tests/test_table.py` SC-101〜112)。**0.5.0 は仕様確定・実装/テストは後続フェーズ**:追加分 SC-021〜026(クラスタ端点エッジ・node↔cluster・曖昧/無名無 label の fail-fast・長ラベル・view 剪定)と SC-113(`## Clusters`)は実装フェーズで検証する。SC-011 は欠番。SC-012(整形式でない XML)は `esc()` により通常到達不能のため skip。`table` の基準 `.md`(`tests/*.model.md`・`samples/*.model.md`)は `## Clusters` 追加に伴い 0.5.0 形式へ再生成する(NFR-01)。

### 4.2 CLI Definition(コマンド定義)

| 生成器 | コマンド | 主オプション |
| --- | --- | --- |
| draw | `python draw.py MODEL.json OUT.drawio [--view KEY]` | `--view`:当該ビューの誘導部分グラフのみ描画(FR-D-16) |
| table | `python table.py MODEL.json OUT.md [--cluster KEY \| --view KEY]` | `--cluster`:対象部分木(`name` の `/` セグメント前方一致)。`--view`:当該ビューに限定。両者は排他(FR-T-10a) |

`.svg` / `.png` 化(draw のみ・任意):`drawio -x -f png -e -b 12 -o OUT.drawio.png OUT.drawio`。

### 4.3 Output Format(`table` の Markdown 出力形式)

- 出力は先頭に **H1 文書タイトル**(全体=モデル `title` / `--view`=ビュー `label`、label 省略時はビューキー)、続いて `## Nodes`・`## Edges`(H2)の2節を順に含む(FR-T-11)。`title` 欠落・空は非ゼロ終了(FR-T-11a)。
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
| FR-D-01 | SC-001 | FR-D-15 | SC-009 |
| FR-D-02 | SC-002 | FR-D-16 / 16a | SC-020 |
| FR-D-03 | SC-003 / SC-005 / SC-017 | FR-T-01 | SC-101 |
| FR-D-03a | SC-014 | FR-T-02 | SC-101 |
| FR-D-04 | SC-018 | FR-T-03 | SC-103 / SC-107 |
| FR-D-05 | SC-001 / SC-015 | FR-T-04 | SC-101 |
| FR-D-06 | SC-003 / SC-016 | FR-T-05 | SC-102 |
| FR-D-07 | SC-003 | FR-T-06 / 07 | SC-103 |
| FR-D-07a | SC-006 | FR-T-06a | SC-105 |
| FR-D-08 | SC-008 | FR-T-08 | SC-104 |
| FR-D-09 | SC-012(skip) | FR-T-09 | SC-106 |
| FR-D-10 | SC-010 | FR-T-10 / 10a | SC-108 / SC-109 |
| FR-D-12 | SC-004 | FR-C-01 | SC-001 / SC-101 |
| FR-D-13 | SC-007 | FR-C-03 | SC-013 |
| FR-D-14 | SC-019 | FR-T-11 / 11a | SC-110 / SC-111 / SC-112 |
| FR-D-03b | SC-025 | FR-D-17 | SC-021 / 022 / 023 / 024 / 026 |
| FR-T-12 | SC-113 |  |  |

個別テストケースの詳細は実装フェーズで AI が生成する。

---

## Chapter 6. Design Principles Compliance(SW設計原則 準拠確認)

| カテゴリ | 原則 | 確認観点と本スイートでの準拠 |
| --- | --- | --- |
| 命名 | Naming | `draw` / `table` は動詞で対称。`description` / `remark` は C4/UML 慣習に沿う(用語集 1.8 と一致)。 |
| 簡潔性 | KISS | レイアウトは単一の再帰ツリー(`direction` row/column)で表現。順序は Python 合成が保証し、dot には葉1群のみ任せる(A2)。 |
| 簡潔性 | YAGNI | per-cluster の寸法上書き・ビュー単位 layout 上書き等は需要が出るまで作らない(0.3.0 は global の `options` 寸法のみ)。 |
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
| 0.3.0 | 2026-06-13 | **後方互換を破棄**し、モデル形式を全面刷新。`layout` を**再帰 cluster ツリー**(`direction` row/column・`label` で箱・`clusters`⊻`nodes`・`color`/`fill` を子孫へ cascade)に、`views`(関心事フィルタ・誘導部分グラフ)を追加。`node.cluster`・`options.clusters`・`options.layout.rows` を廃止、`options.rankdir`→`options.direction`。`draw` が入れ子クラスタを描く(ADR-005 撤回→ADR-009;A1=単一 dot run の `rank=same` は segfault で棄却)。views=ADR-010。LM-1 を可読性上限に書換。FR-D-02/03/03a/04/12/13/14/16/16a・FR-T-04/06/10/10a 改訂・追加、§3.4 ドメインモデル刷新、SC-003/004/005/007 改訂(SC-014 は「rows 余分キー無視」→ FR-D-03a「全 node 1回配置」へ**転用**)・SC-017〜020/108〜109 追加。スキーマ(`schema/model.schema.json`)は2巡の敵対的レビュー反映済み。設計ブリーフ=`poc/cluster-layout/schema-0.3.0-design-ja.md`。 |
| 0.4.0 | 2026-06-14 | **breaking**:`table` をスタンドアロン文書化。top-level `title` を**必須**化し、`table` は常に `# <H1>` + `## Nodes` / `## Edges`(H1+H2)を出力(0.3.x の H4 埋め込みモードを廃止)。H1 は全体=モデル `title` / `--view`=当該ビューの `label`。`title` 欠落は table が fail-fast(FR-T-11a)。`draw` は `title` を無視。schema は top-level `title` を required 化。既存モデルは `title` 追加が必要(samples / ARC v009 等)。`table` の全基準 `.md`(tests/samples)も 0.4.0 形式へ再生成。FR-T-11/11a・SC-110〜112 追加。StrictDoc 等「先頭 H1 必須」ツールに `.md` を直接渡せる。要望 = `docs/improvement-request-table-h1-ja.md`。 |
| 0.5.0 | 2026-06-14 | **feature**:(1) edge 端点に cluster を許可(クラスタ端点エッジ;`source`/`target` が labelled+named cluster を指す → node 優先→cluster 解決、`cid` の箱 mxCell へ接続)。pinned routing にクラスタの箱を固定ノードとして加える**堅牢な箱回避**(ADR-012、FR-D-07/17、LM-5)。(2) cluster に `description`/`remark` を追加し `table` が `## Clusters` 表(`\| cluster \| label \| description \| remark \|`)を出力(ADR-011、FR-T-12)。(3) `-Tplain` 継続行の結合で長い名前/ラベルの解析破綻を修正(ADR-013、FR-D-03b)。FR-D-08/16 改訂、IS-6・LM-5・SC-021〜026/113・ADR-011〜013 追加、トレース表更新。schema(`cluster.description`/`remark`、edge 端点 node\|cluster)更新済み。`scripts/`(draw/table)と `tests/`・基準 `.md` は実装フェーズで 0.5.0 化。 |
