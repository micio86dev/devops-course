"""E2E fixtures: live Flask server (session-scoped) and TodoPage POM."""
import threading
import pytest
from werkzeug.serving import make_server

from app import app as flask_app


# ── Page Object Model ─────────────────────────────────────────────────────────

class TodoPage:
    """Encapsulates every interaction with the todo UI.

    All actions are fire-and-forget; assertions belong in the tests.
    """

    def __init__(self, page, base_url: str) -> None:
        self._page = page
        self._base_url = base_url

    # navigation

    def goto(self) -> "TodoPage":
        self._page.goto(self._base_url)
        self._page.wait_for_selector("#todo-list")
        return self

    def reload(self) -> "TodoPage":
        self._page.reload()
        self._page.wait_for_selector("#todo-list")
        return self

    # actions

    def add(self, text: str, *, via: str = "enter") -> None:
        """Fill the input and submit via Enter (default) or ADD button.

        For non-empty text, waits until JS clears the input after the POST
        completes. This prevents race conditions when chaining multiple adds.
        """
        self._page.fill("#new-todo", text)
        if via == "button":
            self._page.click(".add-btn")
        else:
            self._page.press("#new-todo", "Enter")
        if text.strip():
            self._page.wait_for_function(
                "() => document.getElementById('new-todo').value === ''"
            )

    def toggle(self, index: int = 0) -> None:
        """Click the checkbox of the todo at the given list index."""
        self.items.nth(index).locator(".check").click()

    def delete(self, index: int = 0) -> None:
        """Hover a row to reveal the delete button, then click it."""
        item = self.items.nth(index)
        item.hover()
        item.locator(".del-btn").click()

    # locators (lazy — evaluated on access, never stale)

    @property
    def items(self):
        return self._page.locator(".todo-item")

    @property
    def empty_state(self):
        return self._page.locator(".empty")

    @property
    def input(self):
        return self._page.locator("#new-todo")

    @property
    def title(self):
        return self._page.locator("h1")

    @property
    def add_button(self):
        return self._page.locator(".add-btn")

    def stat(self, name: str):
        """Return the locator for a stats counter: 'total', 'done', or 'left'."""
        return self._page.locator(f"#stat-{name}")

    @property
    def stats(self) -> dict[str, int]:
        """Snapshot of all three counters as integers (no auto-wait)."""
        return {
            "total": int(self._page.locator("#stat-total").text_content()),
            "done":  int(self._page.locator("#stat-done").text_content()),
            "left":  int(self._page.locator("#stat-left").text_content()),
        }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def live_server_url():
    """Start Flask once for the entire E2E session on a free OS-assigned port."""
    server = make_server("127.0.0.1", 0, flask_app)
    port = server.socket.getsockname()[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def todo_page(page, live_server_url):
    """Navigate to the app home page and return a ready-to-use TodoPage."""
    return TodoPage(page, live_server_url).goto()
