---
layout: default
---

# gr-tools

A collection of utility tools by GoodRelax designed to enhance development workflows and text processing efficiency.

## ⚡ Quick Access

[🌐 gr-url-endeco](./gr-url-endeco/)&nbsp;&nbsp;  
[🗺️ grtm2cd](./grtm2cd/)&nbsp;&nbsp;  
[🖼️ gr-svg-extractor](./gr-svg-extractor/)&nbsp;&nbsp;  
[📂 js_renamer](./js_renamer/)&nbsp;&nbsp;  
[📂 cat_files](./cat_files/)&nbsp;&nbsp;

<br>

---

## Description

### [🌐 gr-url-endeco](./gr-url-endeco/)

#### Overview

**Secure Browser-Based URL Encoder/Decoder**
A privacy-focused HTML tool that runs entirely on the client side. No data is sent to external servers, making it safe for handling sensitive strings.

#### Platform / Requirements

- Web Browser (Chrome, Edge, Firefox, Safari, etc.)

#### Details

[Go to gr-url-endeco >](./gr-url-endeco/)

<br>

### [🗺️ grtm2cd](./grtm2cd/)

#### Overview

**Treasure Map to Cat and Dog — Steganographic File Splitter**
A zero-server, single-page web tool that hides any binary file (the "Treasure Map")  
inside two ordinary PNG images (Cat and Dog) using AES-256-GCM encryption and LSB embedding.  
Neither image alone can recover the payload.

#### Platform / Requirements

- Web Browser (Chrome 90+, Firefox 88+, Safari 16.4+)

#### Details

[Go to grtm2cd >](./grtm2cd/)

<br>

### [🖼️ gr-svg-extractor](./gr-svg-extractor/)

#### Overview

**PowerPoint to SVG Extractor**
A lightweight, single-file web tool that extracts clean, formatted SVGs directly from clipboard data (copied shapes from PowerPoint/Excel). Includes dark mode automation.

#### Platform / Requirements

- Web Browser (Chrome / Edge recommended)

#### Details

[Go to gr-svg-extractor >](./gr-svg-extractor/)

<br>

### [📂 js_renamer](./js_renamer/)

#### Overview

**[Alpha] Safe JavaScript Renamer for HTML**
An AST-based utility to safely rename JavaScript identifiers (variables, functions) embedded within HTML files without breaking scope or logic.

#### Platform / Requirements

- Windows (Batch)
- **Node.js (v18 or higher)**

#### Details

[Go to js_renamer >](./js_renamer/)

<br>

### [📂 cat_files](./cat_files/)

#### Overview

**File Concatenator for LLM Context**
A CLI tool that merges multiple source code or log files into a single document with metadata tags.

#### Platform / Requirements

- Windows (Batch)
- _(Optional: PowerShell for UTF-8/LF normalization)_

#### Details

[Go to cat_files >](./cat_files/)

## <br>

## Japanese Description

開発作業やテキスト処理を効率化するための、GoodRelax作のユーティリティツールセットです。

### [🌐 gr-url-endeco](./gr-url-endeco/)

#### 概要

**セキュアなURLエンコーダー/デコーダー**
完全クライアントサイド（ブラウザのみ）で動作するHTMLツールです。外部サーバーにデータを送信しないため、機密情報の取り扱いにも適しています。

#### 動作環境 / 必須要件

- Webブラウザ (Chrome, Edge, Firefox, Safari 等)

#### 詳細

[gr-url-endeco のフォルダへ >](./gr-url-endeco/)

<br>

### [🗺️ grtm2cd](./grtm2cd/)

#### 概要

**宝の地図をネコとイヌに — ステガノグラフィ分割ツール**
任意のバイナリファイル（宝の地図）を2枚のPNG画像（ネコとイヌ）にAES-256-GCM暗号化＋LSB埋め込みで隠すWebツールです。  
サーバー通信なし、ブラウザだけで完結します。1枚の画像だけではデータを復元できません。

#### 動作環境 / 必須要件

- Webブラウザ (Chrome 90+, Firefox 88+, Safari 16.4+)

#### 詳細

[grtm2cd のフォルダへ >](./grtm2cd/)

<br>

### [🖼️ gr-svg-extractor](./gr-svg-extractor/)

#### 概要

**PowerPoint用 SVG抽出ツール**
PowerPointやExcelでコピーした図形データを、きれいなSVGコードとして抽出する単一ファイルのWebツールです。ダークモード用SVGも作成可能です。

#### 動作環境 / 必須要件

- Webブラウザ (Chrome / Edge 推奨)

#### 詳細

[gr-svg-extractor のフォルダへ >](./gr-svg-extractor/)

<br>

### [📂 js_renamer](./js_renamer/)

#### 概要

**[Alpha] HTML内JavaScriptリネームツール**
HTMLファイル内に埋め込まれたJavaScriptの変数や関数名を、AST（抽象構文木）解析を用いて安全に置換します。単純置換によるコード破壊を防ぎます。

#### 動作環境 / 必須要件

- Windows (バッチファイル)
- **Node.js (v18 以上)**

#### 詳細

[js_renamer のフォルダへ >](./js_renamer/)

<br>

### [📂 cat_files](./cat_files/)

#### 概要

**ファイル結合ツール**
指定したディレクトリ内のソースコードやログを、ファイルパスのメタデータ付きで1つのテキストファイルに結合します。

#### 動作環境 / 必須要件

- Windows (バッチファイル)
- _(オプション: UTF-8/LF変換を利用する場合はPowerShellが必要)_

#### 詳細

[cat_files のフォルダへ >](./cat_files/)

<br>

---

## 📜 License

(c) 2026 GoodRelax.
All tools in this repository are released under the [MIT License](./LICENSE).
