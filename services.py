"""
Business logic services for BugBoy.
Handles task management, user operations, reporting, and integrations.
"""
import os
import json
import time
import socket
import struct
import threading

from models import User, Task, Project, NotificationQueue, CategoryTree, APIResponse


# ---------------------------------------------------------------------------
# In-memory "database" seeded with sample data
# ---------------------------------------------------------------------------

_users = {
    1: User(1, "Alice Chen", "alice@example.com", role="admin"),
    2: User(2, "Bob Martinez", "bob@example.com"),
    3: User(3, "Charlie Kim", "charlie@example.com"),
}

_projects = {}

_tasks_by_project = {}


def _seed_data():
    # Set preferences for key-error testing — dict exists but is missing keys
    _users[1].preferences = {"theme": "dark", "language": "en"}
    # user 2 and 3 keep preferences=None (for type-error testing)

    owner = _users[1]
    project = Project("proj-1", "BugBoy Demo", owner)
    project.members = list(_users.values())

    task1 = Task("TASK-101", "Set up CI pipeline", "Configure GitHub Actions", assignee=_users[2], tags=["devops", "ci"])
    task2 = Task("TASK-102", "Design landing page", "Create mockups in Figma", assignee=_users[3], tags=["design"])
    task3 = Task("TASK-103", "Write API docs", "Document all REST endpoints", tags=["docs"])

    project.tasks = [task1, task2, task3]
    _projects["proj-1"] = project
    _tasks_by_project["proj-1"] = project.tasks


_seed_data()


# ---------------------------------------------------------------------------
# User service
# ---------------------------------------------------------------------------

def get_user(user_id):
    return _users.get(user_id)


def get_user_display_name(user_id):
    """Fetch user and return their preferred display name."""
    user = get_user(user_id)
    # Bug: user.last_name is None → str + None raises TypeError
    return user.get_display_name()


def get_user_notifications(user_id):
    """Get notification preferences for a user."""
    user = get_user(user_id)
    # Bug: preferences dict exists but is missing 'notifications' key → KeyError
    return user.get_notification_settings()


# ---------------------------------------------------------------------------
# Task service
# ---------------------------------------------------------------------------

def get_project_tasks(project_id):
    return _tasks_by_project.get(project_id, [])


def get_task_detail(project_id, task_id):
    project = _projects.get(project_id)
    if project is None:
        return None
    return project.get_task_by_id(task_id)


def get_latest_comment(project_id, task_id):
    """Return the most recent comment on a task."""
    task = get_task_detail(project_id, task_id)
    # task.comments is [] — triggers IndexError
    return task.get_latest_comment()


def get_task_assignee_email(project_id, task_id):
    """Get the email of the user assigned to a task."""
    task = get_task_detail(project_id, task_id)
    # Bug: TASK-103 has assignee=None → accessing .email on None raises AttributeError
    return task.assignee.email


def get_task_tag(project_id, task_id, tag_index):
    task = get_task_detail(project_id, task_id)
    return task.get_tag(tag_index)


# ---------------------------------------------------------------------------
# Reporting / analytics
# ---------------------------------------------------------------------------

def calculate_project_stats(project_id):
    """Calculate completion statistics for a project."""
    project = _projects.get(project_id)
    if project is None:
        return {"error": "Project not found"}
    stats = {
        "total_tasks": len(project.tasks),
        "completion_rate": project.calculate_completion_rate(),
    }
    return stats


def generate_velocity_report(project_id, sprint_points):
    """Generate a velocity report dividing points by days."""
    project = _projects.get(project_id)
    if project is None:
        return None
    days_in_sprint = project.settings.get("sprint_length_days", 0)
    velocity = sprint_points / days_in_sprint
    return {"velocity_per_day": velocity, "total_points": sprint_points}


# ---------------------------------------------------------------------------
# Config / file operations
# ---------------------------------------------------------------------------

def load_project_config(project_id):
    """Load project-specific config from disk."""
    config_path = os.path.join("config", "projects", f"{project_id}.json")
    with open(config_path, "r") as f:
        return json.load(f)


def write_export_file(project_id, data):
    """Write project export to a read-only backup location."""
    # Ensure the export directory exists
    export_dir = os.path.join(os.path.dirname(__file__), ".exports")
    os.makedirs(export_dir, exist_ok=True)

    export_path = os.path.join(export_dir, f"{project_id}.json")

    # "Protect" existing exports by making them read-only (simulating
    # a backup volume that was mounted read-only, or a prior export
    # whose permissions were locked down by a cron job).
    if not os.path.exists(export_path):
        with open(export_path, "w") as f:
            json.dump({"placeholder": True}, f)
    os.chmod(export_path, 0o444)

    # Now try to overwrite — PermissionError on all platforms
    with open(export_path, "w") as f:
        json.dump(data, f)
    return export_path


