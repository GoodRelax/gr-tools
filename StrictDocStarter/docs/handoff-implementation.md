# 引継プロンプト — StrictDocStarter 実装フェーズ (別セッション用)

> このファイルの「## 引継プロンプト」以下をコピーして新セッションの最初の指示にする。

---

## 引継プロンプト

あなたは **StrictDocStarter**（StrictDoc を Windows で一発で使えるようにするバッチ/PowerShell 群。「公式の補助」に徹する companion ツール）の実装を引き継ぐ。仕様策定と2種の敵対的レビュー（内部整合＋公式承認視点）は完了済み。これから**サンプル拡充→実装→レビュー→テスト**を進める。

### 0. まず読むもの（source of truth）
- `docs/improvement-items.md` … 全決定（D-1..D-10）・実装TODO（I/S/O）・検証事実。**最優先で熟読**。
- `docs/serve-spec.md` … manage 側 v1.1。**Chapter 6（FR-1100系・可視ウィンドウ方式）と §6.9（テスト）が authoritative**。§2-§5 の旧記述は supersede 済み（§6.7 一覧参照）。
- `docs/setup-spec.md` … setup 側 v1.1。**Chapter 7（FR-330 version / FR-340 uninstall / FR-350 chromedriver / FR-360 install完成）**。
- `docs/upstream-outreach.md` … 実装後の公式誘導プラン（今は読むだけ）。
- ユーザーのグローバル CLAUDE.md: **git commit / push / tag は禁止（ユーザーが手動）**。read-only git と、頼まれれば `git add` のみ可。

### 前提・環境
- Windows 11 / PowerShell 5.1。strictdoc は `C:\Python313`（**現状 0.21.1。下記 Phase 0 で最新 0.23.x へ上げる**）。
- `drawio` スキルが利用可能（SOVD 図の作成→svg/png 出力に使う）。
- 既存実装: `manage-strictdoc.ps1` は**旧・隠れデーモンモデルで実装済**（＝可視ウィンドウへ**リファクタ**が必要）。`lib/install.ps1` は Phase A のみ実装（B/C/D/E はスタブ）。
- 既存テスト基盤: `vm-tests/`。

### 進め方（フェーズ）

