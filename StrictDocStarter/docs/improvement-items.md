# StrictDocStarter 改善項目メモ (improvement-items)

- 記録日: 2026-06-06（随時更新）
- 検証環境: strictdoc **0.23.1**（**Phase 0 で 0.21.1 → 0.23.1 へ更新し再検証済**, pip, `C:\Python313\Lib\site-packages\strictdoc`）/ Windows 11 / Python 3.13.3 / PowerShell 5.1。§1 の各事実は 0.23.1 で再確認済（下記）。
- きっかけ: `.sdoc` の Mermaid 図がエラー → 調査が StrictDoc の feature・設定・サーバ運用・公式提供範囲の棚卸しに発展。
- ゴール: **StrictDocStarter の更新版リリース**。本メモで「分かったこと・決めたこと・やること」を確定 → 最終的に `serve-spec.md` / `setup-spec.md` / `README.md` へ反映（正式仕様化）。

> 本ファイルは**作業メモ（backlog）**。**§1**=検証済み事実 / **§2**=合意済み決定(D-1..D-6) / **§3・§3.5**=実装TODO(I-/S-/O-) / **§4**=設計判断(決定済み D-7..D-10) / **§5**=適用済み / **§6**=参考。

---

## 0. 重要方針（2026-06-06 更新）— 公式に委譲、コアはブートストラップ

調査の結果、StrictDoc 公式は以下を**既に提供**している：**サーバ起動**（`strictdoc server`＝可視コンソール、readiness/error 表示つき）・**プロジェクト雛形**（`strictdoc new`）・**設定形式**（`strictdoc_config.py`）。**公式に無いのはインストーラだけ**（pip/Docker のみ、配布バイナリ無し）。

→ **StrictDocStarter は「Windows 一発ブートストラップ＋ダブルクリック」に集中**し、上記は**公式へ委譲（再発明しない）**。サーバは**可視ウィンドウ方式**へ寄せる（隠れデーモン＋ポーリング＋PID追跡＋transcript ロックを**廃止**）。この方針で **S-2（OneDrive）/ S-5（サーバ管理）は大幅縮小**、自作 config テンプレ（I-1）も縮小。

---

## 1. 検証で確定した技術的事実（すべて実機確認済み）

