"""Simple tests. Run with:  python -m unittest -v"""
import os
import tempfile
import unittest

import app as lead_app

GOOD = {"name": "Asha Rao", "email": "asha@example.com", "phone": "+91 98765 43210",
        "source": "Website", "status": "New", "notes": "Wants a quote"}


class LeadTests(unittest.TestCase):
    def setUp(self):
        # Use a throw-away database file so tests never touch real data.
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        lead_app.app.config["DATABASE"] = self.path
        lead_app.app.config["TESTING"] = True
        lead_app.init_db()
        self.client = lead_app.app.test_client()

    def tearDown(self):
        os.remove(self.path)

    def add(self, **changes):
        data = dict(GOOD, **changes)
        return self.client.post("/leads/add", data=data, follow_redirects=True)

    # 1. dashboard
    def test_dashboard_empty_and_counts(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.add(name="A", email="a@x.com", status="New")
        self.add(name="B", email="b@x.com", status="Contacted")
        self.add(name="C", email="c@x.com", status="Converted")
        self.add(name="D", email="d@x.com", status="Converted")
        page = self.client.get("/").get_data(as_text=True)
        for number, label in [("4", "Total Leads"), ("1", "New"), ("1", "Contacted"), ("2", "Converted")]:
            self.assertRegex(page, rf'card-number">{number}</span>\s*<span class="card-label">{label}')

    # 2 + 3 + 4. add, list, view
    def test_add_list_view(self):
        response = self.add()
        self.assertIn("Lead added successfully", response.get_data(as_text=True))
        self.assertIn("Wants a quote", response.get_data(as_text=True))  # detail page shows notes
        listing = self.client.get("/leads").get_data(as_text=True)
        self.assertIn("Asha Rao", listing)
        self.assertIn("asha@example.com", listing)

    # server-side validation
    def test_validation_errors(self):
        for bad, message in [
            ({"name": ""}, "Name is required"),
            ({"email": "not-an-email"}, "valid email"),
            ({"email": ""}, "Email is required"),
            ({"phone": "abc"}, "Phone may only"),
            ({"source": "Mars"}, "enquiry source"),
            ({"status": "Hacked"}, "Status must be"),
            ({"name": "x" * 101}, "100 characters"),
        ]:
            response = self.client.post("/leads/add", data=dict(GOOD, **bad))
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn(message, response.get_data(as_text=True))
        self.assertNotIn("Asha", self.client.get("/leads").get_data(as_text=True))  # nothing saved

    # 5. edit
    def test_edit(self):
        self.add()
        form = self.client.get("/leads/1/edit").get_data(as_text=True)
        self.assertIn('value="Asha Rao"', form)  # form is pre-filled
        response = self.client.post("/leads/1/edit", data=dict(GOOD, name="Asha Sharma", notes="Updated"),
                                    follow_redirects=True)
        page = response.get_data(as_text=True)
        self.assertIn("Lead updated", page)
        self.assertIn("Asha Sharma", page)
        bad = self.client.post("/leads/1/edit", data=dict(GOOD, email="bad"))
        self.assertEqual(bad.status_code, 400)

    # 6. status
    def test_status_update(self):
        self.add()
        page = self.client.post("/leads/1/status", data={"status": "Converted"},
                                follow_redirects=True).get_data(as_text=True)
        self.assertIn("Status changed to Converted", page)
        page = self.client.post("/leads/1/status", data={"status": "Bogus"},
                                follow_redirects=True).get_data(as_text=True)
        self.assertIn("Status must be", page)
        self.assertIn("badge-converted", page)  # unchanged

    # 7. delete
    def test_delete(self):
        self.add()
        self.assertEqual(self.client.get("/leads/1/delete").status_code, 405)  # GET not allowed
        page = self.client.post("/leads/1/delete", follow_redirects=True).get_data(as_text=True)
        self.assertIn("Lead deleted", page)
        self.assertEqual(self.client.get("/leads/1").status_code, 404)
        # the page offers a confirmation prompt
        self.add()
        self.assertIn("data-confirm", self.client.get("/leads").get_data(as_text=True))

    # 8 + 9. search and filter
    def test_search_and_filter(self):
        self.add(name="Asha Rao", email="asha@example.com", status="New")
        self.add(name="Bob Smith", email="bob@corp.com", status="Contacted")
        by_name = self.client.get("/leads?q=asha").get_data(as_text=True)
        self.assertIn("Asha Rao", by_name)
        self.assertNotIn("Bob Smith", by_name)
        by_email = self.client.get("/leads?q=corp.com").get_data(as_text=True)
        self.assertIn("Bob Smith", by_email)
        self.assertNotIn("Asha Rao", by_email)
        by_status = self.client.get("/leads?status=Contacted").get_data(as_text=True)
        self.assertIn("Bob Smith", by_status)
        self.assertNotIn("Asha Rao", by_status)
        both = self.client.get("/leads?q=bob&status=New").get_data(as_text=True)
        self.assertNotIn("Bob Smith", both)

    # SQL injection attempt must be harmless
    def test_sql_injection_is_safe(self):
        self.add()
        page = self.client.get("/leads?q=' OR '1'='1").get_data(as_text=True)
        self.assertNotIn("Asha Rao", page)

    # HTML in user input must be escaped (XSS)
    def test_html_is_escaped(self):
        self.add(name="<script>alert(1)</script>")
        page = self.client.get("/leads").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_missing_lead_is_404(self):
        for url in ["/leads/99", "/leads/99/edit"]:
            self.assertEqual(self.client.get(url).status_code, 404)

    # 10. persistence: a brand-new connection (like a restart) still sees the data
    def test_data_persists_in_file(self):
        self.add()
        import sqlite3
        rows = sqlite3.connect(self.path).execute("SELECT name FROM leads").fetchall()
        self.assertEqual(rows, [("Asha Rao",)])


if __name__ == "__main__":
    unittest.main()
