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
    sourceType: "module",
    loc: true,
    range: true,
  });
} catch (e) {
  console.error(`[ERROR] Parse error in ${source}:`);
  console.error(e.message);
  process.exit(1);
}

// ============================
// Attach Parent Pointers
// ============================
estraverse.traverse(ast, {
  enter: function (node, parent) {
    node.parent = parent;
  },
});

// ============================
// Pre-scan: Usage Analysis
// ============================
const shorthandUsages = new Set();
const exportedNames = new Set();

estraverse.traverse(ast, {
  enter: function (node) {
    if (node.type === "Property" && node.shorthand) {
      if (node.key && node.key.type === "Identifier") {
        shorthandUsages.add(node.key.name);
      }
    }
    if (node.type === "ExportNamedDeclaration") {
      if (node.declaration) {
        if (node.declaration.declarations) {
          node.declaration.declarations.forEach((decl) => {
            if (decl.id.type === "Identifier") exportedNames.add(decl.id.name);
          });
        }
        if (node.declaration.id && node.declaration.id.type === "Identifier") {
          exportedNames.add(node.declaration.id.name);
        }
      }
      if (node.specifiers) {
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
// Helper: Readable Scope ID Generation
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
  // This merges the "Loop Header" scope and "Loop Body" scope into one visual item.
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
// Helper: Collision & Kind
// ============================
function determineKind(variable, scope) {
  const def = variable.defs[0];
  if (!def) return "implicit-global";

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

function determineCollisionType(variableName, scope) {
  if (shorthandUsages.has(variableName)) return "shorthand";
  if (exportedNames.has(variableName)) return "export";
  if (scope.type === "global" || scope.type === "module") return "global";
  return "none";
}

// ============================
// TSV Generation
// ============================
const rows = [];
rows.push(
  [
    "file_name",
    "loc_start",
    "loc_end",
    "collision_type",
    "kind",
    "scope",
    "old_name",
    "new_name",
  ].join("\t"),
);

const processedDefs = new Set();

for (const scope of scopeManager.scopes) {
  const scopeId = makeScopeId(scope);

  for (const variable of scope.variables) {
    const def = variable.defs[0];
    if (!def || !def.name || !def.name.loc) continue;

    if (processedDefs.has(def.node)) continue;
    processedDefs.add(def.node);

    const locStart = `${def.name.loc.start.line}:${def.name.loc.start.column}`;
    const locEnd = `${def.name.loc.end.line}:${def.name.loc.end.column}`;
    const kind = determineKind(variable, scope);
    const collisionType = determineCollisionType(variable.name, scope);

    rows.push(
      [
        path.basename(source),
        locStart,
        locEnd,
        collisionType,
        kind,
        scopeId,
        variable.name,
        "",
      ].join("\t"),
    );
  }
}

console.log(`[INFO] Processed ${rows.length - 1} identifiers`);

try {
  const dir = path.dirname(output);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(output, rows.join(os.EOL), "utf8");
  console.log(`[INFO] Wrote TSV to ${output}`);
} catch (e) {
  console.error(`[ERROR] Failed to write: ${output}`);
  process.exit(1);
}
