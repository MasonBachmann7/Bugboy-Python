# BugBoy Python

A realistic Flask web application with intentionally embedded runtime errors, designed as a test harness for **BugStack's Python SDK**.

The app simulates a simple task/project management API. Each bug is hidden inside realistic business logic and can be triggered via a specific route.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The dashboard is available at **http://127.0.0.1:5000**.

## Project Structure

```
├── app.py              # Flask app, routes, bug registry, error handler
├── models.py           # Data models (User, Task, Project, etc.)
├── services.py         # Business logic services
├── utils.py            # Utility helpers
├── templates/
│   └── dashboard.html  # Dashboard UI
├── requirements.txt
└── README.md
```

## Triggerable Bugs

| # | Route | Method | Error Type | Description |
|---|-------|--------|------------|-------------|
| 1 | `/trigger/type-error` | GET | `TypeError` | Formatting a user's full display name — `last_name` is `None`, so `str + None` raises `TypeError`. |
| 2 | `/trigger/key-error` | GET | `KeyError` | Loading notification settings — the preferences dict exists but is missing the `'notifications'` key. |
| 3 | `/trigger/attribute-error` | GET | `AttributeError` | Looking up the assignee's email for an unassigned task — accessing `.email` on `None` raises `AttributeError`. |
| 4 | `/trigger/zero-division` | GET | `ZeroDivisionError` | Sprint velocity report divides total points by `sprint_length_days`, which defaults to `0`. |
| 5 | `/trigger/index-error` | GET | `IndexError` | Retrieving the latest comment on a task that has zero comments — `list[-1]` on an empty list. |
| 6 | `/trigger/file-not-found` | GET | `FileNotFoundError` | Loading a project config JSON file from a path that doesn't exist on disk. |
| 7 | `/trigger/json-decode-error` | GET | `JSONDecodeError` | Parsing a webhook response from a simulated third-party service that returns malformed JSON (unquoted key). |
| 8 | `/trigger/unicode-decode-error` | POST | `UnicodeDecodeError` | Processing an incoming webhook payload containing invalid UTF-8 byte sequences (`\xfc`). |
| 9 | `/trigger/recursion-error` | GET | `RecursionError` | Flattening a category tree that has an accidental circular parent→child reference. |
| 10 | `/trigger/connection-error` | GET | `ConnectionError` | Attempting to connect to an internal database host (`db.internal.local`) that is unreachable. |
| 11 | `/trigger/value-error` | POST | `ValueError` | Importing tasks from CSV where the priority column contains `"high"` instead of a number — `int("high")` fails. |
| 12 | `/trigger/permission-error` | GET | `PermissionError` | Exporting project data to a file that was locked read-only by a previous backup job. |
| 13 | `/trigger/timeout-error` | GET | `TimeoutError` | Running a slow aggregation query (10 s) that exceeds the 2 s timeout threshold. |
| 14 | `/trigger/thread-error` | GET | Unhandled Thread Exception | Firing a background notification whose handler crashes — the exception is captured via `threading.excepthook` and re-raised. |
| 15 | `/trigger/memory-error` | POST | `MemoryError` | Submitting a bulk-import payload that builds an O(n²) in-memory cross-reference index. Pass `?count=N` to control size (default 500,000). |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard UI — lists all bugs with trigger buttons |
| `GET /api/bugs` | JSON list of all registered bugs |
| `GET /health` | Health check — returns `{"status": "ok"}` |

## How It Works

Each bug is embedded inside realistic business logic spread across multiple modules (`models.py`, `services.py`, `utils.py`). When triggered, the errors produce multi-frame stack traces that look like genuine production issues — not contrived `raise Exception()` calls.

All unhandled exceptions flow through Flask's `@app.errorhandler(Exception)`, which returns a JSON response containing the error type, message, and full traceback. Any BugStack middleware installed on the Flask app will capture these errors automatically.
