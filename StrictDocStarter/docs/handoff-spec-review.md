# 引継プロンプト — SOVD サンプル仕様書 レビュー (別セッション用)

> このファイルの「## 引継プロンプト」以下を新セッションの最初の指示にする（または「これを読んでレビューしろ」）。
> 背景: 直前のセッションで SOVD サンプルを **要求/ユースケースの分離・最上位要求の新設・UC-UAT-Result・被覆方針の明示・ファイル採番整理** まで改修済み（improvement-items Phase 4-6）。本書はその**レビュー**用。

---

## 引継プロンプト

あなたは **StrictDocStarter 同梱の SOVD サンプル仕様書** (`samples/sovd-automotive/*.sdoc`) を**レビュー**する。直前セッションで大改修済み（下記「現状」）。**source of truth は実ファイル**。レビューは ANMS テンプレ・R1–R6・IEEE 29148（要求と UC の分離）の観点で行い、指摘を重大度付きで提示する。

### 0. 正典（最優先・必読）

- `C:\Users\good_\OneDrive\Documents\GitHub\gr-sw-maker\process-rules\spec-template-ja.md`（**ANMS テンプレ**＝章構成・記法）/ `review-standards-ja.md`（**R1–R6** レビュー基準）。
- 本リポ: `docs/improvement-items.md`（**Phase 6** = 要求/UC 分離・最上位要求・採番整理。Phase 4-5 も参照）/ `docs/serve-spec.md` §3.3（ファイル一覧）/ `docs/handoff-spec-continuation.md`（旧経緯・Phase 0-3）。

### 1. 現状（最終ファイル構成・すべて実在）

`samples/sovd-automotive/`:

