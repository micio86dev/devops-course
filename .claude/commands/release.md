---
description: Cut a Git Flow release: bump version, open release branch, commit, merge to main, tag, back-merge to develop.
argument-hint: "[major|minor|patch] (default: minor)"
---

You are a Git Flow release expert. Execute the following steps **in order**, stopping immediately if any step fails and reporting what went wrong.

## Input

The user may pass a bump type as argument: `major`, `minor`, or `patch`.
If no argument is given, default to `minor`.

Bump type: $ARGUMENTS

---

## Step 1 — Verify clean state

```bash
git status --porcelain
git branch --show-current
```

- If the working tree is **not clean** (any output from `git status --porcelain`), stop and tell the user to commit or stash their changes first.
- If the current branch is **not `develop`**, stop and tell the user to switch to `develop` first.

---

## Step 2 — Pull latest develop

```bash
git fetch origin
git pull origin develop
```

---

## Step 3 — Read current version

Look for the version in this order and read the **first match**:

1. `app/__init__.py` → `__version__ = "X.Y.Z"`
2. `pyproject.toml` → `version = "X.Y.Z"` under `[project]`
3. `setup.cfg` → `version = X.Y.Z` under `[metadata]`

If none is found, start from `0.1.0` and tell the user.

---

## Step 4 — Compute next version

Apply SemVer 2.0.0 rules to the current version:

| Bump | Rule | Example |
|------|------|---------|
| `patch` | increment Z, reset nothing | 1.2.3 → 1.2.4 |
| `minor` | increment Y, reset Z to 0 | 1.2.3 → 1.3.0 |
| `major` | increment X, reset Y and Z to 0 | 1.2.3 → 2.0.0 |

Show the user: `Bumping X.Y.Z → A.B.C (minor)` before continuing.

---

## Step 5 — Open release branch

```bash
git checkout -b release/A.B.C
```

---

## Step 6 — Write new version to all files

Update **every** file that contains the version. Do not skip any.

- `app/__init__.py`: replace `__version__ = "X.Y.Z"` → `__version__ = "A.B.C"`
- `pyproject.toml` (if present): replace `version = "X.Y.Z"` → `version = "A.B.C"` under `[project]`
- `setup.cfg` (if present): same replacement under `[metadata]`

After editing, verify the changes with:

```bash
grep -r "__version__\|^version" app/ pyproject.toml setup.cfg 2>/dev/null
```

---

## Step 7 — Commit the version bump

```bash
git add -A
git commit -m "chore(release): bump version to A.B.C"
```

---

## Step 8 — Merge into main

```bash
git checkout main
git pull origin main
git merge --no-ff release/A.B.C -m "chore(release): merge release/A.B.C into main"
```

---

## Step 9 — Tag the release

```bash
git tag -a vA.B.C -m "Release vA.B.C"
```

---

## Step 10 — Back-merge into develop

```bash
git checkout develop
git merge --no-ff release/A.B.C -m "chore(release): back-merge release/A.B.C into develop"
```

---

## Step 11 — Delete the release branch

```bash
git branch -d release/A.B.C
```

---

## Step 12 — Push everything

```bash
git push origin main develop --tags
git push origin --delete release/A.B.C 2>/dev/null || true
```

---

## Step 13 — Summary

Print a clear summary:

```
✅ Release vA.B.C complete

  Branch merged → main
  Tag created   → vA.B.C
  Back-merged   → develop
  Release branch deleted

Next step: the GitHub Actions pipeline will trigger automatically on main.
Run `docker pull ghcr.io/<repo>/docker-todo:vA.B.C` once the CI finishes.
```