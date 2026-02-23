"""
Data models for the BugBoy task management application.
"""
import json
import threading
import time


class User:
    """Represents a user in the system."""

    def __init__(self, user_id, name, email, role="member"):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role
        self.preferences = None
        self.last_name = None

    def get_display_name(self):
        # Bug: last_name is None — str + None → TypeError
        return self.name + " " + self.last_name

    def get_notification_settings(self):
        # Bug: preferences is a dict without a 'notifications' key → KeyError
        return self.preferences["notifications"]


class Task:
    """Represents a task/ticket in the project board."""

    def __init__(self, task_id, title, description, assignee=None, tags=None, priority=1):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.assignee = assignee
        self.tags = tags or []
        self.priority = priority
        self.comments = []
        self.history = []

    def get_latest_comment(self):
        return self.comments[-1]

    def get_tag(self, index):
        return self.tags[index]

    def to_dict(self):
        return {
            "id": self.task_id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee.name if self.assignee else None,
            "tags": self.tags,
            "priority": self.priority,
        }


class Project:
    """Represents a project containing tasks."""

    def __init__(self, project_id, name, owner):
        self.project_id = project_id
        self.name = name
        self.owner = owner
        self.tasks = []
        self.members = []
        self.settings = {}

    def get_task_by_id(self, task_id):
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def calculate_completion_rate(self):
        completed = len([t for t in self.tasks if t.priority == 0])
        return completed / len(self.tasks) * 100

    def get_config_value(self, key):
        return self.settings[key]


class NotificationQueue:
    """Background notification processing queue."""

    def __init__(self):
        self.queue = []
        self._lock = threading.Lock()

    def enqueue(self, notification):
        with self._lock:
            self.queue.append(notification)

    def process_in_background(self, handler):
        thread = threading.Thread(
            target=self._process_queue,
            args=(handler,),
            daemon=True,
        )
        thread.start()
        return thread

    def _process_queue(self, handler):
        # Simulate processing delay
        time.sleep(0.1)
        for notification in self.queue:
            handler(notification)


class CategoryTree:
    """Hierarchical category structure for tasks."""

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []

    def add_child(self, name):
        child = CategoryTree(name, parent=self)
        self.children.append(child)
        return child

    def get_full_path(self):
        if self.parent is None:
            return self.name
        return self.parent.get_full_path() + " > " + self.name

    def find_category(self, name):
        if self.name == name:
            return self
        for child in self.children:
            result = child.find_category(name)
            if result:
                return result
        return None

    def flatten(self):
        """Flatten the tree into a list - but with a circular reference bug."""
        result = [self.name]
        for child in self.children:
            result.extend(child.flatten())
        return result


class APIResponse:
    """Wrapper around external API responses."""

    def __init__(self, raw_body, status_code=200):
        self.raw_body = raw_body
        self.status_code = status_code
        self._parsed = None

    def json(self):
        if self._parsed is None:
            self._parsed = json.loads(self.raw_body)
        return self._parsed

    def get_field(self, field_name):
        data = self.json()
        return data[field_name]