**Phase 0 — strictdoc を最新へ＋再検証（最初に必ず）**
- `pip install -U strictdoc` で **0.23.x** へ。`strictdoc --version` 記録。
- 主要挙動を最新で再検証し、ズレがあれば spec/improvement-items を即修正:
  - Mermaid: RST `.. raw:: html`（全版）と **Markdown ` ```mermaid ` フェンス（0.23.0+ で MERMAID 有効時）** の両方が export で `class="mermaid"` を出すか。
  - `strictdoc_config.py` は project_path 直下のみ参照（親を遡らない）。
  - `strictdoc server` は foreground（`Uvicorn running on …` / 文法エラーは `Could not parse … TextXSyntaxError` で即終了）。
  - `strictdoc new <path>` の生成物。
- **動作確認版を README に記録**（FR-332）。

**Phase 1 — SOVD サンプル拡充（公式仕様準拠・内容は SOVD に沿う）**
- 配置は **`samples/sovd-automotive/`**。図・数式・Markdown 散文は `[TEXT]` ノードで（sovd の `[GRAMMAR]` 制約は REQUIREMENT のみ）。**内容は必ず SOVD（ASAM SOVD / ISO 17978、認証/データアクセス/DTC/OTA 等）に沿う**こと。
- 作るもの（D-9）:
  - `05-notation-rst.sdoc`（**RST**）: Mermaid（`.. raw:: html` + `<pre class="mermaid">`、SOVD 診断シーケンス）＋ **数式 `.. math::`**（例: 署名検証/タイミングの式）＋ 図 `.. image::`（svg/png）。
  - `06-notation-markdown.sdoc`（**`MARKUP: Markdown`**）: 表 / 箇条書き / **コードハイライト**（` ```python ` 等）/ 画像 ＋ **Mermaid は ` ```mermaid ` フェンス**（0.23.0+）。
  - `samples/sovd-automotive/_assets/`: 画像素材。**`.drawio` は編集ソースとして置き、export した `.svg`/`.png` を `.sdoc` から埋め込む**（StrictDoc は .drawio を直接描画しない＝画像を貼る）。`.png` と `.svg` の両方をサンプルに含める。drawio スキルで SOVD アーキ図/シーケンス図を作成→svg/png 出力。
  - hello-strictdoc を最小化: **`03-try.sdoc` 削除、`04-mermaid.sdoc` 削除**（Mermaid デモは 05 へ昇格）、`01-hello.sdoc`/`02-design.sdoc` のみ残す。
- 各サンプルは **最新 strictdoc で `strictdoc export` し、図/数式/画像が実際に出る**ことを確認（O-4 相当）。MERMAID/MATHJAX を `samples/strictdoc_config.py` で有効化（D-8: `strictdoc new` 出力準拠の薄いラッパ）。

**Phase 2 — 実装（spec 準拠・フェーズ分割）**
- 2a. **manage-strictdoc を可視ウィンドウ方式へ（D-6/FR-1100系）**: 旧 Hidden+poll+PID+transcript ロックを撤去し、`cmd /c start … strictdoc server …` で**可視窓**起動＋ブラウザ。最小メニュー（D-7/FR-1121: Start/Open/Edit config/Quit）。二重起動=ポートチェック（FR-1104）。config scaffold（FR-1140系、if-missing、`strictdoc new` 準拠＋MERMAID追記）。OneDrive/空白/日本語パス警告（FR-1130系）。
- 2b. **setup 完成（O-5/FR-360）**: install.ps1 Phase B/C/D/E。`strictdoc.version`（FR-330、既定 latest／範囲固定可）。HTML2PDF 用 chromedriver は任意取得（FR-350、既定OFF）。
- 2c. **uninstall-strictdoc.bat 新規（FR-340系/D-10）**: config 駆動、dry-run+yes 必須。既定: strictdoc(pip)＋生成物=ON、scaffold config/VS Code拡張/winget追加=OFF。Python/VSCode/Claude/Git 不可。
- 2d. **O-2**: `.gitignore` に `__pycache__/` `*.pyc`。
- 仕様の cross-ref（serve Appendix A.2/A.3、setup FR-806 表に uninstall 行）も実装に反映。

**Phase 3 — コードの敵対的レビュー→修正ループ**
- **別エージェント**でコードをレビュー（spec 準拠/バグ/PowerShell の罠/空白・日本語パス/エラー処理/可視窓の挙動）。**指摘ゼロになるまで修正ループ**（spec レビューと同じ流儀）。

**Phase 4 — Claude Code 単体テスト（安全な範囲のみ）→ バグ修正**
- **dev マシンで本物の install/uninstall を走らせない**（winget/pip で環境破壊するため）。
- dev で可: manage/server（strictdoc 導入済）、`setup … dryrun`、scaffold、パス警告、サンプル export。
- 不可（Hyper-V 送り）: 実 install（Phase B/C/D/E）、uninstall（破壊的）。

**Phase 5 — Hyper-V 自動テスト**
- クリーン Windows VM（スナップショット）で full フロー。**既存 `vm-tests/` を活用/拡張**。serve-spec §6.9 TV1-9 / setup の §5 シナリオを回す。

**全フェーズ共通**
- 途中で**仕様の不具合/改善が出たら、その場で `docs/*-spec.md` と `improvement-items.md` を両方更新**し整合を保つ（FR番号・supersession・版依存記述に注意）。大きな変更は再度敵対的レビュー。
- **「公式の補助」を逸脱しない**（サーバ起動/雛形/設定は公式へ委譲＝D-5）。
- git は commit/push/tag しない。

### 最初の一手
Phase 0（strictdoc を 0.23.x へ上げて主要挙動を再検証、テスト版記録）から開始する。

---

## 補足（このメモを書いた時点の状況・2026-06-06）
- Spec は内部整合レビュー（10→6→0 で収束）＋公式承認視点レビュー（**VERDICT: Yes**、BLOCKER=Mermaid版ズレ 修正済）を通過済み。
- 未着手: 上記 Phase 0-5、README（O-6）。
- 既知の半端: `samples/hello-strictdoc/04-mermaid.sdoc`（RST化済・動くが D-9 で sovd へ移設予定）、`samples/strictdoc_config.py`（MERMAID有効・暫定）。
