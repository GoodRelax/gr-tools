# 引継プロンプト — SOVD サンプル仕様書 改善「継続」 (別セッション用)

> このファイルの「## 引継プロンプト」以下を新セッションの最初の指示にする（または「これを読んで続けろ」）。
> 背景: 前セッションで SOVD サンプルを **ANMS 準拠の自然な仕様書へ全面リライト**し、**V 字（要求→設計→API→テスト→結果）の一気通貫トレース**まで構築済み。本書はその**継続（レビュー・微調整・必要なら拡張）**用。元の出発点メモは `docs/handoff-sample-spec-improvement.md`（歴史的・before 状態）。

---

## 引継プロンプト

あなたは **StrictDocStarter 同梱の SOVD サンプル仕様書** (`samples/sovd-automotive/*.sdoc`) の品質を引き継いで**維持・改善**する。前セッションで「ツール記法デモ（仕様書として不自然）」から「**実務級の自然な仕様書**」へ全面リライト済み。本タスクはその**継続**であり、ゼロからの作り直しではない。**source of truth は実ファイル**。

### 0. 正典（最優先・必読）

- `C:\Users\good_\OneDrive\Documents\GitHub\gr-sw-maker\process-rules\spec-template-ja.md`（**ANMS テンプレ**＝章構成・記法）/ `review-standards-ja.md`（**R1–R6** レビュー基準）。これが spec の書き方の正典。
- 本リポ: `docs/improvement-items.md`（決定・Phase 0–3・**D-9b/c/d/e** の記録）/ `docs/serve-spec.md` §3.3（ファイル一覧）§6.8（サンプル方針）/ `README.md`（「同梱サンプルで SDLC を体感する」walkthrough）。

### 1. 現状（V 字一気通貫・すべて実在）

`samples/sovd-automotive/`:

- `sovd-grammar.sgra` … **共有文法**（要素 `REQUIREMENT / COMPONENT / API / TEST / TEST_RESULT` ＋合議 `SECTION`）。全 `.sdoc` が `[GRAMMAR] / IMPORT_FROM_FILE: sovd-grammar.sgra` で参照。
- `00-overview.sdoc` … 前付け（**遠隔診断の背景ストーリー**＝昔は工場で有線 UDS → TCU+SOVD で遠隔／範囲／用語／参照規格／**表記規約 §6.2 EARS・§6.3 ASIL vs CAL**／構成図／改訂履歴）。
- `01-auth / 02-data-access / 03-dtc-diagnostics / 04-sw-update` … 要求 **L0→L3**（EARS、`ASIL`=安全/`CAL`=セキュリティ、Parent/Child、図/数式を本文統合）。
- `05-common-platform.sdoc` … 機能横断の**共有ユニット**（`PLAT-` ／ **収束 N→1** を多親で表現）。
- `06-architecture.sdoc` … 設計（**単一責務1文の `COMPONENT`×17**、CA 層色分け図、クラス図×3、ADR、`Implements`→要求）。
- `07-api.sdoc` … **HTTP API 契約**（EARS、`Satisfies`→要求）。
- `08-test-spec.sdoc` … テスト（戦略＋単体/結合/システム/受入、**1 シナリオ=1 テスト=1 結果**、約 75 本、`Verifies`→要求/コンポ/API）。
- `09-test-results.sdoc` … 結果（約 75、**判定先頭 TITLE** 例 `[PASS]`/`[FAIL]`、`ResultOf`→テスト、PASS/CONDITIONAL/FAIL/SKIP）。
- `90-appendix-notation.sdoc` … 表記・記法リファレンス（`MARKUP: Markdown` で RST/Markdown 両記法を実演）。
- `_assets/sovd-architecture.{drawio,svg,png}` … 構成図（クラウド→TCU→ゲートウェイ→ECU を含む）。
- `strictdoc_config.py` … `MERMAID / MATHJAX / TRACEABILITY_MATRIX_SCREEN` 有効、`project_path` 直下。

### 2. 確立した規約（**維持せよ**。崩すと一貫性が壊れる）

- **文書**: ANMS を「**精神で**」適用（L0→L3 要求 DB＋V 字下流を維持。単一巨大ファイルには畳まない）。前付けは `00-overview` に集約。
- **要求**: 全文 **EARS**（Ubiquitous/Event/While/If/Where、日本語対応は 00 §6.2）。**単一要求**。受入基準は任意フィールド `VERIFICATION`。
- **安全/セキュリティ分離**: `ASIL`（ISO 26262・安全）と `CAL`（ISO/SAE 21434・セキュリティ）を別フィールド（00 §6.3）。純セキュリティ要求は `ASIL=QM` + `CAL`。
- **設計**: コンポーネントは**単一責務1文**＋**責務ベース命名**（`Table`/`Buffer`/`Chunked` 等の実装名を避ける）。振る舞いはテストのシナリオで表す（ADR-005）。
- **テスト**: **1 Scenario = 1 TEST = 1 RESULT**（Cucumber/ISTQB 粒度）。同一振る舞いのデータ違いのみ `Scenario Outline`+`Examples` で 1 ノード。**仕様(08) と結果(09) を別文書**に分離（1 仕様 : N 結果）。
- **収束(N→1)**: 共有部品は**多親** `Implements`/`Verifies` で表現（兄弟機能間の依存を避け、基盤に依存）。
- **関係ロール**: `Implements`(設計→要求) / `Satisfies`(API→要求) / `Verifies`(テスト→要求/コンポ/API) / `ResultOf`(結果→テスト)。
- **被覆方針**（08 §5.6）: 全 L0 ユースケース・主要 L1・API・全コンポーネントを**直接被覆**。`Constraint`/NFR はレビュー・静的解析・推移被覆で裏づけ（マトリクスの穴＝意図的）。

