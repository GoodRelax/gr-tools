# /en — English Learning Mode

A Claude Code skill that helps Japanese learners practice English while coding.

## What it does

When enabled, Claude checks your English in every message before executing your task:

1. **Corrects** grammar, spelling, and unnatural expressions
2. **Confirms** what you want to do
3. **Waits** for your OK
4. **Executes** the task

## How to install

### Option 1: Ask Claude (Recommended)

Paste the following into your Claude Code chat:

```
Download the skill from the link below and save it to ~/.claude/commands/en.md
https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/en.md
```

### Option 2: Manual

1. Download [en.md](https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/en.md)
2. Place it in `~/.claude/commands/en.md`

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

Japanese (and other non-native) English speakers who want to improve their English naturally while working with Claude Code.

---

## 日本語ガイド

### /en とは？

Claude Code のスキルで、コーディングしながら英語の練習ができます。

有効にすると、Claude はタスクを実行する前に毎回あなたの英語をチェックします：

1. **文法・スペル・不自然な表現を指摘**
2. **やりたいことを確認**
3. **あなたの OK を待つ**
4. **タスクを実行**

### インストール方法

#### 方法1: Claude に任せる（オススメ）

Claude に下記を指示する：

```
下記リンクのスキルを手に入れろ
https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/en.md
```

#### 方法2: 手動

1. [en.md](https://raw.githubusercontent.com/GoodRelax/gr-tools/refs/heads/main/gr-en-coach/skills/en/en.md) をダウンロード
2. `~/.claude/commands/en.md` に配置

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
