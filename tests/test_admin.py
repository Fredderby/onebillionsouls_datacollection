import csv
import io
import os
import re
import unittest
from unittest.mock import patch

import app as attendance_app
from zones import ZONE_STRUCTURE


CREDENTIALS = {
    "SECRET_KEY": "unit-test-secret-key",
    "ADMIN_USER": "admin",
    "ADMIN_PASSWORD": "correct-horse",
}

SAMPLE_ROW = {
    "id": 7,
    "zone": "Greater Accra Zone",
    "region": "Kasoa",
    "division": "Weija",
    "reporting_date": "2026-11-29",
    "submitted_at": "2026-11-26 18:00:00",
    "total_locations": 2,
    "total_pastors": 3,
    "workers_brothers": 5,
    "workers_sisters": 3,
    "total_workers": 8,
    "adults_male": 20,
    "adults_female": 22,
    "youths_male": 4,
    "youths_female": 5,
    "ypf_male": 0,
    "ypf_female": 0,
    "campus_male": 0,
    "campus_female": 0,
    "children_boys": 6,
    "children_girls": 7,
    "online_male": 1,
    "online_female": 2,
}


def division_count():
    return sum(
        len(divisions)
        for regions in ZONE_STRUCTURE.values()
        for divisions in regions.values()
    )


class DefaulterTests(unittest.TestCase):
    def test_lists_every_division_when_nothing_was_submitted(self):
        missing = attendance_app.find_defaulters("2026-11-29", [])

        self.assertEqual(len(missing), division_count())
        self.assertEqual(
            missing[0],
            {"zone": "Central-Western Zone", "region": "Tarkwa", "division": "Tarkwa div"},
        )

    def test_excludes_a_division_that_did_submit(self):
        submitted = [("Greater Accra Zone", "Kasoa", "Weija")]

        missing = attendance_app.find_defaulters("2026-11-29", submitted)

        paths = [(row["zone"], row["region"], row["division"]) for row in missing]
        self.assertEqual(len(missing), division_count() - 1)
        self.assertNotIn(submitted[0], paths)


