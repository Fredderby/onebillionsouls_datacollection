"""Sunday attendance data collection form.

A deliberately small Flask app: one page, one hierarchy endpoint, one submit endpoint.
All configuration comes from .env; the zone/region/division tree comes from zones.py.
"""

import csv
import hmac
import io
import os
import re
import secrets
from datetime import date

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from zones import ZONE_STRUCTURE, get_divisions_by_region, get_regions_by_zone

load_dotenv()

REPORTING_DATE = date(2026, 11, 29)
REPORTING_LABEL = "Sunday, 29 November 2026"

app = Flask(__name__)
# A stable key is only needed for signed cookies; real admin access is gated
# by ADMIN_USER / ADMIN_PASSWORD / SECRET_KEY below.
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DB_KEYS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT") or 3306),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

INTEGER_FIELDS = (
    "total_locations",
    "total_pastors",
    "total_workers",
    "adults_male",
    "adults_female",
    "youths_male",
    "youths_female",
    "ypf_male",
    "ypf_female",
    "campus_male",
    "campus_female",
    "children_boys",
    "children_girls",
    "online_male",
    "online_female",
)

SELECT_FIELDS = ("zone", "region", "division")
OPTIONAL_INTEGER_FIELDS = (
    "ypf_male",
    "ypf_female",
    "campus_male",
    "campus_female",
    "online_male",
    "online_female",
)
ALL_FIELDS = SELECT_FIELDS + INTEGER_FIELDS

CREATE_TABLE_SQL = """
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
"""

