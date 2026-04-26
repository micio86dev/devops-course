---
description: Stage all changes, generate a Conventional Commit message, commit and push to the current branch.
argument-hint: "[optional hint about what changed]"
---

You are a Conventional Commits expert. Inspect the staged/unstaged diff, write a precise commit message, then commit and push.

## Input

Optional hint from the user: $ARGUMENTS

---

## Step 1 — Check there is something to commit

```bash
git status --porcelain
```

If the output is empty, tell the user there is nothing to commit and stop.

---

## Step 2 — Read the diff

```bash
git diff HEAD
```

Study every changed file. Identify:
- What changed (added, removed, modified)
- Which part of the codebase is affected (scope)
- Whether it is a feature, fix, refactor, test, chore, docs, or ci change

---

## Step 3 — Determine commit type and scope

| Type | Use when |
|------|----------|
| `feat` | new functionality visible to the user or API |
| `fix` | bug fix |
| `refactor` | restructuring with no behaviour change |
| `test` | adding or fixing tests only |
| `chore` | deps, build, config, version bumps |
| `docs` | documentation only |
| `ci` | CI/CD pipeline changes |
| `style` | formatting, linting, no logic change |

Scope is the affected module or file group, e.g. `api`, `db`, `auth`, `frontend`, `docker`. Keep it short and lowercase. Omit if the change is truly cross-cutting.

---

## Step 4 — Write the commit message

Format:
```
<type>(<scope>): <short description in imperative mood, max 72 chars>

[optional body: what changed and why, not how — one bullet per logical change]
```

Rules:
- Description in imperative mood: "add", "fix", "remove" — not "added" or "fixes"
- No period at the end of the subject line
- Body only if the change is non-trivial
- If the user provided a hint in $ARGUMENTS, factor it in but still base the message primarily on the diff

Show the proposed message to the user and ask for confirmation before committing:
> `Proposed commit message — proceed? (yes / edit)`

---

## Step 5 — Stage and commit

```bash
git add -A
git commit -m "<message>"
```

If the user asked to edit, apply their changes to the message before committing.

---

## Step 6 — Push

```bash
git push origin HEAD
```

If the branch has no upstream yet:
```bash
git push --set-upstream origin <current-branch>
```

---

## Step 7 — Summary

```
✅ Committed and pushed

  Branch: <current-branch>
  Commit: <short SHA> <subject line>
```