> **Phase 0 再検証（2026-06-06, strictdoc 0.23.1）**: 下記 §1 の主要事実を最新版で再確認済 — (a) Mermaid は RST `.. raw:: html` と Markdown ` ```mermaid ` フェンスの**両方**が export で `<pre class="mermaid">` を出力＋`mermaid.min.js` コピー（`language-mermaid` 止まりにならない）、(b) `strictdoc_config.py` は**入力フォルダ直下のみ**参照・親は遡らない（子フォルダ単独 export で MERMAID 資産が出ないことで確認）、(c) `strictdoc server` は前面コンソールで `Uvicorn running on …` を表示／文法エラー時 `error: Could not parse … TextXSyntaxError` で**即終了**（ポート開かず）、(d) `strictdoc new` 生成 config の `create_config()` 形式は不変・MERMAID 非同梱。**矛盾するズレは無し**（spec の予測どおり）。

### 1.1 Mermaid の正しい記法（0.21.1 で確立 / 0.23.1 で再確認）
- **`[TEXT]` ノード + RST `.. raw:: html` + `<pre class="mermaid">`** が正解（公式ガイド §"Mermaid diagramming and charting tool" と同形）。
  ```
  [TEXT]
  STATEMENT: >>>
  .. raw:: html

      <pre class="mermaid">
      sequenceDiagram
          U->>S: ...
      </pre>
  <<<
  ```
- **不可（※Markdown フェンスは版依存）**: ` ```mermaid ` フェンスは **0.22 以前は不可**（`<code class="language-mermaid">` 止まりで `startOnLoad` が拾わない）だが、 **0.23.0+ では MERMAID 有効時に正式レンダリング**（公式 0.23.0 リリースノート#8 で実証）。`MARKUP: Markdown` での生 `<pre>`（エスケープ）・`.. raw::`（素通り）/ `[REQUIREMENT]` 直後の `[FREETEXT]`（パースエラー）は全版で不変。
- 対応済み: `samples/hello-strictdoc/04-mermaid.sdoc`（RST 化・描画確認済み）。
- ⚠️ **版依存（確定）**: RST raw html は **全版で有効**。加えて **0.23.0+ では Markdown の ` ```mermaid ` フェンスが正式サポート**（MERMAID 有効時、公式 0.23.0 リリースノート#8 で実証済）。**latest 既定（D-4）＝0.23.x なので、Markdown サンプル(06)はフェンス記法を主に使える**。導入版を O-4 smoke test で検証。

### 1.2 MERMAID feature の有効化が必須
- `project_features=["MERMAID"]` が無いと `mermaid.min.js` が output にコピーされない（検証: 無=0 / 有=1、`Copying Mermaid assets`）。
- 実体: `…/strictdoc/export/html/_static_extra/mermaid/mermaid.min.js`（Mermaid v11.12.2, ~2.75MB）。feature ON 時のみ `output/html/_static/mermaid/` へコピー（`html_generator.py:232`）。

### 1.3 strictdoc 設定ファイルの探索仕様
- StrictDoc は**「入力に渡したフォルダ直下」の `strictdoc_config.py`（無ければ `strictdoc.toml`）だけ**を読む。**親は遡らない**（実機確認）。
- → 設定は **`project_path` 直下**（ツール root に置いても無視）。形式は **Python `strictdoc_config.py` 推奨**（TOML は **0.21.x で既に deprecated**＝読込時に警告、移行ガイド "2025-Q4" アンカー）。CLI `--config <path>` で任意の場所も指定可。
- `create_config()` が `ProjectConfig(project_title / project_features / include_doc_paths / exclude_doc_paths …)` を返す形式。

### 1.4 feature（プラグイン）一覧 — `ProjectFeature` 列挙（0.21.1 / **0.23.1 で再確認・列挙不変**）
既定ON = `TABLE_SCREEN` / `TRACEABILITY_SCREEN` / `DEEP_TRACEABILITY_SCREEN` / `SEARCH`。

| feature | 用途 | 安定度 | 既定 | 備考 |
|---|---|---|---|---|
| `TABLE_SCREEN` | 表ビュー | Stable | **ON** | |
| `TRACEABILITY_SCREEN` | トレーサビリティ | Stable | **ON** | |
| `DEEP_TRACEABILITY_SCREEN` | 深いトレーサビリティ | Stable | **ON** | |
| `MATHJAX` | TeX/LaTeX 数式 | **Stable** | OFF | JS同梱。記法 RST `.. math::` / `` :math:`…` `` |
| `SEARCH` | 全文検索 | Exp | **ON** | |
| `HTML2PDF` | PDF 出力 | Exp | OFF | **外部依存: Chrome/chromedriver** |
| `REQIF` | ReqIF 入出力 | Exp | OFF | |
| `DIFF` | 版間差分/変更履歴 | Exp | OFF | |
| `PROJECT_STATISTICS_SCREEN` | 統計 | Exp | OFF | |
| `TREE_MAP_SCREEN` | ツリーマップ | Exp | OFF | |
| `TRACEABILITY_MATRIX_SCREEN` | トレースマトリクス | Exp | OFF | |
| `REQUIREMENT_TO_SOURCE_TRACEABILITY` | 要求⇔ソース | Exp | OFF | source 設定要 |
| `SOURCE_FILE_LANGUAGE_PARSERS` | ソース言語パーサ | Exp | OFF | source 設定要 |
| `MERMAID` | 図 | Exp | OFF | JS同梱 |
| `RAPIDOC` | OpenAPI 表示 | Exp | OFF | JS同梱 |
| `NESTOR` | 関係グラフ画面 | Exp | OFF | JS同梱 |
| `ALL_FEATURES` | 全部入り(メタ) | — | OFF | `ProjectFeature.all()` 展開＝全ON |

- JS実体は `_static_extra/` の **mermaid/mathjax/nestor/rapidoc** の4つのみ（feature ON 時に output へコピー）。
- **コードハイライト = ビルトイン**（Pygments 必須依存、フラグ不要）。**PlantUML = ネイティブ非対応**（回避: 画像化埋め込み / PlantUMLサーバ img / Mermaid 代替）。
- ※ 上表は **`ProjectFeature` enum の分類（stable/experimental）と `DEFAULT_FEATURES`（無 config 時の既定）** に基づく。一方 **`strictdoc new` の生成 config** は `TRACEABILITY_MATRIX_SCREEN` / `REQUIREMENT_TO_SOURCE_TRACEABILITY` を既定 ON にする（テンプレ上は "Stable" コメント下に配置）＝ enum 分類と `strictdoc new` テンプレの既定は別物。

### 1.5 stable と experimental の違い（公式定義）
- stable=既知エッジケース網羅＋十分なユーザがテスト済み。experimental=未完成 or テスト未完。**機械的差は無い**（`is_feature_activated` は単純 membership、警告なし）。違いは成熟度のみ。実務影響=版間で挙動/出力が変わり得る・再現性低下。
- stable は `TABLE/TRACEABILITY/DEEP_TRACEABILITY/MATHJAX` の4つだけ。**MERMAID 含むそれ以外は experimental**。

### 1.6 ALL_FEATURES のネガ
- 実験機能全ON＝不安定/将来変更。`HTML2PDF` の chromedriver 依存も入る。未使用でも JS資産を毎回コピー＝肥大・低速。source 系は設定前提で空回り。再現性低下。→ 本番は非推奨、狙い撃ち列挙。

### 1.7 公式が提供するもの（再発明回避の前提・2026-06-06 確認）
- **公式インストーラは無い**: `pip install strictdoc`（Python 3.10+ 必須）/ nightly（`pip … git+…@main`）/ Docker のみ。**GitHub Releases に配布バイナリ資産ゼロ**（.exe/.msi/winget/standalone なし）。→ **Python も端末も無い Windows ユーザを一発起動する役は公式に無い**＝StrictDocStarter の存在意義。
- **`strictdoc new <path>` が雛形生成**（実機確認）: `docs/high_level_requirements.sdoc` / `docs/low_level_requirements.sdoc` / `src/main.c` / **`strictdoc_config.py`（feature トグル＋`include_doc_paths`/`include_source_paths` 付き）**。※ **MERMAID は含まれない**。→ 我々の config テンプレ自作は重複。
- **`strictdoc server` は foreground（可視コンソール）専用**: デーモン化フラグ無し。**準備完了**= stderr `Application startup complete.` / `Uvicorn running on http://host:port`。**失敗（文法エラー等）**= stdout `error: Could not parse… TextXSyntaxError` を出して**即終了**（ポート開かず）。→ readiness/error は**公式コンソールが提供済み**。
- **server は .sdoc 変更を監視しない**（インメモリ保持）→ 手動編集の反映は**サーバ再起動が必要**（公式明記）。uvicorn reload 無し＝子プロセス1個。
- **プロセス構造**（実機）: `strictdoc.exe`（ランチャ、ポート持たず）→ `python.exe`（実サーバ、ポート LISTEN）。Task Manager で「strictdoc」名前検索だと実体 `python.exe` が出ない＝「見つからない」の正体。探すなら**ポート所有プロセス**で。
- **大規模性能**: parallelized incremental ＋ pickle キャッシュ（`output/_cache`）。**初回コールド ~10–12s / 以降ウォーム ~5s**（100件実測）。`include/exclude_*` の精密化で探索が速い（公式 Performance 節）。
- **版**: 導入＝**0.23.1**（Phase 0 で 0.21.1 から更新）。`strictdoc new` は 0.21.1 で追加、0.23 で Markdown/Mermaid 改善。生成 config の `create_config() → ProjectConfig(project_title / project_features / include_doc_paths / include_source_paths)` 形式は 0.23.1 でも不変・**MERMAID 非同梱**（既定 ON: TABLE/TRACEABILITY/DEEP_TRACEABILITY/SEARCH＋`strictdoc new` が TRACEABILITY_MATRIX_SCREEN/REQUIREMENT_TO_SOURCE_TRACEABILITY を追加、MATHJAX はコメントアウトで同梱）。Phase 0 で実機確認。

