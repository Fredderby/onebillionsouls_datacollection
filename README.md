# Sunday Attendance Report

A simple Flask app for collecting weekly church attendance and workforce statistics.
The zone → region → division dropdowns are driven by `zones.py`; MySQL credentials are
read from `.env`.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5001> (the app reads `PORT` from `.env`; port 5000 may be used by another app).

The `attendance_reports` table is created automatically on startup. Any pre-existing
legacy `submissions` table is left untouched. If the database is unreachable, the app
still starts and shows a friendly message when a report is submitted.

## Docker (port 3003)

```powershell
docker compose up --build
```

Open <http://127.0.0.1:3003>. Compose starts MySQL 8 and the Flask app together:

- `db` uses `DB_NAME`, `DB_USER` and `DB_PASSWORD` from `.env`, stores data in the
  `db_data` volume, and is health-checked before the app starts.
- `web` runs Gunicorn on container port 3003, mapped to host port 3003.
- `MYSQL_ROOT_PASSWORD` is optional; Compose defaults it to `souls_root_password`.

`.dockerignore` keeps `.env` out of the image — credentials reach the container only
through Compose. To stop and keep the data: `docker compose down`. To wipe the database
as well: `docker compose down -v`.

## Configuration

Copy `.env.example` to `.env` and fill in your MySQL details. `.env` is gitignored —
never commit real credentials.

For the admin area also set `SECRET_KEY` (a long random string), `ADMIN_USER` and
`ADMIN_PASSWORD`. If any of the three is missing — or the password is still the
`.env.example` placeholder — admin login stays locked with a setup message. The small
**Admin** link under the form opens `/admin/login`.

## Admin area

After signing in, `/admin` has two tabs:

- **Reports** — newest-first submitted reports, searchable by zone/region/division,
  with a CSV export of the current filtered view.
- **Defaulters** — every division in `zones.py` with no submission for Sunday,
  29 November 2026.

Admin access is read-only; submissions cannot be edited or deleted from the panel.

## Files

- `app.py` — routes, validation, and database access
- `templates/index.html` — the form
- `static/styles.css` — styling
- `static/app.js` — cascading dropdowns, live totals, validation
- `zones.py` — hierarchy dictionary (source of truth for dropdowns)
- `templates/admin_login.html`, `templates/admin.html` — admin login and report tables
- `static/admin.css` — admin-only styling
- `Dockerfile`, `docker-compose.yml`, `.dockerignore` — container setup on port 3003
- `tests/` — validation and admin tests (`python -m unittest discover -s tests`)
