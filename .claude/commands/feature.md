---
description: Finish a Git Flow feature branch: merge --no-ff into develop, delete the branch, push.
argument-hint: "[feature branch name or leave empty to use current branch]"
---

You are a Git Flow expert. Close the current feature branch cleanly and merge it into `develop`.

## Input

Optional branch name from the user: $ARGUMENTS

If provided, use `feature/<argument>` or the full name if it already starts with `feature/`.
If not provided, use the current branch.

---

## Step 1 — Identify the feature branch

```bash
git branch --show-current
```

- If $ARGUMENTS is given, resolve the target branch name.
- If no argument, the current branch is the feature branch.
- If the branch does not start with `feature/`, stop and warn the user:
  > ⚠️ This does not look like a feature branch. Current branch: `<name>`. Use `/feature <name>` or switch to the correct branch first.

---

## Step 2 — Check clean working tree

```bash
git status --porcelain
```

If not clean, stop and ask the user to commit or stash first. Suggest running `/commit` to wrap up the last changes.

---

## Step 3 — Pull latest develop

```bash
git fetch origin
git checkout develop
git pull origin develop
```

---

## Step 4 — Merge the feature branch

```bash
git merge --no-ff <feature-branch> -m "feat: merge <feature-branch> into develop"
```

If there are merge conflicts, stop and report which files conflict:
```bash
git diff --name-only --diff-filter=U
```
Tell the user to resolve the conflicts manually, then run `/commit` and `/feature` again.

---

## Step 5 — Delete the local branch

```bash
git branch -d <feature-branch>
```

---

## Step 6 — Push develop and delete remote branch

```bash
git push origin develop
git push origin --delete <feature-branch> 2>/dev/null || true
```

---

## Step 7 — Summary

```
✅ Feature merged and closed

  Merged:  <feature-branch> → develop
  Deleted: <feature-branch> (local + remote)

Next steps:
  - Open a PR / run tests on develop
  - When ready to ship, run /release minor
```