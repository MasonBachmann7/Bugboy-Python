"""
BugBoy Python — A realistic Flask application with intentionally embedded
runtime errors for testing BugStack's Python SDK.

Run with:  python app.py
"""
import os
import sys
import traceback
import threading

from flask import Flask, request, jsonify, render_template
import bugstack

import services
import utils
import bugstack
import os

app = Flask(__name__)

bugstack.init(
    api_key=os.environ.get("BUGSTACK_API_KEY", ""),
    endpoint=os.environ.get("BUGSTACK_ENDPOINT", "https://bugstack-error-service.onrender.com/api/capture"),
    debug=True,
)


# BugStack error monitoring
bugstack.init(
    api_key=os.environ.get("BUGSTACK_API_KEY", ""),
)

# ── Bug Registry ─────────────────────────────────────────────────────────────
# Every triggerable bug is registered here so the dashboard can list them.

BUGS = [
    {
        "id": "type-error",
        "name": "TypeError",
        "route": "/trigger/type-error",
        "method": "GET",
        "description": "Format a user's full display name — fails because "
                       "last_name is None (can't concatenate str and NoneType).",
        "category": "TypeError",
    },
    {
        "id": "key-error",
        "name": "KeyError",
        "route": "/trigger/key-error",
        "method": "GET",
        "description": "Load notification settings for a user whose preferences "
                       "dict is missing the 'notifications' key.",
        "category": "KeyError / AttributeError",
    },
    {
        "id": "attribute-error",
        "name": "AttributeError",
        "route": "/trigger/attribute-error",
        "method": "GET",
        "description": "Look up the assignee's email for an unassigned task — "
                       "accessing .email on None raises AttributeError.",
        "category": "AttributeError",
    },
    {
        "id": "zero-division",
        "name": "ZeroDivisionError",
        "route": "/trigger/zero-division",
        "method": "GET",
        "description": "Generate a velocity report where sprint_length_days "
                       "defaults to 0, causing division by zero.",
        "category": "ZeroDivisionError",
    },
    {
        "id": "index-error",
        "name": "IndexError",
        "route": "/trigger/index-error",
        "method": "GET",
        "description": "Retrieve the latest comment on a task that has no "
                       "comments — list index out of range.",
        "category": "IndexError",
    },
    {
        "id": "file-not-found",
        "name": "FileNotFoundError",
        "route": "/trigger/file-not-found",
        "method": "GET",
        "description": "Load a project config file from disk that doesn't exist.",
        "category": "FileNotFoundError",
    },
    {
        "id": "json-decode-error",
        "name": "JSONDecodeError",
        "route": "/trigger/json-decode-error",
        "method": "GET",
        "description": "Parse a webhook response from a third-party service "
                       "that returns malformed JSON.",
        "category": "JSONDecodeError",
    },
    {
        "id": "unicode-decode-error",
        "name": "UnicodeDecodeError",
        "route": "/trigger/unicode-decode-error",
        "method": "POST",
        "description": "Process an incoming webhook payload containing "
                       "invalid UTF-8 byte sequences.",
        "category": "UnicodeDecodeError",
    },
    {
        "id": "recursion-error",
        "name": "RecursionError",
        "route": "/trigger/recursion-error",
        "method": "GET",
        "description": "Flatten a category tree that has an accidental "
                       "circular parent→child reference.",
        "category": "RecursionError",
    },
    {
        "id": "connection-error",
        "name": "ConnectionError",
        "route": "/trigger/connection-error",
        "method": "GET",
        "description": "Attempt to connect to an internal database host "
                       "that is unreachable.",
        "category": "ConnectionError",
    },
    {
        "id": "value-error",
        "name": "ValueError",
        "route": "/trigger/value-error",
        "method": "POST",
        "description": "Import tasks from CSV where the priority column "
                       "contains a non-numeric string.",
        "category": "ValueError",
    },
    {
        "id": "permission-error",
        "name": "PermissionError",
        "route": "/trigger/permission-error",
        "method": "GET",
        "description": "Export project data to a file that was locked "
                       "read-only by a previous backup job.",
        "category": "PermissionError",
    },
    {
        "id": "timeout-error",
        "name": "TimeoutError",
        "route": "/trigger/timeout-error",
        "method": "GET",
        "description": "Run a slow aggregation query that exceeds the "
                       "configured timeout threshold.",
        "category": "TimeoutError",
    },
    {
        "id": "thread-error",
        "name": "Unhandled Thread Exception",
        "route": "/trigger/thread-error",
        "method": "GET",
        "description": "Fire a background notification job whose handler "
                       "crashes — exception surfaces via threading.excepthook.",
        "category": "Unhandled Thread Exception",
    },
    {
        "id": "memory-error",
        "name": "MemoryError",
        "route": "/trigger/memory-error",
        "method": "POST",
        "description": "Submit an extremely large bulk-import payload that "
                       "causes excessive memory consumption.",
        "category": "MemoryError",
    },
]


