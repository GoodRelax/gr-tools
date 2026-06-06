# StrictDocStarter — StrictDoc 環境セットアップ + サーバ管理ツール

クリーンな Windows 11 PC で **ZIP 展開 → 2 つの .bat をダブルクリック** だけで、 StrictDoc の **環境構築** と **要求ツリーの閲覧** まで到達できる Windows 用ツールセット。

| ツール | 役割 | 起動 |
|---|---|---|
| `setup-strictdoc.bat` | 環境構築 (1 回きり): Git / Python / StrictDoc / VS Code + 拡張 を winget / pip で導入 | ダブルクリック → UAC → `yes` |
| `manage-strictdoc.bat` | StrictDoc サーバ管理 (daily use): start / stop / status / logs / Edit config をメニュー UI | ダブルクリック → メニュー番号 |
| `gather-logs.bat` | 障害時のログ + 診断回収 (UAC 不要) | ダブルクリック |

詳細仕様:
- [`docs/setup-spec.md`](docs/setup-spec.md) — setup-strictdoc 仕様
- [`docs/serve-spec.md`](docs/serve-spec.md) — manage-strictdoc 仕様
- [`docs/01-environment.md`](docs/01-environment.md) — ユーザ向け Phase 0 / 1 手順

## 動作確認済み strictdoc バージョン (FR-332)

