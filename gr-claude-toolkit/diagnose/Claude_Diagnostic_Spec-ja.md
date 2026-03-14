``````markdown
# Claude エコシステム診断バッチファイル仕様書

> バージョン: 1.2
> 最終更新: 2026-03-14

---

## 1. 目的と方針

Windows 環境における Claude エコシステム（Desktop / CLI / VS Code 拡張 / 設定ファイル群）の構成状態を**読み取り専用**で診断し、推奨構成とのギャップを可視化する。

設計原則:
- **Read-Only**: 一切の設定変更・ファイル書き込みを行わない（出力ファイルを除く）
- **管理者権限不要**: 全チェックがユーザー権限で実行可能（根拠はセクション7.4参照）
- **2つの出力**: 人間用サマリー + Claude 用構造化ログ
- **Claude 連携**: ログを Claude に渡すことで改善提案を受け、半自動で再設定可能にする

---

## 2. 全体フロー

**診断フロー:**

```mermaid
flowchart TB
    Start["ユーザーが<br/>diagnose-claude.bat<br/>を実行"]
    Check1["C1: Desktop インストール診断"]
    Check2["C2: CLI インストール診断"]
    Check3["C3: VS Code 拡張診断"]
    Check4["C4: 認証情報診断"]
    Check5["C5: グローバル settings.json 診断"]
    Check6["C6: プロジェクト settings.json 診断"]
    Check7["C7: Desktop config 診断"]
    Check8["C8: PATH 環境変数診断"]
    Check9["C9: claude.exe 全数スキャン"]
    Check10["C10: プロキシ環境変数診断"]
    Check11["C11: MCP 設定ファイル診断"]
    Summary["人間用サマリー生成<br/>diagnosis-summary.txt"]
    Log["Claude用ログ生成<br/>diagnosis-for-claude.json"]
    Display["サマリーを画面表示"]
    Prompt["Claude連携の案内表示"]
    Action1["A1: プロキシ設定値を<br/>画面に表示するか確認"]
    Action2["A2: MCP設定フォルダを<br/>Explorerで開くか確認"]
    Done["終了"]

    Start -->|"開始"| Check1
    Check1 -->|"次へ"| Check2
    Check2 -->|"次へ"| Check3
    Check3 -->|"次へ"| Check4
    Check4 -->|"次へ"| Check5
    Check5 -->|"次へ"| Check6
    Check6 -->|"次へ"| Check7
    Check7 -->|"次へ"| Check8
    Check8 -->|"次へ"| Check9
    Check9 -->|"次へ"| Check10
    Check10 -->|"次へ"| Check11
    Check11 -->|"集計"| Summary
    Check11 -->|"集計"| Log
    Summary -->|"表示"| Display
    Log -->|"案内"| Prompt
    Prompt -->|"対話"| Action1
    Action1 -->|"次へ"| Action2
    Action2 -->|"完了"| Done
```

バッチファイルが11項目を順に診断し、サマリーとログを生成した後、対話型アクション（A1: プロキシ値表示、A2: MCP フォルダを Explorer で開く）を順に提案する。

---

## 3. ファイル構成

**入出力ファイル構成:**

```text
gr-tools/
└── gr-claude-toolkit/
    ├── README.md                        ... ツール一覧・使い方
    └── diagnose/
        ├── diagnose-claude.bat          ... 診断バッチファイル本体
        ├── Claude_Diagnostic_Spec.md    ... 本仕様書
        ├── [出力] diagnosis-summary.txt ... 人間用サマリー（実行時に生成）
        └── [出力] diagnosis-for-claude.json ... Claude用構造化ログ（同上）
```

出力先はバッチファイルと同じフォルダ（`diagnose/`）。既存ファイルがある場合は上書きする（診断結果は常に最新が正）。

---

## 4. 診断項目の詳細

### C1: Desktop インストール診断

| 項目 | 内容 |
|---|---|
| チェック対象 | MSIX パッケージ `Claude` の存在 |
| 取得方法 | `powershell -Command "Get-AppxPackage *Claude*"` |
| 取得情報 | PackageFamilyName, Version, InstallLocation, Publisher |
| 判定基準 | パッケージが存在すれば OK。Publisher が `Anthropic, PBC` であること |
| 警告条件 | 複数バージョンが存在する場合（旧版残存の可能性） |

### C2: CLI インストール診断