---

## 2. 決定事項（合意済み）

- **D-1**: `strictdoc_config.py` は **`project_path` 直下**（ツール root ではない）。設定は文書と一体で持ち運ぶ。
- **D-2**: 推奨 feature ベースライン = 既定4種 + `MATHJAX` + `MERMAID`。必要に応じ `HTML2PDF`/`DIFF`/`REQIF`/画面系。`ALL_FEATURES` は使わない。
- **D-3（改）**: 設定は **公式 `strictdoc new` の出力に準拠/活用**する（自作テンプレを最小化）。新規プロジェクトは `strictdoc new` を案内。bundled samples には MERMAID/MATHJAX を有効化した config を同梱。配備は scaffold-if-missing（無ければ置く・有れば触らない、`server.config.json` の if-missing 流儀に合わせる）。
- **D-4**: strictdoc バージョンは **既定=最新**（無印 `pip install strictdoc`）、**オプションで範囲固定**（`setup.config.json` の `strictdoc.version`）、**動作確認版は README に記録**。詳細 O-1。
- **D-5（スコープ方針）**: StrictDocStarter のコア価値 = **① Windows ブートストラップ（Python/strictdoc/VS Code 一括導入＋ダブルクリック）② ドメイン教材サンプル ③ Windows 配慮（プロキシ/MOTW/ブラウザ自動/PATH）④ 薄いランチャ**。**サーバ起動・雛形・設定形式・readiness/error は公式へ委譲**し再発明しない。
- **D-6（サーバ起動＝可視ウィンドウ方式）**: `strictdoc server <project_path> --host --port` を**可視コンソール窓**で起動し、公式の readiness/error 表示をそのまま使う。**廃止**: `-WindowStyle Hidden` / ポート30秒ポーリング / PIDファイル＋子PID追跡 / `Start-Transcript` 2重起動ロック。**Stop**=窓を閉じる/Ctrl+C（or ポート所有プロセス kill）。**2重起動検出**=ポート使用中チェック。

---

## 3. 実装TODO（未着手）

- **I-1（縮小 / Phase 1 で samples 分は完了）**: config は **`strictdoc new` の出力をベース**にする（ゼロから自作しない）。bundled samples 用に `MERMAID`/`MATHJAX` を有効化した config を用意。トグル＋安定度コメントは流用。→ **bundled samples（sovd-automotive / hello-strictdoc）には配置済（D-8）**。なお samples は .sdoc がフォルダ直下のフラット構成のため `include_doc_paths`/`include_source_paths` は付けない（付けると直下の .sdoc が除外される）。runtime の scaffold-if-missing は I-2（Phase 2 manage 実装）。
- **I-2**: scaffold-if-missing を Start 前に実装（`project_path\strictdoc_config.py` が無ければ配備、有れば不変、失敗は非致命）。legacy `strictdoc.toml` 併存時の扱いを決定。
- **I-3（Phase 1 完了）**: 暫定の `samples/strictdoc_config.py`（親フォルダ＝default project_path `samples/sovd-automotive` からは読まれない）を撤去し、各 project 直下（`samples/sovd-automotive/`・`samples/hello-strictdoc/`）に MERMAID/MATHJAX 有効・`strictdoc new` 準拠の薄い config を配置（D-8/D-1 整合・FR-1141）。
- **I-4**: `serve-spec.md`/`setup-spec.md` に FR 追記（D-5/D-6 反映、feature 既定セット、scaffold 挙動）。
- **I-5 = O-6**: `README.md`/`docs/` 更新。
- **I-6 = O-2（完了）**: `.gitignore` に `__pycache__/` `*.pyc` を追加済（Phase 1）。
- **I-7 = S-3**: `HTML2PDF` の chromedriver（下記 S-3 に統合）。