- `sovd-grammar.sgra` … 共有文法。要素 `REQUIREMENT`(TYPE: Functional/Non-Functional/Constraint/Restriction/**UseCase**, ASIL, CAL, LAYER …) / `COMPONENT` / `API` / `TEST` / `TEST_RESULT` ＋合議 `SECTION`。全 .sdoc が `IMPORT_FROM_FILE: sovd-grammar.sgra` で参照。
- `00-overview.sdoc` … 前付け（背景・範囲・用語・参照規格・表記規約・§3.4 文書構成＋V字注記・改訂履歴）。
- `01-stakeholder-requirements.sdoc` … **要求 (EARS)**。最上位 `SYS-L0-001`（TYPE=Functional「本システムは〜提供すること」）＋各ドメイン L0（AUTH/DATA/DTC/SWU-L0-00x）。L0-001 は各ドメインの要求、L0-002.. は子要求。
- `02-usecases.sdoc` … **ユースケース (シナリオ)**。アクター定義＋UC図(Mermaid)＋UC一覧＋`UC-000`(システム全体)〜`UC-004`(各ドメイン)。各 UC は TYPE=UseCase、STATEMENT はシナリオ（アクター/事前条件/主成功シナリオ/事後条件/代替フロー）。**UC → 要求**(Parent で実現)。
- `03-auth / 04-data-access / 05-dtc-diagnostics / 06-sw-update` … 要求 L1→L3（EARS、ASIL/CAL、Parent/Child）。各 L1 は対応する L0 要求(01)を Parent。
- `07-common-platform.sdoc` … 共有ユニット（`PLAT-` ／ 収束 N→1）。
- `08-architecture.sdoc` … 設計（`COMPONENT`×17、CA 層色分け、クラス図、ADR、`Implements`→要求）。
- `09-api.sdoc` … HTTP API 契約（EARS、`Satisfies`→要求）。
- `10-test-spec.sdoc` … テスト（UT/IT/ST/AT、`Verifies`→コンポ/要求/**UC**。§5.6 に**被覆表**）。
- `11-test-results.sdoc` … 結果（`TR-*`、判定先頭 TITLE、`ResultOf`→テスト）。
- `90-appendix-notation.sdoc` … 記法リファレンス（`MARKUP: Markdown`）。
- `_assets/sovd-architecture.{drawio,svg,png}` / `strictdoc_config.py`（MERMAID/MATHJAX/TRACEABILITY_MATRIX_SCREEN 有効）。

### 2. 確立した構造（**維持せよ**。崩すと一貫性が壊れる）

- **要求とユースケースの分離**（IEEE 29148 / A-SPICE）: 要求=「システムが満たす条件」(EARS、TYPE=Functional 等)、UC=「アクターの使い方」(シナリオ、TYPE=UseCase)。別文書 (01 vs 02)。
- **V 字トレース**: 最上位要求 `SYS-L0-001` → 各ドメイン L0(01) → L1→L2→L3(03-06) → 共有(07) → 設計(08) → API(09) → テスト(10) → 結果(11)。
- **UC-UAT-Result**: `UC-00x` ← 受入テスト `AT-*`(Verifies) ← `TR-AT-*`(ResultOf)。UC は要求を Parent で実現。
- **被覆方針**(10 §5.6): 全要求に動的テストは付けない。ユースケース→UAT、各層要求→UT/IT/ST、制約(Constraint)→レビュー/静的解析、上位要求→推移被覆。トレーサビリティは全要求・テストケースは選択的。
- **UID**: 各カテゴリ連番・欠番なし（AUTH-L1:001-011 等）。`SYS-L0-001` 最上位、`UC-000..004`。ファイル番号 00-11＋90 連番。

### 3. StrictDoc 制約・落とし穴（**0.23.1**・変更したら再検証）

- `[[SECTION]] … [[/SECTION]]`（composite）。`IMPORT_FROM_FILE: sovd-grammar.sgra`（同フォルダ・ファイル名のみ）。**フォルダ単位で** export/serve。
- カスタム要素のフィールド順は grammar 宣言順に一致必須。関係に `ROLE`（`Parent` + `ROLE: Implements/Satisfies/Verifies/ResultOf`）。
- **textX 落とし穴（重要）**: 文書直下の `[TEXT]`（FREETEXT）と次の `[[SECTION]]` の間は **空行ちょうど 1 つ**。**2 つ以上だと `Expected EOF` でパース失敗**。
- **RST 落とし穴**: インライン `**強調**` / `` ``リテラル`` `` の終端直後が「かな/漢字」「=」だとエラー（約物・スペースは可）。ネスト箇条書きは不可（フラット化）。`.. code-block::` 内は対象外。
- **DOCUMENT `TITLE:` は cp932 安全文字**（em dash `—` 不可。`-` か `―`）。本文・節タイトル・ノード TITLE は UTF-8 可。
- 数式 `.. math::`（MathJax）、Mermaid は RST `.. raw:: html` + `<pre class="mermaid">`（全版）/ Markdown ` ```mermaid ` フェンス（0.23.0+）。

### 4. レビュー観点（今回の重点）

- **R1（要求品質）**: EARS・単一要求・検証可能・testable。複合要求の残り（M3）。
- **R2（設計）/ R6（テスト）**: COMPONENT 単一責務、テスト粒度（1 シナリオ=1 テスト=1 結果）。
- **IEEE 29148 整合**: 要求(01)とUC(02)の分離が適切か。UC→要求(Parent)、UC←AT(Verifies) のトレースが正しいか。UC シナリオの質（アクター/フロー/代替）。
- **被覆**: 10 §5.6 の方針と実トレースの整合（直接/推移/レビューの仕分け、マトリクスの穴が意図的か）。
- **一貫性**: 用語・数値・トレースの stale 参照。文書名参照（01-stakeholder/02-usecases/03-auth…）の整合。
- **既知の据置き**: M2（`DATA-L3-003` 浮動小数点制約が JsonSerializer 由来だが 04-data-access にある＝07 へ移すか）、M3（DTC-L0-003/SWU-L0-002 等の複合要求）、`UC-000` の 0 始まり（システム全体UC、許容範囲）。

### 5. 検証手順（**変更後 必ず**）

- **export クリーン**: `strictdoc export samples/sovd-automotive --output-dir <新規 temp dir>` → `error:`/`warning:` ゼロ（関係未解決/循環は export 失敗＝dangling 検出）。temp dir は毎回新名（`_cache` Permission denied 回避）。
- **描画 grep**: `class="mermaid"` / math / `<table>` / CA 色 `87CEEB|FFD700|90EE90|FF8C00` / `[PASS]` 等。
- **目視（推奨）**: `strictdoc server samples/sovd-automotive --host 127.0.0.1 --port 5111`。**Traceability**（1 階層）と **Deep Traceability**（全階層）と **Traceability Matrix** を確認。Windows でサーバ stop はポート所有 `python.exe` を kill（`Get-NetTCPConnection -LocalPort 5111`）。

### 6. 規約（リポ）

- **git は commit/push/tag をしない**（ユーザが手動）。read-only git と、頼まれれば `git add` のみ。
- スクリプト/設定（`.py`/`.bat`/`.ps1`）本体は ASCII。`.sdoc` 本文は日本語可。
- **公式 StrictDoc は無改変**（D-5）。テーマ/トレース深さ等の要望は `docs/upstream-outreach.md`（§6 ダークモード / §7 Deep Trace 深さ制限）。

### 最初の一手

§0（ANMS テンプレ / R1–R6）を読み、`samples/sovd-automotive` を **export**（＋可能なら **serve** で目視）して現状を把握する。その上で **R1–R6 ＋ IEEE 29148（要求 vs UC）** でレビューし、指摘を重大度付き（Critical/High/Medium/Low）で提示する。質問・意見があれば述べよ。**まずレビュー結果を提示し、修正はユーザーの合意を得てから**着手する。
