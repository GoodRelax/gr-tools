# GR SVG Extractor 仕様書

> **GR** = GoodRelax
> **Version**: 1.1.0
> **Date**: 2026-02-14
> **Scope**: PowerPointからクリップボード経由でコピーした図形をSVGに変換・ダウンロードする、クライアント完結型のシングルページWebツール

---

## 1. 概要

### 1.1 目的

PowerPoint上で図形を選択・コピー（Ctrl+C）し、ブラウザ上でペースト（Ctrl+V）すると、整形済みSVGマークアップを表示し、ダウンロードできるツール。

### 1.2 設計思想

**「入力されたものは全部変換する」** — フィルタリング機能は持たない。

図形の取捨選択はPowerPoint側で行う。本ツールの責務は「クリップボードの中身を忠実にSVGへ変換すること」のみ。これにより状態管理の複雑さを排除し、Extractorとしての単機能性を保つ。

| 原則 | 根拠 |
|------|------|
| KISS | フィルタリングUIと状態管理を排除 |
| YAGNI | ユーザーはPPT側で選択済み。二重のフィルタは不要 |
| SRP | 本ツールの責務は「変換」のみ。「選択」はPowerPointの責務 |
| POLA | ペーストしたもの＝全部出る。驚きがない |

### 1.3 制約

| 項目 | 内容 |
|------|------|
| 実行環境 | モダンブラウザ（Chrome / Edge 推奨） |
| サーバー依存 | なし。すべてクライアント側で完結 |
| 外部ライブラリ | なし。Vanilla JS + Clipboard API のみ |
| ファイル構成 | **単一HTMLファイル**（CSS / JS 内包） |

---

## 2. 入力仕様

### 2.1 クリップボードデータの取得

`paste` イベントの `event.clipboardData` を使用（同期API）。

| 優先度 | MIME type | 内容 | 用途 |
|--------|-----------|------|------|
| 1 | `text/html` | HTML断片（VML要素を含む） | 図形構造の主要ソース |
| 2 | `image/png` | レンダリング済み画像 | フォールバック |

### 2.2 HTMLフラグメントから得られるVML要素

- `<v:rect>`, `<v:roundrect>` — 矩形
- `<v:oval>` — 楕円
- `<v:line>` — 直線
- `<v:polyline>` — 折れ線・多角形
- `<v:shape>` (path) — フリーフォーム
- `<v:group>` — グループ
- `<v:fill>` — 塗りつぶし・グラデーション
- `<v:stroke>` — 線スタイル
- `<v:shadow>` — 影
- `<v:textbox>` — テキスト

### 2.3 フィルタリングなし

クリップボードから取得したデータに対して、図形の種類や属性によるフィルタリングは一切行わない。取得したVML要素をすべて変換対象とする。未対応の図形タイプに遭遇した場合はスキップし、ステータスで通知する。

---

## 3. 対応図形スコープ

### 3.1 対応する図形（v1.0）

| カテゴリ | 図形 | VMLソース |
|----------|------|-----------|
| 基本図形 | 矩形 | `<v:rect>`, `<v:roundrect>` |
| 基本図形 | 楕円・円 | `<v:oval>` |
| 基本図形 | 直線・矢印 | `<v:line>` |
| 基本図形 | 多角形・フリーフォーム | `<v:polyline>`, `<v:shape>` (path) |
| テキスト | テキスト付き図形 | `<v:textbox>` |
| 装飾 | 単色塗りつぶし | `<v:fill type="solid">` |
| 装飾 | グラデーション | `<v:fill type="gradient" / "gradientRadial">` |
| 装飾 | 線スタイル（色, 太さ, 破線） | `<v:stroke>` |
| 装飾 | 影 | `<v:shadow>` |
| 構造 | グループ化 | `<v:group>` |
| 構造 | コネクタ | `<v:line>` + 矢印マーカー |

### 3.2 対応しない図形（v1.0）

SmartArt, グラフ / チャート, 3D効果, アニメーション, 埋め込みOLEオブジェクト

---

## 4. 出力仕様

### 4.1 SVG形式

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="{W}" height="{H}"
     viewBox="0 0 {W} {H}">
  <defs>
    <!-- グラデーション定義, 矢印マーカー等 -->
  </defs>
  <!-- 図形要素 -->