---

## 3.5 追加スコープ（エピック S-1..S-5 ＋ 横断改善 O-1..O-6）

### S-1. サンプル拡充（Mermaid / Markdown / 図）
- 配置: **`samples/sovd-automotive/` 配下**。図・数式・Markdown 散文は **`[TEXT]` ノード**で（sovd の `[GRAMMAR]` 制約は REQUIREMENT のみ）。
- マークアップ別に **2ファイル**: `05-notation-rst.sdoc`（RST raw html の Mermaid＋`.. math::`＋`.. image::`、全版で有効）/ `06-notation-markdown.sdoc`（表/箇条書き/コードハイライト/画像 ＋ **0.23.0+ なら ` ```mermaid ` フェンス**、`MARKUP: Markdown`）。
- `samples/sovd-automotive/_assets/` 新設。トレーサビリティ（L0→L3）の Mermaid 図解も。
- **`strictdoc new` の generic skeleton（hello world）と差別化**: StrictDocStarter のサンプルは **SOVD/ASIL のドメイン教材**として価値を出す（公式雛形の写経にしない）。hello-strictdoc=最小で触る用 / sovd=実務的な記法・トレース・図の教材、と役割分担。
- 前提 `MERMAID`/`MATHJAX` 有効。順序は config 整備 → サンプル。
- **【Phase 1 実装済 2026-06-06, strictdoc 0.23.1】** `05-notation-rst.sdoc`（mermaid×2 / 数式 / SVG=`<object>`）・`06-notation-markdown.sdoc`（` ```mermaid ` フェンス / 表 / コードハイライト / PNG=`<img>`）・`_assets/`（`sovd-architecture.drawio`→svg+png、drawio スキルで作成）を作成し export 検証済。hello は 01/02 に最小化（03-try/04-mermaid 削除、01 の壊れた markdown 画像参照を除去、orphan `_assets/` 削除）。config は各 project_path 直下へ（I-3 参照）。

### S-2. 空白 / 日本語 / OneDrive・SharePoint（**D-6 で大幅縮小**）
- **根本原因は D-6 で解消**: 可視ウィンドウ方式で `Start-Transcript` による `manage.log` 排他ロックを**廃止**するため、**OneDrive/SharePoint 同期との競合（誤「別セッション動作中」）は根本から消える**。「`manage.log` を LOCALAPPDATA へ移動」「named Mutex 化」は**不要**に。
- 残タスク:
  - 同期パス / 空白 / 非ASCII を**検出して警告**（ローカルパス推奨を表示）。
  - (任意) OneDrive **Files On-Demand** で `lib\*.ps1` がプレースホルダ化 → 起動時に存在チェック/警告。
  - パス引用（空白/日本語）の総点検（`.bat` の `%*`、`Start-Process` 引数等）。

### S-3. setup 拡充（追加 feature 用ファイル）— スコープ訂正済
- **訂正**: `MERMAID`/`MATHJAX`/`NESTOR`/`RAPIDOC` の JS は pip `strictdoc` に同梱 → **別途取得不要**。
- 真に外部取得が要るのは **`HTML2PDF` 用の Chrome/chromedriver**（オフライン/プロキシで詰まる）→ **任意で事前取得**。前提=`install.ps1` 完成（O-5）。

### S-4. uninstall-strictdoc.bat（新規）
- setup と対称: `uninstall.config.template.json` 駆動、**dry-run＋明示確認 必須**。
- 既定: 消す(ON)=strictdoc(pip)＋自身の生成物（`LOCALAPPDATA\StrictDocStarter`/`output/`/`temp/`/`*.log`/scaffold config/`__pycache__`）。任意(OFF)=VS Code 拡張・winget 追加ツール。**不可**=Python/VS Code/Claude Code/Git。
- キー例: `uninstall_strictdoc` / `remove_generated_artifacts` / `remove_vscode_extensions`(false) / `remove_winget_optionals`(false) / `keep_user_documents`(true)。

### S-5. サーバ起動方式の刷新（= D-6 可視ウィンドウ）
- Start を「`-WindowStyle Hidden`＋ポート30秒ポーリング」から **可視コンソール窓での `strictdoc server` 起動**へ変更。
- readiness（`Uvicorn running on…`）/ error（`Could not parse…`）は**公式コンソールに委譲** → **#1（文法エラーの無駄待ち）/ #2（大規模で固定30秒タイムアウト誤判定）が消える**。
- **#3（プロセス迷子）**: 窓＝サーバなので Stop=窓を閉じる。Status が要るならポート所有プロセス（`python.exe`）を表示。
- **廃止**: ポーリング / 固定タイムアウト / PIDファイル / 子PID追跡 / transcript ロック / ログ redirect。**2重起動**=ポート使用中チェック。
- メニュー UI は薄いランチャ化（Start=窓を開く / Open=ブラウザ再オープン / Quit）。← メニュー有無は §4 で確定。