# ── Capture unhandled thread exceptions ──────────────────────────────────────
# Store the last background-thread exception so we can surface it.

_last_thread_error = {"error": None, "traceback": None}
_original_excepthook = threading.excepthook


def _thread_excepthook(args):
    _last_thread_error["error"] = args.exc_value
    # Python 3.14 renamed exc_tb → tb
    tb = getattr(args, "exc_tb", None) or getattr(args, "tb", None)
    _last_thread_error["traceback"] = "".join(
        traceback.format_exception(args.exc_type, args.exc_value, tb)
    )
    # Also call the original hook so it still prints to stderr
    if _original_excepthook:
        _original_excepthook(args)


threading.excepthook = _thread_excepthook


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html", bugs=BUGS)


@app.route("/api/bugs")
def list_bugs():
    """JSON endpoint listing all triggerable bugs."""
    return jsonify(BUGS)


# ── Bug trigger routes ───────────────────────────────────────────────────────

@app.route("/trigger/type-error")
def trigger_type_error():
    """GET /trigger/type-error
    Scenario: Formatting a user's full display name.
    Bug: User.last_name is None — str concatenation with None raises TypeError.
    """
    user_id = request.args.get("user_id", 2, type=int)
    display_name = services.get_user_display_name(user_id)
    return jsonify({"display_name": display_name})


@app.route("/trigger/key-error")
def trigger_key_error():
    """GET /trigger/key-error
    Scenario: Loading notification settings for a user.
    Bug: The preferences dict doesn't contain a 'notifications' key.
    """
    user_id = request.args.get("user_id", 1, type=int)
    settings = services.get_user_notifications(user_id)
    return jsonify({"notifications": settings})


@app.route("/trigger/attribute-error")
def trigger_attribute_error():
    """GET /trigger/attribute-error
    Scenario: Looking up the assignee's email for a task notification.
    Bug: TASK-103 has no assignee (None) — accessing .email on None.
    """
    email = services.get_task_assignee_email("proj-1", "TASK-103")
    return jsonify({"assignee_email": email})


@app.route("/trigger/zero-division")
def trigger_zero_division():
    """GET /trigger/zero-division
    Scenario: Generating a sprint velocity report.
    Bug: sprint_length_days defaults to 0 when not configured.
    """
    sprint_points = request.args.get("points", 42, type=int)
    report = services.generate_velocity_report("proj-1", sprint_points)
    return jsonify(report)


@app.route("/trigger/index-error")
def trigger_index_error():
    """GET /trigger/index-error
    Scenario: Fetching the latest comment on a task.
    Bug: The task has no comments — accessing [-1] on an empty list.
    """
    comment = services.get_latest_comment("proj-1", "TASK-101")
    return jsonify({"latest_comment": comment})


@app.route("/trigger/file-not-found")
def trigger_file_not_found():
    """GET /trigger/file-not-found
    Scenario: Loading project-specific configuration from disk.
    Bug: The config file was never created / deployed.
    """
    config = services.load_project_config("proj-1")
    return jsonify(config)


@app.route("/trigger/json-decode-error")
def trigger_json_decode_error():
    """GET /trigger/json-decode-error
    Scenario: Parsing a webhook payload from a third-party service.
    Bug: The 'webhook' service returns JSON with an unquoted key.
    """
    service = request.args.get("service", "webhook")
    data = services.fetch_integration_data(service)
    return jsonify(data)


