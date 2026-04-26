---
description: Cut a Git Flow hotfix from main: bump patch version, fix, merge back to main and develop, tag.
argument-hint: "<short description of the fix>"
---

You are a Git Flow hotfix expert. A hotfix is an urgent fix on production (`main`) that cannot wait for the next release cycle. It always bumps the **patch** version.

Execute the following steps **in order**, stopping immediately if any step fails.

## Input

The user describes the fix: $ARGUMENTS

Use this to name the branch: `hotfix/<kebab-case-description>`
Example: "fix auth token expiry" → `hotfix/fix-auth-token-expiry`

---

## Step 1 — Verify clean state

```bash
git status --porcelain
```

If the working tree is not clean, stop and ask the user to commit or stash first.

---

## Step 2 — Start from main

```bash
git checkout main
git fetch origin
git pull origin main
```

---

## Step 3 — Read current version

Look for the version in this order:

1. `app/__init__.py` → `__version__ = "X.Y.Z"`
2. `pyproject.toml` → `version = "X.Y.Z"` under `[project]`
3. `setup.cfg` → `version = X.Y.Z` under `[metadata]`

---

## Step 4 — Compute patch bump

Increment **Z only**. Example: `1.2.3 → 1.2.4`

Show the user: `Hotfix: bumping X.Y.Z → X.Y.(Z+1) (patch)`

---

## Step 5 — Open hotfix branch

```bash
git checkout -b hotfix/<description>
```

---

## Step 6 — Write new version to all files

Update every file that contains the version:

- `app/__init__.py`: `__version__ = "X.Y.(Z+1)"`
- `pyproject.toml` (if present): `version = "X.Y.(Z+1)"` under `[project]`
- `setup.cfg` (if present): same under `[metadata]`

Verify:

```bash
grep -r "__version__\|^version" app/ pyproject.toml setup.cfg 2>/dev/null
```

---

## Step 7 — Commit version bump

```bash
git add -A
git commit -m "chore(hotfix): bump version to X.Y.(Z+1)"
```

---

## Step 8 — Remind the user to apply the fix

Tell the user:

> ⚠️ Version bumped and branch ready. **Apply your fix now**, then come back and say "hotfix done" to finish.

Wait for the user to confirm before continuing.

---

## Step 9 — Merge into main

```bash
git checkout main
git merge --no-ff hotfix/<description> -m "chore(hotfix): merge hotfix/<description> into main"
```

---

## Step 10 — Tag

```bash
git tag -a vX.Y.(Z+1) -m "Hotfix vX.Y.(Z+1)"
```

---

## Step 11 — Back-merge into develop

**Never skip this step.** The hotfix must land in develop too or it will be lost in the next release.

```bash
git checkout develop
git pull origin develop
git merge --no-ff hotfix/<description> -m "chore(hotfix): back-merge hotfix/<description> into develop"
```

---

## Step 12 — Delete hotfix branch and push

```bash
git branch -d hotfix/<description>
git push origin main develop --tags
git push origin --delete hotfix/<description> 2>/dev/null || true
```

---

## Step 13 — Summary

```
✅ Hotfix vX.Y.(Z+1) complete

  Branch merged → main
  Tag created   → vX.Y.(Z+1)
  Back-merged   → develop
  Hotfix branch deleted

The GitHub Actions pipeline will deploy to production automatically.
```