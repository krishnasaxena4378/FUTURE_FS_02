# FUTURE_FS_02 - Client Lead Management System

A small web app to track client leads. Built with **HTML, CSS, JavaScript, Python Flask and SQLite**. No other frameworks.

## Features

- Dashboard: total, new, contacted and converted leads (click a card to see those leads)
- Lead table with View / Edit / Delete buttons
- Add lead: name, email, phone, enquiry source, status, notes
- View lead details
- Edit lead
- Update status: New, Contacted, Converted
- Delete with a confirmation prompt
- Search by name or email
- Filter by status
- Data is stored in SQLite (`leads.db`), so it is still there after you restart the app
- Server-side validation (the server checks the data even if someone bypasses the browser)

## Project structure

```
FUTURE_FS_02/
├── app.py              # Flask app: database, validation, all routes
├── requirements.txt    # Python packages needed
├── test_app.py         # Automated tests
├── leads.db            # SQLite database (created automatically, not in Git)
├── templates/          # HTML pages (Jinja2 templates)
│   ├── base.html       # Shared header, navigation and flash messages
│   ├── dashboard.html
│   ├── leads.html      # Table + search + filter
│   ├── lead_form.html  # Used for both Add and Edit
│   └── lead_detail.html
└── static/
    ├── style.css
    └── script.js       # Delete confirmation prompt
```

## How to run

You need Python 3.9 or newer.

```bash
# 1. Go into the project folder
cd FUTURE_FS_02

# 2. (Recommended) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Flask
pip install -r requirements.txt

# 4. Start the app
python app.py
```

Open **http://127.0.0.1:5000** in your browser. The database file is created on first start.

Run the tests:

```bash
python -m unittest -v
```

> Before deploying anywhere public, set a real secret key (`SECRET_KEY=some-long-random-text`) and turn off `debug=True` in `app.py`.

---

## How it works (in easy English)

### 1. Flask routes

A **route** connects a web address (URL) to a Python function. When you visit the URL, Flask runs the function and sends back the result.

```python
@app.route("/leads")
def list_leads():
    ...
```

This says: "when someone opens `/leads`, run `list_leads()`."

A route can accept **GET** (just show a page) or **POST** (the browser is sending data to save or change). `<int:lead_id>` in a URL is a variable: `/leads/5` runs the function with `lead_id = 5`.

| URL | Method | What it does |
|---|---|---|
| `/` | GET | Dashboard with the four counts |
| `/leads` | GET | List leads. Optional `?q=text` and `?status=New` |
| `/leads/add` | GET, POST | GET shows the empty form, POST saves a new lead |
| `/leads/<id>` | GET | View one lead |
| `/leads/<id>/edit` | GET, POST | GET shows the filled form, POST saves changes |
| `/leads/<id>/status` | POST | Change only the status |
| `/leads/<id>/delete` | POST | Delete the lead |

Delete is **POST only**. If delete were a normal link (GET), a search engine or a mis-click on a link could delete data.

### 2. HTML forms

A form collects what the user types and sends it to the server.

```html
<form method="post">
  <input type="text" name="name">
  <button type="submit">Add Lead</button>
</form>
```

- `method="post"` sends the data hidden inside the request. `method="get"` puts it in the URL (we use that for search, so a search can be bookmarked).
- The `name="..."` on each input is the key Flask uses to read the value: `request.form.get("name")`.
- Add and Edit share one template (`lead_form.html`). For Edit, the inputs are pre-filled using `value="{{ lead['name'] }}"`.

**Validation** happens twice. HTML attributes like `required` give quick feedback in the browser, but anyone can bypass them, so `validate_lead()` in `app.py` checks everything again on the server. If something is wrong, the form is shown again with error messages and nothing is saved.

**Safety built in:**
- SQL uses `?` placeholders, so typed text can never become SQL code (this stops SQL injection).
- Jinja2 escapes `<` and `>` when printing, so typed HTML or scripts show as plain text (this stops XSS).

### 3. CRUD

CRUD means the four basic things an app does with data:

| Letter | Meaning | In this app | SQL command |
|---|---|---|---|
| **C** | Create | Add Lead form | `INSERT` |
| **R** | Read | Lead list, lead details, dashboard | `SELECT` |
| **U** | Update | Edit form, status update | `UPDATE` |
| **D** | Delete | Delete button | `DELETE` |

### 4. SQL used in this project

SQL is the language used to talk to the database. A database table is like a spreadsheet: columns are fields, rows are leads.

