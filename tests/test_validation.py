import unittest

import app as attendance_app


REQUIRED_SELECTS = ("zone", "region", "division")
REQUIRED_INTEGERS = (
    "total_locations",
    "total_pastors",
    "workers_brothers",
    "workers_sisters",
    "adults_male",
    "adults_female",
    "youths_male",
    "youths_female",
    "children_boys",
    "children_girls",
)
OPTIONAL_INTEGERS = (
    "ypf_male",
    "ypf_female",
    "online_male",
    "online_female",
)


def required_payload():
    payload = {
        "zone": "Greater Accra Zone",
        "region": "Kasoa",
        "division": "Weija",
    }
    payload.update({name: "1" for name in REQUIRED_INTEGERS})
    return payload


class ValidationTests(unittest.TestCase):
    def test_optional_fields_may_be_blank_and_default_to_zero(self):
        payload = required_payload()
        payload.update({name: "" for name in OPTIONAL_INTEGERS})

        values, errors = attendance_app.validate(payload)

        self.assertEqual(errors, {})
        for name in OPTIONAL_INTEGERS:
            self.assertEqual(values[name], 0)

    def test_optional_field_still_rejects_non_numeric_input(self):
        payload = required_payload()
        payload["ypf_male"] = "twelve"

        _, errors = attendance_app.validate(payload)

        self.assertIn("ypf_male", errors)

    def test_every_required_field_is_still_enforced(self):
        for name in REQUIRED_SELECTS + REQUIRED_INTEGERS:
            with self.subTest(field=name):
                payload = required_payload()
                payload.pop(name, None)

                _, errors = attendance_app.validate(payload)

                self.assertIn(name, errors)

    def test_rendered_form_shows_thirteen_required_fields(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn("0 / 13", html)
        self.assertNotIn(
            '<span class="online-title">Online attendees <span class="req"',
            html,
        )

    def test_rendered_form_splits_church_workers(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn('name="workers_brothers"', html)
        self.assertIn('name="workers_sisters"', html)
        self.assertNotIn('name="total_workers"', html)

    def test_rendered_form_has_hidden_submit_progress_bar(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn('id="submitProgress"', html)
        self.assertIn('class="submit-progress"', html)
        self.assertIn('aria-label="Saving report"', html)
        self.assertIn('class="submit-progress-track"', html)
        self.assertIn('class="submit-progress-fill"', html)
        self.assertIn('id="submitProgress" class="submit-progress" role="status" aria-label="Saving report" hidden', html)

    def test_attendance_section_is_labelled_membership(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn('<h2 id="attendanceHeading">Membership</h2>', html)
        self.assertNotIn("Church attendance", html)

    def test_campus_exclusion_note_appears_before_location(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)
        note = "Campus workers and leaders are excluded from this form. Their reports are submitted separately."

        self.assertIn('class="form-note"', html)
        self.assertIn(note, html)
        self.assertLess(html.index(note), html.index('id="locationHeading"'))

    def test_insert_sql_matches_the_payload_shape(self):
        self.assertEqual(
            attendance_app.INSERT_SQL.count("%s"),
            len(attendance_app.ALL_FIELDS) + 2,
        )

    def test_workers_are_cleaned_as_split_values(self):
        values, errors = attendance_app.validate(required_payload())

        self.assertEqual(errors, {})
        self.assertEqual(values["workers_brothers"], 1)
        self.assertEqual(values["workers_sisters"], 1)
        self.assertNotIn("total_workers", values)

    def test_campus_fields_are_not_required_or_accepted(self):
        payload = required_payload()
        values, errors = attendance_app.validate(payload)

        self.assertEqual(errors, {})
        self.assertNotIn("campus_male", values)
        self.assertNotIn("campus_female", values)

        values, errors = attendance_app.validate(
            dict(payload, campus_male="10", campus_female="20")
        )

        self.assertEqual(errors, {})
        self.assertNotIn("campus_male", values)
        self.assertNotIn("campus_female", values)

    def test_rendered_form_has_no_campus_fields(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertNotIn("campus_male", html)
        self.assertNotIn("campus_female", html)


if __name__ == "__main__":
    unittest.main()
