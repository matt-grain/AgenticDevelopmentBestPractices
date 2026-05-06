/**
 * Pre-commit check: useEffect must not contain fetch / API calls.
 *
 * CLAUDE.md hard rule (frontend): never fetch data in useEffect — use
 * useApiQuery / TanStack Query instead. useEffect-for-fetching causes cache
 * misses, race conditions, double-fetching in StrictMode, missing loading
 * states, and untyped error handling.
 *
 * Detected anti-patterns inside useEffect callback bodies:
 *   fetch(...)
 *   axios.get/post/put/delete/patch(...)
 *   api.get(...) / apiClient.get(...) / httpClient.get(...) / etc.
 *
 * The receiver-name regex catches common API-client variable names. Adjust
 * `API_CLIENT_RECEIVER_PATTERN` for project-specific client names.
 */

import * as fs from "fs";
import * as path from "path";
import * as ts from "typescript";
import { Violation, iterSourceFiles, runChecker } from "./_base";

const FETCH_LIKE_IDENTIFIERS = new Set(["fetch"]);
const FETCH_LIKE_METHODS = new Set(["get", "post", "put", "delete", "patch"]);
const API_CLIENT_RECEIVER_PATTERN = /^(axios|api|apiClient|httpClient|http|client)$/i;

function isFetchLikeCall(call: ts.CallExpression): boolean {
  const expr = call.expression;
  if (ts.isIdentifier(expr)) {
    return FETCH_LIKE_IDENTIFIERS.has(expr.text);
  }
  if (ts.isPropertyAccessExpression(expr)) {
    if (!FETCH_LIKE_METHODS.has(expr.name.text)) return false;
    if (ts.isIdentifier(expr.expression)) {
      return API_CLIENT_RECEIVER_PATTERN.test(expr.expression.text);
    }
    if (ts.isPropertyAccessExpression(expr.expression)) {
      // e.g. `this.api.get(...)`
      return API_CLIENT_RECEIVER_PATTERN.test(expr.expression.name.text);
    }
  }
  return false;
}

function isUseEffectCall(node: ts.Node): node is ts.CallExpression {
  if (!ts.isCallExpression(node)) return false;
  const expr = node.expression;
  if (ts.isIdentifier(expr) && expr.text === "useEffect") return true;
  if (ts.isPropertyAccessExpression(expr) && expr.name.text === "useEffect") return true;
  return false;
}

function findFetchInBody(body: ts.Node): ts.CallExpression | null {
  let found: ts.CallExpression | null = null;
  function visit(node: ts.Node): void {
    if (found) return;
    if (ts.isCallExpression(node) && isFetchLikeCall(node)) {
      found = node;
      return;
    }
    ts.forEachChild(node, visit);
  }
  visit(body);
  return found;
}

function checkFile(filePath: string, sourceFile: ts.SourceFile): Violation[] {
  const violations: Violation[] = [];

  function visit(node: ts.Node): void {
    if (isUseEffectCall(node) && node.arguments.length > 0) {
      const callback = node.arguments[0];
      if (ts.isArrowFunction(callback) || ts.isFunctionExpression(callback)) {
        const fetchCall = findFetchInBody(callback.body);
        if (fetchCall) {
          const { line } = sourceFile.getLineAndCharacterOfPosition(fetchCall.getStart());
          violations.push({
            file: filePath,
            line: line + 1,
            message: "useEffect contains a fetch / API call — use TanStack Query (useQuery / useMutation) instead",
          });
        }
      }
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return violations;
}

function main(): number {
  const srcDir = path.resolve("src");
  if (!fs.existsSync(srcDir)) {
    console.log("src/ directory not found");
    return 1;
  }
  const files = iterSourceFiles(srcDir);
  return runChecker(checkFile, files, "No fetch / API calls inside useEffect (use TanStack Query)");
}

process.exit(main());
