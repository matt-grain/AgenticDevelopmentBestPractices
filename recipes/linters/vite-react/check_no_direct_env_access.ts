/**
 * Pre-commit check: only `src/lib/env.ts` may access `import.meta.env` directly.
 *
 * CLAUDE.md hard rule (vite-react): every other file imports the validated `env`
 * object from `@/lib/env`. Centralizing access makes the Zod schema the single
 * source of truth, prevents missing `VITE_` prefix typos from going unnoticed,
 * and gives types to the rest of the app.
 *
 * Allowed: src/lib/env.ts (the Zod schema lives here)
 * Forbidden everywhere else: any `import.meta.env.X` access
 */

import * as fs from "fs";
import * as path from "path";
import * as ts from "typescript";
import { Violation, iterSourceFiles, runChecker } from "./_base";

const ALLOWLIST_SUFFIXES = ["src/lib/env.ts", "src/lib/env.tsx"];

function isAllowlisted(filePath: string): boolean {
  const normalized = filePath.replace(/\\/g, "/");
  return ALLOWLIST_SUFFIXES.some((suffix) => normalized.endsWith(suffix));
}

function isImportMetaEnvAccess(node: ts.Node): boolean {
  // Matches the chain `import.meta.env.X`:
  //   PropertyAccessExpression(.X) whose
  //     .expression is PropertyAccessExpression(.env) whose
  //       .expression is MetaProperty(import.meta)
  if (!ts.isPropertyAccessExpression(node)) return false;
  const inner = node.expression;
  if (!ts.isPropertyAccessExpression(inner)) return false;
  if (inner.name.text !== "env") return false;
  if (!ts.isMetaProperty(inner.expression)) return false;
  if (inner.expression.keywordToken !== ts.SyntaxKind.ImportKeyword) return false;
  return inner.expression.name.text === "meta";
}

function checkFile(filePath: string, sourceFile: ts.SourceFile): Violation[] {
  if (isAllowlisted(filePath)) return [];
  const violations: Violation[] = [];

  function visit(node: ts.Node): void {
    if (isImportMetaEnvAccess(node)) {
      const accessed = (node as ts.PropertyAccessExpression).name.text;
      const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
      violations.push({
        file: filePath,
        line: line + 1,
        message: `Direct \`import.meta.env.${accessed}\` access — import the validated \`env\` from \`@/lib/env\` instead`,
      });
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
  return runChecker(checkFile, files, "Direct import.meta.env access (only src/lib/env.ts may)");
}

process.exit(main());