class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        self.client = attendance_app.app.test_client()
        self.env = patch.dict(os.environ, CREDENTIALS)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_admin_redirects_to_login_when_signed_out(self):
        response = self.client.get("/admin")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_login_page_renders(self):
        response = self.client.get("/admin/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Admin sign in", response.data)

    def test_login_page_shows_setup_message_when_secrets_are_missing(self):
        with patch.dict(
            os.environ,
            {"ADMIN_USER": "", "ADMIN_PASSWORD": "", "SECRET_KEY": ""},
        ):
            response = self.client.get("/admin/login")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Admin is not configured", response.data)

    def test_placeholder_password_keeps_admin_locked(self):
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "replace-with-a-strong-password"}):
            response = self.client.post(
                "/admin/login",
                data={
                    "username": "admin",
                    "password": "replace-with-a-strong-password",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_missing_secrets_revoke_an_existing_session(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )
        self.assertEqual(self.client.get("/admin").status_code, 200)

        with patch.dict(
            os.environ,
            {"ADMIN_USER": "", "ADMIN_PASSWORD": "", "SECRET_KEY": ""},
        ):
            response = self.client.get("/admin")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_wrong_credentials_do_not_create_a_session(self):
        response = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "wrong"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_non_ascii_username_returns_401_instead_of_a_server_error(self):
        response = self.client.post(
            "/admin/login",
            data={"username": "admín", "password": "correct-horse"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_valid_credentials_create_a_session(self):
        response = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_logout_clears_the_session(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        self.client.post("/admin/logout")

        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_export_redirects_when_signed_out(self):
        response = self.client.get("/admin/export.csv")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_export_writes_csv_when_signed_in(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            response = self.client.get("/admin/export.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.content_type)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        text = response.get_data(as_text=True)
        self.assertIn("zone,region,division", text)
        self.assertIn("Greater Accra Zone,Kasoa,Weija", text)

    def test_export_header_matches_data_columns(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            text = self.client.get("/admin/export.csv").get_data(as_text=True)

        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), len(rows[1]))
        self.assertEqual(rows[1][0], "Greater Accra Zone")
        self.assertEqual(rows[1][-1], "2")

    def test_export_neutralises_formula_like_text(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )
        hostile = dict(SAMPLE_ROW, zone="=1+1")

        with patch.object(attendance_app, "fetch_reports", return_value=[hostile]):
            text = self.client.get("/admin/export.csv").get_data(as_text=True)

        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[1][0], "'=1+1")

    def test_export_reports_database_failure(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        with patch.object(attendance_app, "fetch_reports", side_effect=RuntimeError("offline")):
            response = self.client.get("/admin/export.csv")

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Could not load reports", response.data)

    def test_export_does_not_include_campus_columns(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            text = self.client.get("/admin/export.csv").get_data(as_text=True)

        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(len(rows[0]), 20)
        self.assertNotIn("campus_male", rows[0])
        self.assertNotIn("campus_female", rows[0])

    def test_export_includes_split_worker_columns(self):
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            text = self.client.get("/admin/export.csv").get_data(as_text=True)

        rows = list(csv.reader(io.StringIO(text)))
        self.assertIn("workers_brothers", rows[0])
        self.assertIn("workers_sisters", rows[0])
        self.assertIn("workers_total", rows[0])
        self.assertEqual(rows[1][rows[0].index("workers_brothers")], "5")
        self.assertEqual(rows[1][rows[0].index("workers_sisters")], "3")
        self.assertEqual(rows[1][rows[0].index("workers_total")], "8")


class AdminPagesTests(unittest.TestCase):
    def setUp(self):
        self.client = attendance_app.app.test_client()
        self.env = patch.dict(os.environ, CREDENTIALS)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

    def test_reports_tab_shows_submitted_rows(self):
        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            response = self.client.get("/admin")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weija", response.data)
        self.assertIn(b"Reports", response.data)
        self.assertIn(b"Defaulters", response.data)

    def test_reports_tab_surfaces_database_failure(self):
        with patch.object(attendance_app, "fetch_reports", side_effect=RuntimeError("offline")):
            response = self.client.get("/admin")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not load reports", response.data)

    def test_reports_tab_excludes_campus_from_totals(self):
        row = dict(SAMPLE_ROW, campus_male=100, campus_female=100)

        with patch.object(attendance_app, "fetch_reports", return_value=[row]):
            response = self.client.get("/admin")

        html = response.get_data(as_text=True)
        self.assertIn('<td class="numeric">64</td>', html)
        self.assertIn('<td class="numeric total">67</td>', html)
        self.assertNotIn("264", html)

    def test_defaulters_tab_walks_the_whole_hierarchy(self):
        with patch.object(attendance_app, "fetch_submitted_pairs", return_value=[]):
            response = self.client.get("/admin?tab=defaulters")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tarkwa div", response.data)
        self.assertIn(b"Sunday, 29 November 2026", response.data)

    def test_defaulters_tab_surfaces_database_failure(self):
        with patch.object(
            attendance_app, "fetch_submitted_pairs", side_effect=RuntimeError("offline")
        ):
            response = self.client.get("/admin?tab=defaulters")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not load reports", response.data)

    def test_defaulters_tab_uses_the_current_reporting_date(self):
        with patch.object(attendance_app, "fetch_submitted_pairs", return_value=[]) as fetch:
            self.client.get("/admin?tab=defaulters")

        fetch.assert_called_once_with("2026-11-29")

    def test_search_term_is_passed_to_the_query(self):
        with patch.object(attendance_app, "fetch_reports", return_value=[]) as fetch:
            self.client.get("/admin?q=Kasoa")

        fetch.assert_called_once_with("Kasoa")

    def test_like_wildcards_are_escaped(self):
        class Cursor:
            def execute(self, sql, params):
                self.sql = sql
                self.params = params

            def fetchall(self):
                return []

            def close(self):
                pass

        cursor = Cursor()

        class Connection:
            def cursor(self, dictionary=False):
                return cursor

            def close(self):
                pass

        with patch.object(attendance_app, "get_connection", return_value=Connection()):
            attendance_app.fetch_reports("100%_")

        self.assertIn("ESCAPE '!'", cursor.sql)
        self.assertEqual(cursor.params, ("%100!%!_%",) * 3)


class AdminDeleteTests(unittest.TestCase):
    def setUp(self):
        self.client = attendance_app.app.test_client()
        self.env = patch.dict(os.environ, CREDENTIALS)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse"},
        )

    def csrf_token(self):
        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            html = self.client.get("/admin").get_data(as_text=True)
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        self.assertIsNotNone(match, "Reports page must include a CSRF token")
        return match.group(1)

    def delete_connection(self, calls):
        class Cursor:
            def execute(self, sql, params):
                calls.append((" ".join(sql.split()), params))

            def close(self):
                pass

        class Connection:
            def cursor(self, dictionary=False):
                return Cursor()

            def commit(self):
                pass

            def close(self):
                pass

        return Connection()

    def test_signed_out_admin_cannot_delete(self):
        self.client.post("/admin/logout")
        calls = []

        with patch.object(
            attendance_app, "get_connection", return_value=self.delete_connection(calls)
        ):
            response = self.client.post("/admin/reports/7/delete")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])
        self.assertEqual(calls, [])

    def test_reports_page_offers_a_styled_delete_dialog_for_each_row(self):
        with patch.object(attendance_app, "fetch_reports", return_value=[SAMPLE_ROW]):
            html = self.client.get("/admin").get_data(as_text=True)

        self.assertIn('<dialog id="deleteDialog" class="admin-dialog"', html)
        self.assertIn('data-delete-action="/admin/reports/7/delete"', html)
        self.assertIn('data-delete-label="Weija"', html)
        self.assertIn('id="confirmDeleteBtn"', html)
        self.assertIn('name="csrf_token"', html)
        self.assertIn('name="q"', html)
        self.assertIn("/static/admin.js", html)

    def test_delete_removes_the_selected_report_and_keeps_search(self):
        token = self.csrf_token()
        calls = []

        with patch.object(
            attendance_app, "get_connection", return_value=self.delete_connection(calls)
        ), patch.object(attendance_app, "fetch_reports", return_value=[]):
            response = self.client.post(
                "/admin/reports/7/delete",
                data={"csrf_token": token, "q": "Kasoa"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("q=Kasoa", response.headers["Location"])
        self.assertIn("deleted=1", response.headers["Location"])
        self.assertEqual(
            calls, [("DELETE FROM attendance_reports WHERE id = %s", (7,))]
        )
        follow_up = self.client.get(response.headers["Location"])
        self.assertIn(b"Report deleted.", follow_up.data)

    def test_delete_rejects_an_invalid_csrf_token(self):
        self.csrf_token()
        calls = []

        with patch.object(
            attendance_app, "get_connection", return_value=self.delete_connection(calls)
        ):
            response = self.client.post(
                "/admin/reports/7/delete",
                data={"csrf_token": "not-the-session-token", "q": "Kasoa"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid form token", response.data)
        self.assertEqual(calls, [])

    def test_delete_surfaces_database_failure(self):
        token = self.csrf_token()

        with patch.object(attendance_app, "get_connection", side_effect=RuntimeError("offline")):
            response = self.client.post(
                "/admin/reports/7/delete", data={"csrf_token": token}
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Could not delete report", response.data)


class FormEntryPointTests(unittest.TestCase):
    def test_form_footer_links_to_admin_login(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn('href="/admin/login"', html)
        self.assertIn("Admin", html)


if __name__ == "__main__":
    unittest.main()