```sql
-- Create the table (runs once at startup, only if it doesn't exist)
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   -- unique number, added automatically
    name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT,
    source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'New',
    notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create: add a new lead
INSERT INTO leads (name, email, phone, source, status, notes) VALUES (?, ?, ?, ?, ?, ?);

-- Read: all leads, newest first
SELECT * FROM leads ORDER BY id DESC;

-- Read: one lead
SELECT * FROM leads WHERE id = ?;

-- Search by name or email (the % means "anything before/after")
SELECT * FROM leads WHERE (name LIKE '%asha%' OR email LIKE '%asha%') AND status = 'New';

-- Dashboard: count leads per status
SELECT status, COUNT(*) FROM leads GROUP BY status;

-- Update
UPDATE leads SET status = ? WHERE id = ?;

-- Delete
DELETE FROM leads WHERE id = ?;
```

The `?` marks are filled in safely by Python: `db.execute("DELETE FROM leads WHERE id = ?", (lead_id,))`. After any change, `db.commit()` saves it permanently to the `leads.db` file. That file is why the data survives a restart.

### 5. The delete confirmation

Each delete form has `data-confirm="Delete Asha? This cannot be undone."`. `script.js` listens for the form being submitted and shows the browser's `confirm()` box. If the user clicks Cancel, the submit is stopped and nothing is deleted.

---

## Deploy on Render (paid, about $7.25/month, data is kept)

Render runs the app as a normal server, and a **persistent disk** keeps `leads.db` safe across restarts and redeploys.
(Vercel does not work for this app: its disk is read-only, so SQLite fails with `unable to open database file`.)

The repo already contains `render.yaml`, which sets everything up (gunicorn, a 1 GB disk at `/var/data`, `DATABASE_PATH`, `SECRET_KEY`).

1. Create an account at https://render.com and add a payment method.
2. Click **New +** > **Blueprint**, connect your GitHub account and pick the `FUTURE_FS_02` repository.
3. Render reads `render.yaml` and shows one web service with a disk. Click **Apply** / **Deploy**.
4. Wait for the first deploy to finish (a few minutes). Open the `https://lead-manager-xxxx.onrender.com` link shown on the service page.
5. To update later: `git push` to `main` and Render redeploys automatically.

Cost: the paid web service is $7/month and the disk is $0.25 per GB per month (see https://render.com/pricing).
Do not remove the disk: without it, the database file is erased on every deploy.

Without Blueprints you can create a **Web Service** by hand instead: Build command `pip install -r requirements.txt`,
Start command `gunicorn app:app`, add a Disk mounted at `/var/data`, and set the environment variable
`DATABASE_PATH=/var/data/leads.db` plus a random `SECRET_KEY`.

## Deploy on PythonAnywhere (free)

SQLite needs a disk it can write to. Serverless hosts such as **Vercel** have a read-only disk, so this app crashes there with
`sqlite3.OperationalError: unable to open database file`. PythonAnywhere keeps your files, so the app works without changes.

1. Create a free account at https://www.pythonanywhere.com (your site will be `YOURNAME.pythonanywhere.com`).
2. Open the **Consoles** tab, start a **Bash** console and run:
   ```bash
   git clone https://github.com/YOUR-USERNAME/FUTURE_FS_02.git
   cd FUTURE_FS_02
   pip install --user -r requirements.txt
   ```
3. Open the **Web** tab, click **Add a new web app**, choose **Manual configuration** (not Flask), and pick a Python 3.10+ version.
4. On the Web tab, under **Code**, click the **WSGI configuration file** link. Delete everything in it and paste:
   ```python
   import os
   import sys

   project = "/home/YOURNAME/FUTURE_FS_02"
   if project not in sys.path:
       sys.path.insert(0, project)

   os.environ["SECRET_KEY"] = "put-a-long-random-text-here"

   from app import app as application
   ```
   Replace `YOURNAME` with your PythonAnywhere username. Save.
5. Click the green **Reload** button on the Web tab, then open `https://YOURNAME.pythonanywhere.com`.

`leads.db` is created automatically in the project folder the first time the app loads, and it stays there between reloads.
To update the site later: in a Bash console run `cd FUTURE_FS_02 && git pull`, then click **Reload**.

If something fails, check the **Error log** link on the Web tab.

## Upload to GitHub

**Step 1 - Create the repository on GitHub**

1. Sign in at https://github.com and click **New repository**.
2. Repository name: `FUTURE_FS_02`
3. Leave it empty (do **not** tick "Add a README", we already have one). Click **Create repository**.

**Step 2 - Push your code from your computer**

```bash
cd FUTURE_FS_02
git init
git add .
git commit -m "Client Lead Management System"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/FUTURE_FS_02.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. If Git asks for a password, use a [personal access token](https://github.com/settings/tokens) instead of your account password.

`leads.db` is listed in `.gitignore`, so your real lead data is not uploaded.

**Step 3 - Later changes**

```bash
git add .
git commit -m "Describe what you changed"
git push
```

## Ideas for later

- User login
- Export leads to CSV
- Pagination for long lists
- Several dated notes per lead
