# 引継プロンプト — StrictDocStarter 同梱サンプルの「仕様書品質」改善 (別セッション用)

> このファイルの「## 引継プロンプト」以下をコピーして、新セッションの最初の指示にする。
> 背景: サンプルは StrictDoc の機能デモ (Mermaid / 数式 / 画像 / トレースが strictdoc 0.23.1 で描画) としては動作確認済みだが、**「仕様書」として読むと不自然**。正式な仕様書作法に沿って自然な spec に書き直したい。

---

## 引継プロンプト

あなたは **StrictDocStarter**(StrictDoc を Windows で一発起動する companion ツール) に同梱する **SOVD サンプル仕様書** (`.sdoc`) の品質を引き継いで改善する。これらは StrictDoc の機能・記法デモとしては動く (export 成功・図/数式/画像/トレースが描画) が、**仕様書として読むと不自然**: 章立て・前付け・要求の粒度や書式・記法の一貫性が、正式な仕様書作法に達していない。これを、下記の作法に準拠した**自然な仕様書**へ書き直すのが任務。StrictDoc 機能 (記法カバレッジ・トレース・描画) は維持したまま、spec としての品質を上げる。

### 0. まず仕様書の書き方を学べ (最優先・必読 / source of truth)

着手前に次を熟読し、**仕様書の構成・記法・レビュー基準を完全に理解してから**作業する。これが spec の書き方の正典:

- `C:\Users\good_\OneDrive\Documents\GitHub\gr-sw-maker\process-rules` … プロセス規約 (ディレクトリ配下を一通り)
- `spec-template-ja.md` … 仕様書テンプレート (構成・章立て・記述様式)
- `review-standards-ja.md` … レビュー基準 (何を満たせば「良い仕様書」か)