### 横断改善（O-1..O-6）
- **O-1（確定）**: strictdoc バージョン＝既定 latest、`setup.config.template.json` に `strictdoc` ブロック（`python.version` と対称、PEP440 指定子 or `latest`）、**動作確認版を README 記録**（**0.23.1**、Phase 0 で README へ記録済 / FR-332）。消費=`install.ps1` Phase C。
  ```json
  "strictdoc": { "_comment": "pip version spec. 既定 'latest'。再現性重視なら '~=0.23.0' 等。動作確認版は README 参照。", "version": "latest" }
  ```
- **O-2（完了）**: `.gitignore` に `__pycache__/` `*.pyc` を追加済（Phase 1。strictdoc_config.py 読込で生成される副生成物）。
- **O-3**: doctor / health-check（strictdoc 版・config 妥当性・project_path・port 空き・同期パス警告・mermaid 資産）。
- **O-4**: サンプル smoke test（`strictdoc export samples` の成否 ＋ **Mermaid が実際に図化されるか**＝出力に `class="mermaid"` / `mermaid.min.js` が出るかを導入版で検証）→ **版バンプ・版依存記法（例: 0.23.0 で Markdown フェンス可）の破壊を自動検知**。
- **O-5（コア）**: `install.ps1` の Phase B/C/D/E スタブ完成（D-5 でブートストラップが主役）。
- **O-6**: README/docs 更新（Mermaid/TeX、feature On/Off、設定の置き場所、可視ウィンドウ運用、`strictdoc new` 案内）。
- **O-7（v1.2 任意・公式レビュー指摘）**: serve-spec.md の v1.0 隠れデーモン記述（§2.1.3-2.1.7 / §3.4 / §4.1 SC-101.. / §5.2 T1-T10）を Appendix B "superseded" へ物理移動し本文を可視ウィンドウ一本に整理（FR番号維持で traceability 保持）。可読性向上・非ブロッカー。
- **O-8（おまけ・任意・後でやる）: ブラウザのダーク/ライト表示切替（公式 StrictDoc 無改変・分離）**: manage の「Open browser」を `server.config.json` の **`browser_theme: auto|light|dark`（既定 `auto`＝現状の既定ブラウザ起動で挙動不変）** で拡張。`light`/`dark` 時のみ Edge/Chrome を**専用プロファイル**（`--user-data-dir=%LOCALAPPDATA%\StrictDocStarter\viewer` ＋ `--no-first-run --no-default-browser-check` ＋ `--app=<url>`）で開き、dark は `--enable-features=WebContentsForceDark` を付与。**理由**: 起動中ブラウザにフラグは効かない（新URLを既存プロセスに丸投げ）ため別インスタンス必須。**制約**: Edge/Chrome 限定（Firefox 等は既定ブラウザへフォールバック）、強制ダークは一律反転で Mermaid 図が崩れうる、専用プロファイルは拡張/ログイン無し。**StrictDoc は一切無改変**（テーマの本筋＝prefers-color-scheme 対応は upstream-outreach.md §6 の PR）。当面の暫定はブラウザ標準フラグ案内（README「ダークモードで見るには」に記載済）。

---

## 4. 設計判断（2026-06-06 決定済み — 旧 OPEN を解決）

> 判断軸: **「公式の補助 / 一発で使える」**。serve-spec.md / setup-spec.md にも反映済み。

- **D-7 (メニュー / 旧 S-5)**: **最小メニュー**を採用。`manage-strictdoc.bat` は **Start / Open browser / Edit config / Quit** の4項目のみ。Stop/Status/Logs は可視窓が担うため載せない。→ serve-spec FR-1121。
- **D-8 (config 委譲度 / 旧 D-3・I-1)**: **薄いラッパ config を同梱**。bundled samples に MERMAID/MATHJAX 有効化の最小 `strictdoc_config.py`（`strictdoc new` 出力準拠）を置き、新規プロジェクト作成は公式 `strictdoc new <path>` を案内。→ serve-spec FR-1143。
- **D-9 (サンプル整理 / 旧 S-1) — Phase 1 完了**: hello-strictdoc を **最小（01-hello + 02-design）** に戻す。`03-try.sdoc` 削除。`04-mermaid.sdoc` 削除し Mermaid デモは **sovd の `05-notation-rst.sdoc`** へ昇格（SOVD 文脈で作り直し）。→ serve-spec §6.8 S-1 / §6.9。**実施済（2026-06-06, strictdoc 0.23.1 で export 検証）。**
- **D-10 (uninstall 既定 / 旧 S-4)**: 再生成可能な生成物は既定 ON、ユーザー編集物・共有物は既定 OFF。`uninstall_strictdoc`=ON / `remove_generated_artifacts`(output/temp/logs/__pycache__/LOCALAPPDATA)=**ON** / `remove_scaffolded_config`(project_path 内)=**OFF** / `remove_vscode_extensions`=OFF / `remove_winget_optionals`=OFF。dry-run+yes 必須、Python/VSCode/Claude/Git 不可。→ setup-spec FR-342/345。

**残（未着手）**: README.md の O-6 反映（可視ウィンドウ運用・Mermaid/TeX 解説。※FR-332 の動作確認版記録は **Phase 0 で 0.23.1 として完了**）、実装（.bat/.ps1 本体）。

---

## 5. 適用済みの変更（参考）

