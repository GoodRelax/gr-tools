# 公式 StrictDoc への誘導取り付けメモ (upstream-outreach)

- 記録日: 2026-06-06
- 目的: 公式 StrictDoc から StrictDocStarter へ **「Windows で使いたい人はこちら」** の誘導リンクを取り付ける。
- 立ち位置: StrictDocStarter は **自分の repo のまま（L1 独立 companion）**。本体パッケージへの merge（L3）は狙わない。org 傘下の別 repo 化（L2）は任意・打診次第。
- 大原則: **あくまで「公式の補助」**。競合（competing fork）に見せないことが最重要。判断軸は improvement-items.md の **D-5（公式委譲スコープ）**。

> 本メモは作業前のプレイブック。チェックを埋めながら進める。`[ ]` = 未着手。

---

## 0. 確認済みの事実（前提・2026-06-06 調査）

- StrictDoc ライセンス = **Apache-2.0**（寄与の障壁が低い）。`CONTRIBUTING.md` あり。
- 公式は **companion repo 文化**を持つ: `strictdoc-examples` / `strictdoc-templates` / `strictdoc.tmLanguage` / `linux-strictdoc`（いずれも本体パッケージ外の別 repo）。
- 公式 README に **「Project links」節**があり examples / templates を列挙 → **ここへの 1 行追記が最有力の誘導先**。
- 公式 README / docs に **Windows 専用インストール案内は無い** → ちょうど StrictDocStarter が埋める隙間。
- maintainer: **stanislaw 氏（Stanislav Pankevich）**。窓口は GitHub Issues / Discussions（公式が "Share feedback or report issues" を案内）。
- 最も刺さるピッチ = **「Windows オンボーディングの障壁を下げる／latest 追従テストは自分が持つ／merge 不要、リンク 1 本でいい」**。

---

## 1. 手順（効く順）

### Phase 0 — 「リンクされる前提」に磨く（必須の地固め）
maintainer は雑な物にはリンクしない。最低限：
- [ ] **README を英語で整備**: 何を / なぜ / 誰向け（Windows・Python 無しの初心者）
- [ ] **スクショ / GIF**: ダブルクリック → ブラウザで StrictDoc が開くまで
- [ ] **latest strictdoc で動作確認** ＋ テスト版を明記（improvement-items O-1 / O-4 連動。Mermaid 等の版依存記法も latest で再確認）
- [ ] **ライセンス明記**（Apache-2.0 互換が無難）
- [ ] **冒頭にスコープ宣言**（competing に見せない最重要ポイント・D-5）:
  > "This is a community **Windows quickstart** that **complements, not replaces**, the official StrictDoc. It delegates the server / scaffolding / config to `strictdoc server` / `strictdoc new` / `strictdoc_config.py` and only adds the Windows bootstrap. For real projects, follow the official docs."

### Phase 1 — 先に upstream へ「手土産」を出す（goodwill）
- [ ] サンプル 1 本（SOVD / ASIL ドメイン）を `strictdoc-examples` の形式に整えて PR
  - or 小さな **docs 改善 PR**（latest で確認した内容に限る）
- 狙い: 「自己宣伝の人」でなく **「エコシステム貢献者」** として認知される → 後の依頼が通りやすくなる

### Phase 2 — Discussion / Issue で打診（低摩擦の最初の一歩）
- [ ] GitHub Discussion または Issue を立てる
  - タイトル案: *"Community Windows quickstart for StrictDoc — would a README/docs link help Windows users?"*
  - 本文骨子:
    1. 公式に Windows インストーラが無い（gap）
    2. StrictDocStarter がそれを埋めている（補助・委譲スタンスを明記）
    3. **README "Project links" に 1 行、または Installation に Windows note を足す PR を出していいか許可を求める**
    4. 「org 傘下に置く / 別 repo のまま」は**相手に選ばせる**
    5. latest 追従テストは自分が持つ、**merge は不要**
- [ ] 反応を見て Phase 3 へ

### Phase 3 — GO が出たら、ピンポイントの docs/README PR
- [ ] README **"Project links"** 節に 1 行（本命）:
  ```
  - Windows quickstart (community): StrictDocStarter — one-click installer + visible-window server launcher
  ```
- [ ] or **Installation 節の直後**に Windows note（"On Windows, the community StrictDocStarter provides …"）
- [ ] user guide `docs/strictdoc_01_user_guide.sdoc`（dogfood 版）にも同様に
- **小さく・完了形**で出すほど merge されやすい

### Phase 4 — "community-maintained" ラベルを素直に受ける
- 公式は「これは community 製・サポートは別」と注記したがる可能性大 → **素直に受ける**（公式に保証責任を負わせない姿勢が通りやすさに効く）

---

## 2. 誘導先（実在確認済みの挿入ポイント）

| 場所 | 内容 | 優先 |
|---|---|---|
| README「Project links」節（examples/templates の隣） | 1 行リンク | ★本命 |
| README「Installation」節の直後 | Windows note | ◯ |
| `docs/strictdoc_01_user_guide.sdoc` の Installation 相当 | dogfood 版に同記述 | ◯ |

---

## 3. ピッチ草案（英語・相手の利益で語る）

> StrictDoc has no Windows installer today. **StrictDocStarter** gives Windows users a one-click path: it installs Python + strictdoc + VS Code, launches the server in a visible console, and opens the browser. It **strictly complements** the official tool — server, scaffolding and config are delegated to `strictdoc server` / `strictdoc new` / `strictdoc_config.py`; it only adds the Windows bootstrap. I'll keep it **tested against the latest release**. **No merge needed** — a single link from "Project links" would help Windows newcomers find it.

---

## 4. 注意（地雷）

- **競合に見えた瞬間アウト** → 終始「補助・公式へ委譲（D-5）」を前面に。スコープ宣言を README 冒頭に。
- **自己宣伝先行は嫌われる** → Phase 1（手土産 PR）を必ず先に。
- 保証は無い（maintainer 次第）。ただし土壌は良好: Apache-2.0 / CONTRIBUTING / companion 文化 / feedback 招待 の 4 点。
- StrictDocStarter は **L1（自分の repo）のまま**。リンクがそこを指すだけ（コードは merge されない）。

---

## 5. 関連

- スコープ・設計判断: [`improvement-items.md`](improvement-items.md)（**D-5** 公式委譲、**O-1/O-4** 版テスト、**D-9** サンプル）
- companion レベル整理: **L1**=自 repo のまま / **L2**=org 傘下の別 repo（任意・打診） / **L3**=本体パッケージへ merge（やらない）
- 仕様: [`serve-spec.md`](serve-spec.md) / [`setup-spec.md`](setup-spec.md)（v1.1・可視ウィンドウ方式）