(上記 2 つの `.md` は `gr-sw-maker\process-rules\` 配下にある想定。見つからなければ `gr-sw-maker` 内を探す。) サンプルはこの作法に準拠させ、レビュー基準を**全項目満たす**まで仕上げる。

### 1. 対象と現状 (source of truth は実ファイル)

- 対象リポジトリ: `C:\Users\good_\OneDrive\Documents\GitHub\gr-tools\StrictDocStarter`
- 主対象: `samples\sovd-automotive\*.sdoc` (必要に応じ `samples\hello-strictdoc\*.sdoc` も)
- ドメイン: **SOVD** (ASAM SOVD / ISO 17978)、機能安全 **ASIL** (ISO 26262)、A-SPICE 由来の **L0..L3** レイヤ。内容は必ず SOVD の実態に沿う (認証 / 車両データ読取 / DTC / OTA)。
- 既存ファイル:
  - `01-auth.sdoc` / `02-data-access.sdoc` / `03-dtc-diagnostics.sdoc` / `04-sw-update.sdoc` … 各 ~25 要求、L0→L3 階層、Parent/Child トレース。
  - `05-notation-rst.sdoc` / `06-notation-markdown.sdoc` … **記法デモ** (Mermaid / 数式 / 画像 / 表 / コードハイライト)。**ここが最も「仕様書として不自然」**(ツール解説と要求が混在)。要再構成。
  - `_assets\sovd-architecture.{drawio,svg,png}` … 図素材 (drawio が編集ソース)。
- 各 `.sdoc` は独自 `[GRAMMAR]` を宣言: フィールド = `UID` / `TYPE`(SingleChoice: Functional, Non-Functional, Constraint, Restriction, UseCase) / `ASIL`(QM,A,B,C,D) / `LAYER`(L0_Stakeholder,L1_System,L2_ECU_SW,L3_Unit) / `TITLE` / `STATEMENT` / `RATIONALE`(任意)。RELATIONS = Parent / Child。
- 設定: `samples\sovd-automotive\strictdoc_config.py` (MERMAID/MATHJAX 有効)。**strictdoc は入力フォルダ直下の config のみ読む** (親は遡らない)。

### 2. 「不自然さ」の典型 (例。最終判断は §0 の標準で行う)

- **前付けの欠如**: 文書の目的 / 適用範囲 (scope) / 用語・略語定義 / 参照規格 (ASAM SOVD, ISO 17978, ISO 26262, A-SPICE) / 前提・制約 / 改訂履歴 が無い。
- **記法デモの体裁**: `05/06` が「記法デモ」としてツール機能の見本になっている。図・数式は**本来の要求文書に spec として自然に溶け込ませる**べき (例: 認証シーケンス図→`01-auth`、OTA 状態機械→`04-sw-update`、構成図→全体概要/序章)。「記法デモ」という体裁は廃し、付録 (Appendix) 化するか本文へ統合する。
- **markup 不一致**: `[TEXT]` 内で `## 見出し` を使っているが RST 文書では Markdown 見出しが効かず literal 表示になる。文書の markup を統一し、見出しは適切なセクション (RST のセクション、または `[SECTION]` ノード) で表現する。
- **要求文の質**: 検証可能 (testable)・単一要求・EARS 等の一貫した書式になっているか。ASIL/LAYER 付与の妥当性、根拠 (RATIONALE) の適切さ、受入基準の有無。
- **トレースの網羅性**: L0→L1→L2→L3 の親子が漏れなく繋がり、孤立要求が無いか。

### 3. やること

1. §0 の標準に準拠して各 `.sdoc` を**自然な仕様書**へ書き直す (前付け・章立て・要求の粒度と書式・トレース)。
2. 図 / 数式 / 画像 / 表 / コードは**仕様を説明するために**配置する (機能デモのためではない)。StrictDoc の記法カバレッジ (RST raw-html Mermaid・Markdown フェンス・`.. math::`・画像・表・コード) は**どこかに残しつつ**、spec として自然に。
3. `05/06` の扱い (本文統合 / 付録化 / 改題) を標準に照らして決定し実施する。
4. 大きな構成変更を行う場合は `docs\improvement-items.md` の D-9 / S-1 や `docs\serve-spec.md` §3.3/§6.8 の記述とも整合させる (FR 番号・ファイル一覧を更新)。

### 4. StrictDoc 制約 (壊すな・必ず再検証)

- `strictdoc export samples\sovd-automotive` が **成功** し、図/数式/画像が **実際に描画** されること (strictdoc **0.23.1** で確認)。
  - Mermaid: RST は `.. raw:: html` + `<pre class="mermaid">`、Markdown は ` ```mermaid ` フェンス (0.23.0+ で描画)。
  - 数式: `.. math::` / MathJax。画像: RST `.. image::` (SVG は `<object>` で出る)、Markdown `![]()`。
- config は `project_path` 直下に維持。`[GRAMMAR]` を変更するなら**全 `.sdoc` で整合**させ、RELATIONS の UID 参照を壊さない。
- **検証手順**: export 後の HTML に `class="mermaid"` / `mermaid.min.js` / `mjx-container` / `<img>`・`<object>` が出ることを grep 確認。可能なら `strictdoc server samples\sovd-automotive --port 5111` を起動しブラウザ (`http://127.0.0.1:5111/`) で Mermaid 図・数式・画像が描画されることを目視 (左ツリーから各文書へ)。
- 注意: `strictdoc server` 起動中は `strictdoc.exe` がロックされる。pip 操作前にサーバを停止すること。

### 5. 規約

- **git は commit / push / tag をしない** (ユーザが手動)。read-only git と、頼まれれば `git add` のみ。
- スクリプト/設定 (`.py`/`.bat`/`.ps1`) 本体は ASCII。`.sdoc` 本文は日本語可。
- 途中で見つけた spec/StrictDoc 側の不整合は、その場で関連 docs と整合を取る。

### 6. 技術コンテキスト (読むと早い)

- `docs\handoff-implementation.md` … 実装フェーズ全体の引継 (Phase 0-5)。Phase 0 (strictdoc 0.23.1 化・再検証) と Phase 1 (サンプル 05/06 作成・config 配置修正) は完了済み。
- `docs\improvement-items.md` … 決定事項 (D-9 サンプル整理 / S-1 サンプル拡充 / D-8 config) と検証事実 (§1: Mermaid 記法の版依存、config 探索仕様)。
- `docs\serve-spec.md` §3.3 (ファイル構成) / §6.8 (サンプル方針)。

### 最初の一手

§0 の `process-rules` / `spec-template-ja.md` / `review-standards-ja.md` を読み、仕様書作法を把握する。その後 `samples\sovd-automotive\` の現状 `.sdoc` を一通り読み、標準とのギャップを洗い出してから書き直しに着手する。

---

## 補足 (このメモを書いた時点・2026-06-06)

- StrictDoc 動作・記法描画は strictdoc 0.23.1 で確認済み (Mermaid: sequence/flowchart/stateDiagram、MathJax、SVG/PNG 画像、表、コードハイライト — いずれも実ブラウザで描画確認)。**機能面は OK、spec としての自然さが課題**。
- 想定する改善の方向性 (最終判断は §0 標準に従う): 「記法デモ」という独立文書を廃し、図/数式を本来の要求文書または付録へ。各文書に前付け (目的・範囲・用語・参照規格・改訂履歴) を追加。`## 見出し` の markup 不一致を解消。
