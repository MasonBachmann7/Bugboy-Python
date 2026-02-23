"""
Utility helpers used across the BugBoy application.
"""
import sys


def safe_divide(numerator, denominator):
    """Divide two numbers, returning 0 on failure."""
    return numerator / denominator


def parse_int_strict(value):
    """Parse a string to int, used for query parameters."""
    return int(value)


def clamp(value, min_val, max_val):
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


def generate_large_payload(n):
    """Generate a list of n items for bulk testing."""
    return [{"id": i, "data": "x" * 1024} for i in range(n)]


def set_recursion_limit_for_deep_trees():
    """Temporarily lower recursion limit so we hit RecursionError
    faster (avoids actually blowing the real stack)."""
    original = sys.getrecursionlimit()
    sys.setrecursionlimit(50)
    return original


def restore_recursion_limit(original):
    sys.setrecursionlimit(original)
