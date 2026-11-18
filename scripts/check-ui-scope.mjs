#!/usr/bin/env node
/**
 * 轻量前端作用域检查。
 *
 * src/index.tsx 是恢复出来的编译 JS（带 @ts-nocheck），tsc 不会检查。
 * 这个脚本用 TypeScript AST 检查 React hooks 的依赖数组：
 * 数组里引用的标识符必须在本函数、模块顶层或白名单全局中存在。
 *
 * 这正是 v0.26.36 设置页 ReferenceError: batchBusy is not defined 的根因。
 */
import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const ROOT = path.resolve(import.meta.dirname, "..");
const sourceArg = process.argv.find((arg) => arg.startsWith("--source="));
const sourcePath = sourceArg ? path.resolve(sourceArg.slice("--source=".length)) : path.join(ROOT, "src", "index.tsx");

const HOOK_NAMES = new Set(["useMemo", "useCallback", "useEffect", "useLayoutEffect"]);
const GLOBALS = new Set([
  "undefined", "NaN", "Infinity", "arguments", "this",
  "window", "document", "navigator", "location", "console", "globalThis",
  "Math", "JSON", "Object", "Array", "String", "Number", "Boolean", "Date", "RegExp",
  "Promise", "Map", "Set", "WeakMap", "WeakSet", "Symbol", "Error", "TypeError", "RangeError",
  "parseInt", "parseFloat", "isNaN", "isFinite", "encodeURIComponent", "decodeURIComponent",
  "setTimeout", "clearTimeout", "setInterval", "clearInterval", "requestAnimationFrame",
  "cancelAnimationFrame", "fetch", "URL", "URLSearchParams", "AbortController", "TextEncoder",
  "Intl", "structuredClone", "queueMicrotask",
]);

const sourceText = fs.readFileSync(sourcePath, "utf8");
const sourceFile = ts.createSourceFile(sourcePath, sourceText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const errors = [];

function addBindingName(name, out) {
  if (!name) return;
  if (ts.isIdentifier(name)) {
    out.add(name.text);
    return;
  }
  if (ts.isObjectBindingPattern(name) || ts.isArrayBindingPattern(name)) {
    for (const element of name.elements) {
      if (ts.isBindingElement(element)) addBindingName(element.name, out);
    }
  }
}

function collectModuleNames(node) {
  const names = new Set(GLOBALS);
  for (const statement of node.statements) {
    if (ts.isImportDeclaration(statement) && statement.importClause) {
      const clause = statement.importClause;
      if (clause.name) names.add(clause.name.text);
      if (clause.namedBindings) {
        if (ts.isNamespaceImport(clause.namedBindings)) names.add(clause.namedBindings.name.text);
        if (ts.isNamedImports(clause.namedBindings)) {
          for (const element of clause.namedBindings.elements) names.add(element.name.text);
        }
      }
    } else if (ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) addBindingName(declaration.name, names);
    } else if (ts.isFunctionDeclaration(statement) || ts.isClassDeclaration(statement) || ts.isEnumDeclaration(statement)) {
      if (statement.name) names.add(statement.name.text);
    }
  }
  return names;
}

function collectFunctionNames(fn) {
  const names = new Set();
  for (const parameter of fn.parameters) addBindingName(parameter.name, names);
  function visit(node) {
    if (ts.isVariableDeclaration(node)) addBindingName(node.name, names);
    if (ts.isFunctionDeclaration(node) && node.name) names.add(node.name.text);
    if (ts.isClassDeclaration(node) && node.name) names.add(node.name.text);
    if (ts.isCatchClause(node) && node.variableDeclaration) addBindingName(node.variableDeclaration.name, names);
    ts.forEachChild(node, visit);
  }
  visit(fn.body ?? fn);
  return names;
}

function nearestFunction(node) {
  let current = node.parent;
  while (current) {
    if (ts.isFunctionLike(current)) return current;
    current = current.parent;
  }
  return null;
}

function rootIdentifier(expression) {
  let current = expression;
  while (ts.isPropertyAccessExpression(current) || ts.isElementAccessExpression(current) || ts.isNonNullExpression(current)) {
    current = current.expression;
  }
  return ts.isIdentifier(current) ? current.text : "";
}

const moduleNames = collectModuleNames(sourceFile);

function visit(node) {
  if (ts.isCallExpression(node) && node.arguments.length >= 2) {
    const callee = node.expression;
    const hookName = ts.isPropertyAccessExpression(callee) && ts.isIdentifier(callee.name) ? callee.name.text : "";
    const deps = node.arguments[node.arguments.length - 1];
    if (HOOK_NAMES.has(hookName) && ts.isArrayLiteralExpression(deps)) {
      const fn = nearestFunction(node);
      const localNames = fn ? collectFunctionNames(fn) : new Set();
      for (const element of deps.elements) {
        if (ts.isSpreadElement(element)) continue;
        const name = rootIdentifier(element);
        if (!name) continue;
        if (localNames.has(name) || moduleNames.has(name)) continue;
        const position = sourceFile.getLineAndCharacterOfPosition(element.getStart(sourceFile));
        errors.push({
          file: path.relative(ROOT, sourcePath),
          line: position.line + 1,
          column: position.character + 1,
          hook: hookName,
          name,
          text: element.getText(sourceFile),
        });
      }
    }
  }
  ts.forEachChild(node, visit);
}

visit(sourceFile);

if (errors.length) {
  for (const error of errors) {
    console.error(`${error.file}:${error.line}:${error.column} ${error.hook} 依赖项未定义: ${error.name} (${error.text})`);
  }
  console.error(`\n发现 ${errors.length} 个前端作用域错误`);
  process.exit(1);
}
console.log(`前端作用域检查通过：${path.relative(ROOT, sourcePath)}`);