### Phase 0（2026-06-06, strictdoc 0.21.1 → 0.23.1）
- strictdoc を 0.23.1 へ更新し、§1 の主要事実を最新版で再検証（§1 冒頭サマリ参照、矛盾なし）。
- README に FR-332「動作確認済み strictdoc バージョン (0.23.1)」を記録。
- `.gitignore` に `__pycache__/` `*.pyc` を追加（O-2/FR-361。strictdoc_config.py 読込で生成されるため）。

### Phase 1（2026-06-06, サンプル拡充 / S-1・D-9 / strictdoc 0.23.1）
- `samples/sovd-automotive/05-notation-rst.sdoc`・`06-notation-markdown.sdoc` を新規作成（SOVD 内容の記法デモ）。`_assets/sovd-architecture.{drawio,svg,png}` を drawio スキルで作成（drawio=編集ソース、svg/png=埋め込み用）。
- config を各 project_path 直下へ配置（`samples/sovd-automotive/strictdoc_config.py`・`samples/hello-strictdoc/strictdoc_config.py`、MERMAID/MATHJAX 有効・`strictdoc new` 準拠の薄いラッパ）。
- hello-strictdoc を 01/02 に最小化（`03-try.sdoc`・`04-mermaid.sdoc` 削除、`01-hello.sdoc` の壊れた markdown 画像参照を除去、orphan な `_assets/` 削除）。
- strictdoc 0.23.1 で export 検証済（O-4）: 05=`class="mermaid"`×2 + math + SVG `<object>`、06=` ```mermaid ` フェンス + 表 + コードハイライト + PNG `<img>`。

### Phase 2（2026-06-06, サンプル品質リライト / D-9b・S-1 後継 / strictdoc 0.23.1）
- `samples/sovd-automotive/` を ANMS テンプレート準拠の「自然な仕様書」へ全面リライト（`gr-sw-maker/process-rules` の spec-template-ja / review-standards-ja に準拠）。
- **記法デモ廃止**: `05-notation-rst.sdoc` / `06-notation-markdown.sdoc` を削除（「仕様書として不自然」=ツール解説と要求の混在）。図/数式は本来の要求文書へ統合（認証シーケンス→01、SOVD↔UDS→02、DTC ガード→03、OTA 状態機械→04、構成図→00）。記法カバレッジは付録 `90-appendix-notation.sdoc`（Markdown マークアップで RST/Markdown 両記法を実演、` ```mermaid ` フェンス描画確認）へ集約。
- **前付け新設** `00-overview.sdoc`: 遠隔診断（昔は工場で有線 UDS → SOVD+TCU で遠隔）の背景ストーリーを起点に、目的/範囲/用語集/参照規格/表記規約/前提/改訂履歴 + 構成図（Mermaid: クラウド→TCU→ゲートウェイ→ECU）。
- **要求の質**: 全要求を EARS 化・単一要求化、受入基準フィールド `VERIFICATION` を追加、各 L0 をストーリーに紐づけ、L1–L3 のトレース孤立を解消。
- **安全/セキュリティの分離**: フィールド `CAL`（ISO/SAE 21434）を追加し、ASIL（ISO 26262・安全）と区別（00-overview §6.3）。認証等の純セキュリティ要求は ASIL=QM + CAL、走行中フラッシュ禁止等は ASIL D、署名検証は ASIL D + CAL4。
- **文法共通化**: `sovd-grammar.sgra` に切り出し、全 .sdoc が `[GRAMMAR] / IMPORT_FROM_FILE` で参照（ボイラープレート削減・整合の構造的保証）。セクションは 0.23.1 で廃止の `[SECTION]` 後継 `[[SECTION]]`（`IS_COMPOSITE: True`）。
- **収束 (N→1) パス**: 分解 (1→N) の逆向き＝1 つの下位要求が複数の上位要求を実現する「共有要求」を多親リンクで明示（SW 工学の再利用観点）。適用: ScopeAuthorizer (AUTH-L3-002 ← AUTH-L2-003 + DATA-L2-006)、UdsClient (DATA-L3-002 ← DATA-L2-002 + DTC-L2-001 + DTC-L2-003)、OTA 状態機械 (SWU-L1-008 ← SWU-L0-002 + SWU-L0-003)、データ返却順序 (AUTH-L1-011 ← AUTH-L0-004 + AUTH-L0-002)。TLS/認証は「前提」、TokenCache/DataCache は別インスタンスのため意図的に非リンク（グラフ過結合の回避）。
- **共通基盤くくり出し (D-9c)**: 機能横断で再利用される共有ユニット（UdsClient/ScopeAuthorizer/TlsTerminator/JsonSerializer）を `05-common-platform.sdoc`（`PLAT-` 名前空間）へ移設し、各機能の L2 要求がそこへ収束する形にした。依存方向を「機能→基盤」に統一し、兄弟機能間の依存（例: DTC が data-access 文書の UdsClient に依存）を解消（Clean Architecture / SoC / プロダクトラインの共通要素管理）。01/02 から該当ユニットを除去し、参照（DATA-L3-005 の親、DATA-L2-006 の本文）を更新。L3_Unit のまま PLAT- に再採番（旧 UID は欠番＝移設の痕跡）。次段（SW設計）で本書にクラス図/コンポーネント図/API 定義を付与予定。
- **検証**: strictdoc 0.23.1 で `strictdoc export` クリーン（警告ゼロ）、全図（Mermaid×7）/数式（MathJax）/表（list-table・Markdown 表）/画像（SVG・PNG）/コードハイライト/トレース描画確認。`strictdoc server` でも目視確認。
- **副次修正**: ドキュメント TITLE の em dash `—`(U+2014) が cp932 コンソール出力でクラッシュ印字する問題を回避（TITLE は cp932 安全文字に統一）。
- **docs 整合**: `serve-spec.md` §3.3（ファイル一覧）/§6.8（D-9b 追記）/Glossary（samples/）を更新。**D-9 は D-9b により supersede**（hello-strictdoc 最小化は維持）。

