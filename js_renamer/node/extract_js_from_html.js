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
const source = args.source;
const target = args.target;

if (!source || !target) {
  console.error(
    "Usage: node extract_js_from_html.js --source input.html --target output.js",
  );
  process.exit(1);
}

// ============================
// Load HTML
// ============================
let html;
try {
  html = fs.readFileSync(source, "utf8");
} catch (e) {
  console.error(`[ERROR] Failed to read: ${source}`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Helper: Generate element selector
// ============================
function generateSelector(tagName, attrs, index) {
  const id = attrs.id;
  if (id) {
    return `${tagName}#${id}`;
  }
  return `${tagName}[${index}]`;
}

// ============================
// Helper: Parse attributes from tag
// ============================
function parseAttributes(tagString) {
  const attrs = {};
  // Handle double-quoted and single-quoted attribute values separately
  // to allow the opposite quote character inside each value
  const doubleQuotedRegex = /(\w+)\s*=\s*"([^"]*)"/g;
  const singleQuotedRegex = /(\w+)\s*=\s*'([^']*)'/g;
  let match;
  while ((match = doubleQuotedRegex.exec(tagString)) !== null) {
    attrs[match[1]] = match[2];
  }
  while ((match = singleQuotedRegex.exec(tagString)) !== null) {
    // Double-quoted value takes precedence if both exist for same attr
    if (!(match[1] in attrs)) {
      attrs[match[1]] = match[2];
    }
  }
  return attrs;
}

// ============================
// Extract <script> blocks
// ============================
const scriptRegex = /<script([^>]*)>([\s\S]*?)<\/script>/gi;
let match;
let blockId = 1;
const blocks = [];

while ((match = scriptRegex.exec(html)) !== null) {
  const attrs = parseAttributes(match[1]);
  const content = match[2];
  const fullTag = match[0];

  // Skip external scripts (src attribute)
  if (attrs.src) {
    console.log(`[INFO] Skipping external script (src="${attrs.src}")`);
    continue;
  }

  // Skip non-JavaScript types
  const scriptType = attrs.type ? attrs.type.toLowerCase() : "text/javascript";
  if (
    scriptType === "application/ld+json" ||
    scriptType === "application/json" ||
    scriptType === "importmap" ||
    (scriptType.startsWith("text/") && scriptType !== "text/javascript")
  ) {
    console.log(`[INFO] Skipping non-JavaScript script (type="${scriptType}")`);
    continue;
  }

  // Skip empty scripts
  if (!content.trim()) {
    console.log(`[INFO] Skipping empty script block`);
    continue;
  }

  const startPos = match.index;
  const endPos = startPos + fullTag.length;
  const startLine = html.substring(0, startPos).split(/\r?\n/).length;
  const endLine = html.substring(0, endPos).split(/\r?\n/).length;

  blocks.push({
    type: "BLOCK",
    id: blockId++,
    startLine,
    endLine,
    code: content,
    metadata: `BLOCK_${blockId - 1}_START`,
  });
}

console.log(`[INFO] Extracted ${blocks.length} script blocks`);

// ============================
// Extract inline event handlers
// ============================
const eventAttrs = [
  "onclick",
  "ondblclick",
  "onmousedown",
  "onmouseup",
  "onmouseover",
  "onmouseout",
  "onmousemove",
  "onkeydown",
  "onkeyup",
  "onkeypress",
  "onload",
  "onunload",
  "onsubmit",
  "onreset",
  "onchange",
  "onfocus",
  "onblur",
  "onselect",
];

const tagCounters = {};
let inlineId = 1;
const inlineBlocks = [];

for (const eventAttr of eventAttrs) {
  // Two alternations: double-quoted values may contain single quotes and vice versa
  const attrRegex = new RegExp(
    `<(\\w+)([^>]*?\\s+${eventAttr}\\s*=\\s*(?:"([^"]*)"|'([^']*)')[^>]*)>`,
    "gi",
  );
  let inlineMatch;

  while ((inlineMatch = attrRegex.exec(html)) !== null) {
    const tagName = inlineMatch[1].toLowerCase();
    const fullAttrs = inlineMatch[2];
    // Exactly one of the two capture groups will match
    const code = inlineMatch[3] !== undefined ? inlineMatch[3] : inlineMatch[4];

    // Skip empty handlers
    if (!code || !code.trim()) {
      continue;
    }

    // Parse attributes to get ID
    const attrs = parseAttributes(fullAttrs);

    // Track tag index
    if (!tagCounters[tagName]) {
      tagCounters[tagName] = 0;
    }
    tagCounters[tagName]++;

    const selector = generateSelector(
      tagName,
      attrs,
      tagCounters[tagName] - 1,
    );

    inlineBlocks.push({
      type: "INLINE",
      id: inlineId++,
      event: eventAttr,
      selector: selector,
      code: code,
      metadata: `INLINE_${inlineId - 1}_START ${eventAttr} ${selector}`,
    });
  }
}

console.log(`[INFO] Extracted ${inlineBlocks.length} inline handlers`);

// ============================
// Build unified JavaScript
// ============================
const allBlocks = [...blocks, ...inlineBlocks];
let output = "";

for (const block of allBlocks) {
  if (block.type === "BLOCK") {
    output += `//[[${block.metadata}]]\n`;
    output += block.code;
    output += `\n//[[BLOCK_${block.id}_END]]\n\n`;
  } else if (block.type === "INLINE") {
    output += `//[[${block.metadata}]]\n`;
    output += block.code;
    output += `\n//[[INLINE_${block.id}_END]]\n\n`;
  }
}

// ============================
// Write output
// ============================
try {
  const dir = path.dirname(target);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(target, output, "utf8");
  console.log(
    `[INFO] Extracted ${allBlocks.length} JavaScript blocks to ${target}`,
  );
  console.log(
    `[INFO] - ${blocks.length} script blocks, ${inlineBlocks.length} inline handlers`,
  );
} catch (e) {
  console.error(`[ERROR] Failed to write: ${target}`);
  console.error(e.message);
  process.exit(1);
}

process.exit(0);
