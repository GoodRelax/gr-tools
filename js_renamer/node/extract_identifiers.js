#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const espree = require("espree");
const eslintScope = require("eslint-scope");
const estraverse = require("estraverse");
const os = require("os");
const minimist = require("minimist");

// ============================
// CLI Args
// ============================
const args = minimist(process.argv.slice(2));
const source = args.source;
const output = args.output;

if (!source || !output) {
  console.error(
    "Usage: node extract_identifiers.js --source input.js --output table.tsv",
  );
  process.exit(1);
}

// ============================
// Load JS
// ============================
let code;
try {
  code = fs.readFileSync(source, "utf8");
} catch (e) {
  console.error(`[ERROR] Failed to read: ${source}`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Parse AST
// ============================
let ast;
try {
  ast = espree.parse(code, {
    ecmaVersion: "latest",
    sourceType: "module", // Support ES modules for export detection
    loc: true,
    range: true,
  });
} catch (e) {
  console.error(`[ERROR] Parse error in ${source}:`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Pre-scan: Usage Analysis
// ============================
// We need to identify variables used in "shorthand" properties or "exports"
// before we iterate through the scopes.

const shorthandUsages = new Set(); // Names used in { x } or { x } = y
const exportedNames = new Set(); // Names that are exported

estraverse.traverse(ast, {
  enter: function (node) {
    // 1. Detect Shorthand Properties
    // e.g. const obj = { id }; or const { id } = obj;
    if (node.type === "Property" && node.shorthand) {
      if (node.key && node.key.type === "Identifier") {
        shorthandUsages.add(node.key.name);
      }
    }

    // 2. Detect Exports
    // e.g. export const x = 1; or export { x };
    if (node.type === "ExportNamedDeclaration") {
      if (node.declaration) {
        // export const x = ...
        if (node.declaration.declarations) {
          node.declaration.declarations.forEach((decl) => {
            if (decl.id.type === "Identifier") {
              exportedNames.add(decl.id.name);
            }
          });
        }
        // export function f() ...
        if (node.declaration.id && node.declaration.id.type === "Identifier") {
          exportedNames.add(node.declaration.id.name);
        }
      }
      if (node.specifiers) {
        // export { x };
        node.specifiers.forEach((spec) => {
          if (spec.local && spec.local.type === "Identifier") {
            exportedNames.add(spec.local.name);
          }
        });
      }
    }
  },
});

// ============================
// Scope Analysis
// ============================
let scopeManager;
try {
  scopeManager = eslintScope.analyze(ast, {
    ecmaVersion: 2022,
    sourceType: "module",
  });
} catch (e) {
  console.error(`[ERROR] Scope analysis failed:`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Helper: makeScopeId
// ============================
function makeScopeId(scope, ast) {
  const parts = [];
  // 1. Scope type
  parts.push(scope.type);
  // 2. Scope name (if exists)
  parts.push(getScopeName(scope) || "");
  // 3. AST path
  parts.push(getASTPath(scope.block, ast));

  return parts.join("|");
}

// ============================
// Helper: getScopeName
// ============================
function getScopeName(scope) {
  const block = scope.block;
  if (block.id && block.id.name) {
    return block.id.name;
  }
  if (block.type === "Program") {
    return "global";
  }
  return null;
}

// ============================
// Helper: getASTPath
// ============================
function getASTPath(node, root) {
  function traverse(current, currentPath) {
    if (current === node) {
      return currentPath;
    }
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
// Helper: determineKind
// ============================
function determineKind(variable, scope) {
  const def = variable.defs[0];
  if (!def) {
    return "implicit-global";
  }
  switch (def.type) {
    case "Variable":
      return scope.type === "global" || scope.type === "module"
        ? "global/module"
        : "local";
    case "Parameter":
      return "param";
    case "FunctionName":
      return "function";
    case "ClassName":
      return "class";
    case "ImportBinding":
      return "import";
    case "CatchClause":
      return "catch";
    default:
      return "other";
  }
}

// ============================
// Logic: Determine Collision Type
// ============================
function determineCollisionType(variableName, scope) {
  // Priority 1: Shorthand (Most Dangerous)
  // If the variable name is used in a shorthand property anywhere,
  // renaming it effectively changes the property key, breaking contracts.
  if (shorthandUsages.has(variableName)) {
    return "shorthand";
  }

  // Priority 2: Export
  // If the variable is exported, renaming it breaks external imports.
  if (exportedNames.has(variableName)) {
    return "export";
  }

  // Priority 3: Global / Module Scope
  // If it's top-level, it might be accessed by other files or scripts.
  if (scope.type === "global" || scope.type === "module") {
    return "global";
  }

  // Safe to rename
  return "none";
}

// ============================
// TSV Generation
// ============================
const rows = [];
// Header
rows.push(
  [
    "file_name",
    "loc_start",
    "loc_end",
    "collision_type", // New column for human filtering
    "kind",
    "scope",
    "old_name",
    "new_name",
  ].join("\t"),
);

let totalScopes = 0;
let totalVariables = 0;
let skippedVariables = 0;
const processedDefs = new Set();

for (const scope of scopeManager.scopes) {
  totalScopes++;
  const scopeId = makeScopeId(scope, ast);

  for (const variable of scope.variables) {
    totalVariables++;
    const def = variable.defs[0];

    // Skip variables without definitions (e.g., global access like 'console')
    if (!def || !def.name || !def.name.loc) {
      skippedVariables++;
      continue;
    }

    // Deduplication: Process each definition only once
    if (processedDefs.has(def.node)) {
      continue;
    }
    processedDefs.add(def.node);

    const locStart = `${def.name.loc.start.line}:${def.name.loc.start.column}`;
    const locEnd = `${def.name.loc.end.line}:${def.name.loc.end.column}`;
    const kind = determineKind(variable, scope);

    // Determine the risk level
    const collisionType = determineCollisionType(variable.name, scope);

    rows.push(
      [
        path.basename(source),
        locStart,
        locEnd,
        collisionType, // Value: shorthand, export, global, or none
        kind,
        scopeId,
        variable.name,
        "", // new_name is empty by default
      ].join("\t"),
    );
  }
}

console.log(
  `[INFO] Processed ${totalScopes} scopes, ${totalVariables} variables`,
);
console.log(`[INFO] Extracted ${rows.length - 1} identifiers`);

// ============================
// Write Output
// ============================
try {
  const dir = path.dirname(output);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(output, rows.join(os.EOL), "utf8");
  console.log(`[INFO] Wrote TSV to ${output}`);
} catch (e) {
  console.error(`[ERROR] Failed to write: ${output}`);
  console.error(e.message);
  process.exit(1);
}

process.exit(0);
