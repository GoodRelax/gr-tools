# gr-claude-toolkit — Claude Ecosystem Management Tools for Windows

**gr-claude-toolkit** is a collection of tools for diagnosing and maintaining the Claude ecosystem on Windows.

- Read-only diagnostics — no settings are modified
- No admin rights required
- Outputs both human-readable summary and Claude-consumable JSON

---

## Tools

### diagnose/

**diagnose-claude.bat** — Claude ecosystem diagnostic tool.

Checks 11 items across the entire Claude ecosystem:

- C1: Desktop app (MSIX)
- C2: CLI installation (npm)
- C3: VS Code extension
- C4: Credentials file
- C5: Global settings.json
- C6: Project settings.json
- C7: Desktop config (MCP servers)
- C8: PATH environment variable
- C9: claude.exe binary scan (detect old versions)
- C10: Proxy environment variables
- C11: MCP config files (Jira detection)

**Outputs:**
- `diagnosis-summary.txt` — Human-readable summary
- `diagnosis-for-claude.json` — Structured log for Claude analysis

**Interactive actions (after diagnostics):**
- A1: Show proxy environment variable values on screen (not saved to files)
- A2: Open MCP config folders in Explorer (loop until user exits)

**Usage:** Double-click `diagnose-claude.bat` or run from command prompt.

**Spec:** See `Claude_Diagnostic_Spec-en.md` / `Claude_Diagnostic_Spec-ja.md`

---

## Requirements

- Windows 10 / 11
- PowerShell 5.1+
- No admin rights needed

---

## License

MIT License

---
---

# gr-claude-toolkit — Windows 向け Claude エコシステム管理ツール集

**gr-claude-toolkit** は、Windows 上の Claude エコシステムを診断・管理するためのツール集です。

- 読み取り専用の診断 — 設定は一切変更しない
- 管理者権限不要
- 人間用サマリーと Claude 用 JSON の 2 種類を出力

---

## ツール

### diagnose/

**diagnose-claude.bat** — Claude エコシステム診断ツール

Claude エコシステム全体を 11 項目でチェック:

- C1: Desktop アプリ (MSIX)
- C2: CLI インストール (npm)
- C3: VS Code 拡張
- C4: 認証情報ファイル
- C5: グローバル settings.json
- C6: プロジェクト settings.json
- C7: Desktop config (MCP サーバー)
- C8: PATH 環境変数
- C9: claude.exe バイナリスキャン (旧バージョン検出)
- C10: プロキシ環境変数
- C11: MCP 設定ファイル (Jira 検出)

**出力ファイル:**
- `diagnosis-summary.txt` — 人間用サマリー
- `diagnosis-for-claude.json` — Claude 分析用構造化ログ

**対話型アクション (診断後):**
- A1: プロキシ環境変数の値を画面に表示 (ファイルには保存しない)
- A2: MCP 設定フォルダを Explorer で開く (0 を入力するまでループ)

**使い方:** `diagnose-claude.bat` をダブルクリック、またはコマンドプロンプトから実行。

**仕様書:** `Claude_Diagnostic_Spec-ja.md` / `Claude_Diagnostic_Spec-en.md` を参照

---

## 動作要件

- Windows 10 / 11
- PowerShell 5.1 以上
- 管理者権限不要

---

## ライセンス

MIT License
