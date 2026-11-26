import unittest

import app as attendance_app


REQUIRED_SELECTS = ("zone", "region", "division")
REQUIRED_INTEGERS = (
    "total_locations",
    "total_pastors",
    "total_workers",
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
    "campus_male",
    "campus_female",
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

    def test_rendered_form_shows_twelve_required_fields(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn("0 / 12", html)
        self.assertNotIn(
            '<span class="online-title">Online attendees <span class="req"',
            html,
        )

    def test_rendered_form_has_hidden_submit_progress_bar(self):
        html = attendance_app.app.test_client().get("/").get_data(as_text=True)

        self.assertIn('id="submitProgress"', html)
        self.assertIn('class="submit-progress"', html)
        self.assertIn('aria-label="Saving report"', html)
        self.assertIn('class="submit-progress-track"', html)
        self.assertIn('class="submit-progress-fill"', html)
        self.assertIn('id="submitProgress" class="submit-progress" role="status" aria-label="Saving report" hidden', html)


if __name__ == "__main__":
    unittest.main()