| 項目 | 内容 |
|---|---|
| チェック対象 | `claude` コマンドの存在とバージョン |
| 取得方法 | `where claude` + `claude --version` |
| 取得情報 | 実行ファイルパス, バージョン番号 |
| 判定基準 | `claude` が PATH 上に存在し、バージョンが取得できれば OK |
| 警告条件 | `where claude` が複数パスを返す場合（重複インストール） |
| 追加チェック | Desktop Agent Mode 用バイナリ: `%APPDATA%\Claude\claude-code\` 配下のバージョンフォルダを列挙 |
| 警告条件 | Agent Mode 用に旧バージョンの `claude.exe` が残存している場合（ディスク浪費。各約 239MB） |

Desktop は Agent Mode / Cowork 用に CLI バイナリを `%APPDATA%\Claude\claude-code\{version}\claude.exe` に独自にダウンロードする。npm の CLI とは独立したコピーであり、Desktop が自動管理する。旧バージョンが残っている場合はディスク浪費の警告を出す。

### C3: VS Code 拡張診断

| 項目 | 内容 |
|---|---|
| チェック対象 | Claude Code 拡張のインストール状態 |
| 取得方法 | `code --list-extensions` から `anthropic.claude-code` を検索 |
| 取得情報 | 拡張 ID, インストール有無 |
| 判定基準 | `anthropic.claude-code` が一覧に存在すれば OK |
| 警告条件 | VS Code 自体が PATH にない場合は SKIP（エラーではない） |
| 追加チェック | 拡張内蔵バイナリ: `%USERPROFILE%\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe` の存在とバージョン |
| 追加チェック | CLI バージョンとの不一致検出（npm CLI と VS Code 内蔵バイナリのバージョン差） |

VS Code 拡張は npm CLI とは独立した `claude.exe` バイナリ（約 239MB）を内蔵している。拡張更新時に旧バージョンのフォルダが残ることがある。

### C4: 認証情報診断

| 項目 | 内容 |
|---|---|
| チェック対象 | `%USERPROFILE%\.claude\.credentials.json` の存在 |
| 取得方法 | ファイル存在チェック（`if exist`） |
| 取得情報 | ファイルの有無, ファイルサイズ, 更新日時 |
| 判定基準 | ファイルが存在し、サイズが 0 より大きければ OK |
| 注意 | **ファイル内容は絶対に読まない・出力しない**（認証トークンのため） |

### C5: グローバル settings.json 診断

| 項目 | 内容 |
|---|---|
| チェック対象 | `%USERPROFILE%\.claude\settings.json` |
| 取得方法 | ファイル存在チェック + 内容読み取り |
| 取得情報 | allow エントリ数, deny エントリ数, additionalDirectories 数, 全エントリ一覧 |
| 判定基準 | ファイルが存在すれば OK |
| 警告条件 | allow エントリ数が 15 以上（肥大化の兆候） |
| 警告条件 | 一度限りのコマンドパターン検出（`mkdir`, `cp`, `mv`, `rm`, `touch` を含む Bash エントリ） |
| 警告条件 | プロジェクト固有パスを含むエントリ検出（`Read(//c/` や特定ドメインの `WebFetch`） |

### C6: プロジェクト settings.json 診断

| 項目 | 内容 |
|---|---|
| チェック対象 | 既知のプロジェクトフォルダ内の `.claude/settings.json` |
| スキャン対象 | バッチ実行時のカレントディレクトリ、および `%USERPROFILE%` 直下の主要開発フォルダ |
| 取得方法 | フォルダ走査 + ファイル存在チェック + 内容読み取り |
| 取得情報 | 検出されたプロジェクト settings.json のパス一覧, 各ファイルの allow エントリ数 |
| 判定基準 | 情報収集のみ（存在しなくてもエラーではない） |

### C7: Desktop config 診断

| 項目 | 内容 |
|---|---|
| チェック対象 | `%APPDATA%\Claude\claude_desktop_config.json` |
| 取得方法 | ファイル存在チェック + 内容読み取り |
| 取得情報 | ファイルの有無, MCP サーバー定義数, 各サーバー名 |
| 判定基準 | ファイルが存在すれば OK（MCP 未使用なら無くても正常） |

### C8: PATH 環境変数診断

| 項目 | 内容 |
|---|---|
| チェック対象 | npm グローバルパス, Node.js パスが PATH に含まれるか |
| 取得方法 | `echo %PATH%` をパースして `npm` / `nodejs` / `node` を含むパスを抽出 |
| 取得情報 | npm グローバルパス, Node.js パス, 各パスの実在チェック |
| 判定基準 | `%APPDATA%\npm` が PATH に含まれていれば OK |
| 警告条件 | Node.js が PATH にない場合 |

### C9: claude.exe 全数スキャン

| 項目 | 内容 |
|---|---|
| チェック対象 | ユーザープロファイル配下の全 `claude.exe` |
| 取得方法 | `powershell -Command "Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter 'claude.exe' -ErrorAction SilentlyContinue"` |
| 取得情報 | 各バイナリのフルパス, ファイルサイズ, 更新日時 |
| 判定基準 | 情報収集（存在自体はエラーではない） |
| 分類ルール | 検出された各バイナリを以下のカテゴリに自動分類する |

**claude.exe が存在しうる場所と分類:**

```mermaid
flowchart TB
    Scan["C9: claude.exe 全数スキャン<br/>USERPROFILE 配下を再帰検索"]

    subgraph Expected["正常な場所（3箇所）"]
        E1["AppData Roaming npm<br/>node_modules にある claude.exe<br/>npm CLI 本体"]
        E2["AppData Roaming Claude<br/>claude-code にある claude.exe<br/>Desktop Agent Mode 用"]
        E3[".vscode extensions<br/>native-binary にある claude.exe<br/>VS Code 拡張内蔵"]
    end

    subgraph Unexpected["想定外の場所"]
        U1["上記以外のパスにある<br/>claude.exe<br/>手動コピーや旧インストーラ残骸の可能性"]
    end

    Scan -->|"パスマッチ"| E1
    Scan -->|"パスマッチ"| E2
    Scan -->|"パスマッチ"| E3
    Scan -->|"パス不一致"| U1
```

各バイナリは検出パスに基づいて自動分類する。正常な3箇所に該当しないバイナリが見つかった場合は WARNING を出す。

**分類ルール（パスの部分一致で判定）:**

| パスに含まれる文字列 | 分類 | 説明 |
|---|---|---|
| `AppData\Roaming\npm` | npm_cli | npm でインストールした CLI 本体 |
| `AppData\Roaming\Claude\claude-code` | desktop_agent | Desktop が Agent Mode 用にダウンロードしたバイナリ |
| `.vscode\extensions\anthropic.claude-code` | vscode_extension | VS Code 拡張が内蔵するバイナリ |
| 上記いずれにも該当しない | unknown | 想定外の場所（WARNING） |

**旧バージョン残存の検出:**

`desktop_agent` カテゴリでは `%APPDATA%\Claude\claude-code\` 配下に複数のバージョンフォルダが存在する場合がある。同様に `vscode_extension` カテゴリでは `.vscode\extensions\` 配下に旧バージョンの拡張フォルダが残ることがある。最新バージョン以外のバイナリが存在する場合は「旧バージョン残存」として WARNING を出す。

| 状態 | 判定 | 例 |
|---|---|---|
| 各カテゴリで1バイナリのみ | OK | 正常 |
| 同一カテゴリに複数バージョン | WARNING | `claude-code\2.1.74\` と `claude-code\2.1.76\` が両方存在 |
| unknown カテゴリのバイナリ | WARNING | 手動コピーや旧インストーラ残骸の可能性 |

**注意:** MSIX Desktop 本体（`C:\Program Files\WindowsApps\`）はユーザープロファイル外のためこのスキャン対象外。Desktop の存在確認は C1 の `Get-AppxPackage` で行う。

### C10: プロキシ環境変数診断

| 項目 | 内容 |
|---|---|
| チェック対象 | プロキシ関連の環境変数 |
| 対象変数 | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`（および小文字版 `http_proxy`, `https_proxy`, `no_proxy`） |
| 取得方法 | 存在チェック: バッチの `if defined`。フォーマット検証: PowerShell 内で完結 |
| 取得情報 | 各変数の設定有無（SET / NOT_SET）、フォーマットの妥当性（valid / invalid） |
| 判定基準 | 未設定 = OK（プロキシ不要環境）。設定済みかつフォーマット妥当 = OK |
| 警告条件 | 設定済みだがフォーマットが不正（`://` を含まない、ホスト部分が空等） |
| 警告条件 | 大文字版と小文字版で片方のみ設定されている場合（ツールによって参照する変数が異なるため） |

**フォーマット検証ルール:**

| パターン | 判定 | 例 |
|---|---|---|
| `://` を含み、ホスト部分が空でない | valid | `http://proxy.example.com:8080` |
| ホスト名のみ（`://` なし）でポート付き | valid | `proxy.example.com:8080` |
| 空文字列、スペースのみ | invalid | `""`, `" "` |
| その他（判定不能） | unknown | 個別判断不可のためそのまま記録 |

**セキュリティ上の重要な制約:**

プロキシ URL には認証情報（`http://user:password@proxy:port`）が含まれる場合がある。**プロキシ環境変数の値は一切出力してはならない。**

| 操作 | 安全性 | 理由 |
|---|---|---|
| `if defined HTTP_PROXY` | **安全** | 値を展開しない |
| PowerShell 内で検証し `true`/`false` のみ返す | **安全** | 値がバッチ変数に入らない |
| `echo %HTTP_PROXY%` | **危険** | 値がコンソール・ログに漏洩 |
| `set "VAR=%HTTP_PROXY%"` | **危険** | 値がバッチ変数に格納される |

**実装方針:** フォーマット検証は PowerShell 内で完結させ、出力は `true`/`false` のみとする。

```batch
REM Safe: value never leaves PowerShell process
for /f "tokens=*" %%a in ('powershell -NoProfile -Command ^
  "$v=$env:HTTP_PROXY; if($v -and $v -match '://\S+'){echo 'true'}else{echo 'false'}"') do (
    set "C10_HTTP_FORMAT_VALID=%%a"
)
```

### C11: MCP 設定ファイル診断

| 項目 | 内容 |
|---|---|
| チェック対象 | MCP サーバー定義を含む設定ファイルの存在と配置 |
| スキャン対象 | 下表の3箇所 |
| 取得情報 | 各ファイルの存在有無、MCP サーバー名一覧、Jira サーバーの有無 |
| 判定基準 | 情報収集が主目的（MCP 未使用でもエラーではない） |
| 警告条件 | Jira サーバーが Desktop config にあるが CLI 側にない（またはその逆） |

**スキャン対象ファイル:**

| 場所 | ファイルパス | 用途 |
|---|---|---|
| Desktop config | `%APPDATA%\Claude\claude_desktop_config.json` | Desktop アプリ用 MCP 設定（C7 と同一ファイル） |
| グローバル MCP | `%USERPROFILE%\.claude\mcp.json` | Claude CLI グローバル MCP 設定 |
| プロジェクト MCP | 各プロジェクト直下の `.mcp.json` | プロジェクト固有の MCP 設定（C6 と同じスキャン対象ディレクトリ） |

**C7 との関係:** C7 は Desktop config ファイルの存在と概要（MCP サーバー数）を確認する。C11 は MCP 設定を横断的にチェックし、Desktop・CLI・プロジェクト間の整合性を検証する。特に Jira 連携のように会社ごとに設定が異なる MCP サーバーが正しい場所に配置されているかを確認する。

**MCP サーバー名の取得方法:**

```batch
REM Extract server names from JSON using PowerShell
REM Only output server names, NEVER output env block contents (may contain API tokens)
for /f "tokens=*" %%a in ('powershell -NoProfile -Command ^
  "$j=Get-Content '%APPDATA%\Claude\claude_desktop_config.json' -Raw 2>$null | ConvertFrom-Json; ^
   if($j.mcpServers){$j.mcpServers.PSObject.Properties.Name -join ','}"') do (
    set "C11_DESKTOP_SERVERS=%%a"
)
```

**セキュリティ上の注意:**

| 項目 | 対応 |
|---|---|
| MCP サーバーの `env` ブロック | **出力しない**（API トークン等のシークレットを含む可能性） |
| MCP サーバーの `command` / `args` | 出力してよい（実行コマンドのパス情報は診断に有用） |
| サーバー名 | 出力してよい |

**Jira 検出ルール:** サーバー名に `jira`（大文字小文字不問）を含むものを Jira サーバーとみなす。

---

### 対話型アクション（診断完了後）

診断結果の出力後、以下のアクションを順番に提案する。いずれもユーザーが `yes` と入力した場合のみ実行する。**アクションの結果はファイルに出力しない（画面表示のみ）。**

#### A1: プロキシ環境変数の値を画面表示

| 項目 | 内容 |
|---|---|
| 目的 | プロキシ設定の目視確認（値がファイルに残らない安全な方法） |
| 対象変数 | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`（および小文字版） |
| 表示方法 | 環境変数の値をそのまま画面に表示する（マスクなし） |
| ファイル出力 | **しない**（画面表示のみ。diagnosis-summary.txt / diagnosis-for-claude.json には一切書き込まない） |
| 未設定の場合 | `(not set)` と表示 |

**画面表示例:**

```text
[A1] Show proxy environment variable values on screen? (yes/no): yes

  HTTP_PROXY  = http://proxy.company.com:8080
  HTTPS_PROXY = http://proxy.company.com:8080
  NO_PROXY    = localhost,127.0.0.1,.company.com
  http_proxy  = (not set)
  https_proxy = (not set)
  no_proxy    = (not set)
```

**セキュリティ上の注意:** A1 で表示される値はファイルに一切出力しない。C10 の診断結果（SET/NOT_SET とフォーマット妥当性のみ）とは明確に分離する。画面表示は揮発性であり、ユーザーの目視確認用途に限定する。

#### A2: MCP 設定ファイルのフォルダを Explorer で開く

| 項目 | 内容 |
|---|---|
| 目的 | MCP 設定ファイルの編集場所へ素早くアクセス |
| 対象 | C11 で検出された MCP 設定ファイルが存在するフォルダ |
| 動作 | 番号付きリストを表示し、ユーザーが番号を入力すると該当フォルダを Explorer で開く |
| ループ | 0 を入力するまで繰り返し選択可能（複数フォルダを順次開ける） |
| フォルダ未検出時 | `No MCP config locations found.` と表示してスキップ |

**画面表示例:**

```text
[A2] Open MCP config folder in Explorer? (yes/no): yes

  Available MCP config locations:
    1. Desktop config: C:\Users\good_\AppData\Roaming\Claude
    2. Project MCP: C:\Users\good_\...\claude-code-full-auto-dev
    0. Exit

  Enter number (0 to exit): 1
  Opening: C:\Users\good_\AppData\Roaming\Claude

  Enter number (0 to exit): 2
  Opening: C:\Users\good_\...\claude-code-full-auto-dev

  Enter number (0 to exit): 0
  Done.
```

**設計意図:** MCP 設定は複数の場所（Desktop config / Global / Project）に分散している。A2 により、診断結果を見てすぐに該当フォルダを開き、設定ファイルを編集できる。ループ方式により複数のフォルダを連続して開ける。

---

## 5. 出力フォーマット

### 5.1 人間用サマリー（diagnosis-summary.txt）

**サマリー出力例:**

```text
=============================================================
  Claude Ecosystem Diagnostic Report
  Generated: 2026-03-14 15:30:45
=============================================================

[C1] Desktop Installation
  Status  : OK
  Version : 1.6.6679.0
  Package : AnthropicPBC.Claude_1.6.6679.0_neutral__pzs8sxrjxfjjc
  Publisher: CN=Anthropic, PBC

[C2] CLI Installation
  Status  : OK
  Version : 2.1.76
  Path    : C:\Users\good_\AppData\Roaming\npm\claude.cmd

[C3] VS Code Extension
  Status  : OK
  Extension: anthropic.claude-code

[C4] Credentials
  Status  : OK
  File    : EXISTS (last modified: 2026-03-14)
  Note    : Content not inspected (security)

[C5] Global settings.json
  Status  : WARNING
  Path    : C:\Users\good_\.claude\settings.json
  Allow entries    : 47
  Deny entries     : 0
  Additional dirs  : 2
  Warnings:
    - 47 allow entries detected (recommended: <15)
    - One-shot commands found: Bash(mkdir -p ...), Bash(rm ...)
    - Project-specific entries found: Read(//c/.../articles/**)

[C6] Project settings.json
  Found 3 project settings:
    - C:\Users\good_\...\articles\.claude\settings.json (12 entries)
    - C:\Users\good_\...\gr-simple-md-renderer\.claude\settings.json (3 entries)
    - C:\Users\good_\...\claude-code-full-auto-dev\.claude\settings.json (1 entry)

[C7] Desktop Config
  Status  : OK
  Path    : C:\Users\good_\AppData\Roaming\Claude\claude_desktop_config.json
  MCP servers: 0

[C8] PATH Check
  Status  : OK
  npm global: C:\Users\good_\AppData\Roaming\npm (EXISTS in PATH)
  Node.js   : C:\Program Files\nodejs (EXISTS in PATH)

[C9] claude.exe Binary Scan
  Status  : WARNING
  Found 3 binaries:
    [npm_cli]          AppData\Roaming\npm\node_modules\...\claude.exe (239MB, v2.1.76)
    [desktop_agent]    AppData\Roaming\Claude\claude-code\2.1.74\claude.exe (239MB, OLD)
    [vscode_extension] .vscode\extensions\...-2.1.75-...\claude.exe (239MB, v2.1.75)
  Warnings:
    - Old desktop_agent binary: 2.1.74 (latest: 2.1.76) - 239MB reclaimable

[C10] Proxy Settings
  Status    : OK
  HTTP_PROXY : SET [format: valid]
  HTTPS_PROXY: SET [format: valid]
  NO_PROXY   : SET
  Note      : Actual values not shown [security]

[C11] MCP Config Files
  Status  : OK
  Desktop config: EXISTS [2 servers: filesystem, jira]
  Global MCP    : NOT FOUND
  Project MCP   :
    - C:\Users\good_\...\my-project\.mcp.json [1 server: jira]
  Jira servers found: 2 locations

=============================================================
  Summary: 8 OK / 2 WARNING / 0 ERROR / 1 INFO
  Log for Claude: diagnosis-for-claude.json
=============================================================
```

画面表示とファイル出力の両方に同じ内容を使う。ASCII のみで構成し、文字化けを防ぐ。

### 5.2 Claude 用構造化ログ（diagnosis-for-claude.json）

**ログ出力スキーマ:**

```json
{
  "format_version": "1.0",
  "generated_at": "2026-03-14T15:30:45+09:00",
  "machine_name": "NAMA_CHAN",
  "username": "good_",
  "diagnostics": {
    "C1_desktop": {
      "status": "OK",
      "version": "1.6.6679.0",
      "package_family": "AnthropicPBC.Claude_pzs8sxrjxfjjc",
      "install_location": "C:\\Program Files\\WindowsApps\\AnthropicPBC.Claude_1.6.6679.0_neutral__pzs8sxrjxfjjc",
      "warnings": []
    },
    "C2_cli": {
      "status": "OK",
      "version": "2.1.76",
      "path": "C:\\Users\\good_\\AppData\\Roaming\\npm\\claude.cmd",
      "duplicate_paths": [],
      "warnings": []
    },
    "C3_vscode_extension": {
      "status": "OK",
      "extension_id": "anthropic.claude-code",
      "warnings": []
    },
    "C4_credentials": {
      "status": "OK",
      "file_exists": true,
      "file_size_bytes": 1234,
      "last_modified": "2026-03-14",
      "warnings": []
    },
    "C5_global_settings": {
      "status": "WARNING",
      "path": "C:\\Users\\good_\\.claude\\settings.json",
      "allow_count": 47,
      "deny_count": 0,
      "additional_dirs_count": 2,
      "allow_entries": [
        "Bash(pnpm test:*)",
        "Bash(cmd /c \"pnpm test\")",
        "WebSearch"
      ],
      "additional_directories": [
        "C:\\Users\\good_\\AppData\\Local\\Temp",
        "C:\\Users\\good_\\OneDrive\\Documents\\GitHub\\articles\\ai-native-spec"
      ],
      "warnings": [
        "allow_count_high: 47 entries (threshold: 15)",
        "oneshot_commands_detected: Bash(mkdir -p ...), Bash(rm ...)",
        "project_specific_entries_detected: Read(//c/.../articles/**)"
      ],
      "raw_content": "{...full JSON content of settings.json...}"
    },
    "C6_project_settings": {
      "status": "OK",
      "projects_found": [
        {
          "path": "C:\\Users\\good_\\...\\articles\\.claude\\settings.json",
          "allow_count": 12,
          "raw_content": "{...}"
        }
      ],
      "warnings": []
    },
    "C7_desktop_config": {
      "status": "OK",
      "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude_desktop_config.json",
      "mcp_server_count": 0,
      "mcp_server_names": [],
      "raw_content": "{...}",
      "warnings": []
    },
    "C8_path": {
      "status": "OK",
      "npm_global_in_path": true,
      "npm_global_path": "C:\\Users\\good_\\AppData\\Roaming\\npm",
      "nodejs_in_path": true,
      "nodejs_path": "C:\\Program Files\\nodejs",
      "warnings": []
    },
    "C9_binary_scan": {
      "status": "WARNING",
      "binaries_found": [
        {
          "path": "C:\\Users\\good_\\AppData\\Roaming\\npm\\node_modules\\@anthropic-ai\\claude-code\\cli\\claude.exe",
          "category": "npm_cli",
          "size_bytes": 239061152,
          "last_modified": "2026-03-14",
          "version_hint": "2.1.76"
        },
        {
          "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude-code\\2.1.74\\claude.exe",
          "category": "desktop_agent",
          "size_bytes": 238872736,
          "last_modified": "2026-03-12",
          "version_hint": "2.1.74"
        },
        {
          "path": "C:\\Users\\good_\\.vscode\\extensions\\anthropic.claude-code-2.1.75-win32-x64\\resources\\native-binary\\claude.exe",
          "category": "vscode_extension",
          "size_bytes": 239061152,
          "last_modified": "2026-03-13",
          "version_hint": "2.1.75"
        }
      ],
      "categories_summary": {
        "npm_cli": 1,
        "desktop_agent": 1,
        "vscode_extension": 1,
        "unknown": 0
      },
      "old_versions_detected": [
        {
          "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude-code\\2.1.74\\claude.exe",
          "category": "desktop_agent",
          "size_bytes": 238872736,
          "reclaimable": true
        }
      ],
      "total_disk_usage_bytes": 717195040,
      "reclaimable_bytes": 238872736,
      "warnings": [
        "old_desktop_agent_binary: 2.1.74 (239MB reclaimable)",
        "version_mismatch: npm=2.1.76, vscode=2.1.75, desktop_agent=2.1.74"
      ]
    },
    "C10_proxy": {
      "status": "OK",
      "http_proxy_set": true,
      "http_proxy_format_valid": true,
      "https_proxy_set": true,
      "https_proxy_format_valid": true,
      "no_proxy_set": true,
      "http_proxy_lowercase_set": true,
      "https_proxy_lowercase_set": true,
      "no_proxy_lowercase_set": true,
      "case_mismatch": false,
      "warnings": []
    },
    "C11_mcp_config": {
      "status": "OK",
      "locations": [
        {
          "type": "desktop_config",
          "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude_desktop_config.json",
          "exists": true,
          "server_names": ["filesystem", "jira"],
          "has_jira": true
        },
        {
          "type": "global_mcp",
          "path": "C:\\Users\\good_\\.claude\\mcp.json",
          "exists": false,
          "server_names": [],
          "has_jira": false
        },
        {
          "type": "project_mcp",
          "path": "C:\\Users\\good_\\...\\my-project\\.mcp.json",
          "exists": true,
          "server_names": ["jira"],
          "has_jira": true
        }
      ],
      "jira_found_count": 2,
      "warnings": []
    }
  },
  "summary": {
    "ok_count": 8,
    "warning_count": 2,
    "error_count": 0,
    "total_warnings": [
      "C5: allow_count_high (47 entries)",
      "C5: oneshot_commands_detected",
      "C5: project_specific_entries_detected",
      "C9: old_desktop_agent_binary (239MB reclaimable)",
      "C9: version_mismatch across clients"
    ]
  }
}
```

Claude 用ログには `raw_content` として設定ファイルの全内容を含める。これにより Claude が具体的な改善提案を生成できる。ただし `C4_credentials` のみ内容を含めない（セキュリティ上の理由）。

---

## 6. Claude 連携フロー（半自動再設定）

**Claude 連携フロー:**

```mermaid
flowchart TB
    Bat["diagnose-claude.bat 実行"]
    JSON["diagnosis-for-claude.json 生成"]
    User["ユーザーが JSON を<br/>Claude に渡す"]
    Analyze["Claude が診断結果を分析"]
    Proposal["Claude が改善提案を提示<br/>具体的な JSON diff を含む"]
    Confirm["ユーザーが提案を確認<br/>承認 or 修正指示"]
    Backup["Claude がバックアップ作成<br/>settings.json.bak.YYYYMMDD-HHMMSS"]
    Apply["Claude が設定を適用"]
    Recheck["diagnose-claude.bat 再実行<br/>改善を確認"]

    Bat -->|"生成"| JSON
    JSON -->|"コピペ or ファイル指定"| User
    User -->|"入力"| Analyze
    Analyze -->|"出力"| Proposal
    Proposal -->|"レビュー"| Confirm
    Confirm -->|"承認後"| Backup
    Backup -->|"バックアップ完了後"| Apply
    Apply -->|"検証"| Recheck
```

診断 → 分析 → 提案 → 承認 → バックアップ → 適用 → 再診断 の一連のサイクルで、安全に設定を改善する。

### 6.1 ユーザーが Claude に渡す際のプロンプト例

**Claude への依頼テンプレート:**

```text
以下は Claude エコシステム診断ツールの出力です。
診断結果を分析し、改善提案を出してください。

改善提案には以下を含めてください:
1. 各警告の説明と推奨アクション
2. settings.json の具体的な修正内容（before/after の diff）
3. プロジェクト固有エントリの移動先の提案

設定変更を実行する場合は、変更前のバックアップを必ず作成してください。
バックアップファイル名: 元ファイル名.bak.YYYYMMDD-HHMMSS

[ここに diagnosis-for-claude.json の内容を貼り付け]
```

このテンプレートをバッチ実行後の画面に表示し、ユーザーがコピーして使えるようにする。

### 6.2 バックアップ規則

| 項目 | 規則 |
|---|---|
| バックアップ命名 | `元ファイル名.bak.YYYYMMDD-HHMMSS` |
| 例 | `settings.json.bak.20260314-153045` |
| 保存先 | 元ファイルと同じフォルダ |
| タイミング | Claude が設定変更を実行する直前 |
| 保持期間 | 自動削除しない（ユーザー判断で手動削除） |

### 6.3 Claude が実行する改善アクションの例

**改善アクション分類:**

```mermaid
flowchart LR
    subgraph Actions["Claude が提案するアクション"]
        A1["グローバルから<br/>ワンショット許可を削除"]
        A2["プロジェクト固有エントリを<br/>プロジェクト側へ移動"]
        A3["重複エントリの<br/>統合"]
        A4["不足している<br/>推奨設定の追加"]
        A5["旧バージョンバイナリの<br/>削除提案"]
    end

    subgraph Safety["安全装置"]
        S1["変更前バックアップ"]
        S2["ユーザー承認必須"]
        S3["変更後の再診断"]
    end

    A1 -->|"実行前"| S1
    A2 -->|"実行前"| S1
    A3 -->|"実行前"| S1
    A4 -->|"実行前"| S1
    A5 -->|"実行前"| S1
    S1 -->|"確認"| S2
    S2 -->|"適用後"| S3
```

すべてのアクションはバックアップ → 承認 → 適用 → 再診断の安全フローを経る。

---

## 7. 実装上の制約と注意事項

### 7.1 技術的制約

| 制約 | 対応方針 |
|---|---|
| バッチファイル（.bat）は JSON パーサーを持たない | PowerShell のワンライナーで JSON を解析する |
| 文字コード | 出力は UTF-8（`chcp 65001`）。バッチ内コメントは ASCII のみ |
| 実行権限 | 管理者権限不要。ユーザー権限で全チェック可能 |
| PowerShell 実行ポリシー | `-ExecutionPolicy Bypass` で個別スクリプトの制限を回避 |

### 7.2 セキュリティ上の注意

| 項目 | 対応 |
|---|---|
| `.credentials.json` | 存在チェックのみ。内容は読まない・出力しない |
| OAuth トークン | `config.json` の `oauth:tokenCache` は出力しない |
| 環境変数のシークレット | PATH のみ取得。他の環境変数は取得しない |
| プロキシ環境変数 | 値は一切出力しない（`user:password@proxy` 漏洩防止）。SET/NOT_SET とフォーマット妥当性のみ出力。フォーマット検証は PowerShell 内で完結させ、値をバッチ変数に格納しない |
| MCP サーバーの env | サーバー名のみ取得。`env` ブロック内のトークン類は出力しない |

### 7.3 管理者権限が不要である根拠

Claude のコンポーネントは `C:\Program Files\` 配下にもインストールされるが、診断に必要な操作はすべてユーザー権限で実行可能。

**各チェックの権限要件:**

| チェック | 対象の所在 | アクセス方法 | 管理者権限 |
|---|---|---|---|
| C1: Desktop | `C:\Program Files\WindowsApps\` | `Get-AppxPackage`（パッケージ DB から読む。フォルダ直接アクセス不要） | **不要** |
| C2: CLI | `%APPDATA%\npm\`（ユーザー配下） | `where claude` + `claude --version` | **不要** |
| C3: VS Code | `%USERPROFILE%\.vscode\`（ユーザー配下） | `code --list-extensions` | **不要** |
| C4: Credentials | `%USERPROFILE%\.claude\`（ユーザー配下） | ファイル存在チェック | **不要** |
| C5-C6: settings.json | `%USERPROFILE%\.claude\`（ユーザー配下） | ファイル読み取り | **不要** |
| C7: Desktop config | `%APPDATA%\Claude\`（ユーザー配下） | ファイル読み取り | **不要** |
| C8: PATH | 環境変数 | `echo %PATH%` | **不要** |
| C9: Binary scan | `%USERPROFILE%` 配下を再帰検索 | `Get-ChildItem -Recurse` | **不要** |
| C10: Proxy | 環境変数 | `if defined` + PowerShell 内検証 | **不要** |
| C11: MCP config | `%APPDATA%\Claude\`, `%USERPROFILE%\.claude\`, プロジェクト配下 | ファイル読み取り | **不要** |

**重要な設計判断:**

- MSIX の `InstallLocation`（`C:\Program Files\WindowsApps\...`）は管理者権限なしでは直接アクセスできない場合がある。しかし `Get-AppxPackage` コマンドはパッケージデータベースからメタデータ（バージョン、パス、Publisher）を取得するため、フォルダへの直接アクセスは不要
- Node.js 本体は `C:\Program Files\nodejs\` にあるが、読み取りのみならユーザー権限で可能。ただし診断では `node -v` でバージョンを取得するのみで、フォルダ内のファイルは読まない
- C9 のバイナリスキャンは `%USERPROFILE%` 配下に限定する。`C:\Program Files\WindowsApps\` 内の Desktop 本体は C1 の `Get-AppxPackage` で検出済みのためスキャン対象外

### 7.4 エラーハンドリング

| 状況 | 動作 |
|---|---|
| ファイルが存在しない | status を `MISSING` にして続行（エラー停止しない） |
| PowerShell コマンド失敗 | status を `ERROR` にしてエラーメッセージを記録して続行 |
| JSON パースエラー | status を `PARSE_ERROR` にして raw テキストをそのまま記録して続行 |
| VS Code が未インストール | status を `SKIP` にして続行（必須ではないため） |

---

## 8. バッチファイルの画面出力イメージ

**実行時の画面表示:**

```text
=============================================================
  Claude Ecosystem Diagnostic Tool v1.0
=============================================================

Checking [C1] Desktop Installation...    OK (v1.1.6679.0)
Checking [C2] CLI Installation...        OK (v2.1.76)
Checking [C3] VS Code Extension...       OK (v2.1.75, embedded binary: v2.1.75)
Checking [C4] Credentials...             OK
Checking [C5] Global settings.json...    WARNING (47 allow entries)
Checking [C6] Project settings.json...   OK (3 projects found)
Checking [C7] Desktop Config...          OK
Checking [C8] PATH Check...              OK
Checking [C9] Binary Scan...             WARNING (old version: 239MB reclaimable)
Checking [C10] Proxy Settings...         OK
Checking [C11] MCP Config Files...       OK [Jira: 2 locations]

=============================================================
  Result: 9 OK / 2 WARNING / 0 ERROR
=============================================================

Output files:
  Summary : C:\Users\good_\diagnosis-summary.txt
  Log     : C:\Users\good_\diagnosis-for-claude.json

-------------------------------------------------------------
To get improvement suggestions from Claude, copy the prompt
below and paste it into Claude along with the log file:
-------------------------------------------------------------

  [Prompt template displayed here]

=============================================================
  Optional Actions (screen-only, not saved to files)
=============================================================

[A1] Show proxy environment variable values on screen? (yes/no): yes

  HTTP_PROXY  = http://proxy.company.com:8080
  HTTPS_PROXY = http://proxy.company.com:8080
  NO_PROXY    = localhost,127.0.0.1,.company.com
  http_proxy  = (not set)
  https_proxy = (not set)
  no_proxy    = (not set)

[A2] Open MCP config folder in Explorer? (yes/no): yes

  Available MCP config locations:
    1. Desktop config: C:\Users\good_\AppData\Roaming\Claude
    2. Project MCP: C:\Users\good_\...\claude-code-full-auto-dev
    0. Exit

  Enter number (0 to exit): 1
  Opening: C:\Users\good_\AppData\Roaming\Claude

  Enter number (0 to exit): 0
  Done.

=============================================================
  Done. Press any key to exit.
=============================================================
```

各チェック項目を1行ずつリアルタイム表示し、右端にステータスを表示する。ファイルパスと Claude 連携用プロンプトテンプレートを表示した後、対話型アクション（A1: プロキシ値表示、A2: MCP フォルダを Explorer で開く）を順に提案する。対話型アクションの結果はファイルに出力しない（画面表示のみ）。
``````