INSERT_SQL = """
INSERT INTO attendance_reports (
    zone, region, division,
    total_locations, total_pastors, total_workers,
    adults_male, adults_female,
    youths_male, youths_female,
    ypf_male, ypf_female,
    campus_male, campus_female,
    children_boys, children_girls,
    online_male, online_female, reporting_date
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def get_connection():
    """Open a MySQL connection, raising a clear error if .env is incomplete."""
    missing = [key for key in DB_KEYS if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing database configuration: " + ", ".join(missing)
        )
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """Create the table on startup; keep the app usable if the DB is offline."""
    try:
        connection = get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(CREATE_TABLE_SQL)
            # Older versions stored a single total_online column; add the new
            # gender-specific columns without disturbing any existing rows.
            cursor.execute(
                """SELECT COLUMN_NAME FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s""",
                (DB_CONFIG["database"], "attendance_reports"),
            )
            existing_columns = {row[0] for row in cursor.fetchall()}
            if "total_online" in existing_columns:
                cursor.execute(
                    "ALTER TABLE attendance_reports "
                    "MODIFY COLUMN total_online INT NOT NULL DEFAULT 0"
                )
            for column in ("online_male", "online_female"):
                if column not in existing_columns:
                    cursor.execute(
                        f"ALTER TABLE attendance_reports "
                        f"ADD COLUMN {column} INT NOT NULL DEFAULT 0"
                    )
            connection.commit()
            cursor.close()
        finally:
            connection.close()
    except Exception as exc:  # noqa: BLE001 - startup must never hard-fail
        app.logger.warning("Database not available at startup: %s", exc)


def read_payload():
    """Accept JSON (browser) or form-encoded data (curl / plain HTML clients)."""
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}
    return request.form.to_dict()


def validate(payload):
    """Return (clean_values, errors). Optional counts default to zero."""
    errors = {}
    values = {}

    for key in payload:
        if key not in ALL_FIELDS:
            errors[key] = "Unexpected field."

    zone = str(payload.get("zone") or "").strip()
    region = str(payload.get("region") or "").strip()
    division = str(payload.get("division") or "").strip()

    if not zone:
        errors["zone"] = "Please select your zone."
    elif zone not in ZONE_STRUCTURE:
        errors["zone"] = "Select a valid zone."

    if not region:
        errors["region"] = "Please select your region."
    elif zone in ZONE_STRUCTURE and zone not in errors:
        if region not in get_regions_by_zone(zone):
            errors["region"] = "Select a valid region for this zone."

    if not division:
        errors["division"] = "Please select your division."
    elif zone in ZONE_STRUCTURE and region and "region" not in errors:
        if division not in get_divisions_by_region(zone, region):
            errors["division"] = "Select a valid division for this region."

    for key in SELECT_FIELDS:
        if key not in errors:
            values[key] = {"zone": zone, "region": region, "division": division}[key]

    for key in INTEGER_FIELDS:
        raw = str(payload.get(key) or "").strip()
        if raw == "":
            if key in OPTIONAL_INTEGER_FIELDS:
                values[key] = 0
            else:
                errors[key] = "This field is required."
        elif not re.fullmatch(r"[0-9]+", raw):
            errors[key] = "Enter a whole number of 0 or more."
        else:
            values[key] = int(raw)

    return values, errors


@app.route("/")
def index():
    return render_template(
        "index.html",
        reporting_date=REPORTING_LABEL,
        reporting_iso=REPORTING_DATE.isoformat(),
    )


@app.route("/logo")
def logo():
    """Serve the crest from the project root, tolerant of .jpg / .JPG casing."""
    for filename in ("logo.jpg", "logo.JPG"):
        path = os.path.join(app.root_path, filename)
        if os.path.isfile(path):
            return send_file(path, mimetype="image/jpeg")
    return "", 404


@app.route("/api/hierarchy")
def hierarchy():
    return jsonify(ZONE_STRUCTURE)


@app.route("/submit", methods=["POST"])
def submit():
    values, errors = validate(read_payload())
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    params = [values[key] for key in ALL_FIELDS] + [REPORTING_DATE.isoformat()]

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(INSERT_SQL, tuple(params))
        new_id = cursor.lastrowid
        connection.commit()
        cursor.close()
        return jsonify({"ok": True, "id": new_id}), 201
    except Exception as exc:  # noqa: BLE001 - never leak DB details to the client
        app.logger.exception("Failed to save submission: %s", exc)
        if connection is not None:
            try:
                connection.rollback()
            except Exception:  # noqa: BLE001
                pass
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "We could not save your report right now. Please try again.",
                }
            ),
            500,
        )
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass


# ---------- Admin area ----------

REPORT_COLUMNS = (
    "id", "zone", "region", "division", "reporting_date", "submitted_at",
    "total_locations", "total_pastors", "total_workers",
    "adults_male", "adults_female", "youths_male", "youths_female",
    "ypf_male", "ypf_female", "campus_male", "campus_female",
    "children_boys", "children_girls", "online_male", "online_female",
)

CSV_HEADERS = (
    "zone", "region", "division", "reporting_date", "submitted_at",
    "church_locations", "pastors", "workers",
    "adults_male", "adults_female", "youths_male", "youths_female",
    "ypf_male", "ypf_female", "campus_male", "campus_female",
    "children_boys", "children_girls", "online_male", "online_female",
)


def csv_cell(value):
    """Keep spreadsheet apps from evaluating a text cell as a formula."""
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


PLACEHOLDER_ADMIN_PASSWORDS = {"replace-with-a-strong-password", "changeme", "password"}


def admin_available():
    """Admin stays locked until all three secrets are present and not placeholders."""
    if not all(os.getenv(key) for key in ("ADMIN_USER", "ADMIN_PASSWORD", "SECRET_KEY")):
        return False
    return os.getenv("ADMIN_PASSWORD") not in PLACEHOLDER_ADMIN_PASSWORDS


def secure_compare(left, right):
    """Constant-time comparison that also accepts non-ASCII form input."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def is_admin():
    return admin_available() and session.get("admin") is True


def require_admin():
    """Return a redirect response when signed out, otherwise None."""
    if not is_admin():
        return redirect(url_for("admin_login"))
    return None