</svg>
```

### 4.2 SVG要素マッピング

| VML | SVG |
|-----|-----|
| `<v:rect>` | `<rect>` |
| `<v:roundrect>` | `<rect rx="..." ry="...">` |
| `<v:oval>` | `<ellipse>` |
| `<v:line>` | `<line>` |
| `<v:polyline>` | `<polyline>` / `<polygon>` |
| `<v:shape>` (path) | `<path>` |
| `<v:group>` | `<g>` |
| `<v:textbox>` | `<text>` / `<foreignObject>` |
| `<v:fill type="gradient">` | `<linearGradient>` / `<radialGradient>` |
| `<v:stroke>` | `stroke`, `stroke-width`, `stroke-dasharray` 属性 |
| `<v:shadow>` | `<filter>` (feDropShadow) |
| 矢印 | `<marker>` |

### 4.3 XML整形ルール

出力するSVGは人間が読みやすい形に整形する。

| ルール | 内容 |
|--------|------|
| インデント | スペース2個 |
| 改行 | 要素ごとに改行 |
| 属性順序 | 構造属性（id, class）→ 座標属性（x, y, width, height）→ スタイル属性（fill, stroke） |
| `<defs>` | 先頭にまとめて配置 |
| 空要素 | 自己閉じタグ `<rect ... />` |

整形例:

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="400" height="300"
     viewBox="0 0 400 300">
  <defs>
    <linearGradient id="grad-1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ff0000" />
      <stop offset="100%" stop-color="#0000ff" />
    </linearGradient>
  </defs>
  <rect
    x="10" y="20"
    width="180" height="100"
    rx="8" ry="8"
    fill="url(#grad-1)"
    stroke="#333333" stroke-width="2" />
  <text
    x="100" y="75"
    font-family="sans-serif" font-size="14"
    fill="#ffffff" text-anchor="middle">
    サンプルテキスト
  </text>
</svg>
```

### 4.4 フォールバック

VMLが取得できない場合、`image/png` をBase64で `<image>` 要素に埋め込んだSVGを出力する。

### 4.5 ダウンロード

| 項目 | 内容 |
|------|------|
| ファイル名 | `gr-svg-ext.svg` （固定） |
| MIME type | `image/svg+xml` |
| 方式 | Blob URL + `<a download>` による即時ダウンロード |

---

## 5. UI仕様

### 5.1 レイアウト

```
┌─────────────────────────────────────────┐
│  GR SVG Extractor                       │
│  GoodRelax SVG Extraction Tool          │
├─────────────────────────────────────────┤
│                                         │
│    ペーストエリア（Drop Zone）           │
│    "Ctrl+V で図形を貼り付け"            │
│                                         │
├─────────────────────────────────────────┤
│  SVGプレビュー                          │
│  （生成したSVGをインラインレンダリング） │
├─────────────────────────────────────────┤
│  SVGテキスト出力（readonly textarea）    │
│  ※ 整形済みXML                         │
├─────────────────────────────────────────┤
│  ［📋 コピー］  ［⬇ ダウンロード］      │
├─────────────────────────────────────────┤
│  ステータスバー                         │
└─────────────────────────────────────────┘
```

### 5.2 インタラクション

| アクション | 結果 |
|------------|------|
| Ctrl+V | クリップボード読み取り → 変換 → プレビュー + テキスト表示 |
| ［コピー］ | textareaのSVGテキストをクリップボードにコピー |
| ［ダウンロード］ | `gr-svg-ext.svg` としてファイル保存ダイアログ |
| 変換失敗時 | ステータスバーにエラーメッセージ表示 |

### 5.3 初期状態

ペースト前はプレビュー・テキスト・ボタン領域は非表示。ペーストエリアのみ表示し、操作を迷わせない（POLA）。

---

## 6. アーキテクチャ設計

### 6.1 レイヤー構成と責務

