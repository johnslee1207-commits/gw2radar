# Loop Engineering Protocol

Every coding-agent task must follow this loop.

## Loop 1: Understand
Read AGENTS.md / CLAUDE.md, PRD.md, SDD.md, HARNESS.md, and inspect existing code.

## Loop 2: Plan
Produce a short plan with files to change, tests to add, commands to run, and risks.

## Loop 3: Implement
Make the smallest useful vertical slice.

## Loop 4: Verify
Run unit tests, smoke harness, and lint/type checks if configured.

## Loop 5: Repair
Diagnose failures, fix implementation, re-run tests, and do not weaken tests unless the spec is wrong.

## Loop 6: Report
Return summary, files changed, test results, known limitations, and next recommended task.