def fetch_reports(query=""):
    """Return newest-first reports, optionally filtered by location text."""
    query = (query or "").strip()
    columns = ", ".join(REPORT_COLUMNS)
    sql = f"SELECT {columns} FROM attendance_reports"
    params = ()
    if query:
        escaped = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        like = f"%{escaped}%"
        sql += " WHERE zone LIKE %s ESCAPE '!' OR region LIKE %s ESCAPE '!' OR division LIKE %s ESCAPE '!'"
        params = (like, like, like)
    sql += " ORDER BY submitted_at DESC, id DESC"

    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except Exception as exc:  # noqa: BLE001 - the route shows a clear error state
        app.logger.warning("Could not load reports: %s", exc)
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass


def fetch_submitted_pairs(reporting_date):
    """Return (zone, region, division) tuples submitted for one report date."""
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT DISTINCT zone, region, division FROM attendance_reports
               WHERE reporting_date = %s""",
            (reporting_date,),
        )
        pairs = [
            (row["zone"], row["region"], row["division"])
            for row in cursor.fetchall()
        ]
        cursor.close()
        return pairs
    except Exception as exc:  # noqa: BLE001 - the route shows a clear error state
        app.logger.warning("Could not load submitted divisions: %s", exc)
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass


def find_defaulters(reporting_date, submitted_pairs):
    """List every division in zones.py absent from submitted_pairs for this date.

    ``reporting_date`` is the date the caller filtered ``submitted_pairs`` by;
    the comparison itself is on the full (zone, region, division) path.
    """
    submitted = {tuple(pair) for pair in submitted_pairs}
    missing = []
    for zone, regions in ZONE_STRUCTURE.items():
        for region, divisions in regions.items():
            for division in divisions:
                if (zone, region, division) not in submitted:
                    missing.append(
                        {"zone": zone, "region": region, "division": division}
                    )
    return missing


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if not admin_available():
            return (
                render_template(
                    "admin_login.html",
                    error="Admin is not configured. Set ADMIN_USER, ADMIN_PASSWORD and SECRET_KEY in .env.",
                ),
                503,
            )
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user_ok = secure_compare(username, os.getenv("ADMIN_USER") or "")
        pass_ok = secure_compare(password, os.getenv("ADMIN_PASSWORD") or "")
        if user_ok and pass_ok:
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin"))
        return (
            render_template(
                "admin_login.html", error="Those credentials were not recognised."
            ),
            401,
        )
    if not admin_available():
        return (
            render_template(
                "admin_login.html",
                error="Admin is not configured. Set ADMIN_USER, ADMIN_PASSWORD and SECRET_KEY in .env.",
            ),
            503,
        )
    return render_template("admin_login.html", error=None)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin():
    gate = require_admin()
    if gate is not None:
        return gate

    tab = request.args.get("tab", "reports")
    if tab not in ("reports", "defaulters"):
        tab = "reports"
    query = request.args.get("q", "").strip()

    rows = []
    missing = []
    data_error = None
    try:
        if tab == "reports":
            rows = fetch_reports(query)
        else:
            pairs = fetch_submitted_pairs(REPORTING_DATE.isoformat())
            missing = find_defaulters(REPORTING_DATE.isoformat(), pairs)
    except Exception as exc:  # noqa: BLE001 - never present stale data as current
        app.logger.warning("Admin data unavailable: %s", exc)
        rows = []
        missing = []
        data_error = "Could not load reports. Check the database connection and try again."

    return render_template(
        "admin.html",
        tab=tab,
        query=query,
        rows=rows,
        missing=missing,
        data_error=data_error,
        reporting_date=REPORTING_LABEL,
    )


@app.route("/admin/export.csv")
def admin_export():
    gate = require_admin()
    if gate is not None:
        return gate

    query = request.args.get("q", "").strip()
    try:
        rows = fetch_reports(query)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Admin export unavailable: %s", exc)
        return Response(
            "Could not load reports. Check the database connection and try again.",
            status=503,
            mimetype="text/plain",
        )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for row in rows:
        writer.writerow(
            [csv_cell(row.get(column, "")) for column in REPORT_COLUMNS[1:]]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="membership-reports.csv"'},
    )


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT") or 5000), debug=True)