```
┌──────────────────────────────────────────────────────────┐
│                    UI Layer                               │
│  責務: DOM操作, イベントバインド, 表示更新                │
│  原則: SRP (表示のみ), POLA (予測可能なUI応答)           │
├──────────────────────────────────────────────────────────┤
│               Application Layer                          │
│  責務: ユースケース制御 (paste → parse → convert → show) │
│  原則: SoC (フロー制御に専念), SLAP (抽象度統一)        │
├──────────────────────────────────────────────────────────┤
│                 Domain Layer                              │
│  ├─ ShapeModel      … 中間図形モデル定義                │
│  ├─ VmlParser        … VML HTML → 中間モデル            │
│  ├─ SvgBuilder       … 中間モデル → SVG文字列           │
│  └─ XmlFormatter     … SVG文字列の整形                  │
│  原則: OCP (図形タイプ追加で拡張), DIP (抽象モデル依存) │
├──────────────────────────────────────────────────────────┤
│             Infrastructure Layer                         │
│  ├─ ClipboardReader  … Clipboard API抽象化              │
│  └─ FileDownloader   … Blob生成 + ダウンロード処理      │
│  原則: ISP (必要なI/Fのみ公開), DIP (上位は抽象に依存)  │
└──────────────────────────────────────────────────────────┘
```

### 6.2 中間図形モデル（SoC / DIP の核）

```
VML HTML ──→ [VmlParser] ──→ ShapeModel[] ──→ [SvgBuilder] ──→ SVG
                                                                  │
                                                          [XmlFormatter]
                                                                  │
                                                          整形済みSVG文字列
```

```javascript
// === 中間図形モデル ===

/** @typedef {Object} ShapeModel
 *  @property {'rect'|'roundRect'|'ellipse'|'line'|'polyline'|'path'|'group'} type
 *  @property {GeometryModel}   geometry
 *  @property {FillModel|null}  fill
 *  @property {StrokeModel|null} stroke
 *  @property {ShadowModel|null} shadow
 *  @property {TextModel|null}  text
 *  @property {ShapeModel[]}    children   // group の場合のみ
 */

/** @typedef {Object} GeometryModel
 *  @property {number} x
 *  @property {number} y
 *  @property {number} width
 *  @property {number} height
 *  @property {number} [rx]                // roundRect
 *  @property {string} [pathData]          // path の d 属性
 *  @property {{x:number,y:number}[]} [points]
 *  @property {{x1:number,y1:number,x2:number,y2:number}} [line]
 */

/** @typedef {Object} FillModel
 *  @property {'solid'|'linearGradient'|'radialGradient'|'none'} type
 *  @property {string}  [color]
 *  @property {number}  [opacity]
 *  @property {GradientStop[]} [stops]
 *  @property {number}  [angle]
 */

/** @typedef {Object} StrokeModel
 *  @property {string} color
 *  @property {number} width
 *  @property {'solid'|'dash'|'dot'|'dashDot'} pattern
 *  @property {'none'|'arrow'|'triangle'} startArrow
 *  @property {'none'|'arrow'|'triangle'} endArrow
 */

/** @typedef {Object} ShadowModel
 *  @property {string} color
 *  @property {number} offsetX
 *  @property {number} offsetY
 *  @property {number} blur
 */

/** @typedef {Object} TextModel
 *  @property {string} content
 *  @property {string} fontFamily
 *  @property {number} fontSize
 *  @property {string} color
 *  @property {'left'|'center'|'right'} align
 *  @property {boolean} bold
 *  @property {boolean} italic
 */

/** @typedef {Object} GradientStop
 *  @property {number} offset   // 0.0 - 1.0
 *  @property {string} color
 */
```

### 6.3 SW工学原則の適用マップ

| 原則 | 適用箇所 | 設計判断 |
|------|----------|----------|
| **SRP** | 各モジュール | `VmlParser` = パースのみ, `SvgBuilder` = 生成のみ, `XmlFormatter` = 整形のみ |
| **OCP** | 図形タイプ拡張 | `parseXxx()` / `buildXxx()` の追加のみ。既存コード無修正 |
| **LSP** | ShapeModel | 全図形タイプが同一インターフェースを満たす |
| **ISP** | ClipboardReader | `readHtml()` と `readImage()` を分離 |
| **DIP** | Parser / Builder | App層は中間モデルにのみ依存 |
| **SoC** | レイヤー分離 | UI / フロー / ドメイン / I/O が完全分離 |
| **SLAP** | 関数内 | `convert()` 内は `parse()` → `build()` → `format()` の同一抽象度 |
| **DRY** | 共通関数 | `parseColor()`, `emuToPx()` を共通化 |
| **CQS** | Query/Command | `parse()` = Query（モデル返却）, `renderPreview()` = Command（DOM更新） |
| **LOD** | モジュール間 | `SvgBuilder` は `ShapeModel` のみ参照。VML内部構造を知らない |
| **POLA** | UI / 全体 | ペースト→全変換→表示。フィルタなしで驚きなし |
| **KISS** | 全体 | 単一HTML, 外部依存なし, フィルタなし |
| **YAGNI** | スコープ | SmartArt・3D・フィルタリング機能は作らない |
| **PIE** | コード | 型定義と命名で意図を明示 |
| **Naming** | 全体 | `GR SVG Extractor`, `VmlParser`, `SvgBuilder`, `XmlFormatter` |
| **CA** | 依存方向 | UI → App → Domain ← Infra |

