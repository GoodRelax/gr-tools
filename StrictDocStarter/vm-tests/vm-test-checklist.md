# StrictDocStarter VM テストチェックリスト

クリーン Windows 11 VM で StrictDocStarter の挙動を回帰検証する。 **T0 (推奨) で一気通貫**、 または個別ステップを手動実行。

仕様参照: [setup-spec.md §5 Test Strategy](../docs/setup-spec.md) (10 シナリオ仕様)。

---

## T0: クリーン VM での通しテスト (推奨、一発)

**所要 60〜80 分、手動操作は ZIP 展開 + ダブルクリック 3 回 + 手動 SC-015 (10 分)。**

### 手順

1. **VM スナップショットを復元** (完全クリーン状態)
2. ホスト `gr-tools\StrictDocStarter\temp\StrictDocStarter.zip` を VM デスクトップに Ctrl+V → 「すべて展開」 → `Desktop\StrictDocStarter\` 1 階層作成
3. **`Desktop\StrictDocStarter\setup-strictdoc.bat`** ダブルクリック → UAC → `yes` → 完走待ち → Enter (= T1 ベースライン、 Phase A〜E 全 OK)
4. (任意) `setup-strictdoc.bat dryrun` を別途実行 → plan 出力が正常表示されることを確認
5. **`Desktop\StrictDocStarter\vm-tests\run-tests.bat`** ダブルクリック → UAC → 10 シナリオ自動実行 → サマリ → Enter
6. **手動 SC-015 (FR-209 abort)** の確認: 別途 `setup-strictdoc.bat` ダブルクリック → UAC → plan 表示 → **`no`** 入力 → `[WARN] Aborted -` 3 行 + `Config:` 行が表示されることを目視確認 → Enter
7. **`vm-tests\gather-test-logs.bat`** ダブルクリック → エクスプローラ選択状態の ZIP を Ctrl+C → ホストの `TestResult/` に Ctrl+V

### 期待結果

- ステップ 3: Phase A〜E 全 OK、 Phase D は SKIP (URL 空既定)
- ステップ 4: dryrun 完走、 plan に `[REQUIRED]` / `[OPTIONAL]` / `[SKIP]` / `[INSTALL]` タグ表示
- ステップ 5: **9 シナリオ PASS、 1 シナリオ SKIPPED** (NegativeAbort、 手動 fallback)
- ステップ 6: abort guidance 3 行が表示される
- ステップ 7: `StrictDocStarter-test-result-*.zip` に per-scenario log (10 件) + final setup.log + diagnostics.txt

---

## 前提

- クリーン Win11 VM (Hyper-V 等)、 スナップショット取得済
- VM に winget が利用可能 (`winget --version` で確認)
- VM のネットワーク疎通 OK
- ホストの `gr-tools\StrictDocStarter\temp\StrictDocStarter.zip` を VM に運ぶ準備 (拡張セッションのクリップボード)

---

## 10 シナリオ一覧 (run-tests.bat で自動)

| # | シナリオ | 内容 | uninstall 対象 | 所要 (目安) |
|---|---|---|---|---|
| 1 | Idempotency | 何も変えず再実行、 全 SKIP | (なし) | ~30 秒 |
| 2 | PartialOptional | 3 件 uninstall → 再 install | jq, ripgrep, gitlens 拡張 | ~3〜5 分 |
| 3 | RequiredOnly | gh uninstall → 再 install | GitHub CLI | ~2 分 |
| 4 | ExtensionsOnly | 拡張 2 件 uninstall → 再 install | bierner.markdown-mermaid, ms-python.python | ~30 秒 |
| 5 | Mixed | optional + 拡張 1 件 uninstall (他シナリオと完全独立) | Obsidian, MS-CEINTL.vscode-language-pack-ja | ~3〜5 分 |
| 6 | ClaudeExtension | Phase A coverage、 Claude 拡張 uninstall → 再 install | anthropic.claude-code | ~30 秒 |
| 7 | StrictDocPip | Phase C coverage、 pip uninstall → 再 install | strictdoc (pip) | ~3〜5 分 |
| 8 | NegativeAbort | **SKIPPED** (手動 SC-015 に委ね) | (なし) | ~1 秒 (skip msg のみ) |
| 9 | NegativeClaudeBoth | FR-305 排他: config 改変 → 期待動作確認 → 復元 | (なし、 config 一時改変) | ~1〜2 分 |
| 10 | DryrunAssert | dryrun 出力の [REQUIRED]/[OPTIONAL]/[SKIP] タグ + Phase E sort assert | (なし、 dryrun のみ) | ~10 秒 |

シナリオ独立性は **setup-spec.md §5.3 uninstall マトリクス** で保証。 各ツールは 1 シナリオでのみ touch される。

実行モード:
- `run-tests.bat` または `run-tests.bat real` — 本番モード (uninstall + reinstall)
- `run-tests.bat dryrun` — dryrun モード (uninstall せず planner だけ走らせる、 host でも実行可)
- `run-tests.bat foo` (typo) → ValidateSet で **fatal stop** (FR-1003)

タイムアウト: 1 シナリオ 5 分 (`Start-Job -Timeout`)、 タイムアウト時は exit 124 で FAIL 記録 (子孫プロセスは killed されないので Task Manager で winget/msiexec を手動 kill する場合あり)

---

## T1: クリーン VM での初回フル実行 (手動)

**目的:** クリーン状態から `setup-strictdoc.bat` 1 回で開発環境を構築できること。

### 手順

1. VM スナップショット復元
2. `StrictDocStarter.zip` を VM デスクトップに転送 → 展開
3. `Desktop\StrictDocStarter\setup-strictdoc.bat` ダブルクリック
4. UAC → 「はい」 → プラン → `yes` → Phase A〜E 完走 → Enter

### 期待結果

```text
=== Summary ===
  Phase A  : OK    (VS Code + Claude Code 拡張)
  Phase B  : OK    (Git + Python + gh)
  Phase C  : OK    (strictdoc)
  Phase D  : SKIP  (repository.url 空既定)
  Phase E  : OK    (Obsidian/Terminal/PS7/ripgrep/jq + VS Code 拡張群)
