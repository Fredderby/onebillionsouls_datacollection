# Admin Panel — Design Spec

Date: 2026-11-26
Status: awaiting user review

## Goal

Add a small, secure admin area beneath the existing membership report form. An admin logs in with credentials from `.env`, reviews submitted reports, exports a filtered CSV, and sees a **Defaulters** tab listing every division that has not submitted for the current reporting date.

## Confirmed decisions

- Admin scope: **view + search + CSV export** (read-only; no edit or delete).
- Credentials: **single account** in `.env` (`ADMIN_USER`, `ADMIN_PASSWORD`) plus `SECRET_KEY`; no user table, no registration.
- Entry point: subtle **Admin** link in the footer below the form opens `/admin/login` in the same tab.
- Session: Flask's built-in signed cookie session. Missing credentials keep admin locked with a clear setup message.
- Defaulters period: **current report date only** (Sunday, 29 November 2026).
- Defaulter definition: a division from `zones.py` with **no submission** matching `(zone, region, division)` for that date.
- Stacked layouts: tighten the vertical gap between the side card and the form card from 12/16 px to **4 px**.

## Architecture

### Routes

| Route | Method | Behavior |
| --- | --- | --- |
| `/admin/login` | GET | Small login form using existing design tokens. |
| `/admin/login` | POST | Verify credentials with `hmac.compare_digest`; set `session["admin"] = True`; redirect to `/admin`. Bad credentials re-render with an error (401). |
| `/admin` | GET | Protected. Render reports table + tabs. Redirect to login when signed out. |
| `/admin/logout` | POST | Clear session; redirect to login. |
| `/admin/export.csv` | GET | Protected. Stream CSV of the currently filtered rows. |

### Auth rules

- `SECRET_KEY`, `ADMIN_USER`, and `ADMIN_PASSWORD` are read with `python-dotenv`, matching existing MySQL config.
- If any value is missing, `/admin/login` renders a setup error and never grants access.
- Password comparison uses `hmac.compare_digest` to avoid timing leaks.
- The session cookie stores only a boolean flag, never credentials.

### Data

- Reports come from the existing `attendance_reports` table, newest first.
- `?q=` filters by zone / region / division using a parameterised `LIKE` query.
- The same `q` is applied to the CSV export.
- A pure helper `find_defaulters(reporting_date, submitted_pairs)` walks `ZONE_STRUCTURE` and returns paths with no matching submission. It has no database dependency, so it is directly unit-testable.

## UI

- `templates/admin_login.html` — centered card, username/password, submit button, error state.
- `templates/admin.html` — two tabs:
  - **Reports** — search box, Export CSV button, table of zone / region / division / date / totals / submitted time.
  - **Defaulters** — count plus table of zone / region / division for missing submissions.
- `static/admin.css` — admin-only styles using the same OKLCH tokens, fonts, radii and shadows as the main form. No new framework.
- `templates/index.html` — footer Admin link.
- `static/styles.css` — reduce stacked `.sheet` gap to `var(--space-2xs)`.

## Credentials handling

- `.env.example` documents the three new variables with placeholder values.
- The local `.env` (gitignored) gets a generated `SECRET_KEY` and a generated temporary admin password; the password is reported to the user so it can be changed.

## Tests (`tests/test_admin.py`)

1. Login page returns 200.
2. `/admin` redirects to login when signed out.
3. Wrong credentials do not create a session.
4. Correct credentials create a session and `/admin` returns 200.
5. CSV export is protected and returns CSV headers/content when signed in.
6. `find_defaulters` returns every division when nothing submitted.
7. `find_defaulters` excludes a division present in submitted pairs.
8. Report filtering is covered through the route with a mocked connection (no rows written to MySQL).

## Out of scope

- Editing or deleting submissions.
- Multiple admin accounts, password reset, or registration.
- Audit logs and rate limiting (may be added later if needed).
