---
name: pdf2md
description: Convert a PDF file to Markdown. Use this when the user wants to convert a PDF to markdown, extract text from a PDF, or get markdown content from a PDF file.
argument-hint: "[pdf-path] [output.md]"
allowed-tools: Bash, Read, Write
---

Convert a PDF file to Markdown format.

## Arguments

- `$0` - Path to the PDF file (required)
- `$1` - Output markdown file path (optional, defaults to same name as PDF with .md extension)

## Instructions

1. First, verify the PDF file exists at the provided path: `$0`

2. Determine the output file:
   - If `$1` is provided, use it as the output path
   - Otherwise, create the output path by replacing the .pdf extension with .md

3. Ensure pdf2md is installed. Run this command first (it will skip if already installed):
   ```bash
   uv tool install --upgrade ~/.claude/skills/pdf2md/dist/pdf2md-0.1.0-py3-none-any.whl
   ```

4. Run the conversion:
   ```bash
   pdf2md "$0" -o "<output-path>"
   ```

5. If successful, inform the user the file was converted and where the output was saved.

6. If there's an error, explain what went wrong.

## Example Usage

- `/pdf2md document.pdf` - Converts to document.md
- `/pdf2md report.pdf output.md` - Converts to output.md
- `/pdf2md "My Document.pdf"` - Handle paths with spaces

## Additional Options

If the user wants specific pages converted, use the `-p` flag:
```bash
pdf2md "$0" -o "<output>" -p "1-5"
```

If the user wants images extracted too:
```bash
pdf2md "$0" -o "<output>" --images
```