### Phase 3（2026-06-06, 設計→API→テスト層 / D-9d / strictdoc 0.23.1）
- 要求 (01-05) の下流に V 字の残りを追加し、「要求→設計→API→受入テスト→結果」を一気通貫にトレース。
- **文法拡張** (`sovd-grammar.sgra`): 要素 `COMPONENT`（CA_LAYER/MODULE、`Implements`）・`API`（METHOD/PATH/SCOPE/RESPONSE、`Satisfies`）・`TEST`（LEVEL=Unit/Integration/System/Acceptance、`Verifies`）・`TEST_RESULT`（RESULT/EXECUTED_ON/ENVIRONMENT、`ResultOf`）を追加。関係 ROLE 機能を使用。**仕様と結果は別要素・別文書**に分離。
- **`06-architecture.sdoc`（1本に集約・システム全体視点）**: ANMS Ch3 順（3.1 方式＋CA レジェンド → 3.2 **COMPONENT ノード17（全ドメイン網羅、Implements→要求、振る舞いは EARS）** → 3.3 モジュール構成 → 3.4 クラス図×3 → 3.5 システムシーケンス → 3.6 ADR×4）。
- **`07-api.sdoc`（独立文書＝他との契約）**: SOVD HTTP API 10 本。**STATEMENT を EARS 化**（Ubiquitous=スコープ / Event=正常系 / Unwanted=異常系）、METHOD/PATH/RESPONSE はデータ宣言。Satisfies→要求。
- **`08-test-spec.sdoc`**: テスト戦略（V字レベル対応）＋ **全レベルのテスト仕様35本**（単体16=各COMPONENTをVerifies / 結合6→L2 / システム4→L1 / 受入9 Gherkin→L0/API）。
- **`09-test-results.sdoc`（仕様と分離）**: `TEST_RESULT` 35件（各テストへ ResultOf）。PASS/CONDITIONAL×3/FAIL×1/SKIP×2 の実行記録。DEEP TRACE で「要求→設計→API→テスト→結果」被覆と未達(FAIL/SKIP)を一望。**`TEST_RESULT` に TITLE を追加し判定を先頭表示**（例 `[FAIL] ChunkedDownloader 単体`）→ トレーサビリティツリーで OK/NG が一目（meta フィールドの RESULT はツリーに出ないため）。
- **EARS 一貫化の方針**: 振る舞い（API/コンポーネントのメソッド挙動）は EARS、構造（METHOD/PATH、has-property/method）は宣言・クラス図で表現。
- **D-9e SRP/粒度リファイン (テスト=シナリオ単位・コンポ単一責務・命名)**: (1) **テスト粒度を「1 シナリオ=1 テスト=1 結果」**へ（Cucumber/ISTQB 準拠。関連テストの一部 PASS/一部 FAIL を個別表現可能に）。テスト/結果は 50→**約75**。データ違いのみ Scenario Outline で1ノード集約。(2) **COMPONENT を単一責務(1文)＋責務ベース命名**へ（EARS 振る舞いは削除しテストへ移譲＝ADR-005）。実装漏れ命名を改名: DidResolverTable→DidResolver / DtcHistoryBuffer→DtcHistoryStore / ChunkedDownloader→PackageDownloader / FlashSector→FlashSectorWriter / StateMonitor→VehicleStateMonitor / DataReadHandler→DataReadUseCase（対応 L3 要求名・図・モジュールも整合）。(3) **EcdsaVerifier→SignatureVerifier** に統一し ECDSA P-256＋RSA-PSS 2048 両対応（SWU-L2-002 との不整合を解消）。文法 `TEST_RESULT` に TITLE 追加済（判定先頭表示）。export クリーン・全関係解決を確認。
- **トレーサビリティ・マトリクス有効化**: sovd サンプルの `strictdoc_config.py` に `TRACEABILITY_MATRIX_SCREEN` を追加（D-2 ベースラインからの意図的追加。教材としてV字の被覆を全体ビューで見せるため）。出力ルートに `traceability_matrix.html` が生成され、要求×設計/API/テスト/結果の被覆を一覧表示。古い feature コメントの旧ファイル参照（05/06）も現行（01-auth の数式 / 00-04・90 の Mermaid）へ更新。
- **検証**: strictdoc 0.23.1 で export クリーン（警告ゼロ）。COMPONENT/API/SCENARIO・Implements/Satisfies/Verifies・CA 色分け・クラス図・Gherkin コードブロック・RESULT すべて描画。`server` 目視確認。
- **docs 整合**: `serve-spec.md` §3.3／Glossary、`00-overview` §3.4（文書構成＋V字注記）を更新。