---

## 7. 処理フロー

```
User: Ctrl+V
  │
  ▼
[ClipboardReader.readHtml(event)]
  │
  ├─ HTML取得成功
  │    │
  │    ▼
  │  [VmlParser.parse(html)]  ──→  ShapeModel[]
  │    │
  │    ▼
  │  [SvgBuilder.build(shapes)]  ──→  SVG string (raw)
  │    │
  │    ▼
  │  [XmlFormatter.format(svg)]  ──→  SVG string (整形済み)
  │
  ├─ HTML取得失敗
  │    │
  │    ▼
  │  [ClipboardReader.readImage(event)]  ──→  Base64 PNG
  │    │
  │    ▼
  │  [SvgBuilder.buildFromImage(base64)]  ──→  SVG string
  │    │
  │    ▼
  │  [XmlFormatter.format(svg)]
  │
  ▼
[UI.renderPreview(formattedSvg)]
[UI.displayText(formattedSvg)]
[UI.showActions()]                  ← コピー・ダウンロードボタン表示
[UI.updateStatus('変換完了')]

          ┌──────────────┐
User ──→  │ ［コピー］    │ ──→ Clipboard.writeText(svgText)
          │ ［DL］        │ ──→ FileDownloader.download(svgText, 'gr-svg-ext.svg')
          └──────────────┘
```

---

## 8. エラーハンドリング

| 状況 | 対処 | ユーザーへの表示 |
|------|------|-----------------|
| クリップボードにHTMLなし | PNGフォールバック | 「画像として取り込みました（ベクター変換不可）」 |
| クリップボードにデータなし | 処理中止 | 「貼り付けデータが見つかりません」 |
| VMLパース失敗 | PNGフォールバック | 「図形の解析に失敗。画像として取り込みます」 |
| PNGも取得不可 | 処理中止 | 「対応するデータ形式が見つかりません」 |
| 未対応図形タイプ | スキップして続行 | 「一部の図形は変換できませんでした」 |

---

## 9. ファイル構成

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>GR SVG Extractor</title>
  <style>
    /* ========== UI Styles ========== */
  </style>
</head>
<body>
  <!-- ========== UI Markup ========== -->

  <script>
  // ========== [Infrastructure] ClipboardReader ==========
  // ========== [Infrastructure] FileDownloader ==========
  // ========== [Domain] ShapeModel (JSDoc型定義) ==========
  // ========== [Domain] VmlParser ==========
  // ========== [Domain] SvgBuilder ==========
  // ========== [Domain] XmlFormatter ==========
  // ========== [Application] AppController ==========
  // ========== [UI] UIController ==========
  // ========== [Bootstrap] ==========
  </script>
</body>
</html>
```

---

## 10. 技術リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| PPTのクリップボード出力がブラウザ/OS/バージョンで異なる | VMLが取得できない環境 | PNGフォールバック常備。Chrome/Edge + Windows を推奨 |
| VML仕様のカバレッジ | 複雑な図形で変換精度低下 | 段階的に対応追加。未対応は明示的にスキップ |
| Clipboard API のブラウザ制限 | Firefox等で挙動差異 | `paste` イベントの同期APIを使用 |

---

## 11. 将来の拡張ポイント（v1.0では実装しない）

OCP に従い、中間モデルの拡張で対応可能な設計としておく。

- .pptx ファイルのドラッグ＆ドロップ入力（DrawingML パーサー追加）
- ファイル名のカスタマイズ
- 複数回ペーストの履歴管理
- テーマカラーの解決
