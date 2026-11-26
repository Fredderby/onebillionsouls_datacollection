# SDD ledger — plan: docs/superpowers/specs/2026-11-26-admin-panel-design.md

Environment ruling: the workspace had no git repository, so earlier work was tracked in this ledger. The user later supplied a GitHub remote (`Fredderby/onebillionsouls_datacollection.git`), so a local repository is being initialised for the push.

Spec is the binding authority. Pre-flight: no shared interfaces — the spec defines the route/template contract once; Task 2 consumes Task 1's route context names (`tab`, `query`, `rows`, `missing`, `data_error`, `reporting_date`, `error`).

Ruling: `find_defaulters(reporting_date, submitted_pairs)` keeps the spec signature; the date filter is applied in `fetch_submitted_pairs` SQL and the helper compares full (zone, region, division) paths — avoids duplicating date logic and keeps the helper pure — cost if wrong: a caller passing unfiltered pairs would over-report defaulters.
Ruling: tabs are server-rendered via `?tab=` links, not JavaScript — works without JS and is directly testable — cost if wrong: full page reload when switching tabs.
Ruling: a random fallback SECRET_KEY is set at import so the app boots without .env; admin now requires all three env values plus a non-placeholder password — cost if wrong: sessions invalidate on restart when SECRET_KEY is unset.
Ruling: stacked gap is `--space-2xs` (4 px), not zero, per "the gap should be small" — cost if wrong: user may want even tighter spacing.

Task 1: complete (backend auth + defaulters + CSV).
Task 2: complete (admin_login.html, admin.html, admin.css).
Task 3: complete (footer Admin link to `/admin/login`; stacked `.sheet` gap 4 px at 320/375/414/768/1024 px; no overflow, no console errors).
Task 4: complete (credentials generated into .env, .env.example + README updated; live DB round-trip: INSERT → admin list → search → CSV → defaulters exclusion, temp row removed; browser login → Reports → Defaulters 97 rows).

Fresh review outcome: no Critical findings. Fixed all actionable items:
- CSV export now skips the internal `id` column, so 20 headers match 20 data columns.
- CSV cells beginning with `=`, `+`, `-` or `@` are apostrophe-prefixed to prevent formula evaluation.
- GET `/admin/login` and `require_admin()` both enforce `admin_available()`; placeholder passwords are rejected.
- Credential comparison encodes to UTF-8 bytes, so non-ASCII input returns 401 instead of 500.
- `LIKE` wildcards (`!`, `%`, `_`) are escaped with `ESCAPE '!'`.
- Database failures surface a clear admin alert / 503 instead of a false "no results" state.
- Reports subtitle no longer implies a date filter that the query does not apply.
- Footer Admin link targets `/admin/login` per spec.

Tests: `python -m unittest discover -s tests -v` → 28/28 pass at that stage. Review-driven tests were verified RED before fixes and GREEN after.

Docker follow-up: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `requirements.txt` and `README.md` updated for port 3003 with a Compose-managed MySQL 8 service and named volume. `docker compose config` verified (web 3003:3003, DB_HOST=db, health-gated startup); `docker compose build` completed successfully (`souls-web:latest`). Local repo initialised on `main` and pushed to `https://github.com/Fredderby/onebillionsouls_datacollection.git`; root commit `0f2c839`.

Delete follow-up: user asked for admin deletion and then specified that confirmation must "pop up beautifully". Ruling: permanent hard delete only (no schema change), POST-only `/admin/reports/<int:id>/delete`, per-session CSRF token, shared `<dialog>` styled by `admin.css` and driven by `static/admin.js`; native `confirm()` is only a fallback for browsers without `showModal()`. Cost if wrong: deletion is irreversible, so the dialog states that clearly and a deleted division may reappear in Defaulters. Search is preserved via hidden `q`; success/error states are explicit. Five regression tests were written and watched RED before implementation, then GREEN; full suite `python -m unittest discover -s tests -v` → 33/33 pass. Browser verification: temporary row id 7 inserted, Delete opened a modal dialog (`modal: true`, action `/admin/reports/7/delete`, target `Weija`), confirmation removed the row, success banner appeared, no console errors, and SQL confirmed `TEMP_ROW_COUNT 0`.

Database-host follow-up: user reported `Unknown MySQL server host 'db'` again. Root cause confirmed as environmental, not application code: `db` is a Compose service name on `souls_default`; the failing Gunicorn process was running outside that network (no `souls` containers, network, or volume existed at investigation). Fix: started the complete stack with `docker compose up -d --build`; `db` resolved to `172.24.0.2`, `app.get_connection()` returned `1`, a live POST `/submit` returned `201 {"ok":true,"id":2}`, and both containers are healthy/up on 3003. Test rows were removed from the Compose database. README now warns against standalone `docker run` with `DB_HOST=db` and gives `docker compose ps` as the check. Full suite remained 33/33 OK; HTTP smoke checks: form 200, login 200, admin 200.