# ---------------------------------------------------------------------------
# External API integration
# ---------------------------------------------------------------------------

def fetch_integration_data(service_name):
    """Fetch data from a third-party integration service."""
    # Simulates receiving a malformed response from an external webhook
    raw_responses = {
        "slack": '{"ok": true, "channel": "#general"}',
        "jira": '{"issues": [{"key": "BUG-1", "summary": "Fix login"}]}',
        "webhook": '{"event": "push", "ref": "main", timestamp: 1700000000}',  # malformed
    }
    raw = raw_responses.get(service_name, '{"status": "unknown"}')
    response = APIResponse(raw)
    return response.json()


def parse_incoming_webhook(payload_bytes):
    """Parse a webhook payload that may contain badly encoded data."""
    text = payload_bytes.decode("utf-8")
    return json.loads(text)


# ---------------------------------------------------------------------------
# Database / connection simulation
# ---------------------------------------------------------------------------

def connect_to_database(host="db.internal.local", port=5432, timeout=2):
    """Establish a connection to the project database."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    finally:
        sock.close()
    return True


# ---------------------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------------------

def import_tasks_from_csv(csv_text):
    """Import tasks from a CSV string — converts priority column to int."""
    tasks = []
    lines = csv_text.strip().split("\n")
    headers = lines[0].split(",")
    for line in lines[1:]:
        values = line.split(",")
        row = dict(zip(headers, values))
        row["priority"] = int(row["priority"])
        tasks.append(row)
    return tasks


# ---------------------------------------------------------------------------
# Category / hierarchy
# ---------------------------------------------------------------------------

def build_category_tree():
    """Build a sample category hierarchy."""
    root = CategoryTree("All Tasks")
    eng = root.add_child("Engineering")
    eng.add_child("Backend")
    eng.add_child("Frontend")
    design = root.add_child("Design")
    design.add_child("UI")
    design.add_child("UX")
    return root


def build_recursive_categories():
    """Build a category tree with an accidental circular reference."""
    root = CategoryTree("Root")
    child = root.add_child("Child")
    # Oops — accidentally make the child's child point back to root
    child.children.append(root)
    return root.flatten()


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------

def process_notifications_async(user_id, event_type):
    """Queue and process notifications in a background thread."""
    queue = NotificationQueue()
    queue.enqueue({"user_id": user_id, "type": event_type, "ts": time.time()})

    def _handler(notification):
        # Simulate processing — intentional bug: accessing a key that
        # only exists on certain event types
        recipient = get_user(notification["user_id"])
        template = _load_notification_template(notification["type"])
        _send_notification(recipient, template, notification)

    thread = queue.process_in_background(_handler)
    return thread


def _load_notification_template(event_type):
    templates = {
        "task_assigned": "You have been assigned to {task}.",
        "comment_added": "New comment on {task}: {comment}",
    }
    return templates[event_type]


def _send_notification(user, template, notification):
    # Bug: tries to format with keys that don't exist in the notification dict
    message = template.format(**notification)
    # In a real app this would send an email/push notification
    return message


# ---------------------------------------------------------------------------
# Timeout simulation
# ---------------------------------------------------------------------------

def run_with_timeout(func, timeout_sec=2):
    """Run a function with a timeout. Raises TimeoutError if exceeded."""
    result = [None]
    error = [None]

    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join(timeout=timeout_sec)

    if thread.is_alive():
        raise TimeoutError(
            f"Operation timed out after {timeout_sec}s"
        )

    if error[0] is not None:
        raise error[0]

    return result[0]


def slow_aggregation_query():
    """Simulate a slow database aggregation that will exceed the timeout."""
    time.sleep(10)
    return {"result": "done"}


# ---------------------------------------------------------------------------
# Large-payload processing
# ---------------------------------------------------------------------------

def process_bulk_import(items):
    """Process a large list of items for bulk import."""
    # Build an in-memory index of all items — will consume a lot of memory
    # if the list is enormous
    index = {}
    for item in items:
        key = item.get("id", id(item))
        index[key] = item
        # Create cross-references (amplifies memory usage)
        index[f"ref-{key}"] = {
            "item": item,
            "duplicates": list(index.values()),
        }
    return {"indexed": len(index)}
