# drawio-uml 0.3.0 モデル設計ブリーフ(敵対的レビュー基準)

作戦1(クラスタ階層化)+ 作戦2(views)を統合する 0.3.0 モデル形式。**後方互換は考慮不要**(オーナー決定)。
- スキーマ: `schema/model.schema.json`
- 具体例(新形式): `poc/cluster-layout/arc-0.3.0.model.json`
- レイアウト実現性の実証: `poc/cluster-layout/FINDINGS-ja.md`(A2 が狙いの絵を end-to-end 再現済み)

## 1. トップ構造

`nodes`(定義)/ `edges` / `layout`(クラスタツリー)/ `views` / `options`。
0.2.x の `node.cluster` ・ `options.clusters` ・ `options.layout.rows` は**廃止**。

## 2. cluster(レイアウトツリーの要素・再帰)

- `direction`(`row`|`column`)で子/メンバの並べ方を決める(既定 `options.direction`、既定 `column`)。
- **`label` があれば破線ボックスを描く。無ければ「並べるためだけの透明な器」**。
- 中身は **`clusters`(子クラスタ)か `nodes`(メンバのノード名)のどちらか一方**。`label` は内部/葉どちらにも付く(外側の帯 `consider` は label + clusters)。
- `name` = views / table から参照する短い id(任意・一意)。
- `color` → 箱の枠線 + 子孫ノードの `stroke` 既定にカスケード。`fill` → 子孫ノードの `fill` 既定にカスケード(箱自体は塗らない)。ノード側 `fill`/`stroke` が優先。

## 3. 階層数

**スキーマ上は無制限(`cluster` の自己参照)。推奨は 3 段**(band / cluster / sub-cluster)、4 段超で warn。
エンジンは深さ非依存(dot は葉のみ・Python が再帰合成・routing は最終フラット pass)。

## 4. views(作戦2)

- ビューのノード集合 = `nodes`(明示名)∪ `clusters`(指定クラスタ配下の全ノード)。最低一方、両方指定=和集合。
- エッジ = 誘導部分グラフ(両端が集合内のみ)。
- **レイアウト = master の `layout` を選択ノードに剪定 → 同じ A2 で詰め直し**。空クラスタ/帯は消滅、一部だけ残ったクラスタは survivors ぶんに縮小、凡例は生存クラスタに限定。
- 構造の部分集合向き(`perceive→consider→act` のような振る舞いフローは対応エッジが無く疎になる=対象外)。
- ビュー単位の `layout` 上書きは将来(YAGNI)。

## 5. レイアウトエンジン(A2・PoC 実証済)

葉クラスタを**独立 dot run**で組み(`direction`=rankdir、エッジの無い葉は**陰線**で `direction` 方向に整列)→ **Python が `direction` 順に再帰合成** → 全ノード確定後に **pinned neato で全エッジ箱回避**。
A1(単一 dot run で兄弟クラスタの左右順を強制)は `rank=same` がクラスタ所属と衝突し **dot が segfault** → 棄却済み。

## 6. 実行時制約(スキーマでは表現せず draw/table が fail-fast)

- `node.name` 一意。
- `layout` がある時:**全ノードを丁度1回**いずれかの葉 `nodes` に配置(未配置・重複はエラー)。
- `cluster.name` 一意。
- `view.nodes`/`view.clusters`・`edge.source`/`target` が実在を参照(未解決はエラー)。
- ノードは複数 view に属してよいが、`layout` 上の物理位置は1つだけ。

## 7. 決定(オーナー承認済み・ただし欠陥があれば指摘可)

| ID | 決定 |
| --- | --- |
| D1 | 再帰 row/column クラスタツリーを採用(構造+順序+スタイル+所属を1箇所) |
| D2 | 階層数はスキーマ無制限・推奨3・4超 warn(ハードキャップ無し) |
| D3 | cluster の `color`/`fill` を子孫ノードへカスケード(node 側が優先) |
| D4 | `layout` 省略=フラット(dot 全任せ、flow=`options.direction`) |
| D5 | `layout` がある時は全ノードを丁度1回配置(fail-fast) |
| D6 | ボックス描画 ⟺ `label` あり |

## 8. レビュー観点(疑ってかかること)

曖昧さ・足元の落とし穴・一貫性の綻び(例:cluster は `color` だが node は `stroke`/`fill`、`nodes` がオブジェクト定義と名前参照で二義)・抜け・矛盾。ARC 例と view 挙動を本当に表現できるか。実装時に刺さる点。各指摘は**重大度(High/Med/Low)と具体的修正案**つきで。

## 9. 敵対的レビュー反映(0.3.0 確定事項)

