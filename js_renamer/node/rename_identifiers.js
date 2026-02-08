#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const espree = require("espree");
const eslintScope = require("eslint-scope");
const estraverse = require("estraverse");
const escodegen = require("escodegen");
const os = require("os");
const minimist = require("minimist");

// ============================
// CLI Args
// ============================
const args = minimist(process.argv.slice(2));
const source = args.source;
const table = args.table;
const target = args.target;
const logPath = args.log;

if (!source || !table || !target || !logPath) {
  console.error(
    "Usage: node rename_identifiers.js --source input.js --table table.tsv --target out.js --log log.txt",
  );
  process.exit(1);
}

// ============================
// Logger
// ============================
const logLines = [];
function logInfo(msg) {
  const line = `[INFO]  ${new Date().toISOString()} ${msg}`;
  logLines.push(line);
  console.log(line);
}
function logWarn(msg) {
  const line = `[WARN]  ${new Date().toISOString()} ${msg}`;
  logLines.push(line);
  console.warn(line);
}
function logError(msg) {
  const line = `[ERROR] ${new Date().toISOString()} ${msg}`;
  logLines.push(line);
  console.error(line);
}
function writeLog() {
  try {
    fs.writeFileSync(logPath, logLines.join(os.EOL), "utf8");
  } catch (e) {
    console.error(`[ERROR] Failed to write log: ${logPath}`);
  }
}

// ============================
// Phase 1: Load and Parse JS
// ============================
let code;
try {
  code = fs.readFileSync(source, "utf8");
} catch (e) {
  logError(`Failed to read source: ${source}`);
  process.exit(1);
}

let ast;
try {
  ast = espree.parse(code, {
    ecmaVersion: "latest",
    sourceType: "module",
    loc: true,
    range: true,
    comment: true,
    tokens: true,
  });
} catch (e) {
  logError(`Parse error in source: ${e.message}`);
  writeLog();
  process.exit(1);
}

ast = escodegen.attachComments(ast, ast.comments, ast.tokens);

// ============================
// Attach Parent Pointers
// ============================
estraverse.traverse(ast, {
  enter: function (node, parent) {
    node.parent = parent;
  },
});

let scopeManager;
try {
  scopeManager = eslintScope.analyze(ast, {
    ecmaVersion: 2022,
    sourceType: "module",
  });
} catch (e) {
  logError(`Scope analysis failed: ${e.message}`);
  writeLog();
  process.exit(1);
}

// ============================
// Helper: Readable Scope ID
// (MUST EXACTLY MATCH extract_identifiers.js)
// ============================
function makeScopeId(scope) {
  const chain = [];
  let current = scope;

  while (current) {
    const name = getSemanticScopeName(current);
    if (name) {
      chain.unshift(name);
    }
    current = current.upper;
  }

  return chain.join(" | ");
}

function getSemanticScopeName(scope) {
  if (scope.type === "global" || scope.type === "module") {
    return "Global";
  }

  const block = scope.block;

  // FIX: Skip redundant Block scopes that are children of For/ForIn/ForOf scopes
  if (
    block.type === "BlockStatement" &&
    scope.upper &&
    scope.upper.block === block.parent
  ) {
    const pType = block.parent.type;
    if (
      pType === "ForStatement" ||
      pType === "ForInStatement" ||
      pType === "ForOfStatement"
    ) {
      return null;
    }
  }

  // 1. Explicitly Named
  if (block.id && block.id.name) {
    return `${getTypePrefix(scope)}:${block.id.name}`;
  }

  // 2. Inferred
  const inferredName = inferNameFromParent(block);
  if (inferredName) {
    return `${getTypePrefix(scope)}:${inferredName}`;
  }

  // 3. Callback Context
  const callbackContext = inferCallbackContext(block);
  if (callbackContext) {
    const index = getScopeIndex(scope);
    return `${callbackContext} > Arg:${index}`;
  }

  // 4. Anonymous/Control Flow
  let type = getTypePrefix(scope);
  if (type === "Block" || type === "Scope") {
    type = getControlFlowType(block);
  }

  const index = getScopeIndex(scope);
  return `${type}:${index}`;
}

function getTypePrefix(scope) {
  const block = scope.block;
  if (
    block.type === "FunctionExpression" ||
    block.type === "ArrowFunctionExpression" ||
    block.type === "FunctionDeclaration"
  ) {
    if (block.parent && block.parent.type === "PropertyDefinition") {
      return "Field";
    }
    return "Func";
  }
  if (scope.type === "class") return "Class";
  if (scope.type === "catch") return "Catch";
  return "Block";
}

