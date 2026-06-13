# 改善要望: table.py の Markdown 出力を「スタンドアロン文書」として成立させる(H1 始まり)

- 起票日: 2026-06-14
- 対象: `scripts/table.py`(model 0.3.0)、`schema/model.schema.json`
- 種別: 改善要望(後方互換を保つ拡張)
- 状態: 提案(実証済み)

## 背景 / 問題

`table.py` の `render()` は Markdown を必ず `#### Nodes` / `#### Edges`(H4)で開始し、
**H1(文書タイトル)を出力しない**。

このため、生成した `.md` を **スタンドアロンの Markdown 文書として読むツール** に渡すと弾かれる。
実例(StrictDoc 0.23.1 をドキュメントサーバとして使用):

```
Markdown parsing error: the document must start with an H1 heading.
error source: .../strictdoc/backend/markdown/reader.py:111
```

StrictDoc は対象フォルダを再帰スキャンし、`.sdoc` だけでなく `.md` も文書として解釈する。
`_assets/` に置いた table.py 生成物(`*.model.md`)が H4 始まりのため、
**サーバがポートにバインドする前に異常終了**した。

根本原因の所在(現状):

```python
# scripts/table.py : render()  (lines ~217-220)
    return "\n".join([
        "#### Nodes", "", node_table(scope_nodes, paths), "",
        "#### Edges", "", edge_table(scope_edges), "",
    ])
```

`#### `(H4)は元々「親文書へ **埋め込む** 断片」を想定した見出しレベルと思われる。
一方、StrictDoc 等は `.md` 単体が **完結した文書** であること(先頭 H1)を要求するため、
2 つの用途が衝突している。

## 実証(手動で確認済み)

`.md` を次の構造へ手修正したところ、StrictDoc が正常にパース・描画した
(`strictdoc export` が EXIT=0、Nodes/Edges 両テーブル + H1 タイトルが HTML 化され、
第一級の文書ページとして公開された):

```markdown
# <Title>
## Nodes
| ... |
## Edges
| ... |
```

→ 「先頭を H1 にする」だけで解消することを確認。

## 提案(推奨案: モデル駆動 / 後方互換)

モデルに任意のタイトルを持たせ、**存在するときだけ** H1 + H2 を出す。
無ければ従来どおり H4(= 埋め込み用途を温存)。

1. `schema/model.schema.json`: top-level に任意プロパティ `title`(string)を追加
   (ルートが `additionalProperties: false` の場合は許可も追加する)。
2. `scripts/table.py : render()` を次のように変更:

```python
title = model.get("title")
h = "##" if title else "####"   # standalone => H1 + H2 ; embed fragment => H4 (legacy)
parts = (["# " + str(title), ""] if title else [])
parts += [f"{h} Nodes", "", node_table(scope_nodes, paths), "",
          f"{h} Edges", "", edge_table(scope_edges), ""]
return "\n".join(parts)
```

### 後方互換 / テスト

- 既存テスト(`tests/test_table.py`)は `title` を持たないモデルで `"#### Edges"` を
  `split` しているため、**変更なしで通る**。
- `title` を持つ分岐の新規テストを 1 本追加する
  (先頭が `# <title>`、節が `## Nodes` / `## Edges` であること)。

### 利用側の対応(参考)

`*.model.json` に `"title": "..."` を 1 行足して再生成すれば、手修正と同一の出力になり、
**再生成しても直ったまま**になる。

## 代替案

- **`--title TEXT` CLI フラグ**: スキーマ変更が不要。ただしタイトルが SSOT(model.json)の外
  (生成コマンド側)に置かれる。
- **常に H1 を出す**: 最小実装だが、全図の既定出力が変わり、埋め込み用途と既存テストを壊す。非推奨。

## 参考(調査ログ)

- StrictDoc は `.sdoc` / `.md` / `.markdown` / ... を再帰スキャンする
  (`strictdoc/core/file_system/document_finder.py` の `find_files_with_extensions`)。
  `.md` は H1 必須(`strictdoc/backend/markdown/reader.py:111`)。
- `_assets/` は StrictDoc の予約アセットフォルダ(画像配信元)でもあるため、フォルダ単位で
  除外すると参照画像が消える。除外で対処する場合はファイル単位(例 `_assets/*.md`)に限る。
  本要望はそれより上流(生成側)での恒久対策にあたる。
- 該当コード: `scripts/table.py:197-220`(`render`)、`tests/test_table.py`
  (`#### Edges` で `split` している箇所)。
