#!/usr/bin/env node

// ============================
// Dependencies
// ============================
const fs = require("fs");
const path = require("path");
const minimist = require("minimist");

// ============================
// CLI Args
// ============================
const args = minimist(process.argv.slice(2));
const jsPath = args.js;
const sourcePath = args.source;
const targetPath = args.target;

if (!jsPath || !sourcePath || !targetPath) {
  console.error(
    "Usage: node reintegrate_to_html.js --js transformed.js --source source.html --target output.html",
  );
  process.exit(1);
}

// ============================
// Load transformed JS
// ============================
let transformedJs;
try {
  transformedJs = fs.readFileSync(jsPath, "utf8");
} catch (e) {
  console.error(`[ERROR] Failed to read transformed JS: ${jsPath}`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Load original HTML
// ============================
let originalHtml;
try {
  originalHtml = fs.readFileSync(sourcePath, "utf8");
} catch (e) {
  console.error(`[ERROR] Failed to read source HTML: ${sourcePath}`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Parse metadata blocks from transformed JS
// ============================
const blockStartRegex = /^\/\/\[\[(BLOCK|INLINE)_(\d+)_START(.*)\]\]$/gm;
const blocks = [];
let match;

while ((match = blockStartRegex.exec(transformedJs)) !== null) {
  const blockType = match[1]; // BLOCK or INLINE
  const blockId = parseInt(match[2]);
  const metadata = match[3].trim(); // Additional metadata for inline blocks

  const startPos = match.index + match[0].length;
  const endMarker = `//[[${blockType}_${blockId}_END]]`;
  const endPos = transformedJs.indexOf(endMarker, startPos);

  if (endPos === -1) {
    console.warn(
      `[WARN] Missing end marker for ${blockType}_${blockId}, skipping`,
    );
    continue;
  }

  const code = transformedJs.substring(startPos, endPos).trim();

  if (blockType === "BLOCK") {
    blocks.push({
      type: "BLOCK",
      id: blockId,
      code: code,
    });
  } else if (blockType === "INLINE") {
    // Parse metadata: "event selector"
    const metaParts = metadata.split(/\s+/);
    const event = metaParts[0] || "";
    const selector = metaParts.slice(1).join(" ") || "";

    blocks.push({
      type: "INLINE",
      id: blockId,
      event: event,
      selector: selector,
      code: code,
    });
  }
}

console.log(`[INFO] Parsed ${blocks.length} blocks from transformed JS`);
console.log(
  `[INFO] - ${blocks.filter((b) => b.type === "BLOCK").length} script blocks`,
);
console.log(
  `[INFO] - ${blocks.filter((b) => b.type === "INLINE").length} inline handlers`,
);

// ============================
// Helper: Escape regex special chars
// ============================
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ============================
// Reintegrate script blocks
// ============================
let outputHtml = originalHtml;
const scriptBlocks = blocks.filter((b) => b.type === "BLOCK");

// Sort by ID descending to replace from end to start (preserves positions)
scriptBlocks.sort((a, b) => b.id - a.id);

let scriptIndex = 0;
const scriptRegex = /<script([^>]*)>([\s\S]*?)<\/script>/gi;
const scriptMatches = [];

// First, find all script tags
let scriptMatch;
while ((scriptMatch = scriptRegex.exec(originalHtml)) !== null) {
  scriptMatches.push({
    index: scriptIndex++,
    fullMatch: scriptMatch[0],
    attrs: scriptMatch[1],
    content: scriptMatch[2],
    startPos: scriptMatch.index,
    endPos: scriptMatch.index + scriptMatch[0].length,
  });
}

console.log(`[INFO] Found ${scriptMatches.length} script tags in HTML`);

// Replace script blocks by sequential ID (1-indexed)
for (const block of scriptBlocks) {
  const matchIndex = block.id - 1; // Convert 1-indexed to 0-indexed
  if (matchIndex >= 0 && matchIndex < scriptMatches.length) {
    const scriptMatch = scriptMatches[matchIndex];
    const newScript = `<script${scriptMatch.attrs}>\n${block.code}\n</script>`;

    // Replace in output HTML (using position)
    outputHtml =
      outputHtml.substring(0, scriptMatch.startPos) +
      newScript +
      outputHtml.substring(scriptMatch.endPos);

    // Adjust positions of remaining matches
    const lengthDiff = newScript.length - scriptMatch.fullMatch.length;
    for (let i = matchIndex + 1; i < scriptMatches.length; i++) {
      scriptMatches[i].startPos += lengthDiff;
      scriptMatches[i].endPos += lengthDiff;
    }

    console.log(`[INFO] Replaced script block ${block.id}`);
  } else {
    console.warn(
      `[WARN] Could not find script tag for block ${block.id} (index ${matchIndex})`,
    );
  }
}

// ============================
// Reintegrate inline handlers
// ============================
const inlineBlocks = blocks.filter((b) => b.type === "INLINE");

for (const block of inlineBlocks) {
  const event = block.event;
  const selector = block.selector;
  const newCode = block.code;

  // Parse selector
  let tagName = "";
  let elementId = "";
  let elementIndex = -1;

  if (selector.includes("#")) {
    // Format: tagName#id
    const parts = selector.split("#");
    tagName = parts[0];
    elementId = parts[1];
  } else if (selector.includes("[")) {
    // Format: tagName[index]
    const match = selector.match(/^(\w+)\[(\d+)\]$/);
    if (match) {
      tagName = match[1];
      elementIndex = parseInt(match[2]);
    }
  }

  if (!tagName || !event) {
    console.warn(`[WARN] Invalid inline block metadata: ${event} ${selector}`);
    continue;
  }

  // Find and replace inline handler
  if (elementId) {
    // Replace by ID
    // Two passes: one for double-quoted attributes, one for single-quoted
    // Each pass allows the opposite quote character inside the value
    let replaced = outputHtml;

    const dqRegex = new RegExp(
      `(<${tagName}[^>]*?\\bid\\s*=\\s*["']${escapeRegex(elementId)}["'][^>]*?\\s+${event}\\s*=\\s*")([^"]*)(\"[^>]*>)`,
      "gi",
    );
    replaced = replaced.replace(dqRegex, `$1${newCode}$3`);

    if (replaced === outputHtml) {
      const sqRegex = new RegExp(
        `(<${tagName}[^>]*?\\bid\\s*=\\s*["']${escapeRegex(elementId)}["'][^>]*?\\s+${event}\\s*=\\s*')([^']*)('[^>]*>)`,
        "gi",
      );
      replaced = replaced.replace(sqRegex, `$1${newCode}$3`);
    }

    if (replaced !== outputHtml) {
      console.log(
        `[INFO] Replaced inline handler: ${event} on ${tagName}#${elementId}`,
      );
      outputHtml = replaced;
    } else {
      console.warn(
        `[WARN] Could not find inline handler: ${event} on ${tagName}#${elementId}`,
      );
    }
  } else if (elementIndex >= 0) {
    // Replace by index
    // Two passes: one for double-quoted attributes, one for single-quoted
    let currentIndex = 0;
    const beforeReplace = outputHtml;

    const dqRegex = new RegExp(
      `<${tagName}([^>]*?\\s+${event}\\s*=\\s*")([^"]*)("[^>]*)>`,
      "gi",
    );
    outputHtml = outputHtml.replace(dqRegex, (match, p1, p2, p3) => {
      if (currentIndex === elementIndex) {
        currentIndex++;
        console.log(
          `[INFO] Replaced inline handler: ${event} on ${tagName}[${elementIndex}]`,
        );
        return `<${tagName}${p1}${newCode}${p3}>`;
      }
      currentIndex++;
      return match;
    });

    if (outputHtml === beforeReplace) {
      currentIndex = 0;
      const sqRegex = new RegExp(
        `<${tagName}([^>]*?\\s+${event}\\s*=\\s*')([^']*)('[^>]*)>`,
        "gi",
      );
      outputHtml = outputHtml.replace(sqRegex, (match, p1, p2, p3) => {
        if (currentIndex === elementIndex) {
          currentIndex++;
          console.log(
            `[INFO] Replaced inline handler: ${event} on ${tagName}[${elementIndex}]`,
          );
          return `<${tagName}${p1}${newCode}${p3}>`;
        }
        currentIndex++;
        return match;
      });
    }
  }
}

// ============================
// Write output HTML
// ============================
try {
  const dir = path.dirname(targetPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(targetPath, outputHtml, "utf8");
  console.log(
    `[INFO] Successfully reintegrated ${blocks.length} blocks into ${targetPath}`,
  );
} catch (e) {
  console.error(`[ERROR] Failed to write: ${targetPath}`);
  console.error(e.message);
  process.exit(1);
}

process.exit(0);
