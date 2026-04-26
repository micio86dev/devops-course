"""End-to-end tests for the todo UI — Playwright + pytest-playwright.

Test isolation is guaranteed by the `clean_db` autouse fixture defined in
tests/conftest.py: it deletes all rows before every test so each scenario
starts from an empty database.

Ordering note: the API returns todos newest-first (ORDER BY created_at DESC),
so the most recently added item is always at index 0.
"""
import re
from playwright.sync_api import expect


# ── Page load ─────────────────────────────────────────────────────────────────

class TestPageLoad:
    """The page renders correctly with an empty database."""

    def test_title_is_visible(self, todo_page):
        expect(todo_page.title).to_be_visible()

    def test_title_contains_todo(self, todo_page):
        expect(todo_page.title).to_contain_text("todo")

    def test_input_is_visible_and_empty(self, todo_page):
        expect(todo_page.input).to_be_visible()
        expect(todo_page.input).to_have_value("")

    def test_add_button_is_visible(self, todo_page):
        expect(todo_page.add_button).to_be_visible()

    def test_empty_state_is_shown(self, todo_page):
        expect(todo_page.empty_state).to_be_visible()

    def test_stats_start_at_zero(self, todo_page):
        expect(todo_page.stat("total")).to_have_text("0")
        expect(todo_page.stat("done")).to_have_text("0")
        expect(todo_page.stat("left")).to_have_text("0")


# ── Add todo ──────────────────────────────────────────────────────────────────

class TestAddTodo:

    def test_add_via_enter_key(self, todo_page):
        todo_page.add("Buy milk")
        expect(todo_page.items.first).to_contain_text("Buy milk")

    def test_add_via_add_button(self, todo_page):
        todo_page.add("Buy eggs", via="button")
        expect(todo_page.items.first).to_contain_text("Buy eggs")

    def test_input_is_cleared_after_add(self, todo_page):
        todo_page.add("Some task")
        expect(todo_page.items.first).to_be_visible()  # wait for render
        expect(todo_page.input).to_have_value("")

    def test_empty_state_disappears_after_first_add(self, todo_page):
        todo_page.add("First ever task")
        expect(todo_page.empty_state).not_to_be_visible()

    def test_empty_input_does_not_add(self, todo_page):
        todo_page._page.press("#new-todo", "Enter")
        expect(todo_page.empty_state).to_be_visible()
        expect(todo_page.items).to_have_count(0)

    def test_whitespace_only_does_not_add(self, todo_page):
        todo_page.add("   ")
        expect(todo_page.empty_state).to_be_visible()
        expect(todo_page.items).to_have_count(0)

    def test_multiple_todos_all_appear(self, todo_page):
        for text in ("Alpha", "Beta", "Gamma"):
            todo_page.add(text)
        expect(todo_page.items).to_have_count(3)

    def test_newest_todo_appears_first(self, todo_page):
        todo_page.add("Older")
        todo_page.add("Newer")
        expect(todo_page.items).to_have_count(2)
        expect(todo_page.items.first).to_contain_text("Newer")
        expect(todo_page.items.nth(1)).to_contain_text("Older")

    def test_stats_update_after_add(self, todo_page):
        todo_page.add("Task A")
        todo_page.add("Task B")
        expect(todo_page.items).to_have_count(2)
        expect(todo_page.stat("total")).to_have_text("2")
        expect(todo_page.stat("done")).to_have_text("0")
        expect(todo_page.stat("left")).to_have_text("2")


# ── Toggle todo ───────────────────────────────────────────────────────────────