### 3. StrictDoc 制約・落とし穴（**0.23.1**・必ず守る/変更後 再検証）

- **`[SECTION]` は廃止** → 合議型 `[[SECTION]] … [[/SECTION]]`（grammar 要素に `PROPERTIES: IS_COMPOSITE: True`）。
- 共有文法は `IMPORT_FROM_FILE: sovd-grammar.sgra`（**同フォルダ・ファイル名のみ**。`/ \ ..` 不可）。**フォルダ単位で** export/serve すること（単一ファイル指定だと import 解決不可）。
- カスタム要素の**フィールド順は grammar 宣言順に一致必須**。関係に `ROLE` 使用可（`- TYPE: Parent` ＋ `ROLE: Verifies`）。
- **RST 落とし穴**: インライン `**強調**` / `` ``リテラル`` `` の**終端直後が「かな/漢字」や `=` だとエラー**（"Inline strong/literal start-string without end-string"）。約物 `、。」` の直後は可。**ネスト箇条書きは "Unexpected indentation"** → フラット化＋継続行は 2 スペース字下げ。`.. code-block::` 内は対象外。
- **DOCUMENT `TITLE:` は cp932 安全文字**（em dash `—` 不可＝export/server がコンソール印字でクラッシュ。`-` か `―`）。本文・節タイトル・ノード TITLE は UTF-8 で可。
- 数式 `.. math::` は client-side（static HTML は `\[..\]`＋MathJax script、`mjx-container` ではない）。Markdown ` ```mermaid ` フェンスは 0.23.0+。

### 4. 検証手順（**変更後 必ず**）

- **export クリーン**: `strictdoc export samples/sovd-automotive --output-dir <新規 temp dir>` → `error:`/`warning:` ゼロ（"Published: …" は正常ログ）。関係未解決/循環があると export が失敗する＝dangling 検出。
  - 注意: 同名 temp dir 再利用で `_cache` の Permission denied が出ることがある → **毎回新しい dir 名**で。
- **描画 grep**: `class="mermaid"` / `\[`(math) / `<table>`(list-table) / CA 色 `87CEEB|FFD700|90EE90|FF8C00` / `[PASS]` 等。
- **目視（推奨）**: `strictdoc server samples/sovd-automotive --host 127.0.0.1 --port 5111` → `http://127.0.0.1:5111/`。**DEEP TRACE**（要求→設計→API→テスト→結果が辿れる）と **Traceability Matrix**（被覆の穴）を確認。
  - サーバ起動中は `strictdoc.exe` がロック（pip 操作前に停止）。Windows でサーバ stop はポート所有 `python.exe` を kill。

### 5. 規約（リポ）

- **git は commit/push/tag をしない**（ユーザが手動）。read-only git と、頼まれれば `git add` のみ。
- スクリプト/設定（`.py`/`.bat`/`.ps1`）本体は **ASCII**。`.sdoc` 本文は日本語可。
- **公式 StrictDoc は無改変**（D-5：公式へ委譲）。テーマ等の要望は `docs/upstream-outreach.md` §6（prefers-color-scheme）。

### 6. 残・候補（やるなら。ユーザー指示優先）

- **最終通し校正**: 用語・数値・トレースの一貫性、stale 参照の総点検。
- **要求の単一化（厳密版）**: 一部 L3 要求がまだ複合的（1 責務に対し仕様が複数文）。厳密にやるなら要求も単一化＋シナリオで分解。教材としては現状容認も可。
- `hello-strictdoc` は意図的に最小（必要なら前付けだけ追加）。
- （**spec 外・ツール側**）`browser_theme` ダーク/ライト おまけ launcher＝`docs/improvement-items.md` **O-8**（既定 `auto`、公式無改変）。これは spec 作業ではない。

### 最初の一手

§0（ANMS テンプレ / レビュー基準）を読み、`samples/sovd-automotive` を **export**（＋可能なら **serve** で目視）して現状を把握する。その上で**ユーザーの指示（レビュー or 拡張 or 個別修正）に従う**。質問・意見があれば述べよ。
