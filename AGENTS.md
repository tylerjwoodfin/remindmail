# Agent / LLM guide for remindmail

Use this when implementing Taiga tickets or other changes in `~/git/remindmail`.

## Branching workflow

Always work from a **release branch**, not directly from `main`/`master`:

1. Checkout and pull latest `main` (this repo uses `main` as the default branch):

   ```bash
   cd ~/git/remindmail
   git checkout main
   git pull origin main
   ```

2. Cut a **release branch** from `main` using the next version (semver patch/minor as appropriate):

   ```bash
   git checkout -b release/X.Y.Z
   # bump `version` in setup.cfg to `1!X.Y.Z` and commit:
   #   X.Y.Z: Bumped version
   ```

3. Create a **ticket branch** from that release branch (ticket ref lowercase, e.g. `tjw-269`):

   ```bash
   git checkout -b tjw-269
   ```

4. Implement on the ticket branch. Commit messages: `tjw-269: short summary` (or `TJW-269:`).

5. Open a PR **from the ticket branch → the release branch** (not into `main`).

6. After review/merge into the release branch, a separate PR merges `release/X.Y.Z` → `main`.

## Implementation notes

- Prefer the smallest correct diff; match existing style in `src/remind/`.
- Add or extend unit tests under `test/` for parser and send-today logic.
- Natural-language `when` parsing lives in `query_manager.QueryManager.interpret_reminder_date`.
- YAML shape and annual dates (`MM-DD`) are documented in `README.md`.

## Before finishing

Double-check for stray issues elsewhere in the app. If you find unrelated bugs, **ask before fixing** them (do not scope-creep).
