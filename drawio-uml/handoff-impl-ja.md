# drawio-uml 実装・テスト 引継プロンプト(次セッション用)

> このファイルの内容を次セッション冒頭にそのまま渡す。`drawio-uml` ツールスイートの
> **実装とテスト**を行う。作業ディレクトリ: `gr-tools/drawio-uml`。

## 0. まず読む(SSOT — これが唯一の正)

1. `docs/spec-ja.md`(v0.2.1)— 仕様の SSOT。敵対的レビュー(R1–R6)済み・ゲート通過。**これに従って実装する。情報が重複する場合は spec が正。**
2. `scripts/drawio_uml.py`(750行)— 既存の描画実装(リネーム対象)。
3. `references/drawio-uml-reference.md` — 描画の詳細リファレンス。

目的を申告してから読むこと(ユーザーのプロトコル)。

## 1. 現状

- 実装は `scripts/drawio_uml.py` のみ(描画 = `draw`、flat / clustered の両経路に対応)。
- `table`(作表)は**未実装**。
- 命名・配置・スキーマ・dual-track は spec の ADR-004〜008 で確定済み。

## 2. タスク(この順序で)

- **T1. リネーム**:`scripts/drawio_uml.py` → `scripts/draw.py`(`git mv`、**ロジックは1行も変えない**)。`usage` 文字列・`__main__` の表示名も `draw.py` に合わせる。リネーム前に T3 の回帰基準(下記)を取得しておくこと。
- **T2. `table` 実装**:`scripts/table.py` を新規作成。spec の FR-T-01〜09 を満たす。
  - node 表 `| cluster | name | description | remark |`、edge 表 `| arrow | source | target | label | description | remark |`(FR-T-02/03)。
  - cluster はパス文字列。対象 node 群の**共通接頭を除去**し `" / "` 区切りで表示、除去後に全行空なら **cluster 列ごと削除**(FR-T-04/05)。
  - `--cluster KEY`:`/` セグメント境界の前方一致(`a/b` は `a/b`・`a/b/*` に一致、`a/bc` には不一致)。`cluster` 無し node は対象外(FR-T-06)。0件一致は見出しのみ+警告(FR-T-06a)。
  - edge は source / target の**一方でも**対象集合に属せば採用(FR-T-07)。
  - セル `|`→`\|` エスケープ、`description`/`remark` 内の `<br>` は素通し(FR-T-08)。必須欠落(name / source / target)は非ゼロ終了(FR-T-09)。
  - **Python 標準ライブラリのみ**(NFR-02)。
- **T3. テスト**(spec Chapter 5):
  - **回帰**:代表 model.json から現 `drawio_uml.py` の出力 `.drawio` を**基準として保存**(リネーム前に取得)→ `draw.py` で再生成し **md5 byte-identical** を確認(NFR-01)。`tests/` にサンプル model.json + 基準 `.drawio` を置く。
  - **単体**:`table` の純関数(共通接頭計算 / セルエスケープ / `--cluster` フィルタ)を入出力ペアで。
  - **受入**:spec 4.1 の Gherkin(SC-001〜014、SC-101〜106)を実行可能な形にし、結果を spec の各 `**Result:**` に反映(SKIP → PASS / FAIL)。
- **T4(任意・別判断)**:ARC リポジトリ(`Kaggle/ARC-AGI-3`)の `docs/StrictDoc-specs/_assets/build_domain_model.py` を廃止し `draw.py` で代替(v006=v007 のバイト一致で代替可能と実証済み)。ARC 側の作業なので着手前にユーザーへ確認。

## 3. このマシン特有の嵌りどころ

- git-bash の `grep -P` は cp932 locale で動かない。正規表現抽出は **python** で行う。
- model.json は UTF-8。`open(..., encoding="utf-8")` 必須(cp932 で開くと文字化け)。
- cluster パスは内部 `/` 区切り、表示は `" / "`。**`draw` はパス全体を1ラベルとして扱う**(階層を入れ子の箱にしない。ADR-005 / LM-1)。
- `draw` の flat path は最小コーナを原点 (40,40)、clustered path は (70,70) に置く。リネーム後も不変であることを回帰で確認。
- **描画ロジックは変更しない**。挙動が変わると既存図(ARC の `gr-arc-3-domain-model` 等)が壊れる。

## 4. ルール(厳守)

- **`git commit` / `git push` / `git tag` は実行しない**(ユーザーが手動)。read-only git と、頼まれた `git mv` / `git add` は可。
- **コミットを推奨するときは、貼り付け用の英語メッセージを添える** — `Summary`(命令形・約50字)+ `Description`(変更内容と理由)。
- **SSOT は `gr-tools/drawio-uml`**。skill(`~/.claude/skills/drawio-uml`)と利用先(ARC)は配布コピー = **編集しない**。実装後はコピー配布の手順を案内する。
- 環境:`uv run` は不可。Graphviz `dot`/`neato`/`fdp` あり。draw.io CLI = `C:\Program Files\draw.io\draw.io.exe`(`.svg`/`.png` 化は任意)。
- 図・命名で迷ったら勝手に決めず、DA 表(複数案+評価軸)を出してユーザー決定(命名は最重要管理項目)。

## 5. 完了条件

- `scripts/draw.py` にリネーム済み、回帰が byte-identical。
- `scripts/table.py` 実装、FR-T-01〜09 を全達成、受入 Gherkin が PASS。
- `tests/` にサンプル + 基準 + 単体テストが揃い、通る。
- spec の Gherkin `Result` を更新(SKIP → PASS）。
- skill / ARC への配布(コピー)手順を提示。

## 6. 参考:今セッションで確定した主要決定(spec の要点)

- スイート名 `drawio-uml`、機能は動詞 `draw`(描く)/ `table`(表にする)。draw.io 出力が肝なので `drawio-uml` を維持(ADR-004)。
- `description`(責務・主)/ `remark`(傍注・属性に出ない補足)を model に追加。**`draw` は無視・`table` が消費**(ADR-006)。図には出ない。
- cluster はパス文字列で統一。**階層対応は `table` のみ**、`draw` は当面フラット(ADR-005)。
- ルーティング不能(neato/fdp 不在)時は draw.io 自動ルーティングに degrade(ADR-008、`box-avoiding` は保証しない)。
