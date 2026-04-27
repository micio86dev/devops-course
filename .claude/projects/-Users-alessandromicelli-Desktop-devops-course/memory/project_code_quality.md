---
name: Code quality toolchain
description: Ruff + MyPy strict + Prettier + Husky git hooks setup for docker-todo project
type: project
---

Project has a full code quality toolchain installed on feature/husky branch (2026-04-27):

- **Python**: Ruff (format + lint, `pyproject.toml`) + MyPy strict (`files = ["app/app.py"]`)
- **Node**: Prettier 3 (HTML/JS/CSS/YAML/JSON/MD), commitlint (Conventional Commits), lint-staged
- **Git hooks (Husky v9)**:
  - `pre-commit`: lint-staged (ruff format + ruff check --fix on .py; prettier --write on templates/YAML/JSON) + `mypy app/`
  - `commit-msg`: commitlint (rejects non-conventional messages)
- **CI**: `lint` job (ruff + mypy + prettier check) runs parallel to `test` job; `build-push` needs both

**Why:** User wanted strict quality gates enforced locally and in CI.

**How to apply:** After `git clone`, run `npm install` to activate hooks. All Python functions in `app/` need full type annotations. Commit messages must follow Conventional Commits format.