### Phase 4（2026-06-07, サンプル通しレビュー / strictdoc 0.23.1）
- **ローカル衛生**: `samples/sovd-automotive/_assets/output/`（前セッションで `strictdoc server`/`export` を誤って `_assets` 配下へ出力した生成物 48MB / 1341 ファイル。 `.gitignore` の `output/` で無視されコミット汚染は無し）を削除。 strictdoc は `_assets` を「プロジェクトアセット」として丸ごと output へコピーするため、 これで `_assets` コピーが **1341→3 ファイル**、 export が **60.8 秒 → 3.65 秒** に短縮。
- **通しレビュー**: `samples/sovd-automotive/`（00-09 + 90 + grammar）を `gr-sw-maker/process-rules` の review-standards-ja（R1-R6）＋ 用語/数値/トレース一貫性で全数精査。 **Critical/High 指摘ゼロ**。 トレース（Implements/Satisfies/Verifies/ResultOf）は export クリーンが全解決を裏づけ、 D-9e の改名（DidResolver / DtcHistoryStore / PackageDownloader / FlashSectorWriter / VehicleStateMonitor / SignatureVerifier 等）は 06設計・08テスト・モジュール構成すべてに反映済・旧名残存なし。 テスト結果サマリ（計75: PASS66/COND5/FAIL1/SKIP3）を実ノードで検算し一致。
- **軽微修正（適用済み）**:
  - L1: `05-common-platform` に移設マッピング表（UdsClient←DATA-L3-002 / ScopeAuthorizer←AUTH-L3-002 / TlsTerminator←AUTH-L3-003 / JsonSerializer←DATA-L3-004）を追加し、 欠番の由来を明示。
  - L3: `00-overview` §3.3 リソース表に「正式契約は 07-api 参照・本サンプルは主要リソース抜粋（全DTC一括クリア・actuator は割愛）」注記を追加。
  - L4: `05-common-platform` 収束図に「TLS 要求は代表として 01-auth に集約、 図では Auth からの依存のみ」注記を追加（RATIONALE の「全機能横断」と図の橋渡し）。
  - L6: `09-test-results` サマリの「(例示)」→「(集計)…(本サンプルの実行記録例)」へ表現修正。
- **検証**: 変更後 export 再実行で警告ゼロ、 mermaid/MathJax/list-table/判定マーカー/traceability_matrix すべて描画維持、 追記4点の HTML 反映を grep 確認。
- **据置き指摘（Medium、 今回は未対応 = deferred。 D-9 系の様式判断であり非ブロッカー）**:
  - **M1 (exec:actuator の孤立)**: スコープ例（00§3.3 / AUTH-L1-003 / 90§G）と RBAC テスト（AT-015）に登場するが、 対応する機能要求・API・コンポーネントが存在しない。 リスク=低（教材の一貫性のみ。 安全/トレース健全性には影響なし）。 解消案=(a) 言及削除で read 系＋write 系に統一、 もしくは (b) 最小のアクチュエータ要求/API/テストを1本追加して着地。 **次サイクルの第一候補**。
  - **M2 (DATA-L3-005 の所属)**: 「浮動小数点の表現」は中身が共有 JsonSerializer（PLAT-L3-004 の子）の制約で、 05-common-platform へ移す方が SoC 上自然。 リスク=極低（配置の好み）。
  - **M3 (複合要求)**: 一部 L0/L1 要求が 1 ノード 2 文（DTC-L0-003 / SWU-L0-002 等）。 厳密な単一化＋シナリオ分解は範囲大のため別タスク（ハンドオフ §6「要求の単一化（厳密版）」に対応）。 教材としては現状容認。

### 旧セッションの変更（上記 Phase 0/1 により supersede 済）
- ~~`samples/hello-strictdoc/04-mermaid.sdoc`（RST raw html 化）~~ → D-9 で **削除**（Mermaid デモは 05-notation-rst.sdoc へ昇格）。
- ~~`samples/strictdoc_config.py`（親フォルダ、`project_features=["MERMAID"]`）~~ → default project_path から読まれないため **撤去**、各 project 直下へ移設（I-3）。
- ~~副生成物 `samples/__pycache__/`~~ → `.gitignore` 対象化（O-2）。

## 6. 参考リンク / 位置情報

- 公式 User Guide: https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html （§Mermaid / §Selecting features / §Experimental features / §Web server / §Performance considerations / §Installing StrictDoc）
- 公式 .sdoc ソース: https://github.com/strictdoc-project/strictdoc/blob/main/docs/strictdoc_01_user_guide.sdoc
- `ProjectFeature` 列挙: `…/strictdoc/core/project_config.py`
- JS資産: `…/strictdoc/export/html/_static_extra/{mermaid,mathjax,nestor,rapidoc}/`
- サーバ起動/readiness: 公式は foreground、`Application startup complete.` / `Uvicorn running on …`（stderr）、`Could not parse… TextXSyntaxError`（stdout, 即終了）。
- 公式雛形: `strictdoc new <path>`（docs/src/`strictdoc_config.py` 生成、MERMAID は含まず）。
- 既存 if-missing 実装の参考: `lib/server-config.ps1` の `Initialize-ServerConfig`。