別エージェントの敵対的レビュー(High 4 / Med 5 / Low 5)を反映。スキーマ記述は更新済み(再検証緑)。

- **F1 ノードのクラスタパス(table 用)**:**root→葉の「名前付き祖先クラスタの連鎖」**(無名段はスキップ)と定義。`table` のクラスタ列・`--cluster X` は X の名前付きサブツリーで照合。
- **F2 凡例の出所**:**最外殻の labelled クラスタのみ**(`label` を持ち、`label` を持つ祖先がいないクラスタ)を `color` で重複排除して凡例に出す。ARC では input/consider/output/vocabulary の4つ。内側の world/goal/plan は出ない。新フィールド不要。旧 FR-D-12 を 0.3.0 で改訂。
- **F3 name = 参照鍵**:重複名は fail-fast、無名クラスタは view/`--cluster` から到達不可、`view.clusters` は `cluster.name` に解決(未解決は fail-fast)。
- **F4 内部クラスタの view 選択**:可。サブツリー全ノードを含む。剪定で生存メンバを持つ入れ子箱は残す。ARC 例に `conception`(`clusters:["consider"]`)を fixture 追加。
- **F5 カスケード**:`color`/`fill` は**最近接**の祖先が決め、両者は独立に解決。node 側 `fill`/`stroke` が優先。
- **F6 `direction` 既定**:`cluster.direction` から JSON-Schema の `default` を削除(validator が `column` を注入して `options.direction` を握り潰すのを防ぐ)。解決順 = cluster → options → column(文書規約のみ)。
- **F7 葉の順序**:`nodes` の並び順は**葉に内部エッジが無い時のみ**整列順。エッジ有時は dot の rank 配置が支配(並びはヒント)。
- **F8 root**:通常は内部クラスタ。葉 root(`nodes`)も可=単一フラット群。root に `label` を付けると全体を囲む箱。
- **F10 空 view 防止**:`view.nodes`/`view.clusters` に `minItems:1`(空選択を弾く)。
- **F11 深さ**:推奨 ≤3 段、4 超で warn(ハードキャップ無し)で統一。
- **F13 命名**:cluster は `color`(箱枠線＋子孫 stroke の二役)、node は `stroke`/`fill`。`additionalProperties:false` で誤キーは fail-fast。
- **F14 調整値**:`node_separation`/`rank_separation`/`column_width` は**意図的に global**(per-cluster 上書きは YAGNI、必要なら後日)。

### 実装フェーズの要注意(スキーマ欠陥ではない)

PoC `draw_poc.py` は**旧形式**(`node.cluster`・`options.layout.rows`)を読む。FINDINGS の「A2 実証」は**レイアウト幾何**の証明であり、**新スキーマの走査**ではない。よって本実装では再帰コンポーザ・箱描画(現 `cluster_box_cells` は `/` 分割前提)・凡例(最外殻ルール)・table のパス導出を**新ツリー向けに新規実装**する。`_route_pinned`(flat)は流用可。

## 10. 敵対的レビュー 2巡目 反映(0.3.0 確定・追補)

2巡目で「設計欠陥は無いが artifact 側の明文化漏れ」3点を解消(スキーマ記述に反映・再検証緑):
- **N1 凡例ルールをスキーマに明記**:`cluster.color` 記述に「最外殻 labelled クラスタが色で重複排除して swatch、色無しは #888888」を追加。
- **N2 クラスタパスの符号化を明記**:`cluster.name` 記述に「名前付き祖先を `/` で連結・`name` に `/` 禁止(fail-fast)・`--cluster` は `/` セグメント境界一致・最深の名前付き祖先が内部クラスタならそのパス(`consider` vs `consider/world` で区別)」を追加。
- **N5 深さ警告は labelled 段のみ数える**:`cluster.clusters` 記述を「root→葉の **labelled** 段のみ数えて ≤3 推奨・4超 warn(無名の器=root/帯/行は数えない。ARC 最深= consider→world=2 段)」に修正。これで正準 ARC 例が自分の警告を踏まない。

その他(spec へ反映):N3 無名クラスタは参照不可(設計どおり・draw/table は info note 推奨)/ N4 labelled な葉 root・無名単一子チェーンは合法 no-op / N6 **剪定ビューの最外殻・凡例はプルーン後ツリーで再計算**(view `world` では `world` が最外殻になる)/ N7 view キーと cluster 名は別名前空間(`--view X` と `--cluster X` は別物)。
**stale な 0.2.x 文書**(`docs/proposal-views-ja.md` の旧 FR-D-12・`/`前方一致、`docs/spec-ja.md` の ADR-005・LM-1)は 0.3.0 spec で明示的に supersede する。