function getControlFlowType(node) {
  switch (node.type) {
    case "IfStatement":
      return "If";
    case "SwitchStatement":
      return "Switch";
    case "CatchClause":
      return "Catch";
    case "ForStatement":
      return "For";
    case "ForInStatement":
      return "ForIn";
    case "ForOfStatement":
      return "ForOf";
    case "WhileStatement":
      return "While";
    case "DoWhileStatement":
      return "DoWhile";
  }

  if (node.type === "BlockStatement" && node.parent) {
    switch (node.parent.type) {
      case "IfStatement":
        return "If";
      case "ForStatement":
        return "For";
      case "ForInStatement":
        return "ForIn";
      case "ForOfStatement":
        return "ForOf";
      case "WhileStatement":
        return "While";
      case "DoWhileStatement":
        return "DoWhile";
      case "TryStatement":
        return "Try";
      case "CatchClause":
        return "Catch";
      case "SwitchStatement":
        return "Switch";
    }
  }

  return "Block";
}

function inferNameFromParent(node) {
  if (!node.parent) return null;
  if (
    node.parent.type === "VariableDeclarator" &&
    node.parent.id.type === "Identifier"
  ) {
    return node.parent.id.name;
  }
  if (
    node.parent.type === "AssignmentExpression" &&
    node.parent.left.type === "MemberExpression"
  ) {
    if (node.parent.left.property.type === "Identifier") {
      return node.parent.left.property.name;
    }
  }
  if (
    node.parent.type === "Property" &&
    node.parent.key.type === "Identifier"
  ) {
    return node.parent.key.name;
  }
  if (
    node.parent.type === "MethodDefinition" &&
    node.parent.key.type === "Identifier"
  ) {
    return node.parent.key.name;
  }
  if (
    node.parent.type === "PropertyDefinition" &&
    node.parent.key.type === "Identifier"
  ) {
    return node.parent.key.name;
  }
  return null;
}

function inferCallbackContext(node) {
  if (!node.parent) return null;
  if (node.parent.type === "CallExpression") {
    if (node.parent.callee.type === "Identifier") {
      return `Call:${node.parent.callee.name}`;
    }
    if (
      node.parent.callee.type === "MemberExpression" &&
      node.parent.callee.property.type === "Identifier"
    ) {
      return `Call:${node.parent.callee.property.name}`;
    }
  }
  return null;
}

function getScopeIndex(scope) {
  if (!scope.upper) return 0;
  return scope.upper.childScopes.indexOf(scope);
}

// ============================
// Phase 2: Load TSV
// ============================
let tsvContent;
try {
  tsvContent = fs.readFileSync(table, "utf8");
} catch (e) {
  logError(`Failed to read TSV: ${table}`);
  process.exit(1);
}

const renameMap = new Map();
const lines = tsvContent.split(/\r?\n/).slice(1);

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (!line.trim()) continue;

  const cols = line.split("\t");
  if (cols.length < 8) continue;

  const scope = cols[5];
  const oldName = cols[6];
  const newName = cols[7];

  if (newName && newName.trim() !== "") {
    const key = `${scope}::${oldName}`;
    renameMap.set(key, newName.trim());
  }
}

logInfo(`Loaded ${renameMap.size} rename entries from TSV`);

// ============================
// Phase 3: Build Node Rename Map
// ============================
const nodeRenameMap = new Map();
let successCount = 0;
let collisionCount = 0;

function isNameDefinedInScope(scope, name) {
  for (const v of scope.variables) {
    if (v.name === name) return true;
  }
  return false;
}

const processedVariables = new Set();

for (const scope of scopeManager.scopes) {
  const scopeId = makeScopeId(scope);

  for (const variable of scope.variables) {
    const varKey = `${scopeId}::${variable.name}`;

    if (processedVariables.has(varKey)) continue;
    processedVariables.add(varKey);

    if (renameMap.has(varKey)) {
      const newName = renameMap.get(varKey);

      if (isNameDefinedInScope(scope, newName)) {
        logWarn(
          `Skipped '${variable.name}' -> '${newName}' in '${scopeId}'. Collision detected.`,
        );
        collisionCount++;
        continue;
      }

      variable.defs.forEach((def) => {
        if (def.name) nodeRenameMap.set(def.name, newName);
      });
      variable.references.forEach((ref) => {
        if (ref.identifier) nodeRenameMap.set(ref.identifier, newName);
      });

      successCount++;
    }
  }
}

logInfo(`Prepared ${successCount} variables for renaming.`);
logInfo(`Skipped ${collisionCount} collisions.`);

// ============================
// Phase 4: Execute Rename
// ============================
estraverse.replace(ast, {
  enter: function (node) {
    if (node.type === "Identifier" && nodeRenameMap.has(node)) {
      return {
        ...node,
        name: nodeRenameMap.get(node),
      };
    }
  },
});

// ============================
// Phase 5: Generate Output
// ============================
try {
  const outputCode = escodegen.generate(ast, {
    comment: true,
    format: {
      indent: { style: "    " },
      quotes: "auto",
    },
  });

  const dir = path.dirname(target);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(target, outputCode, "utf8");
  logInfo(`Successfully wrote to ${target}`);
} catch (e) {
  logError(`Code generation failed: ${e.message}`);
  writeLog();
  process.exit(1);
}

writeLog();
process.exit(0);