class TestToggleTodo:

    def test_toggle_adds_done_class(self, todo_page):
        todo_page.add("Complete me")
        todo_page.toggle(0)
        expect(todo_page.items.first).to_have_class(re.compile(r"\bdone\b"))

    def test_done_item_shows_checkmark(self, todo_page):
        todo_page.add("Check me")
        todo_page.toggle(0)
        expect(todo_page.items.first.locator(".check")).to_have_text("✓")

    def test_done_text_has_line_through(self, todo_page):
        todo_page.add("Strike me")
        todo_page.toggle(0)
        expect(todo_page.items.first).to_have_class(re.compile(r"\bdone\b"))
        expect(todo_page.items.first.locator(".todo-text")).to_have_css(
            "text-decoration-line", "line-through"
        )

    def test_toggle_twice_removes_done_class(self, todo_page):
        todo_page.add("Toggle me twice")
        todo_page.toggle(0)  # → done
        todo_page.toggle(0)  # → not done
        expect(todo_page.items.first).not_to_have_class(re.compile(r"\bdone\b"))

    def test_toggle_twice_clears_checkmark(self, todo_page):
        todo_page.add("Toggle twice")
        todo_page.toggle(0)
        todo_page.toggle(0)
        expect(todo_page.items.first.locator(".check")).to_have_text("")

    def test_toggle_increments_done_stat(self, todo_page):
        todo_page.add("Task 1")
        todo_page.add("Task 2")
        expect(todo_page.items).to_have_count(2)
        todo_page.toggle(0)
        expect(todo_page.stat("done")).to_have_text("1")
        expect(todo_page.stat("left")).to_have_text("1")

    def test_untoggle_decrements_done_stat(self, todo_page):
        todo_page.add("Task")
        expect(todo_page.items).to_have_count(1)
        todo_page.toggle(0)  # done → 1
        todo_page.toggle(0)  # done → 0
        expect(todo_page.stat("done")).to_have_text("0")
        expect(todo_page.stat("left")).to_have_text("1")

    def test_toggle_does_not_change_total(self, todo_page):
        todo_page.add("Task")
        expect(todo_page.items).to_have_count(1)
        todo_page.toggle(0)
        expect(todo_page.stat("total")).to_have_text("1")


# ── Delete todo ───────────────────────────────────────────────────────────────

class TestDeleteTodo:

    def test_delete_removes_item(self, todo_page):
        todo_page.add("Delete me")
        todo_page.delete(0)
        expect(todo_page.items).to_have_count(0)

    def test_empty_state_returns_after_last_delete(self, todo_page):
        todo_page.add("Last item")
        todo_page.delete(0)
        expect(todo_page.empty_state).to_be_visible()

    def test_only_target_item_is_deleted(self, todo_page):
        todo_page.add("Keep me")
        todo_page.add("Delete me")   # index 0 (newest first)
        expect(todo_page.items).to_have_count(2)
        todo_page.delete(0)
        expect(todo_page.items).to_have_count(1)
        expect(todo_page.items.first).to_contain_text("Keep me")

    def test_delete_decrements_total_stat(self, todo_page):
        todo_page.add("Task 1")
        todo_page.add("Task 2")
        expect(todo_page.items).to_have_count(2)
        todo_page.delete(0)
        expect(todo_page.stat("total")).to_have_text("1")

    def test_delete_done_item_updates_all_stats(self, todo_page):
        todo_page.add("Done task")
        todo_page.toggle(0)
        expect(todo_page.stat("done")).to_have_text("1")
        todo_page.delete(0)
        expect(todo_page.stat("total")).to_have_text("0")
        expect(todo_page.stat("done")).to_have_text("0")
        expect(todo_page.stat("left")).to_have_text("0")


# ── XSS protection ────────────────────────────────────────────────────────────

class TestXSS:

    def test_html_tags_are_displayed_as_literal_text(self, todo_page):
        payload = "<b>bold</b>"
        todo_page.add(payload)
        expect(todo_page.items.first.locator(".todo-text")).to_have_text(payload)

    def test_script_tag_is_not_executed(self, todo_page):
        payload = "<script>window.__xss = true</script>"
        todo_page.add(payload)
        expect(todo_page.items.first).to_be_visible()
        result = todo_page._page.evaluate("() => window.__xss")
        assert result is None

    def test_ampersand_and_angle_brackets_are_escaped(self, todo_page):
        payload = "a & b > c < d"
        todo_page.add(payload)
        expect(todo_page.items.first.locator(".todo-text")).to_have_text(payload)


# ── Persistence ───────────────────────────────────────────────────────────────

class TestPersistence:

    def test_todo_survives_page_reload(self, todo_page):
        todo_page.add("Persistent task")
        todo_page.reload()
        expect(todo_page.items.first).to_contain_text("Persistent task")

    def test_done_state_survives_page_reload(self, todo_page):
        todo_page.add("Complete and reload")
        todo_page.toggle(0)
        todo_page.reload()
        expect(todo_page.items.first).to_have_class(re.compile(r"\bdone\b"))

    def test_deleted_todo_does_not_return_after_reload(self, todo_page):
        todo_page.add("Add then delete")
        todo_page.delete(0)
        todo_page.reload()
        expect(todo_page.empty_state).to_be_visible()