- **検証済み: strictdoc 0.23.1** (Windows 11 / Python 3.13.3 / PowerShell 5.1、 2026-06-06)。 確認内容: Mermaid 図 (RST `.. raw:: html` + `<pre class="mermaid">` ／ Markdown ` ```mermaid ` フェンス〔0.23.0+〕の両方が描画)、 数式 `.. math::` (MathJax)、 コードハイライト (Pygments)、 表、 `strictdoc server` の前面コンソール起動 (readiness 行 `Uvicorn running on …` ／ 文法エラー時 `Could not parse … TextXSyntaxError` で即終了)。
- 既定では **最新版**を `pip install strictdoc` で導入する。 最新追従のため、 将来版で同梱サンプル / 設定が壊れる可能性がある (サンプル smoke test で検知予定: O-4)。 **再現性を固定**したい場合は特定版を指定して導入する (例: `pip install "strictdoc==0.23.1"`)。

## 制限事項

- **プロキシ環境は v1.0 では非対応**。 home Wi-Fi / モバイルテザリング等の直接接続環境での実行を推奨。 起動時に proxy を検出すれば `[WARN]` を表示するが、 install の自動設定は行わない。 詳細・回避策は [Proxy / 企業ネットワークについて](#proxy--企業ネットワークについて) を参照

---

## 使い方 (4 ステップ)

### ステップ 1〜3: 環境セットアップ (初回のみ、 約 30 分)

1. **`StrictDocStarter.zip` をデスクトップにコピー** (Hyper-V 拡張セッションのクリップボード経由など)
2. **デスクトップで ZIP を右クリック → 「すべて展開」** → `Desktop\StrictDocStarter\` フォルダができる
3. **`Desktop\StrictDocStarter\setup-strictdoc.bat` をダブルクリック**
   - UAC ダイアログ → **はい** → プラン表示 → **`yes`** → Phase A〜E 一気通貫 → サマリ → Enter で閉じる
   - 実行場所に `setup.config.json` / `env-report.json` / `setup.log` が生成される

### ステップ 4: 要求ツリーを表示 (毎回)

4. **`Desktop\StrictDocStarter\manage-strictdoc.bat` をダブルクリック**
   - **初回のみ**: `server.config.json` が template から自動生成され、 既定エディタ (VS Code → notepad fallback) が開く → そのまま保存 → manage 画面で Enter
   - メニュー画面が出たら **`1`** (Start) を入力 → 30 秒以内にブラウザが `http://127.0.0.1:5111/` を自動 open
   - 同梱の **SOVD 自動車サンプル (~100 要求、 ASIL / Layer / Type custom fields)** ツリーが表示される
   - 確認後はメニューに戻って **`2`** (Stop) でサーバ停止、 **`Q`** で manage 終了

これで「ZIP 展開 → setup → manage → ブラウザで要求閲覧」 まで完結。

---

## サーバ管理 (`manage-strictdoc.bat`)

ダブルクリックでメニュー UI が起動。 詳細仕様は [`docs/serve-spec.md`](docs/serve-spec.md)。

### メニュー項目

| キー | アクション | 内容 |
|---|---|---|
| `1` | Start | `strictdoc server` をバックグラウンド起動 + 既定ブラウザで自動 open |
| `2` | Stop | 起動中のサーバを停止 (PID file + 本人確認 + Stop-Process → 必要なら -Force) |
| `3` | Status | 現状を再 probe (5 状態: `RUNNING` / `STARTING` / `STOPPED` / `STALE_PID_FILE` / `OTHER_OWNS_PORT`) |
| `4` | Logs | server stdout 末尾 50 行 + stderr 末尾 20 行を表示 |
| `5` | Edit config | `server.config.json` を既定エディタで開く (メニュー戻り時に自動 reload + validate) |
| `Q` | Quit | メニュー終了 (サーバ稼働中なら警告 1 行) |

### 設定ファイル (`server.config.json`)

| フィールド | 既定 | 内容 |
|---|---|---|
| `project_path` | `<starter_root>\samples\sovd-automotive` | StrictDoc プロジェクトルート (`.sdoc` を置くフォルダ) |
| `host` | `127.0.0.1` | bind host (IPv4 / `localhost` / IPv6 literal) |
| `port` | `5111` | server port (1024..65535) |
| `open_browser` | `true` | Start 成功時にブラウザを自動 open |
| `output_path` | `""` | strictdoc `--output-path` (空なら `<project>/output`) |

placeholder:
- `<user>` → `$env:USERNAME` (実行時展開)
- `<starter_root>` → `manage-strictdoc.bat` のあるフォルダの絶対パス (unzip 先依存なし)

### 同梱サンプル

| パス | 要求数 | 用途 |
|---|---|---|
| `samples/sovd-automotive/` | 100 reqs + 記法デモ 2 件 | SOVD 自動車診断の **初期 default**。 ASAM SOVD / ISO 17978 ベース、 ASIL (ISO 26262) / Layer (A-SPICE) / Type custom fields 付き。 認証 / データ読取り / DTC / OTA 更新の 4 機能領域 × L0..L3 階層。 加えて記法デモ `05-notation-rst.sdoc` (Mermaid / 数式 / 画像) と `06-notation-markdown.sdoc` (表 / コード / 画像 / Mermaid フェンス)、 図素材 `_assets/` (drawio 編集ソース + svg + png)。 MERMAID/MATHJAX 有効の `strictdoc_config.py` 同梱 |
| `samples/hello-strictdoc/` | 5 reqs | 「Hello, World」 風のミニマル要求書 (`01-hello` + `02-design`)。 **自分の要求書を書き始めるときの編集テンプレ** として使用。 MERMAID/MATHJAX 有効の `strictdoc_config.py` 同梱 |

### サーバ状態の永続化

| ファイル | パス |
|---|---|
| PID file | `%LOCALAPPDATA%\StrictDocStarter\server-<port>.pid` |
| サーバ stdout log | `%LOCALAPPDATA%\StrictDocStarter\server-<port>.log` |
| サーバ stderr log | `%LOCALAPPDATA%\StrictDocStarter\server-<port>.err.log` |
| manage 操作ログ | `<bat と同フォルダ>\manage.log` |

---

## 環境セットアップ (`setup-strictdoc.bat`)

### サブコマンド

| サブコマンド | 内容 | 状態 |
|---|---|---|
| (引数なし) | `auto` 相当 | 実装済 |
| `auto` | 環境検査 → プラン → yes → Phase A〜E 一気通貫 | 実装済 |
| `help` | ヘルプ表示 | 実装済 |
| `check` | 環境/プロキシ/SSL 検査 → `env-report.json` | 実装済 |
| `config` | `setup.config.json` テンプレ生成 + edit-then-yes | 実装済 |
| `dryrun` | プラン列挙のみ (副作用なし、 `auto` と同一 planner) | 実装済 |
| `install` | install エンジン直接呼び出し (Phase A〜E のフル流用は `auto` 経由を推奨) | 実装済 (auto 経由) |
| `clone` | repo clone + ジャンクション | 実装済 |
| `all` | check → config → install → clone | 実装済 (互換のための旧フロー、 通常は `auto` を使用) |

明示的にサブコマンドを指定したい場合は PowerShell から:

```powershell
cd $env:USERPROFILE\Desktop\StrictDocStarter
.\setup-strictdoc.bat check
```

### auto フロー (yes 1 回でやること)

| Phase | 内容 | 既導入ならスキップ |
|---|---|---|
| **A** | VS Code + Claude Code 拡張 (`anthropic.claude-code`) | ✓ |
| **B** | Git / Python / GitHub CLI (winget) | ✓ |
| **C** | `pip install strictdoc` | ✓ |
| **D** | `git clone` + Obsidian ジャンクション (**既定スキップ**) | ✓ |
| **E** | Obsidian / Terminal / PowerShell 7 / ripgrep / jq + VS Code 拡張群 | ✓ (個別) |

`setup.config.json` が無ければテンプレ既定で自動生成 (`<user>` は実ユーザ名に置換)。 事前にカスタマイズしたければ `setup-strictdoc.bat config` を先に。

### Phase D について (GitHub アカウントなしでも OK)

**既定では Phase D はスキップされる** (`repository.url` が空)。 GitHub アカウントを持っていない人や特定リポを clone したくない人もそのまま `auto` を回せる。

Phase D を有効にする場合は `setup.config.json` を編集:

```json
"repository": {
  "url": "https://github.com/YourName/YourRepo.git",
  "visibility": "public"
}
```

または `options.skip_clone: true` で明示的にスキップ。

認証 GUI 対策として、 Phase D 内では `GIT_TERMINAL_PROMPT=0` / `GCM_INTERACTIVE=Never` を設定するので URL が不正でも認証ダイアログは出ずに即失敗する。

### オプション項目をカスタマイズするには

`auto` の `yes` プロンプトで **`yes` 以外の任意入力** (例: `no` / `n` / Enter / 任意文字列) は **すべて abort** として扱われる。 abort 時には **設定ファイルの絶対パス + 再実行コマンド** が表示される。 ワークフロー:

1. `setup-strictdoc.bat` をダブルクリック → UAC → プラン表示 → `no` を入力
2. 表示された `Config: C:\...\setup.config.json` を **Notepad / VS Code 等で開く**
3. `_comment_<key>` を見ながら **`install_*` フラグを編集** (例: `"install_claude_winget": false` → `true` で Claude Code CLI を opt-in)
4. 保存して `setup-strictdoc.bat` を **再ダブルクリック** (冪等なので 2 回目以降は差分のみ install)

### Required ツール (toggle 不可)

下記は常時 install (ADR-014):

- Git / Python / GitHub CLI (Phase B)
- StrictDoc (Phase C)
- VS Code + Claude Code 拡張 (Phase A)

既にインストール済の環境では `Test-*Installed` により自動 SKIP されるため追加コストはほぼゼロ。

---

## Proxy / 企業ネットワークについて

**v1.0 では proxy 環境の自動設定をサポートしない**。 直接インターネット接続できる環境 (家庭 Wi-Fi、 モバイルテザリング、 ゲスト Wi-Fi 等) での実行を推奨。

### 検出

`setup-strictdoc.bat` 起動時、 以下のいずれかが見つかれば plan 表示後に `[WARN]` 行を表示 (install を止めはしない):

- IE Internet Options の Proxy server 設定
- 環境変数 `HTTP_PROXY` / `HTTPS_PROXY`
- WinHTTP proxy (`netsh winhttp show proxy`)

詳細を確認したい場合は `setup-strictdoc.bat check` を実行 → `env-report.json` に全検出結果が記録される。

### 症状

| ツール | 典型エラー |
|---|---|
| winget | `Network Error 0x80072EE7` 等 |
| pip   | `Could not find a version that satisfies...` (DNS failure 風) |
| git   | `unable to access ...: Could not resolve host` |
| code --install-extension | 静かに失敗 |

### 回避策 (優先順)

**1. 直接接続環境で 1 回だけ実行 (最推奨)** — `setup-strictdoc.bat` は 30 分前後で完走するので、 その間だけ家庭 Wi-Fi 等に繋いで実行。 install されたツールは PATH に残り winget の package も local cache に保存される。

**2. 各ツールの proxy 設定を手動で**:

| ツール | 設定方法 |
|---|---|
| winget / pip / code / git (env var) | 起動前に `$env:HTTP_PROXY = "http://user:pass@proxy:8080"; $env:HTTPS_PROXY = $env:HTTP_PROXY` 設定 → 同セッションで `setup-strictdoc.bat` |
| git (永続) | `git config --global http.proxy http://user:pass@proxy:8080` |
| pip (永続) | `pip config set global.proxy http://user:pass@proxy:8080` |

**3. NTLM 認証 proxy の場合** — [Px (Python NTLM Proxy)](https://github.com/genotrance/px) を事前 install して localhost で起動 → 各ツールの env var を `http://localhost:3128` に向ける。

**4. SSL インスペクション (HTTPS 再暗号化) がある場合** — 追加で CA 証明書を git / pip / Node の信頼ストアに登録する必要がある。 各ツールのドキュメント参照。

将来 (v2.x 以降) の自動設定 (Px 自動 install、 認証情報 prompt、 CA 証明書配備等) は別途検討予定。 当面はユーザによる手動設定を前提とする。

---

## ファイル構成

```text
StrictDocStarter/
├── setup-strictdoc.bat                  # 環境構築ランチャ (UAC)
├── setup-strictdoc.ps1                  # ↑ dispatcher
├── manage-strictdoc.bat                 # サーバ管理ランチャ (UAC 不要)
├── manage-strictdoc.ps1                 # ↑ メニュー loop
├── gather-logs.bat                      # ログ + 診断 ZIP 化ランチャ
├── gather-logs.ps1                      # ↑ 本体
├── setup.config.template.json           # setup 設定テンプレ
├── server.config.template.json          # manage 設定テンプレ (default = samples/sovd-automotive)
├── .gitignore
├── README.md                            # 本ファイル
├── _lib/
│   └── elevate.bat                      # 共通 UAC / MOTW / CWD ヘルパ
├── lib/
│   ├── logger.psm1                      # Start-Transcript ラップ
│   ├── check.ps1                        # 環境検査
│   ├── config.ps1                       # setup 設定生成 / Expand-UserPlaceholders
│   ├── install.ps1                      # winget / pip / VS Code 拡張
│   ├── clone.ps1                        # git clone + ジャンクション
│   ├── auto.ps1                         # Phase A〜E オーケストレーション
│   ├── proxy.ps1                        # プロキシ検出 (スタブ)
│   ├── server-config.ps1                # manage 設定 gen/load/validate/edit
│   └── server-process.ps1               # strictdoc server start/stop/status/logs
├── docs/
│   ├── 01-environment.md                # ユーザ向け Phase 0 / 1 手順
│   ├── lessons-learned-phase0.md        # 開発中の技術知見
│   ├── setup-spec.md                    # setup-strictdoc 仕様 (FR / ADR / Gherkin)
│   └── serve-spec.md                    # manage-strictdoc 仕様 (FR / ADR / Gherkin)
├── samples/
│   ├── hello-strictdoc/                 # 5 reqs、 編集テンプレ
│   │   ├── 01-hello.sdoc
│   │   ├── 02-design.sdoc
│   │   └── strictdoc_config.py          # MERMAID/MATHJAX 有効 (strictdoc new 準拠)
│   └── sovd-automotive/                 # 初期 default (SOVD ドメイン教材)
│       ├── 01-auth.sdoc                 # 25 reqs、 認証/認可
│       ├── 02-data-access.sdoc          # 25 reqs、 車両データ識別/読取
│       ├── 03-dtc-diagnostics.sdoc      # 25 reqs、 DTC / フリーズフレーム
│       ├── 04-sw-update.sdoc            # 25 reqs、 OTA / 署名検証 / rollback
│       ├── 05-notation-rst.sdoc         # RST 記法デモ: Mermaid(raw html)/数式/画像
│       ├── 06-notation-markdown.sdoc    # Markdown 記法デモ: 表/コード/画像/Mermaidフェンス
│       ├── _assets/                     # 図素材 (sovd-architecture.drawio + .svg + .png)
│       └── strictdoc_config.py          # MERMAID/MATHJAX 有効 (strictdoc new 準拠)
└── vm-tests/                            # VM 上で setup-strictdoc を検証
    ├── run-tests.bat                    # 自動テストランナー (10 シナリオ)
    ├── run-tests.ps1                    # ↑ 本体
    ├── gather-test-logs.bat             # test-results/ + setup.log を ZIP 化
    ├── gather-test-logs.ps1             # ↑ 本体
    └── vm-test-checklist.md             # VM テスト手順
```

5 つの .bat (`setup-strictdoc.bat`, `manage-strictdoc.bat`, `gather-logs.bat`, `vm-tests/{run-tests,gather-test-logs}.bat`) は冒頭で `call ...\_lib\elevate.bat <need_admin|no_admin>` を呼ぶ。 UAC / MOTW / CWD のロジックは `_lib/elevate.bat` に一元化済。

---

## 自動テスト (setup-strictdoc 用)

`vm-tests\run-tests.bat` をダブルクリックで **10 シナリオ連続実行** (実 uninstall + reinstall を伴うため、 全ツール導入済 VM 前提)。 plan のみで素早く検証したい場合は `run-tests.bat dryrun` で uninstall せず dryrun を回す。

| # | シナリオ | やること |
|---|---|---|
| 1 | T_idempotency | 何も変えず再実行、 全 skip 確認 |
| 2 | T_partial_optional | jq + ripgrep + gitlens 拡張を uninstall → 再 install |
| 3 | T_required_only | gh CLI uninstall → 再 install |
| 4 | T_extensions_only | VS Code 拡張 2 件 uninstall → 再 install |
| 5 | T_mixed | 必須 + 任意 + 拡張 を 1 つずつ uninstall → 全部再 install |
| 6 | T_claude_extension | Phase A の Claude Code 拡張 uninstall → 再 install |
| 7 | T_strictdoc_pip | Phase C の strictdoc pip uninstall → 再 install |
| 8 | T_negative_claude_both | `install_claude_winget` + `install_claude_npm` 両 true で排他 abort 確認 |
| 9 | T_dryrun_assert | dryrun 出力の `[INSTALL]` / `[SKIP]` タグ + Phase ヘッダの正規表現 assert |
| 10 | T_negative_abort | `yes` 以外入力時の abort guidance を log grep で確認 (手動でも可) |

各シナリオの実行ログは `vm-tests/test-results/<scenario>.log` に保存。

manage-strictdoc の自動テストは host で実施可能 (VM 不要、 詳細は `docs/serve-spec.md` §5 Test Strategy)。

---

## 出力ファイル (gitignore 対象)

`.bat` のあるフォルダに生成される。 ZIP 配布物には含まれない。

| ファイル | 生成元 | 内容 |
|---|---|---|
| `env-report.json` | `setup-strictdoc.bat check`/`auto` | 環境スナップショット |
| `setup.config.json` | `setup-strictdoc.bat config`/`auto` | setup ユーザ設定 (パスワードは含めない) |
| `setup.log` | setup 全実行 (Append) | コンソール出力 + winget/pip/git の生出力 |
| `server.config.json` | `manage-strictdoc.bat` 初回 | manage ユーザ設定 |
| `manage.log` | manage 全実行 (Append) | メニュー操作トレース |

`%LOCALAPPDATA%\StrictDocStarter\` には manage 系の PID file + server log が生成される (上述)。

---

## 制約

- Windows 11 + winget 必須
- `setup-strictdoc.bat`: 管理者権限必須 (UAC 自動昇格)
- `manage-strictdoc.bat`: 管理者権限不要 (user 権限で動作)
- スクリプト本体および console 出力メッセージは英語 ASCII only (ADR-008)
- パスワード/PAT は設定ファイル・永続環境変数・スクリプトに残さない
- Claude Code 拡張 ID は `anthropic.claude-code` を仮定。 違えば `lib/install.ps1` の `$script:CCExtensionId` を更新
- 信頼境界は **単一 Windows アカウント**。 別アカウント / 昇格プロセスによる PID file 改ざんは検出しない (PoC スコープ)

---

## ツール検出ロジック (setup)

「既にインストール済みかどうか」 を判定する方法。 **インストール先が標準外でも極力検出できる** 多段フォールバック。

| ツール | 検出順 |
|---|---|
| Git / gh / rg / jq / wt / pwsh / strictdoc | (1) PATH (`Get-Command`) |
| Python | (1) PATH + WindowsApps スタブ除外 + `--version` パターン検証 |
| **VS Code** | (1) PATH → (2) 既知パス 3 通り → (3) **レジストリ Uninstall キーから InstallLocation / DisplayIcon** |
| Obsidian | (1) レジストリ Uninstall キー (DisplayName 一致) → (2) 既知パス 4 通り |
| Claude Code 拡張 | `code --list-extensions` |
| VS Code 拡張群 | `code --list-extensions` |

### 検出から漏れた場合の挙動

- プランでは「未インストール → install 予定」 と表示
- 実行時に `winget install` が走るが、 winget 側で既存検出 → `[SKIP]` で抜ける (再 install されない)
- 結果として **数秒〜十数秒の遅延だけ** で、 機能的には正しい状態に収束

「検出漏れ = 誤動作」 にはならず、 最悪でも遅延だけ。 安全に運用可能。

---

## Mark-of-the-Web (MOTW) 対策

VM へクリップボード経由で運ばれた `.ps1` / `.psm1` は Windows により「**別マシン由来**」 とマークされ、 Bypass ポリシーでも実行が阻害される (PowerShell が「実行可否」 の警告ダイアログを出す) ことがある。

**.bat 群は起動時に自動で `Unblock-File` を実行** するため、 通常は気にする必要なし。 それでもブロックされる場合は手動で:

```powershell
Get-ChildItem -Path $env:USERPROFILE\Desktop\StrictDocStarter -Recurse -File | Unblock-File
```

または各 `.ps1` を右クリック → プロパティ → 「ブロックの解除」 にチェック → OK。

---

## デスクトップが OneDrive 配下の場合

Windows 11 で OneDrive 同期が有効だと、 デスクトップが `C:\Users\<user>\OneDrive\Desktop` 配下になることがある。 StrictDocStarter 自体は動くが、 `setup.log` / `manage.log` などの生成物が OneDrive に同期されることに注意。 気になるなら `C:\StrictDocStarter\` 等に展開しても同じく動作する (どこから実行しても OK)。

---

## ログ / 診断の回収

`setup-strictdoc.bat` または `manage-strictdoc.bat` の実行 (成功/失敗問わず) 後、 **`gather-logs.bat` をダブルクリック** すると:

1. `setup.log` / `env-report.json` / `setup.config.json` / `manage.log` / `server.config.json` (存在するもの) を回収
2. `%LOCALAPPDATA%\StrictDocStarter\server-*.log` / `*.err.log` / `*.pid` も回収
3. `diagnostics.txt` を新規生成 (Windows/PowerShell/winget バージョン、 ExecutionPolicy、 既存ツール、 プロキシ設定、 PATH、 PowerShell イベントログ、 manage 状態等)
4. `%TEMP%\StrictDocStarter-result-<タイムスタンプ>.zip` に圧縮
5. エクスプローラを開き、 その ZIP を選択状態で表示

エクスプローラ上で **Ctrl+C** → ホスト側で **Ctrl+V** (拡張セッション のクリップボード経由) で送付完了。

---

## トラブルシュート

### setup

- **PowerShell ExecutionPolicy** — `.bat` 内で `-ExecutionPolicy Bypass` を渡しているので通常は問題なし。 それでも止まる場合は VM の Group Policy を確認
- **PATH refresh が効かない** — winget 直後に新コマンドが見えない場合、 `setup.log` を確認後、 ターミナル再起動して `setup-strictdoc.bat` を再実行 (冪等性により既導入分はスキップされ未完了分のみ再試行される)
- **VS Code 拡張インストール失敗** — 拡張 ID が変わっている可能性。 `code --list-extensions` で確認
- **gh auth 中断** — public repo なら起きない。 `setup.config.json` の `repository.visibility` で切替

### manage

- **`strictdoc not found on PATH`** — setup-strictdoc.bat が未実行か Python venv 未 activate。 新 PowerShell で `strictdoc --version` を確認
- **メニュー画面の Status が `[STARTING]` のまま** — 30 秒以内なら正常 (LISTEN 待ち)。 30 秒超で `[STALE_PID_FILE]` に遷移したら Start ボタンが自動 cleanup → 再 start を試行
- **「Another manage-strictdoc session appears to be running」** — 別 .bat 窓が動作中の検出 (二重起動防止)。 既存窓を閉じてから再実行
- **`OTHER_OWNS_PORT`** — 別アプリが 5111 を占有。 menu 5 で port を変更
- **`[WARN] PID X is not a strictdoc process. Aborting stop.`** — PID file の PID が strictdoc 以外を指す残骸。 メッセージに表示される PID file を手動削除 → 再試行

その他は `gather-logs.bat` でログ回収し共有。