```

### 確認コマンド (新しい PowerShell で)

```powershell
code --list-extensions | findstr anthropic
git --version
python --version
strictdoc --version
gh --version
rg --version
jq --version
```

すべてバージョン情報が出れば OK。

---

## SC-015: 手動 negative test (FR-209 abort guidance)

run-tests.bat の T_negative_abort は **自動化不能** (PowerShell の Read-Host が piped stdin を読まないため)。 v1.0 では手動で確認:

### 手順

1. T1 完了後の VM で `Desktop\StrictDocStarter\setup-strictdoc.bat` ダブルクリック
2. UAC → 「はい」 → plan 表示 → `Proceed with the above? Type 'yes' to install, anything else to abort: ` プロンプト
3. **`no` と入力 → Enter**

### 期待結果

以下 5 行が表示される:

```text
[WARN]  Aborted - 'yes' not entered.
[INFO]  To customize installation:
[INFO]    1. Edit setup.config.json (path shown below)
[INFO]    2. Re-run setup-strictdoc.bat (idempotent - already-installed tools are skipped)
[INFO]  Config: C:\Users\<your-username>\Desktop\StrictDocStarter\setup.config.json
```

`<your-username>` 部分が `$env:USERNAME` 実値で展開済であることを確認 (`<user>` リテラルが残っていれば FR-208 違反)。

---

## ログ回収

`vm-tests\gather-test-logs.bat` ダブルクリック → `%TEMP%\StrictDocStarter-test-result-*.zip` 生成 → エクスプローラで select 状態 → Ctrl+C → ホストへ Ctrl+V

含まれるファイル (期待):
- `T_*.log` × 10 (各シナリオの setup-strictdoc.ps1 transcript)
- `T_*.runner-capture.log` × 10 (runner 側の生 stdout/stderr capture、 FR-1004)
- 最新 `setup.log` (T1 ベースラインの transcript)
- `diagnostics.txt` (Windows / PS / winget version、 既存 tool、 PATH 等)

---

## 報告いただきたい内容

各テスト (T1 / 10 シナリオ / SC-015) について:
- [ ] 期待通り動作したか (OK / NG)
- [ ] NG なら: 実際の出力と推定原因
- [ ] 所要時間 (NFR-008 で REAL モード合計 60 分以内が目標)
- [ ] サマリの 10 シナリオ結果 (PASS / FAIL / SKIPPED)
- [ ] 違和感を覚えた挙動・出力 (細かい UX 含む)

特に NegativeClaudeBoth は v1.0 で FR-305 が auto.ps1 に未実装の場合 `[WARN] FR-305 enforcement not yet observable in log` という soft warn が出る — それが想定挙動。

## トラブル発生時

`gather-test-logs.bat` で取得した ZIP を共有してください。 各 `T_*.runner-capture.log` には sub-process が transcript 開始前に死んだ場合の生エラーが含まれます (FR-1004)。
