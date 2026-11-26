# Sunday Attendance Data Collection Form — Design Spec

Date: 2026-11-26

## Goal

Build a single-page web form that collects weekly church statistics for a division:
location hierarchy, workforce counts, and Sunday attendance broken down by category
and gender, plus a single total-online figure. The form must look modern and polished,
remain trivial to run and modify, and store every submission in MySQL.

## Decisions confirmed with the user

- One **summary attendance grid** for the whole division — not dynamic per-location rows.
  The "Total No. of church locations" field is a required count, not a row generator.
- Each attendance category has Male and Female inputs; online attendance is captured in a
  separate panel with **online males and online females**. YPF, Campus and Online counts
  are optional; blank values are stored as 0. All other fields remain required.
- Workforce labels read "Number of church Locations" and "Number of Pastors".
- Stack: **Flask + vanilla HTML/CSS/JS**. No frontend framework, no build step.

## Existing assets (must be preserved, not replaced)

- `zones.py` — contains `ZONE_STRUCTURE` (zone → region → division list) and the helpers
  `get_all_zones()`, `get_regions_by_zone(zone)`, `get_divisions_by_region(zone, region)`.
  This is the single source of truth for the cascading dropdowns.
- `.env` — contains `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
  Real credentials must never be committed or printed in logs/errors.

## Non-goals

- No login/authentication, user accounts, admin dashboard, or edit/delete of submissions.
- No dynamic location rows, no per-location breakdown, no image uploads.
- No migrations framework, no ORM, no JavaScript build tooling.

## Architecture and files

All files live directly in the project root (no new top-level folder). A `docs/` tree is
acceptable for documentation; `templates/` and `static/` are the only new subfolders
needed by the app.

| File | Purpose |
| --- | --- |
| `app.py` | Flask app: routes, DB connection, validation, table bootstrap. |
| `templates/index.html` | Single-page form markup with semantic sections and labels. |
| `static/styles.css` | All styling: layout, cards, inputs, states, responsive rules. |
| `static/app.js` | Fetch hierarchy, cascade selects, live totals, inline validation. |
| `zones.py` | Existing hierarchy dictionary/helpers — imported by `app.py`. |
| `.env` | Existing credentials — loaded with `python-dotenv`. |
| `.env.example` | Placeholder keys only, committed as documentation. |
| `.gitignore` | Ignore `.env`, `__pycache__/`, `*.pyc`, virtualenvs. |
| `requirements.txt` | Flask, mysql-connector-python, python-dotenv. |

### Routes

- `GET /` — render `templates/index.html`, passing the reporting date label.
- `GET /api/hierarchy` — return `ZONE_STRUCTURE` as JSON. One small request at page load;
  the browser filters it client-side so dependent selects update instantly with no extra
  round trips.
- `POST /submit` — accept JSON or form-encoded data, validate, insert one row, return JSON
  `{ "ok": true, "id": <int> }` on success or `{ "ok": false, "errors": {field: message} }`
  with HTTP 400 on validation failure and HTTP 500 with a generic message on DB failure.

## Data model

One flat table, auto-created on startup with `CREATE TABLE IF NOT EXISTS`. The database
already contains an empty legacy `submissions` table with an incompatible older schema
(`country`, `workers_brothers`, `adults_m`, …), so this form writes to a dedicated
`attendance_reports` table and leaves the legacy table untouched:

```sql
CREATE TABLE IF NOT EXISTS attendance_reports (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    zone            VARCHAR(120) NOT NULL,
    region          VARCHAR(120) NOT NULL,
    division        VARCHAR(120) NOT NULL,
    total_locations INT NOT NULL,
    total_pastors   INT NOT NULL,
    total_workers   INT NOT NULL,
    adults_male     INT NOT NULL,
    adults_female   INT NOT NULL,
    youths_male     INT NOT NULL,
    youths_female   INT NOT NULL,
    ypf_male        INT NOT NULL,
    ypf_female      INT NOT NULL,
    campus_male     INT NOT NULL,
    campus_female   INT NOT NULL,
    children_boys   INT NOT NULL,
    children_girls  INT NOT NULL,
    online_male     INT NOT NULL DEFAULT 0,
    online_female   INT NOT NULL DEFAULT 0,
    reporting_date  DATE NOT NULL,
    submitted_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

`reporting_date` is the fixed Sunday being reported: **2026-11-29**. It is set by the
server on insert (not accepted from the client) so every row is unambiguous even if a
submission is made later. `submitted_at` records the actual creation time.

## Fields and validation

| Field | Label | Type | Rule |
| --- | --- | --- | --- |
| zone | Select your zone | select | Required; must be a key in `ZONE_STRUCTURE`. |
| region | Select your region | select | Required; must be a key under the chosen zone. |
| division | Select your division | select | Required; must be in the list under the chosen zone/region. |
| total_locations | Total No. of church locations in your division | integer | Required; >= 0. |
| total_pastors | Total No. of pastors in your division | integer | Required; >= 0. |
| total_workers | Total No. of church workers (brothers and sisters) | integer | Required; >= 0. |
| adults_male / adults_female | ADULTS — Male / Female | integer | Required; >= 0. |
| youths_male / youths_female | YOUTHS — Male / Female | integer | Required; >= 0. |
| ypf_male / ypf_female | YPF — Male / Female | integer | Optional; blank = 0, otherwise >= 0. |
| campus_male / campus_female | CAMPUS — Male / Female | integer | Optional; blank = 0, otherwise >= 0. |
| children_boys / children_girls | CHILDREN — Boys / Girls | integer | Required; >= 0. |
| online_male / online_female | Online males / Online females | integer | Optional; blank = 0, otherwise >= 0. |

Server-side validation is authoritative; browser validation is for fast feedback only.
On failure, return one error per invalid field keyed by the input `name`, and also reject
any unknown extra fields. Inconsistent hierarchy combinations are rejected even if a
client bypasses the cascading selects.

## UI specification

- One centered card on a soft gradient background, with a header showing the form title
  and "Sunday, 29 November 2026".
- Three visually separated sections: **Location** (three cascading selects), **Workforce**
  (three number inputs), **Sunday attendance** (a compact table/grid of five category
  rows × Male/Female inputs, then a distinct online panel with Male and Female fields).
- Cascading behaviour: region select is disabled until a zone is chosen; division is
  disabled until a region is chosen; changing a parent clears and re-enables the child.
- Live computed totals: male total, female total, and grand total update as number inputs
  change. The grid also shows a per-row subtotal for quick proofreading.
- All fields carry a visible "Required" indicator; invalid fields show an inline message
  and are focused on submit failure.
- Submit button shows a loading state and is disabled during the request; on success the
  form is replaced by a clean confirmation panel showing the saved reference id and a
  "Submit another response" button that resets everything.
- Responsive down to phone width; inputs and buttons are keyboard accessible with clear
  focus states. Uses system fonts, CSS variables, subtle shadows, and transitions — no
  external CDN dependencies.

## Error handling

- Missing `.env` or bad credentials produce a clear startup message and a friendly JSON
  error on submit; raw DB errors and passwords are never returned to the browser.
- Network/DB failures during submit keep the form and its values intact and show an
  error banner so the user can retry.
- Duplicate submissions are intentionally allowed — there is no uniqueness constraint.

## Verification

1. `python -c "import app"` confirms the module imports and the table bootstrap path works
   (connection permitting).
2. `GET /` returns the form HTML; `GET /api/hierarchy` returns JSON matching `zones.py`.
3. `POST /submit` with a complete valid payload inserts exactly one row with the correct
   `reporting_date`.
4. `POST /submit` with a missing field, negative number, or mismatched hierarchy is
   rejected with HTTP 400 and a field-keyed error.
5. If the configured cloud MySQL host is unreachable from this machine, verification is
   limited to import/static checks, and the run instructions and limitation are reported
   to the user.

## Assumptions

- `zones.py` and `.env` remain unchanged and are the authoritative hierarchy and config.
- The form is for a single fixed reporting date; supporting arbitrary dates is out of scope.
- Numbers are whole non-negative counts; decimals are not accepted.
