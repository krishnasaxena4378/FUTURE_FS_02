"""Client Lead Management System - a small Flask + SQLite app."""
import os
import re
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["DATABASE"] = os.path.join(os.path.dirname(__file__), "leads.db")

STATUSES = ["New", "Contacted", "Converted"]
SOURCES = ["Website", "Referral", "Social Media", "Email", "Phone Call", "Other"]


# ---------------------------------------------------------------- database
def get_db():
    """Open one database connection per request and reuse it."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # lets us use row["name"]
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the leads table if it does not exist yet."""
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL,
            phone      TEXT,
            source     TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'New',
            notes      TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()
    db.close()


# -------------------------------------------------------------- validation
def validate_lead(form):
    """Clean the form data and return (clean_data, list_of_errors)."""
    data = {
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip(),
        "phone": form.get("phone", "").strip(),
        "source": form.get("source", "").strip(),
        "status": form.get("status", "New").strip(),
        "notes": form.get("notes", "").strip(),
    }
    errors = []

    if not data["name"]:
        errors.append("Name is required.")
    elif len(data["name"]) > 100:
        errors.append("Name must be 100 characters or less.")

    if not data["email"]:
        errors.append("Email is required.")
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data["email"]):
        errors.append("Please enter a valid email address.")

    if data["phone"] and not re.fullmatch(r"[0-9+\-()\s]{7,20}", data["phone"]):
        errors.append("Phone may only contain digits, spaces, + - ( ) and be 7-20 characters.")

    if data["source"] not in SOURCES:
        errors.append("Please choose an enquiry source.")

    if data["status"] not in STATUSES:
        errors.append("Status must be New, Contacted or Converted.")

    if len(data["notes"]) > 2000:
        errors.append("Notes must be 2000 characters or less.")

    return data, errors


# ------------------------------------------------------------------ routes
@app.route("/")
def dashboard():
    """Show the four counts at the top of the app."""
    db = get_db()
    rows = db.execute("SELECT status, COUNT(*) AS total FROM leads GROUP BY status").fetchall()
    counts = {row["status"]: row["total"] for row in rows}
    stats = {
        "total": sum(counts.values()),
        "new": counts.get("New", 0),
        "contacted": counts.get("Contacted", 0),
        "converted": counts.get("Converted", 0),
    }
    recent = db.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("dashboard.html", stats=stats, recent=recent)


@app.route("/leads")
def list_leads():
    """Show all leads. Optional ?q=search text and ?status=New/Contacted/Converted."""
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    sql = "SELECT * FROM leads WHERE 1=1"
    params = []

    if search:
        sql += " AND (name LIKE ? OR email LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if status in STATUSES:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY id DESC"
    leads = get_db().execute(sql, params).fetchall()
    return render_template("leads.html", leads=leads, search=search, status=status, statuses=STATUSES)


@app.route("/leads/add", methods=["GET", "POST"])
def add_lead():
    """GET shows the empty form. POST validates and saves a new lead."""
    if request.method == "POST":
        data, errors = validate_lead(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("lead_form.html", lead=data, sources=SOURCES,
                                   statuses=STATUSES, editing=False), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO leads (name, email, phone, source, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (data["name"], data["email"], data["phone"], data["source"], data["status"], data["notes"]),
        )
        db.commit()
        flash("Lead added successfully.", "success")
        return redirect(url_for("view_lead", lead_id=cursor.lastrowid))

    blank = {"name": "", "email": "", "phone": "", "source": "", "status": "New", "notes": ""}
    return render_template("lead_form.html", lead=blank, sources=SOURCES, statuses=STATUSES, editing=False)


def get_lead_or_404(lead_id):
    lead = get_db().execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if lead is None:
        abort(404)
    return lead


@app.route("/leads/<int:lead_id>")
def view_lead(lead_id):
    """Show every detail of one lead."""
    lead = get_lead_or_404(lead_id)
    return render_template("lead_detail.html", lead=lead, statuses=STATUSES)


@app.route("/leads/<int:lead_id>/edit", methods=["GET", "POST"])
def edit_lead(lead_id):
    """GET shows the form filled with current values. POST validates and updates."""
    lead = get_lead_or_404(lead_id)

    if request.method == "POST":
        data, errors = validate_lead(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("lead_form.html", lead=data, sources=SOURCES,
                                   statuses=STATUSES, editing=True), 400

        db = get_db()
        db.execute(
            "UPDATE leads SET name = ?, email = ?, phone = ?, source = ?, status = ?, notes = ? WHERE id = ?",
            (data["name"], data["email"], data["phone"], data["source"], data["status"], data["notes"], lead_id),
        )
        db.commit()
        flash("Lead updated.", "success")
        return redirect(url_for("view_lead", lead_id=lead_id))

    return render_template("lead_form.html", lead=lead, sources=SOURCES, statuses=STATUSES, editing=True)


@app.route("/leads/<int:lead_id>/status", methods=["POST"])
def update_status(lead_id):
    """Change only the status of a lead."""
    get_lead_or_404(lead_id)
    status = request.form.get("status", "")
    if status not in STATUSES:
        flash("Status must be New, Contacted or Converted.", "error")
        return redirect(url_for("view_lead", lead_id=lead_id))

    db = get_db()
    db.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    db.commit()
    flash(f"Status changed to {status}.", "success")
    return redirect(url_for("view_lead", lead_id=lead_id))


@app.route("/leads/<int:lead_id>/delete", methods=["POST"])
def delete_lead(lead_id):
    """Delete a lead. POST only, so a link or a crawler can never delete by accident."""
    get_lead_or_404(lead_id)
    db = get_db()
    db.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    db.commit()
    flash("Lead deleted.", "success")
    return redirect(url_for("list_leads"))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
