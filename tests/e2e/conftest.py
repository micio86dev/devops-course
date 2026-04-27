"""E2E fixtures: live Flask server (session-scoped) and TodoPage POM."""

import threading
from collections.abc import Generator

import pytest
from playwright.sync_api import Locator, Page
from werkzeug.serving import make_server

from app.app import app as flask_app

# ── Page Object Model ─────────────────────────────────────────────────────────


class TodoPage:
    """Encapsulates every interaction with the todo UI.

    All locators use data-testid attributes — never CSS classes or UI text —
    so tests are decoupled from visual design and copy changes.
    All actions are fire-and-forget; assertions belong in the tests.
    """

    def __init__(self, page: Page, base_url: str) -> None:
        self._page = page
        self._base_url = base_url

    # navigation

    def goto(self) -> "TodoPage":
        self._page.goto(self._base_url)
        self._page.get_by_test_id("todo-list").wait_for()
        return self

    def reload(self) -> "TodoPage":
        self._page.reload()
        self._page.get_by_test_id("todo-list").wait_for()
        return self

    # actions

    def add(self, text: str, *, via: str = "enter") -> None:
        """Fill the input and submit via Enter (default) or ADD button.

        For non-empty text, waits until JS clears the input after the POST
        completes. This prevents race conditions when chaining multiple adds.
        """
        self._page.get_by_test_id("new-todo").fill(text)
        if via == "button":
            self._page.get_by_test_id("add-btn").click()
        else:
            self._page.get_by_test_id("new-todo").press("Enter")
        if text.strip():
            self._page.wait_for_function("() => document.getElementById('new-todo').value === ''")

    def toggle(self, index: int = 0) -> None:
        """Click the checkbox of the todo at the given list index."""
        self.items.nth(index).get_by_test_id("todo-check").click()

    def delete(self, index: int = 0) -> None:
        """Hover a row to reveal the delete button, then click it."""
        item = self.items.nth(index)
        item.hover()
        item.get_by_test_id("todo-delete").click()

    # locators (lazy — evaluated on access, never stale)

    @property
    def items(self) -> Locator:
        return self._page.get_by_test_id("todo-item")

    @property
    def empty_state(self) -> Locator:
        return self._page.get_by_test_id("empty-state")

    @property
    def input(self) -> Locator:
        return self._page.get_by_test_id("new-todo")

    @property
    def title(self) -> Locator:
        return self._page.get_by_test_id("app-title")

    @property
    def add_button(self) -> Locator:
        return self._page.get_by_test_id("add-btn")

    def stat(self, name: str) -> Locator:
        """Return the locator for a stats counter: 'total', 'done', or 'left'."""
        return self._page.get_by_test_id(f"stat-{name}")

    @property
    def stats(self) -> dict[str, int]:
        """Snapshot of all three counters as integers (no auto-wait)."""
        return {
            "total": int(self._page.get_by_test_id("stat-total").text_content() or "0"),
            "done": int(self._page.get_by_test_id("stat-done").text_content() or "0"),
            "left": int(self._page.get_by_test_id("stat-left").text_content() or "0"),
        }


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    """Start Flask once for the entire E2E session on a free OS-assigned port."""
    server = make_server("127.0.0.1", 0, flask_app)
    port = server.socket.getsockname()[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def todo_page(page: Page, live_server_url: str) -> TodoPage:
    """Navigate to the app home page and return a ready-to-use TodoPage."""
    return TodoPage(page, live_server_url).goto()
