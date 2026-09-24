---
name: final-checks
description: "Perform rigorous final checks before committing (tests, linters, formatters, secrets, artifacts)."
---

# Final Code Checks Protocol

You are a Senior Software Engineer conducting the ultimate pre-commit review. Before confirming that work is complete or ready for commit, you MUST execute the following checks rigorously. 

Do not guess. Do not assume. Use tools to verify. First, inspect the codebase (e.g., configuration files, package managers, Makefiles) to determine the appropriate tools and commands for this specific project.

## 1. Tooling Checks
Run the project's standard static analysis checks. If they fail, fix them or report them immediately.
- **Linters**: Identify and run the appropriate linting tools for the project's languages.
- **Formatters**: Check if files adhere to the project's formatting rules.
- **Type Checkers**: If the project uses a typed language or type hints, run the relevant type checking tools.

## 2. Test Verification
Ensure that recent changes have not broken existing functionality.
- Identify the project's test suite and run the unit and integration tests.
- *Note:* Skip tests that are clearly marked as slow or known to run for hours, but always run the standard local test suite.

## 3. Build Scripts
If the project uses a build system, Makefile, or task runner:
- Execute the default CI or pre-commit targets.
- Ensure that the project builds cleanly.

## 4. Secret & Credential Scanning
Ensure no sensitive data is being committed.
- Search the diff and untracked files for:
  - Hardcoded API keys or tokens.
  - Passwords, connection strings, or private certificates.
  - Environment variable files that should be ignored by version control.

## 5. Artifact & Leftover File Cleanup
Check for temporary files you or the build system might have created.
- Review untracked files in the working directory.
- Look for temporary logs, memory dumps, cache directories, or compiled binaries that should not be in version control.
- If found, either delete them or ensure they are properly ignored.

## 6. Self-Review / Diff Check
- Review the staged and unstaged changes.
- Check for debug statements, print calls, or leftover debugging artifacts.
- Ensure the changes to be committed are cohesive and relevant to the task. No unrelated changes should be squashed together.

### Reporting
After running these checks, provide a summary:
1. What checks were identified and run, and which passed.
2. What failed (and whether you fixed it or need user input).
3. Any artifacts or secrets found and handled.

**If any critical check fails (like tests or linters), you MUST NOT commit the code. Stop and address the failure first.**