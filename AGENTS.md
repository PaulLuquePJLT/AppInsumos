# AGENTS

## Purpose
This file helps AI coding agents understand the app structure, entrypoint, and conventions for the Mini WMS Insumos Streamlit project.

## Project overview
- A Streamlit-based warehouse management mini-app for inventory, locations, stock, and logistics accounts.
- Main UI is in `app.py` and app pages are under `pages/`.
- Database access uses `sqlalchemy`, `pyodbc`, and SQL Server stored procedures.
- Environment config is loaded from `.env` via `python-dotenv` in `src/db.py`.

## Entrypoint
- Run the app from the repository root with:
  - `streamlit run app.py`
- `app.py` configures the Streamlit page and relies on `pages/` for the multipage UI.

## Key directories and files
- `app.py` — Streamlit entrypoint, page config, and global layout styling.
- `pages/` — multipage UI files; each page is a separate Streamlit script.
- `src/db.py` — creates SQLAlchemy engine for SQL Server using DB_* env vars.
- `src/queries.py` — SELECT and INSERT wrappers for product, location, stock, and account queries.
- `src/movimientos.py` — executes stored procedures for entries, exits, and transfers.
- `src/utils.py` — helper for executing non-query SQL.
- `src/auth.py` — currently empty placeholder.

## Environment and runtime
- Required environment variables (loaded from `.env` or system env):
  - `DB_SERVER`
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - optional: `DB_DRIVER` (defaults to `ODBC Driver 18 for SQL Server`)
- Dependencies are listed in `requirements.txt`.

## Important conventions
- Preserve parameterized SQL and `text()` usage when updating database access.
- `src/movimientos.py` uses stored procedures; do not replace procedure logic without verifying SQL Server side definitions.
- UI changes should generally be made in `pages/*.py` page modules.
- There is no explicit test suite detected in the repo.

## Notes for agents
- Prefer understanding the Streamlit `pages/` layout before changing navigation or page behavior.
- Prefer updating `src/queries.py` for data retrieval and `src/movimientos.py` for movement operations.
- Avoid adding secrets or plaintext DB credentials to the repository.
