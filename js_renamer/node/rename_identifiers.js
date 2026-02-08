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

// Attach comments for escodegen
ast = escodegen.attachComments(ast, ast.comments, ast.tokens);

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
// Phase 2: Load TSV
// ============================
let tsvContent;
try {
  tsvContent = fs.readFileSync(table, "utf8");
} catch (e) {
  logError(`Failed to read TSV: ${table}`);
  process.exit(1);
}

const renameMap = new Map(); // Key: "scopeId::oldName", Value: "newName"
const lines = tsvContent.split(/\r?\n/).slice(1); // Skip header

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (!line.trim()) continue;

  const cols = line.split("\t");
  // Expected columns: file_name, loc_start, loc_end, collision_type, kind, scope, old_name, new_name
  if (cols.length < 8) continue;

  const scope = cols[5];
  const oldName = cols[6];
  const newName = cols[7];

  // We only care if new_name is provided by the user
  if (newName && newName.trim() !== "") {
    const key = `${scope}::${oldName}`;
    renameMap.set(key, newName.trim());
  }
}

logInfo(`Loaded ${renameMap.size} rename entries from TSV`);

// ============================
// Helper Functions
// ============================
function makeScopeId(scope, ast) {
  const parts = [];
  parts.push(scope.type);
  parts.push(getScopeName(scope) || "");
  parts.push(getASTPath(scope.block, ast));
  return parts.join("|");
}

function getScopeName(scope) {
  const block = scope.block;
  if (block.id && block.id.name) return block.id.name;
  if (block.type === "Program") return "global";
  return null;
}

function getASTPath(node, root) {
  function traverse(current, currentPath) {
    if (current === node) return currentPath;
    for (const key in current) {
      const value = current[key];
      if (Array.isArray(value)) {
        for (let i = 0; i < value.length; i++) {
          if (typeof value[i] === "object" && value[i] !== null) {
            const result = traverse(value[i], [...currentPath, key, i]);
            if (result) return result;
          }
        }
      } else if (typeof value === "object" && value !== null) {
        const result = traverse(value, [...currentPath, key]);
        if (result) return result;
      }
    }
    return null;
  }
  const foundPath = traverse(root, []);
  return foundPath ? foundPath.join(".") : "";
}

// ============================
// Phase 3: Build Node Rename Map
// ============================
const nodeRenameMap = new Map(); // key: Identifier Node, value: string (newName)
let successCount = 0;
let collisionCount = 0;

// Helper to check for collisions in the same scope
function isNameDefinedInScope(scope, name) {
  for (const v of scope.variables) {
    if (v.name === name) {
      return true;
    }
  }
  return false;
}

// Deduplication map to ensure we process a variable only once per scope
const processedVariables = new Set();

for (const scope of scopeManager.scopes) {
  const scopeId = makeScopeId(scope, ast);

  for (const variable of scope.variables) {
    // Unique ID for this variable instance in this scope
    const varKey = `${scopeId}::${variable.name}`;

    // Skip if we already processed this variable (though scope loop should be unique)
    if (processedVariables.has(varKey)) continue;
    processedVariables.add(varKey);

    // Check if there is a rename rule for this variable
    if (renameMap.has(varKey)) {
      const newName = renameMap.get(varKey);

      // 1. Scope Collision Check
      // Ensure we don't rename 'a' to 'b' if 'b' already exists in the same scope.
      // This prevents syntax errors (redeclaration) or logic errors (shadowing merges).
      if (isNameDefinedInScope(scope, newName)) {
        logWarn(
          `Skipped renaming '${variable.name}' -> '${newName}' in scope '${scopeId}'. Reason: '${newName}' is already defined in this scope.`,
        );
        collisionCount++;
        continue;
      }

      // 2. Apply Rename
      // We rename the definition and ALL references.

      // Rename definition(s)
      variable.defs.forEach((def) => {
        if (def.name) {
          nodeRenameMap.set(def.name, newName);
        }
      });

      // Rename references
      variable.references.forEach((ref) => {
        if (ref.identifier) {
          nodeRenameMap.set(ref.identifier, newName);
        }
      });

      successCount++;
    }
  }
}

logInfo(`Prepared ${successCount} variables for renaming.`);
logInfo(`Skipped ${collisionCount} variables due to scope collisions.`);

// ============================
// Phase 4: Execute Rename
// ============================
estraverse.replace(ast, {
  enter: function (node) {
    if (node.type === "Identifier" && nodeRenameMap.has(node)) {
      const newName = nodeRenameMap.get(node);
      // Create a new node to ensure clean replacement
      return {
        ...node,
        name: newName,
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
      indent: {
        style: "    ", // Default 4 spaces, can be adjusted
      },
      quotes: "auto",
    },
  });

  const dir = path.dirname(target);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(target, outputCode, "utf8");
  logInfo(`Successfully wrote transformed code to ${target}`);
} catch (e) {
  logError(`Code generation failed: ${e.message}`);
  writeLog();
  process.exit(1);
}

writeLog();
process.exit(0);
