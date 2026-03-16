# /en — English Learning Mode

A Claude Code skill that helps Japanese learners practice English while coding.

## What it does

When enabled, Claude checks your English in every message before executing your task:

1. **Corrects** grammar, spelling, and unnatural expressions
2. **Confirms** what you want to do
3. **Waits** for your OK
4. **Executes** the task

## How to install (Claude Chat / Claude Cowork)

### Via prompt (Recommended)

1. Paste the following prompt:

```
Output the skill from the link below as SKILL.md.
I will copy the result to my skills and use it as /en.
https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md
```

2. Then click **"Copy to your skills"** in the output.

### Manual

1. Right-click [SKILL.md](https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md) → **Save link as...** → save as `SKILL.md` (change the extension from `.txt` to `.md`)
2. Go to **Customize → Skills → "+" → "Upload skill"**
3. Upload the downloaded file

## How to install (Claude Code)

### Via prompt (Recommended)

Paste the following prompt:

```
Download the skill from the link below and save it to ~/.claude/skills/en/SKILL.md
* Save to ~/.claude/ in the user's home directory, NOT the project's .claude/ directory.
https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md
```

### Manual

1. Right-click [SKILL.md](https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md) → **Save link as...** → save as `SKILL.md` (change the extension from `.txt` to `.md`)
2. Place it in `~/.claude/skills/en/SKILL.md` (user home, not project)

## How to use

In Claude Code, type:

```
/en on    — Enable English Learning Mode
/en off   — Disable English Learning Mode
/en       — Same as /en on
```

## Teaching style

- Uses leading questions instead of giving answers directly
- Encourages self-correction
- Keeps feedback brief and friendly
- Provides direct help when you're stuck

## Who is this for?

Non-native English speakers who want to improve their English naturally while working with Claude Code.

---

## 日本語ガイド

### /en とは？

Claude Code のスキルで、コーディングしながら英語の練習ができます。

有効にすると、Claude はタスクを実行する前に毎回あなたの英語をチェックします：

1. **文法・スペル・不自然な表現を指摘**
2. **やりたいことを確認**
3. **あなたの OK を待つ**
4. **タスクを実行**

### インストール方法（Claude Chat / Claude Cowork）

#### プロンプトで（推奨）

1. 下記のプロンプトを貼り付ける：

```
下記リンク先のスキルを一切変更せずにファイル名を `SKILL.md` として出力せよ。
2行目の `name: en` も省略するな。
ユーザは出力結果を自分のスキルにコピーして、 カスタムコマンド `/en` で使えるようにする。
https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md
```

2. 出力後、**「自分のスキルにコピー」** ボタンを押す。

#### 手動で

1. [SKILL.md](https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md) を右クリック → **「名前を付けてリンク先を保存」** → ファイル名を `SKILL.md` にする（`.txt` になる場合は `.md` に変更）
2. **カスタマイズ → スキル → 「+」 → 「スキルをアップロード」** でアップロード

### インストール方法（Claude Code）

#### プロンプトで（推奨）

下記のプロンプトを貼り付ける：

```
下記リンクのスキルをダウンロードして ~/.claude/skills/en/SKILL.md に保存せよ。
※プロジェクトの .claude/ ではなく、ユーザーホームの ~/.claude/ に配置すること。
https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md
```

#### 手動で

1. [SKILL.md](https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/SKILL.md) を右クリック → **「名前を付けてリンク先を保存」** → ファイル名を `SKILL.md` にする（`.txt` になる場合は `.md` に変更）
2. `~/.claude/skills/en/SKILL.md` に配置（プロジェクトではなくユーザーホーム）

### 使い方

Claude Code で以下のように入力します：

```
/en on    — 英語学習モードを有効にする
/en off   — 英語学習モードを無効にする
/en       — /en on と同じ
```

### 指導スタイル

- 答えを直接教えるのではなく、誘導する質問を使います
- 自分で気づいて直すことを促します
- フィードバックは簡潔でフレンドリーに
- 困っているときは直接ヘルプします

### 対象ユーザー

Claude Code を使いながら、自然に英語力を伸ばしたい日本語話者（およびその他の非ネイティブスピーカー）向けです。

---

© 2026 GoodRelax. MIT License.
