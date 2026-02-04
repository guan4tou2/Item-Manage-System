# Uncommitted Code Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce an actionable review of current uncommitted changes.

**Architecture:** Gather staged/unstaged diffs, read full files for context, cross-check against project patterns and tests to confirm correctness before flagging issues.

**Tech Stack:** Python 3.13, Flask 3.1, SQLAlchemy 2.0, PyMongo, Bootstrap 5.

### Task 1: Capture working tree state

**Files:**
- Inspect: `git status`, `git diff`, `git diff --cached`

**Step 1: Record short status**

Run: `git status -sb`
Expected: List of modified/staged files

**Step 2: Collect unstaged diff**

Run: `git diff`
Expected: Unstaged changes printed for review

**Step 3: Collect staged diff**

Run: `git diff --cached`
Expected: Staged changes printed for review

### Task 2: Read changed files in full

**Files:**
- Inspect: `<each file from diff>`

**Step 1: List changed paths**

Run: `git diff --name-only && git diff --cached --name-only`
Expected: All modified file paths

**Step 2: Read full contents for context**

Use: `read` tool on each path
Expected: Full file context visible

### Task 3: Analyze changes for defects

**Files:**
- Inspect: `<each file from diff>`
- Reference: `tests/` for related cases

**Step 1: Check logic and edge cases**

Action: Evaluate control flow, error handling, data validation per change
Expected: Clear understanding of correctness

**Step 2: Cross-check against patterns/tests**

Action: Compare with similar code and existing tests; note any missing coverage
Expected: Identified potential issues with rationale

### Task 4: Summarize review findings

**Files:**
- Output: Review report in final message

**Step 1: Draft concise findings**

Action: List issues with severity, scenario, file:line references
Expected: Ready-to-send review bullets

**Step 2: Deliver review**

Action: Provide final feedback to user
Expected: User receives actionable review summary
