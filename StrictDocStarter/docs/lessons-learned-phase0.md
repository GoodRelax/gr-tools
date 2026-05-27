# Lessons Learned — StrictDocStarter

StrictDocStarter ツール自体の開発・検証で得られた技術知見。 クリーン Windows 11 VM + 開発機 (host PC) での実行から抽出。

---

## 環境構築フェーズ — StrictDocStarter 自動セットアップ ツール

### L-1. dryrun と auto はプラン生成パスが別経路だった

VM では `auto` のみ検証していたため、 `Get-ClonePlan` / `Get-InstallPlan` のバグが host で初めて顕在化。
**回避策**: dryrun を `Build-AutoPlan` + `Show-AutoPlan` に統一して経路を 1 本化。
**教訓**: 新しい subcommand を追加するときは、 既存の planner を流用するか、 新しい planner を作るかを最初に決める。 複数経路は drift する。

### L-2. テンプレート config の `<user>` プレースホルダが Test-Path で例外

Windows ファイル名で `<` `>` は禁止文字。 dryrun 時にテンプレートをそのまま config として読むと crash。
**回避策**: path 操作前に必ず `Expand-UserPlaceholders` で `<user>` → `$env:USERNAME` に置換。
**教訓**: プレースホルダ規約は config レイヤで吸収し、 ロジック層には絶対に届けない。

### L-3. Build-AutoPlan のプラン表示は probe 必須

config の install フラグだけで列挙すると「既にあるのに install 予定」 という誤情報になる。
**回避策**: プラン表示は `config × 実環境 (探査結果)` で組み立てる。 `[INSTALL]/[SKIP]` タグ + 4 状態 (required / already installed / optional enabled / optional disabled) で明示。
**教訓**: 「設定が意図するアクション」 と 「実際に実行されるアクション」 は別物。 UI は後者を見せる。

### L-4. VS Code は Phase A 必須 = Optional リストから除外

「Optional ツール」 というラベルと「Phase A で実質必須」 が矛盾していた。
**回避策**: Phase A を VS Code の唯一の窓口にし、 `install_vscode` フラグ廃止。
**教訓**: ツールの分類軸 (required / optional) は 1 箇所で管理し、 config と Phase ロジックの両方が同じ定義を見る。

### L-5. ⭐ 外部コマンド stderr を `EAP=Stop` で拾うと誤検知

`$ErrorActionPreference = "Stop"` + `2>&1` の組み合わせは、 pip の dependency resolver 警告 (`ERROR: ...` のテキスト) を terminating error として catch してしまう。 pip の exit code は 0 で install は実際成功している。
**回避策**: 外部コマンドラッパは EAP を一時的に `Continue` に下げ、 `$LASTEXITCODE` のみを真実とする。 `clone.ps1` の `Invoke-GitClone` で既に確立済のパターンを `Install-StrictDoc` / `Install-VSCodeExtensions` / `Install-ClaudeCodeExtension` にも適用。
**さらに**: 「exit code 信用」 より「最終状態確認 (`Test-*Installed` + バージョン取得)」 の方が頑健。 2 段防御 (ADR-013) で運用。
**教訓**: 外部プロセスの stderr 出力規約に依存しない。 実態 (`--version` レスポンス等) を最終判定の根拠にする。

### L-6. gather-logs.ps1 は env-report.json が無くても動く

auto モードでは check 段階をスキップするので env-report.json が生成されない。 gather-logs.ps1 はその場合 setup.log + setup.config.json + diagnostics.txt の 3 ファイルだけで ZIP を作る。 期待通り。
**教訓**: 副次成果物の有無を強制せず、 あれば同梱、 無ければスキップ。 fail-soft 設計。

---

## 凡例

- ⭐ = 採用判断 / Phase 移行判断に直結する重要知見

## 関連ドキュメント

- [setup-spec.md](setup-spec.md) — StrictDocStarter 仕様書 (FR / ADR / シーケンス図)
- [01-environment.md](01-environment.md) — ユーザ向け Phase 0 手順書
- [../README.md](../README.md) — StrictDocStarter 全体の使い方
