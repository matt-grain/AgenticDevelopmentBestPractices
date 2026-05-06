/**
 * Shared utilities for pre-commit check scripts.
 *
 * Mirrors the Python `_base.py` shape: Violation type, file iterator, runner.
 * Standalone — no external deps beyond TypeScript itself.
 * Run via: pnpm tsx tools/pre_commit_checks/check_X.ts
 */

import * as fs from "fs";
import * as path from "path";
import * as ts from "typescript";

export interface Violation {
  file: string;
  line: number;
  message: string;
}

export function formatViolation(v: Violation): string {
  return `${v.file}:${v.line}: ${v.message}`;
}

const DEFAULT_EXCLUDES = ["node_modules", "dist", "build", ".vite", "coverage", ".next"];

export function iterSourceFiles(rootDir: string, excludes: string[] = DEFAULT_EXCLUDES): string[] {
  const results: string[] = [];

  function walk(dir: string): void {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (excludes.includes(entry.name)) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
        results.push(full);
      }
    }
  }

  walk(rootDir);
  return results.sort();
}

export function parseFile(filePath: string): ts.SourceFile | null {
  try {
    const text = fs.readFileSync(filePath, "utf8");
    return ts.createSourceFile(filePath, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  } catch (e) {
    process.stderr.write(`Failed to parse ${filePath}: ${String(e)}\n`);
    return null;
  }
}

export function runChecker(
  checkerFunc: (filePath: string, sourceFile: ts.SourceFile) => Violation[],
  files: string[],
  description: string,
): number {
  const violations: Violation[] = [];
  for (const filePath of files) {
    const sourceFile = parseFile(filePath);
    if (sourceFile) {
      violations.push(...checkerFunc(filePath, sourceFile));
    }
  }

  if (violations.length > 0) {
    console.log("=".repeat(70));
    console.log(`VIOLATION: ${description}`);
    console.log("=".repeat(70));
    console.log();
    for (const v of violations) {
      console.log(`  ${formatViolation(v)}`);
    }
    console.log();
    console.log(`Total: ${violations.length} violation(s)`);
    return 1;
  }

  console.log(`OK: ${description} - checked ${files.length} file(s)`);
  return 0;
}
