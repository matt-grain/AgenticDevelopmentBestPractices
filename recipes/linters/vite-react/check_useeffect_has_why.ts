/**
 * Pre-commit check: every `useEffect(...)` call has a leading `// WHY: ...` comment.
 *
 * CLAUDE.md hard rule (frontend): useEffect is the most-misused React primitive —
 * most legitimate uses can be replaced by useMemo, a TanStack Query hook, or
 * nothing at all. Forcing every survivor to carry a written justification
 * dramatically reduces the population.
 *
 * The comment must contain the literal token `WHY:` (case-insensitive) followed
 * by some text. Both `// WHY: ...` and block-style `\* WHY: ... *\` are accepted.
 */

import * as fs from "fs";
import * as path from "path";
import * as ts from "typescript";
import { Violation, iterSourceFiles, runChecker } from "./_base";

const WHY_PATTERN = /\bWHY:\s*\S/i;

function isUseEffectCall(node: ts.Node): node is ts.CallExpression {
  if (!ts.isCallExpression(node)) return false;
  const expr = node.expression;
  if (ts.isIdentifier(expr) && expr.text === "useEffect") return true;
  // Also catch `React.useEffect(...)` etc.
  if (ts.isPropertyAccessExpression(expr) && expr.name.text === "useEffect") return true;
  return false;
}

function hasLeadingWhyComment(node: ts.Node, sourceFile: ts.SourceFile): boolean {
  const ranges = ts.getLeadingCommentRanges(sourceFile.text, node.getFullStart());
  if (!ranges) return false;
  for (const range of ranges) {
    const text = sourceFile.text.slice(range.pos, range.end);
    if (WHY_PATTERN.test(text)) return true;
  }
  return false;
}

function checkFile(filePath: string, sourceFile: ts.SourceFile): Violation[] {
  const violations: Violation[] = [];

  function visit(node: ts.Node): void {
    if (isUseEffectCall(node)) {
      // Comments attach to the enclosing ExpressionStatement, not the CallExpression itself.
      const parent = node.parent;
      const target = parent && ts.isExpressionStatement(parent) ? parent : node;
      if (!hasLeadingWhyComment(target, sourceFile)) {
        const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
        violations.push({
          file: filePath,
          line: line + 1,
          message: "useEffect has no leading `// WHY: ...` comment — explain why this side effect is unavoidable",
        });
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
  return runChecker(checkFile, files, "Every useEffect has a leading // WHY: comment");
}

process.exit(main());