@app.route("/trigger/unicode-decode-error", methods=["POST"])
def trigger_unicode_decode_error():
    """POST /trigger/unicode-decode-error
    Scenario: Ingesting a webhook from an external system.
    Bug: Payload contains invalid UTF-8 bytes.
    """
    # Simulate receiving raw bytes with bad encoding
    bad_payload = b'{"user": "M\xfcller", "action": "login"}'
    result = services.parse_incoming_webhook(bad_payload)
    return jsonify(result)


@app.route("/trigger/recursion-error")
def trigger_recursion_error():
    """GET /trigger/recursion-error
    Scenario: Flattening the task category tree for a dropdown.
    Bug: A circular reference causes infinite recursion.
    """
    original_limit = utils.set_recursion_limit_for_deep_trees()
    try:
        categories = services.build_recursive_categories()
        return jsonify({"categories": categories})
    finally:
        utils.restore_recursion_limit(original_limit)


@app.route("/trigger/connection-error")
def trigger_connection_error():
    """GET /trigger/connection-error
    Scenario: Connecting to the project database on startup.
    Bug: The database host is unreachable (DNS or firewall).
    """
    services.connect_to_database(host="db.internal.local", port=5432, timeout=2)
    return jsonify({"status": "connected"})


@app.route("/trigger/value-error", methods=["POST"])
def trigger_value_error():
    """POST /trigger/value-error
    Scenario: Importing tasks from a CSV upload.
    Bug: The priority column contains 'high' instead of a number.
    """
    csv_data = request.data.decode("utf-8") if request.data else None
    if not csv_data:
        csv_data = "title,description,priority\nFix login,Users can't log in,high\nUpdate docs,Add API examples,2"
    tasks = services.import_tasks_from_csv(csv_data)
    return jsonify({"imported": len(tasks), "tasks": tasks})


@app.route("/trigger/permission-error")
def trigger_permission_error():
    """GET /trigger/permission-error
    Scenario: Exporting project data for backup.
    Bug: Previous export was locked read-only by a backup cron job.
    """
    project = services._projects.get("proj-1")
    task_data = [t.to_dict() for t in project.tasks]
    path = services.write_export_file("proj-1", task_data)
    return jsonify({"exported_to": path})


@app.route("/trigger/timeout-error")
def trigger_timeout_error():
    """GET /trigger/timeout-error
    Scenario: Running a slow analytics aggregation query.
    Bug: The query takes 10 s but the timeout is 2 s.
    """
    result = services.run_with_timeout(services.slow_aggregation_query, timeout_sec=2)
    return jsonify(result)


@app.route("/trigger/thread-error")
def trigger_thread_error():
    """GET /trigger/thread-error
    Scenario: Firing a background notification after a task update.
    Bug: The notification handler tries to format a template with missing keys.
    """
    _last_thread_error["error"] = None
    _last_thread_error["traceback"] = None

    thread = services.process_notifications_async(user_id=1, event_type="task_assigned")
    thread.join(timeout=5)

    if _last_thread_error["error"]:
        # Re-raise the background error in the request context so BugStack
        # can capture it with full context
        raise _last_thread_error["error"]

    return jsonify({"status": "notification sent"})


@app.route("/trigger/memory-error", methods=["POST"])
def trigger_memory_error():
    """POST /trigger/memory-error
    Scenario: Bulk-importing a huge dataset.
    Bug: The import builds an O(n²) cross-reference index in memory.
    """
    count = request.args.get("count", 500_000, type=int)
    items = utils.generate_large_payload(count)
    result = services.process_bulk_import(items)
    return jsonify(result)


# ── Healthcheck ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "bugboy-python"})


# ── Error handler (lets errors propagate naturally for BugStack) ─────────────

@app.errorhandler(Exception)
def handle_exception(e):
    """Capture the error with BugStack, then return a JSON error response."""
    bugstack.capture_exception(e)
    tb = traceback.format_exc()
    app.logger.error("Unhandled exception:\n%s", tb)
    return jsonify({
        "error": type(e).__name__,
        "message": str(e),
        "traceback": tb,
    }), 500


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("BugBoy Python is running at http://127.0.0.1:5000")
    print(f"  {len(BUGS)} bugs ready to trigger\n")
    app.run(debug=True, port=5000)
